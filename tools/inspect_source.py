import zipfile, re, pathlib, collections
with zipfile.ZipFile("filmcraft-main.zip") as z:
    paths=[n for n in z.namelist() if not n.startswith("__MACOSX/") and not n.endswith("/")]
    focus=[n for n in paths if n.startswith(("filmcraft-main/apps/","filmcraft-main/packaging/macos/","filmcraft-main/assets/app-icon/","filmcraft-main/docs/brand/")) or (n.startswith("filmcraft-main/crates/ui-egui/src/") and n.count("/")<=5)]
    print("=== FOCUSED TREE ===")
    for x in focus[:350]:print(x)
    print("=== LOCALE RELATED ===")
    names=[p for p in paths if re.search("i18n|local|lang|translat|strings|vi[_-]vn|vietnam|font",p,re.I)]
    for n in names[:140]:print(n)
    print("=== USER VISIBLE BRAND AND LOCALIZATION ===")
    found=0
    for p in paths:
        if not(p.endswith((".rs",".toml",".sh",".plist",".md",".json",".yml",".svg",".py"))):continue
        if not(p.startswith(("filmcraft-main/crates/ui-egui/","filmcraft-main/apps/","filmcraft-main/packaging/macos/","filmcraft-main/assets/app-icon/"))):continue
        try: text=z.read(p).decode("utf-8")
        except:continue
        lines=text.splitlines()
        hits=[(i+1,line.strip()) for i,line in enumerate(lines) if re.search(r'FilmCraft|filmcraft|tr\!\(|localiz|locale|Language|English|Deutsch|Français|Menu|Home|Title|Window|window_title|icon',line,re.I)]
        if not hits:continue
        print(f"### {p} LINES={len(lines)} HITS={len(hits)}")
        for i,line in hits[:12]: print(f"{i}: {line[:230]}")
        found+=1
        if found>=48:break
    print("=== KEY FILE PREVIEWS ===")
    patterns=["filmcraft-main/Cargo.toml","filmcraft-main/crates/ui-egui/Cargo.toml"]
    patterns +=[p for p in paths if p.startswith("filmcraft-main/packaging/macos/") and p.endswith((".sh",".plist",".py"))][:6]
    patterns +=[p for p in paths if p.startswith("filmcraft-main/crates/ui-egui/src/") and re.search(r"app.rs|main.rs|lib.rs|locale|i18n|localization",p,re.I)][:6]
    for p in patterns[:16]:
        if p not in paths: continue
        print("###",p)
        contents=z.read(p).decode("utf-8","replace")
        print(contents[:5500])
