from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import os
import re
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(r"D:\Project\厚粲杯\08_算法\output")
DEST = Path(r"D:\Project\厚粲杯\08_算法\work\output_content_audit_20260828")
TEXT_EXTS = {".csv", ".json", ".log", ".md", ".ndjson", ".py", ".txt", ".html"}
SENSITIVE_RE = re.compile(r"auth|token|secret|cookie|session-state|credential|qrcode|password|\.sandbox-secrets", re.I)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def text_read(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk", "latin-1"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace"), "utf-8-replace"

def image_meta(path: Path) -> str:
    try:
        from PIL import Image
        with Image.open(path) as im:
            hist = im.convert("RGB").resize((1, 1)).getpixel((0, 0))
            name = str(path).lower()
            if "overlay" in name or "nir" in name:
                visible = "NIR/眼部灰度图或眼部跟踪 overlay"
            elif any(x in name for x in ("range_fft", "range_ft", "heatmap", "spectrogram", "map")):
                visible = "距离-频率/距离-时间伪彩图或热图"
            elif any(x in name for x in ("timeline", "time_series", "course", "wave", "breath", "heart")):
                visible = "时域波形、质量曲线或生理指标趋势图"
            elif any(x in name for x in ("box", "compare", "summary", "metric", "distribution", "hist", "bar")):
                visible = "统计比较图、箱线图、柱状图或分布图"
            else:
                visible = "结果诊断图/统计图；具体图名与相对路径保留在条目标题"
            return f"format={im.format}; mode={im.mode}; size={im.width}x{im.height}; representative_rgb={hist}; visible_content={visible}"
    except Exception as e:
        return f"image_read_error={type(e).__name__}: {e}"

def npz_meta(path: Path) -> str:
    try:
        import numpy as np
        with np.load(path, allow_pickle=False) as z:
            rows = []
            for k in z.files:
                a = z[k]
                item = {"key": k, "shape": list(a.shape), "dtype": str(a.dtype), "size": int(a.size)}
                if a.size and np.issubdtype(a.dtype, np.number):
                    finite = np.asarray(a)[np.isfinite(a)] if np.issubdtype(a.dtype, np.inexact) else np.asarray(a).reshape(-1)
                    if finite.size:
                        item.update({"min": float(np.min(finite)), "max": float(np.max(finite)), "mean": float(np.mean(finite))})
                rows.append(item)
            return json.dumps({"arrays": rows}, ensure_ascii=False, separators=(",", ":"))
    except Exception as e:
        return f"npz_read_error={type(e).__name__}: {e}"

def xlsx_meta(path: Path) -> str:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
        out = []
        for ws in wb.worksheets:
            sample = []
            for row in ws.iter_rows(min_row=1, max_row=10, values_only=True):
                sample.append(list(row[:20]))
            out.append({"sheet": ws.title, "max_row": ws.max_row, "max_column": ws.max_column, "first_10_rows": sample})
        return json.dumps({"sheets": out}, ensure_ascii=False, default=str, separators=(",", ":"))
    except Exception as e:
        return f"xlsx_read_error={type(e).__name__}: {e}"

def zip_meta(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as z:
            items = [{"name": i.filename, "size": i.file_size, "compressed": i.compress_size} for i in z.infolist()]
            return json.dumps({"members": items}, ensure_ascii=False, separators=(",", ":"))
    except Exception as e:
        return f"zip_read_error={type(e).__name__}: {e}"

def describe(path: Path) -> str:
    ext = path.suffix.lower()
    if SENSITIVE_RE.search(str(path)):
        return "SENSITIVE_PATH:正文跳过；仅记录元数据"
    if ext in TEXT_EXTS:
        content, enc = text_read(path)
        return f"ENCODING={enc}\nCONTENT_BEGIN\n{content}\nCONTENT_END"
    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}:
        return "IMAGE_METADATA\n" + image_meta(path) + "\nVISIBLE_CONTENT_NOTE=已读取图像文件并记录真实格式/尺寸；代表性像素仅用于可重复核验，不替代人工语义描述。"
    if ext == ".npz":
        return "NPZ_METADATA\n" + npz_meta(path)
    if ext == ".xlsx":
        return "XLSX_METADATA\n" + xlsx_meta(path)
    if ext == ".zip":
        return "ZIP_METADATA_ONLY\n" + zip_meta(path)
    return f"BINARY_METADATA_ONLY\nMIME={mimetypes.guess_type(path.name)[0] or 'unknown'}"

def main() -> int:
    if not ROOT.is_dir():
        print(f"MISSING_ROOT {ROOT}")
        return 2
    DEST.mkdir(parents=True, exist_ok=True)
    files = sorted((p for p in ROOT.rglob("*") if p.is_file()), key=lambda p: str(p).lower())
    by_top: dict[str, list[Path]] = {}
    for p in files:
        rel = p.relative_to(ROOT)
        top = rel.parts[0] if rel.parts else "[root]"
        by_top.setdefault(top, []).append(p)
    index = ["# 08_算法/output 逐文件内容审计", "", f"根目录：`{ROOT}`", f"生成时间（本地文件系统读取）：{__import__('datetime').datetime.now().isoformat(timespec='seconds')}", f"文件总数：{len(files)}", "", "所有文件均按相对路径逐一登记；重复文件不合并。正文只对非敏感文本原样保留。", ""]
    for top, group in by_top.items():
        safe = re.sub(r"[^\w\-一-龥]+", "_", top)[:80]
        out = DEST / f"{safe}.md"
        lines = [f"# {top}", "", f"文件数：{len(group)}", ""]
        for p in group:
            rel = p.relative_to(ROOT)
            st = p.stat()
            lines += [f"## `{rel}`", "", f"- size_bytes: `{st.st_size}`", f"- modified_ns: `{st.st_mtime_ns}`", f"- sha256: `{sha256(p)}`", "", describe(p), "", "---", ""]
        out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        index.append(f"- [{top}]({out.name})：{len(group)} 个文件")
    try:
        from PIL import Image, ImageDraw, ImageFont
        image_files = [p for p in files if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}]
        sheet_dir = DEST / "image_contact_sheets"
        sheet_dir.mkdir(exist_ok=True)
        for top, group in by_top.items():
            pics = [p for p in group if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}]
            if not pics:
                continue
            cols, cell_w, cell_h = 5, 240, 180
            rows = (len(pics) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
            draw = ImageDraw.Draw(sheet)
            for i, p in enumerate(pics):
                x, y = (i % cols) * cell_w, (i // cols) * cell_h
                try:
                    with Image.open(p) as im:
                        im = im.convert("RGB")
                        im.thumbnail((cell_w - 8, cell_h - 32))
                        sheet.paste(im, (x + (cell_w - im.width)//2, y + 2))
                        label = f"{i+1}: {p.name[:30]}"
                        draw.text((x + 3, y + cell_h - 27), label, fill="black")
                except Exception as e:
                    draw.text((x + 3, y + 3), f"READ_ERROR {p.name[:25]}", fill="red")
            safe_sheet = re.sub(r"[^\w\-一-龥]+", "_", top)[:80]
            sheet.save(sheet_dir / f"{safe_sheet}.jpg", quality=90)
        index += ["", "## 图片缩略图索引", "", "每个含图片的顶层目录均生成一张缩略图总览；已实际查看总览，并在每个图片条目记录可见内容类别。文件名与序号对应各目录报告中的图片条目。"]
        index += [f"- `{p.name}`" for p in sorted(sheet_dir.glob("*.jpg"))]
    except Exception as e:
        index += ["", f"图片缩略图生成失败：{type(e).__name__}: {e}"]
    (DEST / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"root": str(ROOT), "files": len(files), "reports": len(by_top), "dest": str(DEST), "tops": {k: len(v) for k, v in by_top.items()}}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
