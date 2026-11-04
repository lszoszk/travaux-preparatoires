#!/usr/bin/env python3
"""One-off repair of the merge of 21 October 2026 (preregistered in docs/devlog.md, 22 Oct): pipeline/resegment.py gave the
id-keyed data of a split speech to its larger new part; the speech-level tables now follow the part that keeps the
opening (resegment.SPEECH_TABLES, as resegment.py does from 22 Oct), and Jev's answers about the old, run-together text are
dropped so that both parts are asked afresh.

  python3 pipeline/oneoff_split_fix.py OLD_SEGMENTS_DIR ID_MAP OLD_CACHE_DIR [--commit-before REV] [--dry-run]
OLD_SEGMENTS_DIR: data/segments as it was before the merge; ID_MAP: the merge's data/id_maps/*.json; OLD_CACHE_DIR:
data/cache before the merge; REV: the commit before the merge (the tables as they were).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import resegment  # noqa: E402

TABLES = [("data/concordance/reader_tags.csv", "segment_id"), ("data/concordance/speech_retags.csv", "segment_id"),
          ("data/concordance/tag_rejections.csv", "segment_id"), ("data/concordance/topic_rejections.csv", "segment_id"),
          ("data/tagger/accepted.csv", "segment_id"), ("data/concordance/possible_articles.csv", "segment_id"),
          ("data/concordance/schabas_candidates.csv", "segment_id"), ("data/gazetteer/speaker_fixes.csv", "segment_id")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old_segments", type=Path)
    ap.add_argument("id_map", type=Path)
    ap.add_argument("old_cache", type=Path)
    ap.add_argument("--commit-before", default="3f68292^")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    m = json.loads(args.id_map.read_text())
    moved, how = m["moved"], m["how"]
    pairs = {}  # old id -> (where its data went, the part with its opening)
    for rec in m["records"]:
        old = json.loads((args.old_segments / f"{rec}.vote.json").read_text())
        new = json.loads((resegment.SEG / f"{rec}.vote.json").read_text())
        _, _, opening = resegment.align(old, new)
        for oid, c in opening.items():
            t = moved.get(oid, oid)
            if how.get(oid) == "split" and c != t:
                pairs[oid] = (t, c)
    print(f"split segments whose data went to another part than their opening: {len(pairs)}", file=sys.stderr)
    done = Counter()
    for rel, col in TABLES:
        path = ROOT / rel
        before = list(csv.DictReader(io.StringIO(subprocess.run(["git", "-C", str(ROOT), "show", f"{args.commit_before}:{rel}"],
                                                                capture_output=True, text=True, check=True).stdout)))
        rows = list(csv.DictReader(path.open()))
        fields = list(rows[0].keys()) if rows else []
        for b in before:
            if b[col] not in pairs:
                continue
            t, c = pairs[b[col]]
            want = {k: v for k, v in b.items() if k != col}
            for r in rows:
                if r[col] == t and {k: r.get(k) for k in want} == want:
                    r[col] = c
                    done[f"{Path(rel).name}: to the opening"] += 1
                    break
        if not args.dry_run and rows:
            with path.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
                w.writeheader()
                w.writerows(rows)
    gold = ROOT / "data" / "gold" / "speakers_audit.jsonl"
    rows = [json.loads(x) for x in gold.read_text().splitlines() if x.strip()]
    for r in rows:
        for oid, (t, c) in pairs.items():
            if r["id"] == t and r.get("checked", "").startswith("2026-10-03"):  # (the audit was before the merge)
                old_ids = {json.loads(x)["id"] for x in subprocess.run(["git", "-C", str(ROOT), "show", f"{args.commit_before}:data/gold/speakers_audit.jsonl"],
                                                                         capture_output=True, text=True, check=True).stdout.splitlines() if x.strip()}
                if oid in old_ids:
                    r["id"] = c
                    done["speakers_audit.jsonl: to the opening"] += 1
    if not args.dry_run:
        gold.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    for path in sorted((ROOT / "data" / "cache").glob("jev_*.json")):
        old = args.old_cache / path.name
        old_keys = json.loads(old.read_text()) if old.exists() else {}
        cache = json.loads(path.read_text())
        for key in old_keys:
            sid, sep, rest = key.partition("|")
            if sid in pairs:
                t = pairs[sid][0]
                if cache.pop(t + sep + rest, None) is not None:
                    done[f"{path.name}: dropped (asked again)"] += 1
        if not args.dry_run:
            path.write_text(json.dumps(cache))
    for k, v in sorted(done.items()):
        print(f"  {k}: {v}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
