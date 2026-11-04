#!/usr/bin/env python3
"""Pilot of judging the possible articles (preregistered in docs/devlog.md, 29 Oct 2026): the untagged speeches whose
possible_article holds a readers' suggestion (not the Schabas pages), one item per (speech, article), a random sample
for two blind judges, and the tally of their answers.

  python3 eval/possible_pilot.py draw --n 100 --seed 2044 --out eval/possible_pilot
  python3 eval/possible_pilot.py tally eval/possible_pilot JUDGE_A.json JUDGE_B.json
  python3 eval/possible_pilot.py rest --batches 10 --out eval/possible_full     # the pairs the pilot did not draw
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "api"))
from merge_tag_changes import COLS, item  # noqa: E402

SUGGESTION_RE = re.compile(r"^(UDHR|ICCPR|ICESCR|ICCPR\+ICESCR) (\d{1,2}) ")


def pairs(con) -> tuple[list[tuple[dict, str, int]], dict[str, list[dict]]]:
    con.row_factory = sqlite3.Row
    by_sym = defaultdict(list)
    for r in con.execute(f"SELECT {COLS}, possible_article FROM segments ORDER BY symbol, seq"):
        by_sym[r["symbol"]].append(dict(r))
    out = []
    for segs in by_sym.values():
        for s in segs:
            if s["kind"] != "speech" or s["final_article"] is not None or not s["possible_article"]:
                continue
            for part in s["possible_article"].split("; "):
                m = SUGGESTION_RE.match(part + " ")
                if m and "Schabas" not in part:
                    out.append((s, m.group(1), int(m.group(2))))
    return out, by_sym


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draw")
    d.add_argument("--n", type=int, default=100)
    d.add_argument("--seed", type=int, default=2044)
    d.add_argument("--out", type=Path, required=True)
    r = sub.add_parser("rest")
    r.add_argument("--batches", type=int, default=10)
    r.add_argument("--out", type=Path, required=True)
    t = sub.add_parser("tally")
    t.add_argument("dir", type=Path)
    t.add_argument("a", type=Path)
    t.add_argument("b", type=Path)
    args = ap.parse_args()
    con = sqlite3.connect(f"file:{ROOT / 'data' / 'travaux.sqlite3'}?mode=ro", uri=True)
    if args.cmd in ("draw", "rest"):
        ps, by_sym = pairs(con)
        titles = defaultdict(dict)
        for r in csv.DictReader((ROOT / "data" / "concordance" / "articles.csv").open(encoding="utf-8")):
            titles[r["instrument"]][r["article"]] = r["short_title"]
        import server
        finals = {i: server.final_texts(i) for i in ("UDHR", "ICCPR", "ICESCR")}
        if args.cmd == "draw":
            sample = random.Random(args.seed).sample(ps, args.n)
        else:
            drawn = {(x["segment_id"], x["tag"].split(" (")[0]) for x in json.loads((ROOT / "eval" / "possible_pilot" / "sample.json").read_text())}
            sample = [p for p in ps if (p[0]["id"], f"{p[1]} art. {p[2]}") not in drawn]
        items = []
        for k, (s, inst, fin) in enumerate(sample):
            segs = by_sym[s["symbol"]]
            i = next(j for j, x in enumerate(segs) if x["id"] == s["id"])
            context = " ".join(x["text"] or "" for x in segs[max(0, i - 3):i])
            it = item(s, "possible/pilot", titles, finals, {"article_instrument": inst, "final_article": fin, "draft_article": None},
                      "a candidate article", context)
            it["id"] = f"{'P' if args.cmd == 'draw' else 'F'}{k + 1:03d}"
            it["segment_id"] = s["id"]
            items.append(it)
        args.out.mkdir(parents=True, exist_ok=True)
        if args.cmd == "rest":
            size = math.ceil(len(items) / args.batches)
            for b in range(args.batches):
                (args.out / f"batch{b + 1:02d}.json").write_text(json.dumps(items[b * size:(b + 1) * size], ensure_ascii=False, indent=1) + "\n")
            print(f"{len(items)} pairs in {args.batches} batches -> {args.out}")
            return 0
        (args.out / "sample.json").write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n")
        print(f"{len(ps)} pairs of {len({s['id'] for s, _, _ in ps})} speeches; {len(items)} drawn -> {args.out / 'sample.json'}")
        return 0
    items = json.loads((args.dir / "sample.json").read_text())
    a, b = json.loads(args.a.read_text()), json.loads(args.b.read_text())
    both = [x for x in items if a[x["id"]]["correct"] and b[x["id"]]["correct"]]
    split = [x for x in items if a[x["id"]]["correct"] != b[x["id"]]["correct"]]
    ps, _ = pairs(con)
    lo, hi = wilson(len(both), len(items))
    print(f"both right {len(both)}/{len(items)} ({len(both) / len(items):.0%}; 95% {lo:.0%}-{hi:.0%}); split {len(split)}; "
          f"projected for {len(ps)} pairs: {len(both) / len(items) * len(ps):.0f} ({lo * len(ps):.0f}-{hi * len(ps):.0f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
