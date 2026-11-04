#!/usr/bin/env python3
"""The tags before and after the repair of split speeches' data (pipeline/oneoff_split_fix.py; preregistered in
docs/devlog.md, 22 Oct 2026): the segmentation is the same, so speeches are compared by id. Counts new, changed and
dropped tags, how many of the tags the merge had dropped are back (DROPPED: a JSON list of {id, old_tag}), and writes a
blind sample of 20 new or changed tags (seed 2033) in the form of eval/audit_sample.py.

  python3 eval/split_fix_check.py OLD.sqlite3 DROPPED.json [--out eval/split_fix]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "api"))
from merge_tag_changes import item, segments, tag  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old", type=Path)
    ap.add_argument("dropped", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "eval" / "split_fix")
    args = ap.parse_args()
    old, new = segments(args.old), segments(ROOT / "data" / "travaux.sqlite3")
    import csv
    import server
    titles = {}
    for r in csv.DictReader((ROOT / "data" / "concordance" / "articles.csv").open(encoding="utf-8")):
        titles.setdefault(r["instrument"], {})[r["article"]] = r["short_title"]
    finals = {i: server.final_texts(i) for i in ("UDHR", "ICCPR", "ICESCR")}
    n, changed = Counter(), []
    for sym, segs in new.items():
        before = {s["id"]: s for s in old.get(sym, [])}
        for k, s in enumerate(segs):
            if s["kind"] != "speech":
                continue
            o = before.get(s["id"])
            a, b = tag(o) if o else None, tag(s)
            kind = "same" if a == b else "new" if not a else "dropped" if not b else "changed"
            n[kind] += 1
            if kind in ("new", "changed"):
                changed.append(item(s, f"split-fix/{kind}", titles, finals, s, s["article_mapping"] or "", segs[k - 1]["text"] if k else ""))
    now = {s["id"]: tag(s) for segs in new.values() for s in segs}
    dropped = json.loads(args.dropped.read_text())
    back = sum(1 for d in dropped if now.get(d["id"]) and f"{now[d['id']][0]} {now[d['id']][1]}" == d["old_tag"])
    for k, v in n.most_common():
        print(f"  {k}: {v}", file=sys.stderr)
    print(f"of the {len(dropped)} tags the merge dropped, back: {back}", file=sys.stderr)
    args.out.mkdir(parents=True, exist_ok=True)
    sample = random.Random(2033).sample(changed, min(20, len(changed)))
    (args.out / "sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=1) + "\n")
    (args.out / "counts.json").write_text(json.dumps({**dict(n), "dropped_by_merge_back": back, "dropped_by_merge": len(dropped)},
                                                     indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
