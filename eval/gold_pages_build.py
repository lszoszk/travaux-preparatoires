#!/usr/bin/env python3
"""A sample of meeting-record pages for hand annotation (eval/annotate_pages.py): for each page, its OCR lines as the
segmenter reads them (pipeline/segment.py load_lines: page furniture removed, line-end hyphens joined), and where the database
now starts a segment on it (line, kind, speaker, delegation), as the annotator's starting point.

The annotations (data/gold/segment_pages.json) are keyed by page and by line, not by segment id, so a later resegmentation
leaves them valid; eval/segment_gold_eval.py compares them with the database.

  python3 eval/gold_pages_build.py [--per 8] [--seed 100]     # -> eval/gold_pages/pages.json
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "eval"))
from ocr import page_image, scan_pdf  # noqa: E402
from segment import load_lines  # noqa: E402
from segment_audit_sample import stratum  # noqa: E402

OUT = ROOT / "eval" / "gold_pages" / "pages.json"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def starts_on_page(lines: list[str], segs: list[dict]) -> list[dict]:
    """Each segment that starts on the page, placed on the line where its text begins (or, for one cut inside a line, the line
    that holds its first words)."""
    out, at = [], 0
    for s in segs:
        head = norm(s["text"])[:40]
        found = None
        for k in range(at, len(lines)):
            line = norm(lines[k])
            if line and (head.startswith(line[:40]) or line.startswith(head[:30])):
                found, offset = k, 0
                break
            if head[:30] and head[:30] in line:
                found, offset = k, line.index(head[:30])
                break
        if found is None:
            continue
        at = found
        out.append({"line": found, "offset": offset, "kind": s["kind"], "speaker": s["speaker"] or "",
                    "delegation": s["delegation"] or "", "words": head})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=8)
    ap.add_argument("--seed", type=int, default=100)
    args = ap.parse_args()
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    con.row_factory = sqlite3.Row
    pages = defaultdict(list)
    for r in con.execute("SELECT DISTINCT s.symbol, s.page_start, d.instrument, d.body, d.session FROM segments s "
                         "JOIN documents d USING(symbol) WHERE s.kind = 'speech' ORDER BY s.symbol, s.page_start"):
        st = stratum(r["instrument"], r["body"], r["session"], r["symbol"])
        if st and scan_pdf(r["symbol"]):
            pages[st].append((r["symbol"], r["page_start"]))
    rnd = random.Random(args.seed)
    items = []
    for st in sorted(pages):
        for sym, page in rnd.sample(pages[st], min(args.per, len(pages[st]))):
            img = page_image(sym, page)
            lines = [ln for p, ln in load_lines(sym, "vote") if p == page]
            segs = [dict(s) for s in con.execute("SELECT * FROM segments WHERE symbol = ? AND page_start = ? AND kind NOT IN "
                                                 "('masthead', 'footnote') ORDER BY seq", (sym, page))]
            items.append({"id": f"{sym} p{page}", "stratum": st, "symbol": sym, "page": page,
                          "image": str(Path(img).relative_to(ROOT)) if img else None, "lines": lines,
                          "starts": starts_on_page(lines, segs), "unplaced": len(segs) - len(starts_on_page(lines, segs))})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=1))
    print(f"{len(items)} pages -> {OUT.relative_to(ROOT)}; segments not placed on a line: {sum(i['unplaced'] for i in items)}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
