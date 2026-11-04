#!/usr/bin/env python3
"""Precision of article tags, from the hand-checked samples in data/gold/article_tags.jsonl.

Each round is a fresh stratified sample (eval/article_tag_sample.py) judged by hand: is the
speech about the article it is tagged with? Rounds before a fix measure what the fix was for;
the latest round is the current estimate. A 95% interval (Wilson) is given, since 50 speeches
leave room either way.

With --jev, each round again among the tags Jev's check keeps (probability >= 0.5, from
data/cache/jev_article_check_v2.json, written by eval/jev_article_check.py): what the round's
precision would have been with the check in place.

Usage: python3 eval/article_tag_precision.py [--jev]
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def main() -> int:
    rows = [json.loads(l) for l in (ROOT / "data" / "gold" / "article_tags.jsonl").read_text().splitlines()]
    by_round = defaultdict(list)
    for r in rows:
        by_round[r["round"]].append(r)
    checks = {}
    if "--jev" in sys.argv:
        checks = json.loads((ROOT / "data" / "cache" / "jev_article_check_v2.json").read_text())
    for rnd, rs in sorted(by_round.items()):
        if checks:
            n_all = len(rs)
            rs = [r for r in rs if (checks.get(r["id"]) if checks.get(r["id"]) is not None else 1) >= 0.5]
            print(f"(Jev drops {n_all - len(rs)} of {n_all}) ", end="")
        k, n = sum(r["correct"] for r in rs), len(rs)
        lo, hi = wilson(k, n)
        strata = defaultdict(lambda: [0, 0])
        for r in rs:
            s = r["stratum"].split("/")[0] + "/" + r["stratum"].split("/")[1]
            strata[s][0] += r["correct"]
            strata[s][1] += 1
        print(f"round {rnd}: {k}/{n} = {k / n:.0%} (95% interval {lo:.0%}-{hi:.0%})  "
              + "  ".join(f"{s} {a}/{b}" for s, (a, b) in strata.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
