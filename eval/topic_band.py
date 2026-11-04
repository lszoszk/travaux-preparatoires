#!/usr/bin/env python3
"""The topics Jev picked in a band of p (preregistered in docs/devlog.md, 29 Oct 2026: 0.8-0.9, then 0.7-0.8): every
untagged speech in the band, in batches for two blind judges, and the rows both judges let through.

  python3 eval/topic_band.py draw --batches 6 --out eval/topic_band
  python3 eval/topic_band.py draw --low 0.7 --high 0.8 --prefix S --batches 11 --out eval/topic_band_07
  python3 eval/topic_band.py accept eval/topic_band JUDGE_DIR      # JUDGE_DIR/opus_NN.json, sonnet_NN.json -> topic_accepted.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED = ROOT / "data" / "concordance" / "topic_accepted.csv"
GENERAL = {"topic": "general", "label": "General debate",
           "description": "the declaration or the covenant(s) as a whole, or several of the questions at once, none of them dominating"}


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draw")
    d.add_argument("--batches", type=int, default=6)
    d.add_argument("--low", type=float, default=0.8)
    d.add_argument("--high", type=float, default=0.9)
    d.add_argument("--prefix", default="T")
    d.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("accept")
    a.add_argument("dir", type=Path)
    a.add_argument("judges", type=Path)
    args = ap.parse_args()
    if args.cmd == "accept":
        items = [x for p in sorted(args.dir.glob("batch*.json")) for x in json.loads(p.read_text())]
        A, B = {}, {}
        for p in sorted(args.judges.glob("opus_*.json")):
            A.update(json.loads(p.read_text()))
        for p in sorted(args.judges.glob("sonnet_*.json")):
            B.update(json.loads(p.read_text()))
        both = [x for x in items if A[x["id"]]["correct"] and B[x["id"]]["correct"]]
        split = sum(A[x["id"]]["correct"] != B[x["id"]]["correct"] for x in items)
        mine = {x["segment_id"] for x in items}  # the other bands' rows stay
        kept = [r for r in csv.DictReader(ACCEPTED.open(encoding="utf-8")) if r["segment_id"] not in mine] if ACCEPTED.exists() else []
        with ACCEPTED.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["segment_id", "topic", "note"], lineterminator="\n")
            w.writeheader()
            w.writerows(kept)
            for x in both:
                w.writerow({"segment_id": x["segment_id"], "topic": x["topic"],
                            "note": f"Jev's pick at p = {x['p']:.2f}, judged right by two blind judges (29 October 2026, {x['id']})"})
        (args.dir / "judgments.json").write_text(json.dumps({x["id"]: {"opus": A[x["id"]], "sonnet": B[x["id"]]} for x in items},
                                                            ensure_ascii=False, indent=1) + "\n")
        print(f"{len(items)} judged: both right {len(both)}, split {split}, both wrong {len(items) - len(both) - split} -> {ACCEPTED}")
        return 0
    con = sqlite3.connect(f"file:{ROOT / 'data' / 'travaux.sqlite3'}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    topics = {r["topic"]: r for r in csv.DictReader((ROOT / "data" / "concordance" / "topics.csv").open(encoding="utf-8"))}
    topics["general"] = GENERAL
    cache = json.loads((ROOT / "data" / "cache" / "jev_topics.json").read_text())
    segs = {}
    for r in con.execute("SELECT id, symbol, seq, kind, speaker, delegation, text, final_article FROM segments ORDER BY symbol, seq"):
        segs.setdefault(r["symbol"], []).append(dict(r))
    items = []
    for sym, rows in segs.items():
        for i, s in enumerate(rows):
            c = cache.get(s["id"])
            if s["kind"] != "speech" or s["final_article"] is not None or not c or c.get("pick") not in topics \
                    or not args.low <= c.get("p", 0) < args.high:
                continue
            t = topics[c["pick"]]
            who = f"{s['speaker']} ({s['delegation']}): " if s["speaker"] else ""
            items.append({"id": f"{args.prefix}{len(items) + 1:03d}", "segment_id": s["id"], "symbol": sym, "topic": c["pick"], "p": c["p"],
                          "question": f"{t['label']}: {t['description']}",
                          "before": " ".join(x["text"] or "" for x in rows[max(0, i - 3):i])[-600:],
                          "speech": (who + (s["text"] or ""))[:1800]})
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "questions.json").write_text(json.dumps({k: f"{v['label']}: {v['description']}" for k, v in topics.items()},
                                                        ensure_ascii=False, indent=1) + "\n")
    size = math.ceil(len(items) / args.batches)
    for b in range(args.batches):
        (args.out / f"batch{b + 1:02d}.json").write_text(json.dumps(items[b * size:(b + 1) * size], ensure_ascii=False, indent=1) + "\n")
    print(f"{len(items)} speeches in {args.batches} batches -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
