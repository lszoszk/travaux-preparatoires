#!/usr/bin/env python3
"""Reads a set of pages with one of the three OCR witnesses tried for the name guard (docs/devlog.md, 20 Oct, preregistered):
PP-OCRv5 (engine "paddle"), docTR with the CRNN recognizer ("doctr"), PERO OCR with its published printed model ("pero"). Each
runs with its defaults, in its own virtual environment (~/.venvs/ocr-<engine>); the text goes to
data/ocr/<doc>/<engine>/page-NNN.txt like any other engine's, the seconds per page to data/logs/ocr_witness_<engine>.jsonl.

Reading order is PERO's own (its region sorter); for the other two, which return boxes (PaddleOCR's text lines, docTR's lines), ours: boxes on the same height make a
line, left to right; a page whose boxes fall into two columns (at least 8 boxes wholly left of the middle and 8 wholly right,
together 60% of the boxes) is read: full-width boxes above the columns, left column, right column, full-width boxes below.

  ~/.venvs/ocr-paddle/bin/python eval/ocr_witness_read.py paddle eval/vlm_pilot/dev_set.json eval/gold_pages/pages.json
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OCR = ROOT / "data" / "ocr"
PERO_CONFIG = Path.home() / ".venvs" / "pero-model" / "pero_eu_cz_print_newspapers_2022-09-26" / "config_cpu.ini"


def pages_of(path: Path) -> list[tuple[str, int]]:
    d = json.loads(path.read_text())
    if isinstance(d, dict):
        return [(x["symbol"], p) for x in d["documents"] for p in x["pages"]]
    return [(x["symbol"], x["page"]) for x in d]


def lines_of(boxes: list[tuple[float, float, float, float, str]], width: float) -> list[str]:
    """Boxes (x0, y0, x1, y1, text) in reading order, joined into lines."""
    if not boxes:
        return []
    mid = width / 2
    left = [b for b in boxes if b[2] < mid]
    right = [b for b in boxes if b[0] > mid]
    groups = [boxes]
    if len(left) >= 8 and len(right) >= 8 and len(left) + len(right) >= 0.6 * len(boxes):
        top, bottom = min(b[1] for b in left + right), max(b[3] for b in left + right)
        full = [b for b in boxes if b not in left and b not in right]
        h = statistics.median(b[3] - b[1] for b in boxes)
        groups = [[b for b in full if b[3] <= top + h / 2], left, right, [b for b in full if b[3] > top + h / 2]]
    out = []
    for g in groups:
        if not g:
            continue
        h = statistics.median(b[3] - b[1] for b in g)
        line, yc = [], None
        for b in sorted(g, key=lambda b: (b[1] + b[3]) / 2):
            c = (b[1] + b[3]) / 2
            if line and abs(c - yc) > 0.5 * h:
                out.append(" ".join(x[4] for x in sorted(line)))
                line = []
            line.append(b)
            yc = c if len(line) == 1 else (yc * (len(line) - 1) + c) / len(line)
        if line:
            out.append(" ".join(x[4] for x in sorted(line)))
    return out


def reader(engine: str):
    if engine == "paddle":
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(lang="en", use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)

        def read(img: Path) -> list[str]:
            r = ocr.predict(str(img))[0]
            boxes = [(*map(float, b), t) for b, t in zip(r["rec_boxes"], r["rec_texts"]) if t.strip()]
            from PIL import Image
            return lines_of(boxes, Image.open(img).width)
        return read
    if engine == "doctr":
        from doctr.io import DocumentFile
        from doctr.models import ocr_predictor
        model = ocr_predictor(det_arch="db_resnet50", reco_arch="crnn_vgg16_bn", pretrained=True)

        def read(img: Path) -> list[str]:
            page = model(DocumentFile.from_images([str(img)])).pages[0]
            # (docTR's lines, not its words: words wholly left and right of the middle would make every page two-column)
            boxes = [(ln.geometry[0][0], ln.geometry[0][1], ln.geometry[1][0], ln.geometry[1][1], " ".join(w.value for w in ln.words))
                     for b in page.blocks for ln in b.lines if ln.words]
            return lines_of(boxes, 1.0)
        return read
    if engine == "pero":
        import configparser

        import cv2
        from pero_ocr.core.layout import PageLayout
        from pero_ocr.document_ocr.page_parser import PageParser
        config = configparser.ConfigParser()
        config.read(PERO_CONFIG)
        parser = PageParser(config, config_path=str(PERO_CONFIG.parent))

        def read(img: Path) -> list[str]:
            image = cv2.imread(str(img), 1)
            layout = parser.process_page(image, PageLayout(id=img.stem, page_size=(image.shape[0], image.shape[1])))
            return [ln.transcription for r in layout.regions for ln in r.lines if ln.transcription]
        return read
    raise SystemExit(f"unknown engine {engine}")


def main() -> int:
    engine, *sets = sys.argv[1:]
    pages = [p for s in sets for p in pages_of(Path(s))]
    read = reader(engine)
    log = (ROOT / "data" / "logs" / f"ocr_witness_{engine}.jsonl").open("a")
    for k, (sym, page) in enumerate(pages, 1):
        safe = sym.replace("/", "_")
        img = OCR / safe / "img" / f"page-{page:03d}.png"
        out = OCR / safe / engine / f"page-{page:03d}.txt"
        if out.exists():
            continue
        t = time.time()
        try:
            lines = read(img)
        except Exception as e:  # (one page's failure is logged, the run goes on: PERO's layout fails on some pages)
            log.write(json.dumps({"symbol": sym, "page": page, "error": f"{type(e).__name__}: {e}"[:200]}) + "\n")
            print(f"{engine} {k}/{len(pages)} {sym} p{page}: {type(e).__name__}", file=sys.stderr, flush=True)
            continue
        sec = time.time() - t
        out.parent.mkdir(exist_ok=True)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log.write(json.dumps({"symbol": sym, "page": page, "seconds": round(sec, 2), "lines": len(lines)}) + "\n")
        log.flush()
        print(f"{engine} {k}/{len(pages)} {sym} p{page}: {len(lines)} lines, {sec:.1f} s", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
