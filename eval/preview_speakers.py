#!/usr/bin/env python3
"""Speakers of the current database against a preview's (pipeline/preview_mixed.py), speech by speech through the preview's id map
(data/id_maps/<latest>.json in the copy: old id -> new id), judged by the name the new segment's own text prints at its opening.

For each speech whose speaker changed within the same delegation: "better" (the new speaker fits the printed name, the old did
not), "worse" (the reverse), "both fit", "neither fits", "no printed name". A speaker fits when it equals the printed name without
spaces, hyphens or accents, or at a ratio of at least 90, or equals its last word. Changes across delegations are left out: they
are mostly the id map's (an old speech whose words went to a neighbour after a split).

  python3 eval/preview_speakers.py OLD.sqlite3 <copy> [--json OUT] [--list worse]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from name_guard import bare  # noqa: E402
from segment import POSTTITLE_RE, SPEAKER_RE  # noqa: E402


def printed(text: str) -> str | None:
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    m = SPEAKER_RE.match(first) or POSTTITLE_RE.match(first)
    return m.group("name") if m else None


def fits(speaker: str, name: str | None) -> bool:
    if not speaker or not name:
        return False
    a, b = bare(speaker), bare(name)
    return a == b or fuzz.ratio(a, b) >= 90 or bool(name.split()) and a == bare(name.split()[-1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old", type=Path)
    ap.add_argument("copy", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--list", choices=["better", "worse", "both fit", "neither fits"])
    args = ap.parse_args()
    idmap = json.loads(sorted((args.copy / "data" / "id_maps").glob("*.json"))[-1].read_text())
    moved, lost = idmap["moved"], set(idmap["lost"])
    q = "SELECT id, upper(coalesce(speaker, '')), coalesce(delegation, ''), text FROM segments WHERE kind = 'speech'"
    old = {i: r for i, *r in sqlite3.connect(args.old).execute(q)}
    new = {i: r for i, *r in sqlite3.connect(args.copy / "data" / "travaux.sqlite3").execute(q)}
    res, examples, same, changed = Counter(), {}, 0, 0
    for i, (sp, dl, _) in old.items():
        j = moved.get(i, i)
        if i in lost or j not in new:
            continue
        sp2, dl2, t2 = new[j]
        if sp == sp2:
            same += 1
            continue
        changed += 1
        if dl != dl2:
            continue
        name = printed(t2)
        if name is None:
            k = "no printed name"
        else:
            f1, f2 = fits(sp, name), fits(sp2, name)
            k = "better" if f2 and not f1 else "worse" if f1 and not f2 else "both fit" if f1 else "neither fits"
        res[k] += 1
        examples.setdefault(k, []).append({"old_id": i, "new_id": j, "old": sp, "new": sp2, "printed": name})
    print(f"speeches through the id map: same speaker {same}, changed {changed}; within the same delegation: {dict(res)}",
          file=sys.stderr)
    if args.list:
        for x in examples.get(args.list, []):
            print(f"  {x['new_id']:24} {x['old']:20} -> {x['new']:20} printed {x['printed']}", file=sys.stderr)
    if args.json:
        args.json.write_text(json.dumps({"same": same, "changed": changed, "within_delegation": dict(res), "examples": examples},
                                        ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
