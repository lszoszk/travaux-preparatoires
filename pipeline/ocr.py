#!/usr/bin/env python3
"""Run the local OCR engines on harvested PDFs and keep every engine's output per page.

Engines (all local and free):
  layer      the text layer already in the UN PDF (ABBYY / Acrobat, 2005-2013 vintage)
  tess4      Tesseract 5 LSTM, --psm 4 (single column of variable sizes)
  tess6      Tesseract 5 LSTM, --psm 6 (uniform block of text)
  tess6min   tess6 on a stroke-thickened image (MinFilter 3): helps faint typewriter text
  tess3      Tesseract --psm 3 (automatic layout; for two-column printed records)
  vision     Apple Vision (bin/vision_ocr) on a lightly blurred image

Tesseract settings follow generalcomments-repo/ocr_jurisprudence.py (LSTM engine,
autocontrast, preserve_interword_spaces). Nothing is chosen here: the combination and
the quality gate are later steps, measured by eval/ocr_bench.py.

Output: data/ocr/<safe symbol>/<engine>/page-NNN.txt (gitignored), plus meta.json
with per-page confidence where the engine reports one.

Usage: python3 pipeline/ocr.py data/manifest/harvest_pilot_udhr_18_19.json [--pages 4] [--engines ...]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz
from PIL import Image, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import safe_name  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OCR = ROOT / "data" / "ocr"
VISION = ROOT / "bin" / "vision_ocr"
ENGINES = ["layer", "tess4", "tess6", "tess6min", "tess3", "vision"]
DPI = 300  # the 1947-66 scans are ~300 dpi natively; rendering higher adds nothing
WORKERS = 8  # parallel Tesseract processes, one thread each (OpenMP threading is slower here)
TESS_ENV = {**os.environ, "OMP_THREAD_LIMIT": "1"}


def sample_pages(n_pages: int, k: int) -> list[int]:
    """k pages spread across the document (0-based); all pages when k is 0 or >= n."""
    if not k or k >= n_pages:
        return list(range(n_pages))
    step = (n_pages - 1) / (k - 1) if k > 1 else 0
    return sorted({round(i * step) for i in range(k)})


def scan_pdf(symbol: str) -> Path | None:
    """The harvested PDF of a document (data/raw/<symbol>-EN.pdf, or the French original of a machine-translated one)."""
    raw = ROOT / "data" / "raw"
    for lang in ("EN", "FR"):
        p = raw / f"{safe_name(symbol)}-{lang}.pdf"
        if p.exists():
            return p
    return None


def page_image(symbol: str, page: int) -> Path | None:
    """data/ocr/<symbol>/img/page-NNN.png, rendered from the PDF if it is not on disk (the images are 43 GB and can be left
    out of a copy of the project: the audits render the pages they draw)."""
    path = OCR / safe_name(symbol) / "img" / f"page-{page:03d}.png"
    if path.exists():
        return path
    pdf_path = scan_pdf(symbol)
    if not pdf_path:
        return None
    with fitz.open(pdf_path) as pdf:
        return render(pdf, page - 1, OCR / safe_name(symbol)) if 0 < page <= len(pdf) else None


def render(pdf: fitz.Document, pno: int, out_dir: Path) -> Path:
    path = out_dir / "img" / f"page-{pno + 1:03d}.png"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        pdf[pno].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY).save(path)
    return path


def variant(img_path: Path, kind: str) -> Path:
    """Preprocessed copy of a page image, cached next to it."""
    path = img_path.with_name(f"{img_path.stem}.{kind}.png")
    if not path.exists():
        with Image.open(img_path) as img:
            img = ImageOps.autocontrast(ImageOps.grayscale(img))
            if kind == "min":
                img = img.filter(ImageFilter.MinFilter(3))
            elif kind == "blur":
                img = img.filter(ImageFilter.GaussianBlur(0.8))
            img.save(path)
    return path


def tesseract(img: Path, psm: int) -> tuple[str, float | None]:
    """Text in Tesseract's own line order, plus mean word confidence."""
    proc = subprocess.run(
        ["tesseract", str(img), "stdout", "-l", "eng", "--oem", "1", "--psm", str(psm),
         "-c", "preserve_interword_spaces=1", "tsv"],
        check=True, capture_output=True, text=True, env=TESS_ENV,
    )
    lines: dict[tuple[int, int, int], list[tuple[int, str]]] = {}
    confs = []
    for row in csv.DictReader(proc.stdout.splitlines(), delimiter="\t", quoting=csv.QUOTE_NONE):
        word = (row.get("text") or "").strip()
        if not word:
            continue
        conf = float(row.get("conf") or -1)
        if conf >= 0:
            confs.append(conf)
        key = (int(row["block_num"]), int(row["par_num"]), int(row["line_num"]))
        lines.setdefault(key, []).append((int(row["word_num"]), word))
    text = "\n".join(" ".join(w for _, w in sorted(ws)) for _, ws in sorted(lines.items()))
    return text, (sum(confs) / len(confs) if confs else None)


def vision_order(lines: list[dict]) -> str:
    """Put Vision's line boxes in reading order, handling two-column pages.

    Lines narrower than half the page sit in a column; if both columns hold at least
    five lines the page is two-column: full-width lines above the columns, then the
    left column, the right column, and full-width lines below.
    """
    left = [l for l in lines if l["x"] + l["w"] <= 0.53]
    right = [l for l in lines if l["x"] >= 0.47]
    if len(left) >= 5 and len(right) >= 5:
        cols = left + right
        top = min(l["y"] for l in cols)
        span = [l for l in lines if l not in left and l not in right]
        above = sorted((l for l in span if l["y"] < top), key=lambda l: l["y"])
        below = sorted((l for l in span if l["y"] >= top), key=lambda l: l["y"])
        ordered = above + sorted(left, key=lambda l: l["y"]) + sorted(right, key=lambda l: l["y"]) + below
        return "\n".join(l["text"] for l in ordered)
    # single column: group boxes on the same baseline, left to right
    rows: list[list[dict]] = []
    for l in sorted(lines, key=lambda l: l["y"]):
        if rows and abs(rows[-1][0]["y"] - l["y"]) < l["h"] * 0.5:
            rows[-1].append(l)
        else:
            rows.append([l])
    return "\n".join(" ".join(b["text"] for b in sorted(r, key=lambda b: b["x"])) for r in rows)


def vision(imgs: list[Path]) -> dict[Path, tuple[str, float | None]]:
    """One Vision process per document (start-up dominates per-page cost)."""
    proc = subprocess.run([str(VISION), *map(str, imgs)], check=True, capture_output=True, text=True)
    out = {}
    for line in proc.stdout.splitlines():
        obj = json.loads(line)
        ls = obj["lines"]
        conf = sum(l["conf"] for l in ls) / len(ls) if ls else None
        out[Path(obj["image"])] = (vision_order(ls), conf * 100 if conf is not None else None)
    return out


def ocr_document(symbol: str, pdf_path: Path, pages: int, engines: list[str]) -> dict:
    out_dir = OCR / safe_name(symbol)
    meta_path = out_dir / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"symbol": symbol, "pages": {}}
    pdf = fitz.open(pdf_path)
    todo = sample_pages(pdf.page_count, pages)
    meta["n_pages"] = pdf.page_count

    def save(engine: str, pno: int, text: str, conf: float | None) -> None:
        path = out_dir / engine / f"page-{pno + 1:03d}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        meta["pages"].setdefault(str(pno + 1), {})[engine] = {"conf": conf, "chars": len(text)}

    def done(engine: str, pno: int) -> bool:
        return (out_dir / engine / f"page-{pno + 1:03d}.txt").exists()

    imgs = {pno: render(pdf, pno, out_dir) for pno in todo}
    jobs = []
    for pno in todo:
        if "layer" in engines and not done("layer", pno):
            save("layer", pno, pdf[pno].get_text(), None)
        for engine, psm, kind in (("tess4", 4, "auto"), ("tess6", 6, "auto"),
                                  ("tess6min", 6, "min"), ("tess3", 3, "auto")):
            if engine in engines and not done(engine, pno):
                jobs.append((engine, pno, variant(imgs[pno], kind), psm))
    with ThreadPoolExecutor(WORKERS) as pool:  # the work happens in tesseract subprocesses
        results = pool.map(lambda j: (j[0], j[1], *tesseract(j[2], j[3])), jobs)
        for engine, pno, text, conf in results:
            save(engine, pno, text, conf)
    if "vision" in engines:
        pending = [pno for pno in todo if not done("vision", pno)]
        if pending:
            by_img = {variant(imgs[p], "blur"): p for p in pending}
            for img, (text, conf) in vision(list(by_img)).items():
                save("vision", by_img[img], text, conf)
    meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return {"symbol": symbol, "pages_done": len(todo), "n_pages": pdf.page_count}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("harvest_log", type=Path)
    ap.add_argument("--pages", type=int, default=0, help="pages per document, spread evenly (0 = all)")
    ap.add_argument("--all-if-under", type=int, default=0,
                    help="OCR every page of documents with at most this many pages, whatever --pages says")
    ap.add_argument("--engines", nargs="+", default=ENGINES, choices=ENGINES)
    ap.add_argument("--only", nargs="*", help="limit to these symbols")
    args = ap.parse_args()
    log = json.loads(args.harvest_log.read_text())
    for symbol, entry in sorted(log.items()):
        if entry.get("status") != "ok" or (args.only and symbol not in args.only):
            continue
        pages = 0 if entry.get("pages", 0) <= args.all_if_under else args.pages
        r = ocr_document(symbol, ROOT / entry["file"], pages, args.engines)
        print(f"  {symbol}: {r['pages_done']}/{r['n_pages']} pages", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
