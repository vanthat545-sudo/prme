#!/usr/bin/env python3
"""Fill missing FilmCraft English->Vietnamese UI catalog entries with an Apache-2.0 Marian model.

Preserve source keys, formatting placeholders, escaped newlines, string context and
existing human-curated translations. Translate only UI text; never touch engine/CLI code.
Machine translations require human linguistic QA before stable release.
"""
import collections
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

MODEL="Helsinki-NLP/opus-mt-en-vi"
PLACEHOLDER=re.compile(r"(\{[^{}]+\}|\\n|\\t)")
def split_parts(value):
    return PLACEHOLDER.split(value)
def is_meta(part):
    return bool(PLACEHOLDER.fullmatch(part))
def en_has_words(s):
    return bool(re.search(r"[a-zA-Z]{2,}",s))
def safe_ellipsis(src, translated):
    if src.endswith("…"):
        return translated.rstrip(" .…")+"…"
    if translated.endswith("…") and not src.endswith("…"):
        return translated.rstrip("…")
    return translated
def clean_translation(raw,original):
    v=raw.strip().replace("\n"," ").replace("\r"," ").replace("\t"," ")
    if not v:return original
    if re.search("filmcraft",v,re.I):v=re.sub("(?i)filmcraft","AI Video",v)
    # Keep a readable technical label unchanged if the model has no useful equivalent.
    return v

def main(archive):
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    torch.set_num_threads(2)
    z=zipfile.ZipFile(archive)
    base="filmcraft-main/crates/ui-egui/src/i18n/"
    source=z.read(base+"es.tsv").decode("utf-8").splitlines()
    existing=z.read(base+"vi.tsv").decode("utf-8").splitlines()
    records=[]
    for line in source:
        if line.startswith("#") or not line.strip():continue
        cols=line.split("\t")
        if len(cols)==3: records.append((cols[0],cols[1]))
    curated={}
    for line in existing:
        if line.startswith("#") or not line.strip():continue
        parts=line.split("\t")
        if len(parts)==3:curated[(parts[0],parts[1])]=parts[2]
    print(f"Catalog total={len(records)} curated={len(curated)}",flush=True)
    to_translate=[]
    for key in records:
        if key in curated:continue
        parts=split_parts(key[1])
        for part in parts:
            if part and not is_meta(part) and en_has_words(part):
                norm=part.strip()
                if norm and norm not in to_translate:to_translate.append(norm)
    print("Unique English segments:",len(to_translate),flush=True)
    tokenizer=MarianTokenizer.from_pretrained(MODEL)
    model=MarianMTModel.from_pretrained(MODEL)
    model.eval()
    mapped={}
    BATCH=24
    with torch.no_grad():
        for i in range(0,len(to_translate),BATCH):
            batch=to_translate[i:i+BATCH]
            inputs=tokenizer(batch,return_tensors="pt",padding=True,truncation=True,max_length=160)
            output=model.generate(**inputs,num_beams=2,max_length=192,early_stopping=True)
            translations=tokenizer.batch_decode(output,skip_special_tokens=True)
            for en,vi in zip(batch,translations):
                mapped[en]=clean_translation(vi,en)
            if i % (BATCH*25)==0:print("translated",min(i+BATCH,len(to_translate)),"/",len(to_translate),flush=True)
    machine={}; failures=[]
    for key in records:
        if key in curated: continue
        src=key[1]
        parts=split_parts(src)
        output=[]
        for p in parts:
            if is_meta(p):output.append(p)
            elif p and en_has_words(p):
                tr=mapped.get(p.strip(),p.strip())
                left=p[:len(p)-len(p.lstrip())]; right=p[len(p.rstrip()):]
                output.append(left+tr+right)
            else: output.append(p)
        vi=safe_ellipsis(src,"".join(output))
        if not vi.strip():vi=src
        if sorted(re.findall(r"\{([^{}]+)\}",vi)) != sorted(re.findall(r"\{([^{}]+)\}",src)):
            failures.append(key);continue
        vi=vi.replace("\n",r"\n").replace("\t",r"\t")
        if "\t" in vi or "\n" in vi: failures.append(key);continue
        machine[key]=vi
    if len(failures)>10:raise RuntimeError(f"Too many placeholder or format failures: {failures[:12]}")
    header=["# Vietnamese (vi) — AI Video UI translation catalog.",
            "# Curated entries retained. Remaining entries were machine translated with "+MODEL+".",
            "# Human review is required before calling the localization production-ready.",
            "# Product names and technical formats may remain untranslated."]
    rows=header.copy()
    for ctx,en in records:
        vi=curated.get((ctx,en),machine.get((ctx,en),en))
        if en.endswith("…") and not vi.endswith("…"):vi=vi.rstrip(". ")+"…"
        elif not en.endswith("…") and vi.endswith("…"):vi=vi.rstrip("…")
        rows.append("\t".join((ctx,en,vi)))
    output=Path("translations/vi.tsv")
    output.parent.mkdir(exist_ok=True)
    output.write_text("\n".join(rows)+"\n",encoding="utf-8")
    report={"model":MODEL,"total":len(records),"curated":len(curated),"machine_translated":len(machine),"remaining_uncertain":len(failures),
      "coverage_keys":len(rows)-len(header),"source_sha256":hashlib.sha256(z.read(base+"es.tsv")).hexdigest(),
      "status":"MACHINE DRAFT — requires Vietnamese proofreading and functional UI verification"}
    Path("translations/vi-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    assert len(records)==len(set(records)),"Catalog has duplicate keys"
    assert len(machine)+len(curated)+len(failures)==len(records)
if __name__=="__main__":
    main(Path(sys.argv[1]))
