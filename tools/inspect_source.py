import zipfile, re, pathlib
with zipfile.ZipFile("filmcraft-main.zip") as z:
    files=[x for x in z.namelist() if x.startswith("filmcraft-main/") and not x.endswith("/")]
    chosen=[
"crates/ui-egui/src/i18n/mod.rs",
"crates/ui-egui/src/i18n/catalog.rs",
"crates/ui-egui/src/i18n/ja.tsv",
"crates/ui-egui/src/i18n/fr.tsv",
"crates/ui-egui/src/brand.rs",
"apps/filmcraft/src/main.rs",
"apps/filmcraft-web/web/index.html",
"packaging/macos/Info.plist.in",
"packaging/macos/package.sh",
"crates/ui-egui/src/menus.rs",
"crates/ui-egui/src/state.rs",
"crates/ui-egui/src/credits.rs",
"apps/filmcraft/build.rs",
"assets/app-icon/README.md",
]
    for name in chosen:
        p="filmcraft-main/"+name
        if p not in files:continue
        s=z.read(p).decode("utf8","replace"); lines=s.splitlines()
        print("=== FILE",name,"LINES",len(lines),"BYTES",len(s),"===")
        if name.endswith(".tsv"):
            print("SAMPLE",repr(lines[:20]))
            print("TOTAL",len(lines))
        elif name.endswith("package.sh"):
            for i,l in enumerate(lines):
                if i<18 or i>95 and i<135 or "DMG" in l or "CFBundle" in l: print(str(i+1)+": "+l[:300])
        elif name.endswith("main.rs") and name.startswith("apps/"):
            for i,l in enumerate(lines):
                if i<35 or re.search("FilmCraft|filmcraft-macos|icon|window_title|title|Window",l,re.I):print(str(i+1)+": "+l[:250])
        elif name.endswith("state.rs"):
            for i,l in enumerate(lines):
                if re.search("language|locale|System|English|Settings",l,re.I):print(str(i+1)+": "+l[:250])
        elif name.endswith("menus.rs"):
            for i,l in enumerate(lines):
                if re.search("Language|Japanese|English|German|Français|Italian|Portugu|locale|i18n|Language",l,re.I):print(str(i+1)+": "+l[:250])
        else:
            print(s[:19000])
    print("=== UI STRING COUNTS BY FILE ===")
    for p in files:
        if p.startswith("filmcraft-main/crates/ui-egui/src/") and p.endswith(".rs"):
            s=z.read(p).decode("utf8","replace")
            hits=len(re.findall(r"\b(?:tl|tlf)!\s*\(",s))
            if hits>0: print(hits,p)
