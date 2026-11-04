#!/usr/bin/env python3
"""Plausibility check for article tags: does a tagged speech talk about its article?

For every speech tagged with a final UDHR article (and at least 40 words long), the speech
is compared (TF-IDF cosine) with the 30 final article texts. A tag is "plausible" when its
article is among the speech's 5 closest. Low rates for one (stage, draft article) pair point
to a wrong concordance row. This is a sanity signal, not a gold standard: debates stray.

Usage: python3 eval/article_topic_check.py
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STOP = set("the of and to a in that be it was he his for as not on by with which is had this should would or an "
           "right rights everyone every one shall have has all their its are were at from any no such article "
           "said representative delegation committee commission text his her they them been also but if".split())


def toks(t: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]{3,}", t.lower()) if w not in STOP]


def main() -> int:
    finals = json.loads((ROOT / "data/concordance/udhr_final.json").read_text())["articles"]
    con = sqlite3.connect(ROOT / "data/travaux.sqlite3")
    segs = con.execute("SELECT s.final_article, d.stage || CASE WHEN s.article_mapping LIKE '%chair or agenda%' "
                       "THEN ' (from chair/agenda)' ELSE ' (under a heading)' END, s.draft_article, s.text FROM segments s JOIN documents d "
                       "ON d.symbol = s.symbol WHERE s.kind='speech' AND s.final_article IS NOT NULL AND s.article_instrument='UDHR'").fetchall()
    docs = {int(k): toks(v) for k, v in finals.items()}
    df = Counter(w for ws in docs.values() for w in set(ws))
    idf = {w: math.log(31 / (1 + c)) + 1 for w, c in df.items()}
    vec = {}
    for k, ws in docs.items():
        tf = Counter(ws)
        v = {w: c * idf[w] for w, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values()))
        vec[k] = {w: x / norm for w, x in v.items()}
    by_pair = defaultdict(lambda: [0, 0])
    by_stage = defaultdict(lambda: [0, 0])
    for fin, stage, draft, text in segs:
        ws = [w for w in toks(text) if w in idf]
        if len(text.split()) < 40 or not ws:
            continue
        tf = Counter(ws)
        scores = sorted(((sum(c * idf[w] * vec[k].get(w, 0) for w, c in tf.items()), k) for k in vec), reverse=True)
        ok = fin in [k for _, k in scores[:5]]
        for key, d in (((stage, draft, fin), by_pair), (stage, by_stage)):
            d[key][0] += ok
            d[key][1] += 1
    print("stage: plausible / checked")
    for st, (ok, n) in sorted(by_stage.items(), key=lambda x: str(x[0])):
        print(f"  {st}: {ok}/{n} = {ok / n:.0%}")
    print("\n(stage, draft -> final) pairs with <= 30% plausible (n >= 8):")
    for (st, dr, fin), (ok, n) in sorted(by_pair.items(), key=lambda x: x[1][0] / x[1][1]):
        if n >= 8 and ok / n <= 0.3:
            print(f"  {st} draft {dr} -> final {fin}: {ok}/{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
