#!/usr/bin/env python3
"""Check again the Commission's records the harvest-time relevance filter left out.

pipeline/ocr_all.py decides from the ODS text layer of a record's first two pages whether it
is about the Covenants. The text layers of the 1949-54 mimeographed records are often garbled,
so records the session reports give to covenant articles were left out (E/CN.4/SR.303, 320,
323, 324, 330, 351, 353; the 1952 debate on self-determination, SR.252-265). This reads their
first two pages with Apple Vision and counts a record as relevant if it names the Covenant(s) or
self-determination, or if its session's report lists the meeting for an article
(data/concordance/covenant_drafts_chr.csv). Updates the relevance files ocr_all.py reads.

Usage: python3 pipeline/relevance_recheck.py [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
import zlib
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocr import render, vision  # noqa: E402
from ocr_all import COVENANT_RE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "data" / "manifest"
SHARDS = 3


def listed_meetings() -> set[int]:
    out = set()
    for r in csv.DictReader((ROOT / "data" / "concordance" / "covenant_drafts_chr.csv").open()):
        if r["meetings"] and r["final_article"] != "general":
            out |= {int(m) for m in r["meetings"].split()}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    log = json.loads((MAN / "harvest_covenants.json").read_text())
    rels = {i: json.loads(p.read_text()) if (p := MAN / f"relevance_covenants_{i}.json").exists() else {} for i in range(SHARDS)}
    listed = listed_meetings()
    todo = [s for s, e in log.items() if s.startswith("E/CN.4/SR.") and e.get("status") == "ok"
            and not rels[zlib.crc32(s.encode()) % SHARDS].get(s, {"relevant": True})["relevant"]]
    # the records added since the harvest (downloaded by hand) have no verdict yet
    todo += [s for s, e in log.items() if s.startswith("E/CN.4/SR.") and e.get("status") == "ok" and e.get("via") != "ods"
             and s not in rels[zlib.crc32(s.encode()) % SHARDS]]
    changed = 0
    for sym in sorted(set(todo), key=lambda s: int(s.rsplit(".", 1)[1])):
        meeting = int(sym.rsplit(".", 1)[1])
        pdf = fitz.open(ROOT / log[sym]["file"])
        with tempfile.TemporaryDirectory() as tmp:
            imgs = [render(pdf, p, Path(tmp)) for p in range(min(2, pdf.page_count))]
            text = " ".join(t for t, _ in vision(imgs).values())
        # self-determination: the 1952 session took up the covenants' article under that agenda item (SR.252-266); the
        # later items on recommendations for respect of the right (1953-54) are not the covenants'
        m = COVENANT_RE.search(text) or (252 <= meeting <= 266 and re.search(r"self[\s-]*determination", text, re.I))
        ok = bool(m) or meeting in listed
        why = (f"vision pp. 1-2: {text[max(0, m.start() - 60):m.end() + 60]}" if m else
               "listed for an article in its session's report" if ok else "vision pp. 1-2: no mention")
        print(f"{sym:16} {'RELEVANT' if ok else '-':9} {why[:120]}", flush=True)
        shard = zlib.crc32(sym.encode()) % SHARDS
        if ok and not args.dry_run:
            rels[shard][sym] = {"relevant": True, "evidence": " ".join(why.split())[:300], "rechecked": True}
            changed += 1
        elif not args.dry_run:
            rels[shard][sym] = {"relevant": False, "evidence": "no mention on pp. 1-2 (Vision)", "rechecked": True}
    if not args.dry_run:
        for i, rel in rels.items():
            (MAN / f"relevance_covenants_{i}.json").write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(set(todo))} records checked; {changed} now relevant", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
