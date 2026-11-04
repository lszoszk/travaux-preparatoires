#!/usr/bin/env python3
"""Scores the blind review (eval/preview_review.py): the answers joined with eval/preview_review/key.json, so that "A"/"B"
become "preview better"/"current better". Per item kind: preview better, current better, both good, both wrong, unsure; the
share of the preview among the decided items (one or the other better); and the reviewer's consistency on the repeats (the same
item shown again with A and B swapped: the same verdict after unswapping). The repeats are not counted twice in the shares.

  python3 eval/preview_review_score.py [--json eval/preview_review/score.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "eval" / (sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else "preview_review")


def verdict(choice: str, key: dict) -> str:
    if choice in ("A", "B"):
        return "preview better" if key[choice] == "preview" else "current better"
    return choice


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    ap.add_argument("--dir", default="preview_review", help="the round: a folder under eval/")
    args = ap.parse_args()
    items = {it["id"]: it for it in json.loads((DIR / "items.json").read_text())["items"]}
    key = json.loads((DIR / "key.json").read_text())
    answers = {}
    path = DIR / "answers.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                a = json.loads(line)
                answers[a["id"]] = a
    v = {i: verdict(a["choice"], key[i]) for i, a in answers.items() if i in key}
    by_kind = defaultdict(Counter)
    for i, x in v.items():
        if "repeat_of" not in key[i]:
            by_kind[items[i]["kind"]][x] += 1
    out = {"answered": len(v), "items": len(items), "by_kind": {}, "repeats": {}}
    print(f"answered {len(v)} of {len(items)}", file=sys.stderr)
    for kind in sorted(by_kind):
        c = by_kind[kind]
        decided = c["preview better"] + c["current better"]
        share = c["preview better"] / decided if decided else None
        out["by_kind"][kind] = {**c, "preview share of decided": share}
        print(f"  {kind:8} " + ", ".join(f"{k} {c[k]}" for k in
              ("preview better", "current better", "both good", "both wrong", "unsure"))
              + (f"; preview {share:.0%} of {decided} decided" if decided else ""), file=sys.stderr)
    pairs = [(i, key[i]["repeat_of"]) for i in v if "repeat_of" in key[i] and key[i]["repeat_of"] in v]
    same = sum(v[r] == v[o] for r, o in pairs)
    out["repeats"] = {"pairs": len(pairs), "same": same, "differ": [{"id": o, "first": v[o], "again": v[r]} for r, o in pairs if v[r] != v[o]]}
    print(f"  repeats: {same} of {len(pairs)} the same verdict", file=sys.stderr)
    notes = [{"id": i, "kind": items[i]["kind"], "symbol": items[i]["symbol"], "page": items[i]["page"], "verdict": v[i], "note": answers[i]["note"]}
             for i in v if answers[i].get("note")]
    out["notes"] = notes
    for n in notes:
        print(f"  note {n['id']} {n['symbol']} p{n['page']} ({n['verdict']}): {n['note']}", file=sys.stderr)
    if args.json:
        args.json.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
