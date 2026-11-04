#!/usr/bin/env python3
"""How much of Schabas's index our article tags cover, page by page (preregistered in docs/devlog.md, 21 Oct 2026). PRIVATE
INPUT, counts only out.

Each index reference (article, book page) lands on one or two documents and on one or more of their UN pages
(eval/schabas_candidates.py's index_cells); the segments of the record on that UN page come from the cached alignment
(data/private/schabas_alignment.json). A cell (article, record, UN page) is
- covered: a segment on the page carries the article (final_article, UDHR);
- possible: none does, but one has it among its possible articles;
- missed: neither;
- not aligned: no segment of ours was found on the page (OCR or segmentation; not counted as a miss).
Per article and per kind of record: documents (reports, drafts, letters), article debates (meeting records with at least one
UDHR tag) and general debates (meeting records with none). The measure is asymmetric by design: the index lists mentions,
so a tag of ours that the index lacks is not counted wrong; those (record, article) pairs are listed privately
(data/private/schabas_ours_only.json) for the audit.

  python3 eval/schabas_coverage.py [--json eval/schabas_coverage.json] [--label before]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "pipeline"))
from schabas_candidates import ALIGN, doc_ranges, index_cells  # noqa: E402

OURS_ONLY = ROOT / "data" / "private" / "schabas_ours_only.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    held = {s for (s,) in con.execute("SELECT symbol FROM documents WHERE instrument = 'UDHR'")}
    cells = index_cells(held)
    al = json.loads(ALIGN.read_text())
    seg = {sid: (fin, poss or "") for sid, fin, poss in con.execute(
        "SELECT id, CASE WHEN coalesce(article_instrument, 'UDHR') = 'UDHR' THEN final_article END, possible_article FROM segments "
        "WHERE symbol IN (SELECT symbol FROM documents WHERE instrument = 'UDHR')")}
    tagged = defaultdict(set)
    for sym, fin in con.execute("SELECT symbol, final_article FROM segments WHERE final_article IS NOT NULL AND "
                                "coalesce(article_instrument, 'UDHR') = 'UDHR'"):
        tagged[sym].add(int(fin))
    meeting = lambda s: "/SR." in s or "/PV." in s
    kind = lambda s: "documents" if not meeting(s) else "article debates" if tagged[s] else "general debates"
    res = defaultdict(Counter)
    for (sym, label), arts in cells.items():
        ids = al.get(sym, {}).get(label)
        for art in arts:
            if ids is None or not ids:
                k = "not aligned"
            elif any(seg.get(i, (None, ""))[0] == art for i in ids):
                k = "covered"
            elif any(re.search(rf"\bUDHR {art}(?!\d)", seg.get(i, (None, ""))[1]) for i in ids):
                k = "possible"
            else:
                k = "missed"
            res[("all", "all")][k] += 1
            res[("kind", kind(sym))][k] += 1
            res[("article", str(art))][k] += 1
    # the pairs only we have: records the book reproduces, articles we tag there that the index never lists in them
    in_book = set(doc_ranges())
    listed = defaultdict(set)
    for (sym, _), arts in cells.items():
        listed[sym] |= set(arts)
    ours_only = sorted((sym, a) for sym in tagged if sym in in_book for a in tagged[sym] if a not in listed[sym])
    OURS_ONLY.write_text(json.dumps(ours_only))
    def line(c: Counter) -> str:
        n = sum(c.values()) or 1
        aligned = n - c["not aligned"] or 1
        return (f"covered {c['covered']:5} ({c['covered'] / aligned:.0%} of aligned)  possible {c['possible']:5}  "
                f"missed {c['missed']:5}  not aligned {c['not aligned']:5}")
    print(f"index cells (article, record, UN page): {sum(res[('all', 'all')].values())} {args.label}", file=sys.stderr)
    print(f"  all              {line(res[('all', 'all')])}", file=sys.stderr)
    for k in ("article debates", "general debates", "documents"):
        print(f"  {k:16} {line(res[('kind', k)])}", file=sys.stderr)
    for a in sorted((k for g, k in res if g == "article"), key=int):
        print(f"  art {a:>2}           {line(res[('article', a)])}", file=sys.stderr)
    print(f"(record, article) pairs only we tag, in records the book reproduces: {len(ours_only)} (ids: {OURS_ONLY.relative_to(ROOT)})",
          file=sys.stderr)
    if args.json:
        out = json.loads(args.json.read_text()) if args.json.exists() else {}
        out[args.label or "latest"] = {f"{g}:{k}": dict(c) for (g, k), c in res.items()} | {"ours_only_pairs": len(ours_only)}
        args.json.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
