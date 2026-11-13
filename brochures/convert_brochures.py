"""Turn the in-class hackathon brochure photos into provenance-stamped .txt files the notebook can build from.

Run from the repo folder:  python brochures/convert_brochures.py
Reads brochures/images/*.jpg|jpeg|png, writes brochures/docs/<name>.txt. Both folders are in .gitignore.

The kit's normalize_any has no branch for images, so each photo is turned upright (phones store rotation in
EXIF), shrunk to at most 2000 px on its long side, wrapped in a one-page PDF and sent through the kit's own
normalize_pdf, which reads the rendered page (text, tables and figures). One Messages API call per image.
A photo that already has a .txt is skipped, so a rerun only pays for what is missing.
"""
import io
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import anthropic
from dotenv import load_dotenv
from PIL import Image, ImageOps

import utilities as kw

IMAGES = ROOT / "brochures" / "images"
DOCS = ROOT / "brochures" / "docs"
MAX_SIDE = 2000

load_dotenv(ROOT / ".env")
MODEL = os.environ.get("COOKBOOK_BUILD_MODEL", os.environ.get("COOKBOOK_MODEL") or "claude-haiku-5-5")


def taken_on(img, path):
    """The photo's own date (EXIF DateTimeOriginal) if it has one, else the file's modified date."""
    raw = img.getexif().get_ifd(0x8769).get(36867) or img.getexif().get(306)
    if raw:
        try:
            return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").date().isoformat()
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()


def as_pdf(path):
    """The photo upright and shrunk, as the bytes of a one-page PDF, plus its date."""
    with Image.open(path) as img:
        when = taken_on(img, path)
        page = ImageOps.exif_transpose(img).convert("RGB")
    page.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    page.save(buf, format="PDF", resolution=150)
    return buf.getvalue(), when


def main():
    photos = sorted(p for p in IMAGES.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    others = sorted(p.name for p in IMAGES.iterdir() if p.is_file() and p.suffix.lower() not in (".jpg", ".jpeg", ".png") and not p.name.startswith("."))
    if others:
        sys.exit(f"Not images, so not converted (move them out or add a branch): {others}")
    if not photos:
        sys.exit(f"No .jpg/.jpeg/.png files in {IMAGES}")
    DOCS.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()
    tmp = DOCS / "_page.pdf"
    for n, photo in enumerate(photos, 1):
        out = DOCS / f"{photo.stem}.txt"
        if out.exists():
            print(f"[{n}/{len(photos)}] {photo.name}: already converted, skipped")
            continue
        pdf, when = as_pdf(photo)
        tmp.write_bytes(pdf)
        text = kw.normalize_pdf(client, tmp, MODEL)
        header = (
            f"[SOURCE: in-class hackathon brochure | file: {photo.name} | photographed: {when} | "
            f"note: transcribed from a photo]"
        )
        out.write_text(header + "\n\n" + text)
        print(f"[{n}/{len(photos)}] {photo.name}: {len(text):,} characters -> {out.relative_to(ROOT)}")
    tmp.unlink(missing_ok=True)
    print(f"done: {len(list(DOCS.glob('*.txt')))} documents in {DOCS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
