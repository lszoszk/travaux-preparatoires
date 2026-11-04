#!/usr/bin/env python3
"""Speeches whose attribution contradicts their own printed opening.

A speech's text opens with the speaker as the record prints it ("Mr. PAVLOV (Union of Soviet
Socialist Republics) pointed out ..."). If the name it was attributed to fits neither that
printed name nor that printed delegation, something went wrong: typically another engine's
reading of a neighbouring opening was taken for this one. Printed names are OCR, so a
mismatch in one of the two is normal; in both, it is an error to look at.

Also counted: in the General Assembly's printed records, speeches whose name three engines or
more read alike, in capitals, and which were attributed to someone clearly different
("Mr. SINHA (India)" given to SAKSENA): the attendee list lacked the speaker.

Usage: python3 eval/attribution_consistency.py [--show 20]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]


def fold(s: str | None) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", (s or "").upper()) if not unicodedata.combining(c))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=20)
    args = ap.parse_args()
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    rows = con.execute("SELECT id, speaker_raw, country_raw, speaker, delegation, speaker_method, votes FROM segments "
                       "WHERE kind='speech' AND speaker IS NOT NULL AND speaker_raw IS NOT NULL").fetchall()
    bad, strangers = [], []
    for id_, raw, craw, sp, de, meth, votes in rows:
        names = [m.group(1) for v in json.loads(votes or "[]") for m in [re.match(r"([A-Z][A-Z' -]+?) \(", v)] if m]
        top = max(set(names), key=names.count, default="")
        if id_.startswith("a_") and names.count(top) >= 3:
            a, b = set(re.split(r"[\s-]+", fold(top))), set(re.split(r"[\s-]+", fold(sp)))
            if not (a <= b or b <= a) and fuzz.ratio(fold(top), fold(sp)) < 75:
                strangers.append((id_, top, sp, de, meth))
        name = max(fuzz.ratio(fold(raw), fold(sp)),
                   fuzz.partial_ratio(fold(raw), fold(sp)) if min(len(raw), len(sp)) >= 4 else 0)
        deleg = fuzz.partial_ratio(fold(craw)[:40], fold(de)[:40])
        if name < 50 and deleg < 60:
            bad.append((id_, raw, craw, sp, de, meth))
    print(f"{len(rows)} attributed speeches; {len(bad)} contradict their printed name and delegation "
          f"({dict(Counter(b[5] for b in bad))})")
    for b in bad[:args.show]:
        print("  ", b)
    print(f"{len(strangers)} in printed records attributed to someone other than the name the engines agree on")
    for s in strangers[:args.show]:
        print("  ", s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
