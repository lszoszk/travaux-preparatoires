#!/usr/bin/env python3
"""UN symbols that Schabas reproduces or lists but the UN Library guide does not link.

Inputs (private, from eval/schabas_reference.py --toc --all):
  data/private/schabas_toc.json       the book's Table of documents
  eval/private/reference/*.json       the documents found in the book's text
Only UN symbols leave the private area: data/manifest/udhr_supplement.json lists
them with discovery_basis "finding_aid", to be fetched from the UN like the rest.

Usage: python3 pipeline/build_udhr_supplement.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_udhr_manifest import SYMBOL_RE, doc_type, meeting_no, series  # noqa: E402
from common import canon  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "data" / "manifest" / "udhr.json"
TOC = ROOT / "data" / "private" / "schabas_toc.json"
REF = ROOT / "eval" / "private" / "reference"
OUT = ROOT / "data" / "manifest" / "udhr_supplement.json"


def main() -> int:
    def fix(s: str) -> str:  # table typos such as "A/C.3.SR.91"
        return canon(re.sub(r"(\d)\.(SR|PV|L)\.", r"\1/\2.", s))

    guide = {canon(d["symbol"]) for d in json.loads(GUIDE.read_text())["documents"]}
    toc = {fix(r["symbol"]) for r in json.loads(TOC.read_text())}
    text = {fix(json.loads(p.read_text())["symbol"]) for p in REF.glob("*.json")}
    # Symbols read from the book's text are confirmed by its running heads
    # (eval/schabas_reference.py), so they are kept too; ones that don't exist are
    # reported as unavailable by the harvest.
    extra = sorted(s for s in (toc | text) - guide if SYMBOL_RE.match(s))
    only_text = sorted(text - toc - guide)
    docs = [{"symbol": s, "doc_type": doc_type(s), "series": series(s), "meeting_no": meeting_no(s),
             "discovery_basis": "finding_aid" if s in toc else "finding_aid_text", "meeting_date": None,
             "mentions": []} for s in extra]
    OUT.write_text(json.dumps({
        "description": "UDHR drafting documents listed in a published compilation's table of documents "
                       "but not linked from the UN Library guide (symbols only)",
        "count": len(docs), "documents": docs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"guide {len(guide)} | book table {len(toc)} | book text {len(text)}", file=sys.stderr)
    print(f"in both guide and table: {len(guide & toc)}", file=sys.stderr)
    print(f"not in guide -> supplement: {len(extra)} -> {OUT.relative_to(ROOT)}", file=sys.stderr)
    print(f"guide only (not in the book's table): {len(guide - toc)}", file=sys.stderr)
    print(f"book text only (not in table or guide; included): {len(only_text)} e.g. {only_text[:8]}", file=sys.stderr)
    by = {}
    for d in docs:
        by[d["series"]] = by.get(d["series"], 0) + 1
    print("supplement by series:", sorted(by.items(), key=lambda kv: -kv[1])[:12], file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
