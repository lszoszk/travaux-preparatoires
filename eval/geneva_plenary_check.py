#!/usr/bin/env python3
"""Tags of the Geneva plenary (E/CN.4/SR.34-42) against the maps of those meetings.

data/gold/geneva_plenary_maps.json gives, for every passage, the article(s) the record shows under
discussion: a Declaration article (E/CN.4/57 numbering), a Convention article (E/CN.4/56), or a pair
of them. A tagged speech agrees when its text and number are among those of its passage. Coverage:
the speeches in an article's passage that carry a tag (after Jev's check).

Usage: python3 eval/geneva_plenary_check.py [-v]
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def numbers(a) -> set[str]:
    t = str(a or "")
    r = re.fullmatch(r"(\d+)\s*(?:-|to)\s*(\d+)", t)
    if r:
        return {str(i) for i in range(int(r.group(1)), int(r.group(2)) + 1)}
    return set(re.findall(r"\d+", t if "," in t else t.split(".")[0]))


def main() -> int:
    maps = json.loads((ROOT / "data/gold/geneva_plenary_maps.json").read_text())["maps"]
    ref = {}
    for m in maps:
        for sp in m["spans"]:
            ok = set()
            if sp["instrument"] in ("declaration", "pair"):
                ok |= {("UDHR", n) for n in numbers(sp["declaration_article"])}
            if sp["instrument"] in ("convention", "pair"):
                ok |= {("ICCPR", n) for n in numbers(sp["convention_article"])}
            for q in range(sp["from_seq"], sp["to_seq"] + 1):
                ref[(m["symbol"], q)] = ok
        for ex in m["exceptions"]:
            inst = {"declaration": "UDHR", "convention": "ICCPR"}.get(ex["instrument"])
            ref[(m["symbol"], ex["seq"])] = {(inst, n) for n in numbers(ex["article"])} if inst else set()
    con = sqlite3.connect(ROOT / "data/travaux.sqlite3")
    rows = con.execute("SELECT s.symbol, s.seq, s.article_instrument, s.draft_article, s.final_article FROM segments s "
                       "JOIN documents d USING(symbol) WHERE d.stage = 'geneva_plenary' AND s.kind = 'speech'").fetchall()
    tagged = [r for r in rows if r[4] is not None]
    agree = [r for r in tagged if (r[2], (re.match(r"\d+", r[3] or "") or [None])[0]) in ref.get((r[0], r[1]), set())]
    in_spans = [r for r in rows if ref.get((r[0], r[1]))]
    covered = [r for r in in_spans if r[4] is not None]
    print(f"tagged speeches agreeing with the maps: {len(agree)}/{len(tagged)}")
    print(f"speeches in an article's passage that carry a tag: {len(covered)}/{len(in_spans)}")
    if "-v" in sys.argv:
        for r in tagged:
            if r not in agree:
                print("  ", r, sorted(ref.get((r[0], r[1]), set())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
