#!/usr/bin/env python3
"""Rebrand FilmCraft presentation as AI Video without renaming engine crates or APIs.
Only UI/packaging, font-safe artwork, and translation catalogs are modified.
Original uploaded ZIP is never changed.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ARCHIVE = ROOT / "filmcraft-main.zip"
OUT = ROOT / "build"
SRC = OUT / "filmcraft-main"
ASSETS = ROOT / "branding"

# Translation memory for the most common editing commands, panels and status labels.
# Incomplete keys intentionally retain their English fallback, never a guessed translation.
GLOSSARY = {
    "File":"Tệp","Edit":"Chỉnh sửa","View":"Hiển thị","Window":"Cửa sổ","Help":"Trợ giúp",
    "Tools":"Công cụ","Settings":"Cài đặt","Preferences":"Tùy chọn","Project":"Dự án",
    "Sequence":"Chuỗi dựng","Clip":"Đoạn video","Media":"Tư liệu","Audio":"Âm thanh",
    "Video":"Video","Text":"Văn bản","Effects":"Hiệu ứng","Effect":"Hiệu ứng",
    "Transitions":"Chuyển cảnh","Transition":"Chuyển cảnh","Export":"Xuất video",
    "Import":"Nhập","Render":"Kết xuất","Preview":"Xem trước","Timeline":"Dòng thời gian",
    "Inspector":"Bảng thuộc tính","Properties":"Thuộc tính","Color":"Màu sắc",
    "Color Correction":"Chỉnh màu","Color Grading":"Phân màu","Filters":"Bộ lọc",
    "Presets":"Bộ thiết lập","Preset":"Thiết lập sẵn","Captions":"Phụ đề",
    "Subtitles":"Phụ đề","Titles":"Tiêu đề","Tracks":"Các rãnh","Track":"Rãnh",
    "New":"Mới","Open":"Mở","Save":"Lưu","Save As…":"Lưu thành…",
    "Save As":"Lưu thành","Close":"Đóng","Quit":"Thoát","Exit":"Thoát",
    "Undo":"Hoàn tác","Redo":"Làm lại","Cut":"Cắt","Copy":"Sao chép",
    "Paste":"Dán","Delete":"Xóa","Remove":"Gỡ bỏ","Duplicate":"Nhân bản",
    "Select All":"Chọn tất cả","Select None":"Bỏ chọn","Cancel":"Hủy",
    "OK":"Đồng ý","Apply":"Áp dụng","Reset":"Đặt lại","Done":"Xong",
    "Continue":"Tiếp tục","Back":"Quay lại","Next":"Tiếp theo",
    "Search":"Tìm kiếm","Refresh":"Làm mới","Browse":"Duyệt",
    "Start":"Bắt đầu","Stop":"Dừng","Pause":"Tạm dừng","Play":"Phát",
    "Record":"Ghi âm","Recording":"Đang ghi","Mute":"Tắt tiếng",
    "Unmute":"Bật tiếng","Volume":"Âm lượng","Gain":"Mức khuếch đại",
    "Speed":"Tốc độ","Duration":"Thời lượng","Position":"Vị trí",
    "Scale":"Tỷ lệ","Rotation":"Xoay","Opacity":"Độ mờ",
    "Width":"Chiều rộng","Height":"Chiều cao","Resolution":"Độ phân giải",
    "Frame Rate":"Tốc độ khung hình","Format":"Định dạng","Quality":"Chất lượng",
    "High":"Cao","Medium":"Trung bình","Low":"Thấp","Auto":"Tự động",
    "Automatic":"Tự động","Custom":"Tùy chỉnh","Default":"Mặc định",
    "None":"Không có","All":"Tất cả","On":"Bật","Off":"Tắt",
    "Enabled":"Đã bật","Disabled":"Đã tắt","Show":"Hiện","Hide":"Ẩn",
    "Add":"Thêm","New Project":"Dự án mới","Open Project":"Mở dự án",
    "Recent Projects":"Dự án gần đây","Create Project":"Tạo dự án",
    "Save Project":"Lưu dự án","Import Media":"Nhập tư liệu",
    "Export Video":"Xuất video","Export Settings":"Cài đặt xuất",
    "Export Frame":"Xuất khung hình","Export Audio":"Xuất âm thanh",
    "Export Project":"Xuất dự án","New Sequence":"Tạo chuỗi dựng",
    "Sequence Settings":"Cài đặt chuỗi dựng","Project Settings":"Cài đặt dự án",
    "Audio Effects":"Hiệu ứng âm thanh","Video Effects":"Hiệu ứng video",
    "Effect Controls":"Điều khiển hiệu ứng","Audio Mixer":"Bộ trộn âm thanh",
    "Video Track":"Rãnh video","Audio Track":"Rãnh âm thanh",
    "New Track":"Thêm rãnh","Add Track":"Thêm rãnh","Delete Track":"Xóa rãnh",
    "Split Clip":"Tách đoạn video","Trim":"Cắt xén","Ripple Delete":"Xóa dồn",
    "Zoom In":"Phóng to","Zoom Out":"Thu nhỏ","Zoom":"Thu phóng",
    "Fit":"Vừa khung","Fit to Window":"Vừa cửa sổ","Fullscreen":"Toàn màn hình",
    "Full Screen":"Toàn màn hình","Home":"Trang chủ","Welcome":"Chào mừng",
    "Getting Started":"Bắt đầu sử dụng","About":"Giới thiệu",
    "About FilmCraft":"Giới thiệu AI Video","FilmCraft Project":"Dự án AI Video",
    "FilmCraft":"AI Video","Language":"Ngôn ngữ","System Language":"Ngôn ngữ hệ thống",
    "Interface Language":"Ngôn ngữ giao diện","English":"Tiếng Anh",
    "Japanese":"Tiếng Nhật","Vietnamese":"Tiếng Việt","Tiếng Việt":"Tiếng Việt",
    "Keyboard Shortcuts":"Phím tắt","Shortcuts":"Phím tắt",
    "General":"Chung","Appearance":"Giao diện","Advanced":"Nâng cao",
    "Update":"Cập nhật","Check for Updates":"Kiểm tra cập nhật",
    "Updates":"Cập nhật","Documentation":"Tài liệu","Support":"Hỗ trợ",
    "New File":"Tệp mới","Open File":"Mở tệp","Save File":"Lưu tệp",
    "File Name":"Tên tệp","Folder":"Thư mục","Choose Folder":"Chọn thư mục",
    "Destination":"Vị trí lưu","Source":"Nguồn","Output":"Đầu ra",
    "Output File":"Tệp đầu ra","Progress":"Tiến độ",
    "Working…":"Đang xử lý…","Loading…":"Đang tải…","Saving…":"Đang lưu…",
    "Exporting…":"Đang xuất video…","Rendering…":"Đang kết xuất…",
    "Importing…":"Đang nhập…","Ready":"Sẵn sàng","Error":"Lỗi",
    "Warning":"Cảnh báo","Success":"Thành công","Failed":"Thất bại",
    "Retry":"Thử lại","Details":"Chi tiết","Status":"Trạng thái",
    "Name":"Tên","Type":"Loại","Size":"Kích thước",
    "Date":"Ngày","Time":"Thời gian","Start Time":"Thời điểm bắt đầu",
    "End Time":"Thời điểm kết thúc","In Point":"Điểm vào","Out Point":"Điểm ra",
    "Markers":"Điểm đánh dấu","Marker":"Điểm đánh dấu","Add Marker":"Thêm điểm đánh dấu",
    "Delete Marker":"Xóa điểm đánh dấu","Show All":"Hiện tất cả",
    "Hide All":"Ẩn tất cả","Refresh Media":"Làm mới tư liệu",
    "Source Monitor":"Màn hình nguồn","Program Monitor":"Màn hình chương trình",
    "Reference Monitor":"Màn hình tham chiếu","History":"Lịch sử",
    "Transcript":"Bản chép lời","Transcription":"Chuyển giọng nói thành văn bản",
    "Voice-over":"Thuyết minh","Voiceover":"Thuyết minh","Text to Speech":"Văn bản thành giọng nói",
    "Speech to Text":"Giọng nói thành văn bản","Speech":"Giọng nói",
    "Stabilization":"Ổn định hình ảnh","Noise Reduction":"Giảm nhiễu",
    "Sharpen":"Làm nét","Blur":"Làm mờ","Brightness":"Độ sáng",
    "Contrast":"Độ tương phản","Saturation":"Độ bão hòa",
    "Exposure":"Phơi sáng","Highlights":"Vùng sáng","Shadows":"Vùng tối",
    "White Balance":"Cân bằng trắng","Temperature":"Nhiệt độ màu",
    "Hue":"Sắc độ","Vibrance":"Độ rực màu","Levels":"Mức sáng",
    "Mask":"Mặt nạ","Masks":"Mặt nạ","Transform":"Biến đổi",
    "Crop":"Cắt khung","Flip":"Lật","Horizontal":"Ngang","Vertical":"Dọc",
    "Left":"Trái","Right":"Phải","Top":"Trên","Bottom":"Dưới",
    "Center":"Giữa","Align":"Căn chỉnh","Animation":"Hoạt ảnh",
    "Keyframe":"Khung hình khóa","Keyframes":"Khung hình khóa",
    "Effects Browser":"Thư viện hiệu ứng","Media Browser":"Thư viện tư liệu",
    "Add Media":"Thêm tư liệu","Remove Media":"Gỡ tư liệu",
    "Playhead":"Con trỏ phát","Ripple Edit":"Dựng dồn",
    "Preferences…":"Tùy chọn…","Settings…":"Cài đặt…",
    "About FilmCraft…":"Giới thiệu AI Video…",
    "Open…":"Mở…","Save…":"Lưu…","Import…":"Nhập…","Export…":"Xuất…",
    "Delete…":"Xóa…","Cancel Export":"Hủy xuất video",
}

def replacement(file, old: str, new: str, required=True) -> None:
    path=SRC/file
    txt=path.read_text(encoding="utf-8")
    if old not in txt:
        if required: raise RuntimeError(f"Missing expected text in {file}: {old[:90]}")
        return
    path.write_text(txt.replace(old,new),encoding="utf-8")

def make_translation(source: Path, output: Path):
    rows=source.read_text("utf-8").splitlines()
    covered=0; total=0
    out=["# Tiếng Việt cho AI Video. Nguồn chuỗi gốc: es.tsv của FilmCraft.",
         "# Chỉ dịch mục đã kiểm chứng về thuật ngữ; các mục chưa có bản dịch giữ nguyên tiếng Anh.",
         "# Format: context<TAB>English source<TAB>Vietnamese translation."]
    for line in rows:
        if line.startswith("#") or not line.strip():continue
        cols=line.split("\t")
        if len(cols)!=3:continue
        context,en,_=cols
        total+=1
        tr=GLOSSARY.get(en)
        if not tr:
            match=re.fullmatch(r"(Add|Remove|Delete|Show|Hide|Open|Save|Import|Export|New) (.+)",en)
            if match and match[2] in GLOSSARY:
                verb=GLOSSARY.get(match[1])
                tr=f"{verb} {GLOSSARY[match[2]].lower()}"
        if not tr and en.startswith("FilmCraft"):
            tr=en.replace("FilmCraft","AI Video")
        if not tr: continue
        # Exact placeholder and ending-punctuation rules of catalog tests.
        ph=lambda t: sorted(re.findall(r"\{([^{}]+)\}",t))
        if ph(tr)!=ph(en):continue
        if en.endswith("…")!=tr.endswith("…"):
            if en.endswith("…"):tr=tr.rstrip(". ")+"…"
            else:continue
        tr=tr.replace("\n",r"\n").replace("\t",r"\t")
        out.append("\t".join((context,en,tr)))
        covered+=1
    output.write_text("\n".join(out)+"\n",encoding="utf-8")
    return total,covered

def modify_i18n():
    mod=Path("crates/ui-egui/src/i18n/mod.rs")
    replacement(mod,"    En,\n    Ja,","    En,\n    Vi,\n    Ja,")
    replacement(mod,"static JAPANESE: OnceLock<Catalog>","static VIETNAMESE: OnceLock<Catalog> = OnceLock::new();\nstatic JAPANESE: OnceLock<Catalog>")
    replacement(mod,"pub const ALL: [Self; 12] = [Self::En,","pub const ALL: [Self; 13] = [Self::En, Self::Vi,")
    # Keep existing defaults and old locale behavior in all engines. Vietnam selection is explicit in state.
    replacement(mod,'Self::En => "en",','Self::En => "en",\n            Self::Vi => "vi",')
    replacement(mod,'Self::En => "English",','Self::En => "English",\n            Self::Vi => "Tiếng Việt",')
    replacement(mod,'"en" => Some(Self::En),','"en" => Some(Self::En),\n            "vi" => Some(Self::Vi),')
    replacement(mod,"const PRIMARY: [(&str, Language); 12]","const PRIMARY: [(&str, Language); 13]")
    replacement(mod,'("en", Language::En),','("en", Language::En),\n            ("vi", Language::Vi),')
    replacement(mod,"Self::En => None,","Self::En => None,\n            Self::Vi => Some(VIETNAMESE.get_or_init(|| Catalog::parse(include_str!(\"vi.tsv\")))),")
    replacement(mod,"Language::En => None,","Language::En => None,\n            Language::Vi => Some(include_str!(\"vi.tsv\")),")
    # Add a proper Vietnamese menu option and handling (IDs, not label text, are stable).
    menus=Path("crates/ui-egui/src/menus.rs")
    replacement(menus,'uic!("app.language.english", "English", ["Edit", "Language"], None),',
                'uic!("app.language.english", "English", ["Edit", "Language"], None),\n    uic!("app.language.vietnamese", "Tiếng Việt", ["Edit", "Language"], None),')
    replacement(menus,'"app.language.english"\n', '"app.language.english"\n            | "app.language.vietnamese"\n')
    replacement(menus,'"app.language.japanese" => crate::i18n::Language::Ja,',
                '"app.language.vietnamese" => crate::i18n::Language::Vi,\n            "app.language.japanese" => crate::i18n::Language::Ja,')
    replacement(menus,'"app.language.english" => it.checked = Some(app.ui.language == crate::i18n::Language::En),',
                '"app.language.english" => it.checked = Some(app.ui.language == crate::i18n::Language::En),\n            "app.language.vietnamese" => it.checked = Some(app.ui.language == crate::i18n::Language::Vi),')
    replacement(Path("crates/ui-egui/src/state.rs"),"language: crate::i18n::Language::default(),",
                "language: crate::i18n::Language::Vi,")
    keys=SRC/"crates/ui-egui/src/i18n"
    total,covered=make_translation(keys/"es.tsv",keys/"vi.tsv")
    return total,covered

def svg_assets():
    import cairosvg
    from PIL import Image
    icon_svg=ASSETS/"ai-video-icon.svg"
    cover_svg=ASSETS/"ai-video-cover.svg"
    ai_icon=cairosvg.svg2png(url=str(icon_svg),output_width=1024,output_height=1024)
    icon=Image.open(io.BytesIO(ai_icon)).convert("RGBA")
    asset=SRC/"assets/app-icon"
    icon.save(asset/"filmcraft-1024.png")
    icon.resize((512,512),Image.Resampling.LANCZOS).save(asset/"filmcraft-macos-512.png")
    icon.save(asset/"hicolor/256x256/apps/ai.storyteller.filmcraft.png")
    # Regenerate every existing size; do not rename Linux internal icon IDs.
    for p in (asset/"hicolor").rglob("ai.storyteller.filmcraft.png"):
        w=int(p.parent.parent.name.split("x")[0])
        icon.resize((w,w),Image.Resampling.LANCZOS).save(p)
    ico=icon.resize((256,256),Image.Resampling.LANCZOS)
    ico.save(asset/"filmcraft.ico",format="ICO",sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    # macOS iconset has its own transparent margin: 80% tile, center.
    iconset=OUT/"ai-video.iconset"
    iconset.mkdir(exist_ok=True)
    for pt in [16,32,128,256,512]:
        for scale in [1,2]:
            pixels=pt*scale
            canvas=Image.new("RGBA",(pixels,pixels),(0,0,0,0))
            inset=round(pixels*.07)
            tile=icon.resize((pixels-inset*2,pixels-inset*2),Image.Resampling.LANCZOS)
            canvas.paste(tile,(inset,inset),tile)
            tag=f"icon_{pt}x{pt}"+("@2x" if scale==2 else "")+".png"
            canvas.save(iconset/tag)
    if shutil.which("iconutil"):
        subprocess.run(["iconutil","-c","icns",str(iconset),"-o",str(asset/"filmcraft.icns")],check=True)
    else:
        print("WARNING: iconutil unavailable; keeping original .icns, build on macOS to update it.")
    cover_data=cairosvg.svg2png(url=str(cover_svg),output_width=1600,output_height=560)
    cover=Image.open(io.BytesIO(cover_data)).convert("RGBA")
    (OUT/"AI-Video-cover.png").write_bytes(cover_data)
    (OUT/"AI-Video-icon.png").write_bytes(ai_icon)
    # Home/About wordmark now uses AI Video branding instead of ArtCraft wordmark.
    brandpath=SRC/"docs/brand/ai-video-wordmark.png"
    cover.save(brandpath)
    replacement(Path("crates/ui-egui/src/brand.rs"),"../../../docs/brand/artcraft-logo-white.png","../../../docs/brand/ai-video-wordmark.png")
    replacement(Path("crates/ui-egui/src/brand.rs"),"../../../docs/brand/artcraft-logo.png","../../../docs/brand/ai-video-wordmark.png")
    # Use new backdrop in DMG Finder window; retains existing layout metadata until regenerate.
    bg=cover.resize((660,400),Image.Resampling.LANCZOS).convert("RGB")
    bg.save(SRC/"packaging/macos/dmg/background.tiff",format="TIFF")
    (SRC/"packaging/macos/dmg/background.svg").write_bytes(cover_svg.read_bytes())
    icon.resize((128,128),Image.Resampling.LANCZOS).save(SRC/"apps/filmcraft-web/web/favicon.png")
    return bool(shutil.which("iconutil"))

def modify_brand():
    replacement(Path("apps/filmcraft/src/main.rs"),'run_native("FilmCraft",','run_native("AI Video",')
    replacement(Path("apps/filmcraft/src/main.rs"),'.with_title("FilmCraft")','.with_title("AI Video")')
    replacement(Path("apps/filmcraft/src/main.rs"),'.set_title("FilmCraft")','.set_title("AI Video")')
    replacement(Path("apps/filmcraft/src/main.rs"),'"FilmCraft could not start its window:','"AI Video không thể mở cửa sổ:') 
    replacement(Path("apps/filmcraft/build.rs"),'.set("ProductName", "FilmCraft")','.set("ProductName", "AI Video")')
    replacement(Path("apps/filmcraft/build.rs"),'.set("FileDescription", "FilmCraft video editor")','.set("FileDescription", "AI Video - Trình chỉnh sửa video")')
    plist=Path("packaging/macos/Info.plist.in")
    replacement(plist,"<key>CFBundleDevelopmentRegion</key>\n  <string>en</string>","<key>CFBundleDevelopmentRegion</key>\n  <string>vi</string>")
    for key in ("CFBundleDisplayName","CFBundleName"):
        replacement(plist,f"<key>{key}</key>\n  <string>FilmCraft</string>",f"<key>{key}</key>\n  <string>AI Video</string>")
    replacement(plist,"FilmCraft uses the microphone to record voice-over onto the timeline.",
                "AI Video sử dụng micro để ghi lời thuyết minh vào dòng thời gian.")
    replacement(plist,"<key>CFBundleIdentifier</key>\n  <string>ai.storyteller.filmcraft</string>",
                "<key>CFBundleIdentifier</key>\n  <string>com.aivideo.editor</string>")
    # Retain original engine executable and .fcproj UTType to preserve project compatibility.
    pkg=Path("packaging/macos/package.sh")
    replacement(pkg,'APP="$WORK/FilmCraft.app"','APP="$WORK/AI Video.app"')
    replacement(pkg,'ditto "$APP" "$STAGE/FilmCraft.app"','ditto "$APP" "$STAGE/AI Video.app"')
    replacement(pkg,'DMG="$DIST/filmcraft-$VERSION-macos-$ARCH.dmg"','DMG="$DIST/AI-Video-$VERSION-macos-$ARCH.dmg"')
    replacement(Path("packaging/macos/dmg/generate.py"),'VOLUME = "FilmCraft"','VOLUME = "AI Video"')
    replacement(Path("packaging/macos/dmg/generate.py"),'"FilmCraft.app":','"AI Video.app":')
    index=Path("apps/filmcraft-web/web/index.html")
    replacement(index,'<html lang="en">','<html lang="vi">')
    replacement(index,'<title>FilmCraft</title>','<title>AI Video</title>')
    replacement(index,'Loading FilmCraft…','Đang tải AI Video…')
    replacement(index,'FilmCraft stopped working','AI Video đã gặp lỗi')
    replacement(index,'Unsaved changes are kept in the browser every few seconds and come back when you reload.',
                'Các thay đổi chưa lưu được lưu tạm trong trình duyệt và có thể khôi phục khi tải lại.')
    replacement(index,'>Reload</button>','>Tải lại</button>')
    replacement(index,'FilmCraft failed to start:', 'AI Video không thể khởi động:')
    # Old internal executable name, CLI, import formats, config keys and automation IDs are not touched.

def archive():
    name=OUT/"AI-Video-v0.13.0-Vietnamese-Source.zip"
    with zipfile.ZipFile(name,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(SRC.rglob("*")):
            if p.is_file(): z.write(p, p.relative_to(OUT))
    return name

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    with zipfile.ZipFile(SOURCE_ARCHIVE) as z:
        for m in z.infolist():
            p=Path(m.filename)
            if not p.parts or p.parts[0]!="filmcraft-main":continue
            if ".." in p.parts or p.is_absolute(): raise ValueError("unsafe zip member")
            if m.is_dir():continue
            dest=OUT/p
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(z.read(m))
    if not (SRC/"Cargo.toml").exists(): raise RuntimeError("Source archive missing Cargo.toml")
    # Protected engine bytes allow a strong regression check: no engine files are edited.
    protected=list((SRC/"crates/engine").rglob("*"))+list((SRC/"crates/render").rglob("*"))+list((SRC/"crates/export").rglob("*"))
    protected=[p for p in protected if p.is_file()]
    before={str(p.relative_to(SRC)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    total,covered=modify_i18n()
    modify_brand()
    icon_native=svg_assets()
    after={str(p.relative_to(SRC)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    assert before==after,"Core video engine was modified!"
    # Confirm original project format is still registered.
    plist=(SRC/"packaging/macos/Info.plist.in").read_text()
    assert "fcproj" in plist and "ai.storyteller.filmcraft.project" in plist
    assert "AI Video" in plist
    assert (SRC/"assets/app-icon/filmcraft.icns").exists()
    import plistlib
    # Info.plist.in contains @VERSION@ placeholders, but is otherwise valid XML.
    plistlib.loads(plist.replace("@VERSION@","0.13.0").replace("@SHORT_VERSION@","0.13.0").replace("@BUILD_SHA@","source").encode())
    from PIL import Image
    for p in ["assets/app-icon/filmcraft-macos-512.png","apps/filmcraft-web/web/favicon.png"]:
        with Image.open(SRC/p) as img:img.verify()
    report={
        "branding":"AI Video","source_version":"FilmCraft 0.13.0",
        "translation_catalog_source":total,"translation_catalog_translated":covered,
        "translation_coverage_percent":round(100*covered/total,2) if total else 0,
        "source_engine_files_preserved":len(protected),
        "macos_icon_regenerated":icon_native,
        "status":"TEST ONLY — source package; translation incomplete; no signed app generated",
        "note":"Core engine/codecs/format IDs preserved; untranslated UI strings still fall back to English."
    }
    (OUT/"REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    bundle=archive()
    print(json.dumps({**report,"output":str(bundle),"bytes":bundle.stat().st_size},ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
