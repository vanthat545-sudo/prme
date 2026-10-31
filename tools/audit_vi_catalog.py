#!/usr/bin/env python3
"""Audit completeness and format safety of the AI Video Vietnamese UI catalog.

This is a structural check: it cannot certify the quality of machine translation
or labels hardcoded outside the locale catalog.
"""
from pathlib import Path
import collections, json, re, sys, zipfile

def parse(text, label):
    out={}
    failures=[]
    for n,line in enumerate(text.splitlines(),1):
        if line.startswith("#") or not line.strip():continue
        cols=line.split("\t")
        if len(cols)!=3 or not cols[1] or not cols[2]:
            failures.append(f"{label} line {n}: malformed tab-separated row")
            continue
        k=(cols[0],cols[1])
        if k in out:failures.append(f"{label} line {n}: duplicate {k!r}")
        out[k]=cols[2]
    return out,failures

def placeholders(value):
    return sorted(re.findall(r"\{([^{}]+)\}",value))

def audit():
    archive=Path("filmcraft-main.zip")
    path="filmcraft-main/crates/ui-egui/src/i18n/es.tsv"
    with zipfile.ZipFile(archive) as z:
        source,src_errors=parse(z.read(path).decode("utf8"),"source")
    dest=Path("translations/vi.tsv")
    if not dest.is_file():
        raise SystemExit("FAIL: full Vietnamese translations/vi.tsv not yet available")
    translated,tr_errors=parse(dest.read_text("utf8"),"Vietnamese")
    missing=[k for k in source if k not in translated]
    extra=[k for k in translated if k not in source]
    bad=[]
    identical=[]
    quality_flags=[]
    for k,v in translated.items():
        if k not in source:continue
        original=k[1]
        if placeholders(original)!=placeholders(v):bad.append({"key":original,"reason":"placeholder mismatch"})
        if original.endswith("…")!=v.endswith("…"):bad.append({"key":original,"reason":"ellipsis mismatch"})
        if original==v: identical.append(original)
        # A machine-generated line can be formatted correctly yet completely unusable.
        # Reject runaway repetitions and unnatural length explosions before releasing.
        if len(v)>max(190,len(original)*3+95):
            quality_flags.append({"key":original,"reason":"abnormally long translation","translation":v[:160]})
        tokens=re.findall(r"[\wÀ-ỹ]+",v.lower())
        if any(tokens[i]==tokens[i+1]==tokens[i+2]==tokens[i+3] for i in range(max(0,len(tokens)-3))):
            quality_flags.append({"key":original,"reason":"repeated word loop","translation":v[:160]})
        if v.count("&")>=3:
            quality_flags.append({"key":original,"reason":"stray ampersand sequence","translation":v[:160]})
    report={
       "source_entries":len(source),"vietnamese_entries":len(translated),
       "missing_entries":len(missing),"unknown_entries":len(extra),
       "format_errors":len(src_errors)+len(tr_errors)+len(bad),
       "same_english_vietnamese_count":len(identical),
       "machine_translation_quality_flags":len(quality_flags),
       "quality_samples":quality_flags[:35],
       "examples_missing":[k[1] for k in missing[:25]],
       "examples_untranslated":[k for k in identical[:25]],
       "errors":(src_errors+tr_errors)[:30]+bad[:30],
       "qa_note":"No missing keys does NOT establish correct Vietnamese or translate hardcoded UI labels."
    }
    print(json.dumps(report,ensure_ascii=False,indent=2))
    Path("translation-audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if missing or extra or src_errors or tr_errors or bad or quality_flags:
        raise SystemExit("FAIL: Vietnamese catalog has missing keys, format errors or machine-translation quality failures")
if __name__=="__main__":
    audit()
