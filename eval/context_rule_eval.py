#!/usr/bin/env python3
"""Round 114: a variant of the context rule (api/build_db.py, TRAVAUX_CTX_VARIANT) measured on the gold.

  python3 eval/context_rule_eval.py BASE.sqlite3 VARIANT.sqlite3 [--sample 40 --seed 114 --out FILE]

Gold rows (data/gold/article_tags.jsonl) judged right whose tag is in BASE: lost if VARIANT tags the segment otherwise. Rows
judged wrong: fixed if VARIANT neither keeps that tag nor keeps the segment's context article (a refusal hides the tag in both
databases, the context article shows what the rule did). Changed tags outside the gold are counted, and --sample draws them
for the blind check (old tag, new tag hidden from the judges).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"(UDHR|ICCPR\+ICESCR|ICCPR|ICESCR)\s+(?:art\.\s+)?(\d+)")


def tags(db: Path) -> dict[str, tuple]:
    con = sqlite3.connect(db)
    return {i: (k, f"{ins} {fin}" if fin else None, d) for i, k, ins, fin, d in
            con.execute("SELECT id, kind, article_instrument, final_article, draft_article FROM segments")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", type=Path)
    ap.add_argument("variant", type=Path)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=114)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    B, V = tags(a.base), tags(a.variant)
    gold = {}
    for line in (ROOT / "data" / "gold" / "article_tags.jsonl").open():
        g = json.loads(line)
        m = TAG_RE.match(g.get("tag") or "")
        if m and g.get("correct") is not None:
            gold.setdefault(g["id"], []).append((f"{m.group(1)} {m.group(2)}", g["correct"]))
    c = Counter()
    for sid, rows in gold.items():
        if sid not in B:
            continue
        for tag, right in rows:
            if right and B[sid][1] == tag:
                c["right in base"] += 1
                c["right lost"] += V[sid][1] != tag
            elif not right:
                c["wrong"] += 1
                c["wrong fixed"] += V[sid][1] != tag and (V[sid][2] != B[sid][2] or B[sid][1] == tag)
    changed = [sid for sid in B if B[sid][1] != V[sid][1]]
    outside = [sid for sid in changed if sid not in gold]
    c["tags changed"], c["outside the gold"] = len(changed), len(outside)
    kinds = Counter((B[s][0], "removed" if V[s][1] is None else "added" if B[s][1] is None else "moved") for s in changed)
    print(json.dumps(dict(c)), json.dumps(sorted(kinds.items())))
    if a.sample and a.out:
        pick = sorted(random.Random(a.seed).sample(outside, min(a.sample, len(outside))))
        a.out.write_text(json.dumps([{"id": s, "old": B[s][1], "new": V[s][1], "kind": B[s][0]} for s in pick], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
