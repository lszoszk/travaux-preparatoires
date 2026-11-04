#!/usr/bin/env python3
"""A sample of pages for the segmentation audit: does the record's division into speeches match the page?

Draws pages at random (fixed seed) from each kind of meeting record, and writes for each the page image and the
segments that start or run on it (kind, speaker, delegation, the opening and the end of the text), for a reader who
compares them with the image: a speech missed (two speakers in one segment), a false split, a wrong speaker or
delegation, the text of the other column or of a running header in a speech, text missing.

Usage: python3 eval/segment_audit_sample.py OUT.json [--per 12] [--seed 66]
       python3 eval/segment_audit_sample.py OUT.json --pages EARLIER.json     # the same pages again, with the segments now in the database
       python3 eval/segment_audit_sample.py OUT.json --pages SAMPLE.json --db OLD.sqlite3   # the same pages with the segments of an earlier build
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
from ocr import page_image, safe_name, scan_pdf  # noqa: E402


def stratum(corpus: str, body: str | None, session: str | None, symbol: str) -> str | None:
    if "/SR." not in symbol and "/PV." not in symbol:
        return None
    m = re.match(r"(\d+)", session or "")
    if corpus == "UDHR":
        return "UDHR 1946-48 plenary" if "/PV." in symbol else "UDHR 1946-48"
    if body == "Commission on Human Rights":
        return "CHR 1949-54"
    if m and int(m.group(1)) >= 17:
        return "Third Committee 1962-66"
    return "Third Committee 1950-61"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--per", type=int, default=12)
    ap.add_argument("--seed", type=int, default=66)
    ap.add_argument("--pages", type=Path, help="reuse the pages of an earlier sample (a paired comparison after a fix)")
    ap.add_argument("--db", type=Path, help="the database whose segments are listed (default data/travaux.sqlite3: with --pages, the "
                                            "segments of an earlier build give the other half of a paired comparison)")
    args = ap.parse_args()
    con = sqlite3.connect(args.db or ROOT / "data" / "travaux.sqlite3")
    con.row_factory = sqlite3.Row
    if args.pages:
        items = []
        for old in json.loads(args.pages.read_text()):
            segs = [{"id": s["id"], "kind": s["kind"], "speaker": s["speaker"], "delegation": s["delegation"],
                     "pages": f"{s['page_start']}-{s['page_end']}", "opening": " ".join((s["text"] or "").split())[:220],
                     "ending": " ".join((s["text"] or "").split())[-160:]}
                    for s in con.execute("SELECT * FROM segments WHERE symbol = ? AND kind != 'masthead' AND page_start <= ? "
                                         "AND page_end >= ? ORDER BY seq", (old["symbol"], old["page"], old["page"]))]
            items.append({**old, "id": f"{old['symbol']} p{old['page']}", "segments": segs})
        args.out.write_text(json.dumps(items, ensure_ascii=False, indent=1))
        print(f"{len(items)} pages of {args.pages.name} with the segments now in the database", file=sys.stderr)
        return 0
    pages = defaultdict(list)
    for r in con.execute("SELECT DISTINCT s.symbol, s.page_start, d.instrument, d.body, d.session FROM segments s "
                         "JOIN documents d USING(symbol) WHERE s.kind = 'speech' ORDER BY s.symbol, s.page_start"):
        st = stratum(r["instrument"], r["body"], r["session"], r["symbol"])
        if st and scan_pdf(r["symbol"]):
            pages[st].append((r["symbol"], r["page_start"], None))
    rnd = random.Random(args.seed)
    items = []
    for st in sorted(pages):
        for sym, page, _ in rnd.sample(pages[st], min(args.per, len(pages[st]))):
            img = str(page_image(sym, page))  # (rendered from the PDF if the image is not on disk)
            segs = [{"id": s["id"], "kind": s["kind"], "speaker": s["speaker"], "delegation": s["delegation"],
                     "pages": f"{s['page_start']}-{s['page_end']}", "opening": " ".join((s["text"] or "").split())[:220],
                     "ending": " ".join((s["text"] or "").split())[-160:]}
                    for s in con.execute("SELECT * FROM segments WHERE symbol = ? AND kind != 'masthead' AND page_start <= ? "
                                         "AND page_end >= ? ORDER BY seq", (sym, page, page))]
            items.append({"id": f"{sym} p{page}", "stratum": st, "symbol": sym, "page": page, "image": img, "segments": segs})
    args.out.write_text(json.dumps(items, ensure_ascii=False, indent=1))
    print(f"{len(items)} pages: " + ", ".join(f"{k} {min(args.per, len(v))}" for k, v in sorted(pages.items())), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
