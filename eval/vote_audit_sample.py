#!/usr/bin/env python3
"""A sample of votes and decisions for the vote audit: do the figures, the outcome and the clause match the page?

Draws decisions (the Votes view's rows) at random (fixed seed) from the meeting records, in the kinds of record the segmentation
audit uses, with at least --roll of them roll-calls, and writes for each the page image and what the database holds: the clause
voted on, the outcome, the figures (yes, no, abstentions, unanimous, without a vote), the proposers, the roll-call lists if any,
and the article the vote is filed under. A reader compares them with the image. Images are rendered on demand from the PDF
(pipeline/ocr.py, page_image).

Usage: python3 eval/vote_audit_sample.py OUT.json [--n 70] [--roll 8] [--seed 78]
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
sys.path.insert(0, str(ROOT / "api"))
from ocr import page_image, scan_pdf  # noqa: E402
from segment_audit_sample import stratum  # noqa: E402
import server  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--n", type=int, default=70)
    ap.add_argument("--roll", type=int, default=8)
    ap.add_argument("--seed", type=int, default=78)
    ap.add_argument("--db", type=Path)
    args = ap.parse_args()
    con = sqlite3.connect(args.db or ROOT / "data" / "travaux.sqlite3")
    con.row_factory = sqlite3.Row
    titles = {i: server.article_titles(i) for i in ("UDHR", "ICCPR", "ICESCR")}
    rows = con.execute("SELECT d.*, s.page_start, s.text AS seg_text, p.instrument corpus, p.body, p.session FROM decisions d "
                       "JOIN segments s ON s.id = d.segment_id JOIN documents p ON p.symbol = d.symbol "
                       "WHERE d.symbol GLOB '*/SR.*' OR d.symbol GLOB '*/PV.*'").fetchall()
    pools, rolls = defaultdict(list), []
    for r in rows:
        st = stratum(r["corpus"], r["body"], r["session"], r["symbol"])
        if not st or not scan_pdf(r["symbol"]):
            continue
        (rolls if r["roll_call"] else pools[st]).append((st, r))
    rng = random.Random(args.seed)
    chosen = []
    rng.shuffle(rolls)
    chosen += rolls[:args.roll]
    left = args.n - len(chosen)
    strata = sorted(pools)
    for st in strata:
        rng.shuffle(pools[st])
        chosen += pools[st][:max(1, round(left / len(strata)))]
    items = []
    for st, r in chosen:
        rc = json.loads(r["roll_call"]) if r["roll_call"] else None
        inst = (r["article_instrument"] or "").split("+")[0]
        items.append({
            "id": r["id"], "symbol": r["symbol"], "page": r["page_start"], "stratum": st, "image": str(page_image(r["symbol"], r["page_start"])),
            "clause": (r["subject"] or "")[:400], "outcome": r["outcome"],
            "yes": r["yes"], "no": r["no"], "abstentions": r["abstentions"], "unanimous": bool(r["unanimous"]),
            "without_vote": bool(r["without_vote"]), "proposers": json.loads(r["proposers"] or "[]"),
            "roll_call": {k: v for k, v in rc.items()} if rc else None, "roll_complete": r["roll_complete"],
            "filed_under": (f"{r['article_instrument']} art. {r['final_article']} ({titles.get(inst, {}).get(str(r['final_article']), '')})"
                            if r["final_article"] else None),
            "segment_text": re.sub(r"\s+", " ", r["seg_text"] or "")[:700]})
    rng.shuffle(items)
    args.out.write_text(json.dumps(items, ensure_ascii=False, indent=1))
    by = defaultdict(int)
    for x in items:
        by[x["stratum"] + (" (roll-call)" if x["roll_call"] else "")] += 1
    print(len(items), dict(sorted(by.items())), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
