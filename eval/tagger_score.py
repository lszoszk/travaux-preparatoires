#!/usr/bin/env python3
"""Score an article tagger's predictions against data/gold/tagger_eval.jsonl (eval/tagger_eval_build.py).

Predictions: a CSV with columns segment_id, instrument, final_article, score (instrument ICCPR,
ICESCR, UDHR or ICCPR+ICESCR; a speech with no prediction, or final_article empty, is "no tag").

Main measure, on the speeches the coverage audits judged that are still untagged: at each score
threshold, how many the tagger tags (n), how many of those are right (precision: a tag is right
only if its article is the label; "NONE", "NO_FINAL" and another article are wrong), and how many
of the speeches about a final article it tags rightly (recall). Article 1 of either covenant, and
"ICCPR+ICESCR", match each other (the article is the same in both). Secondary: on the judged tags
(source tag_gold), the share of right tags the tagger reproduces and of wrong tags it repeats.

  python3 eval/tagger_score.py predictions.csv [--split dev|test|all]
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "data" / "gold" / "tagger_eval.jsonl"


def same(pred: str, label: str) -> bool:
    if pred == label:
        return True
    if " " not in label:  # NONE, NO_FINAL
        return False
    pi, pn = pred.rsplit(" ", 1)
    li, ln = label.rsplit(" ", 1)
    covenants = {"ICCPR", "ICESCR", "ICCPR+ICESCR"}
    return pn == ln and pi in covenants and li in covenants and (pn == "1" or "+" in pi or "+" in li)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions")
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    args = ap.parse_args()
    rows = [json.loads(line) for line in EVAL.read_text().splitlines()]
    rows = [r for r in rows if args.split == "all" or r["split"] == args.split]
    pred = {}
    for p in csv.DictReader(open(args.predictions)):
        if p.get("final_article"):
            pred[p["segment_id"]] = (f"{p['instrument']} {int(p['final_article'])}", float(p["score"]))
    target = [r for r in rows if r["source"] == "coverage" and r["current_tag"] is None]
    about = sum(1 for r in target if r["label"] not in ("NONE", "NO_FINAL"))
    print(f"split {args.split}: {len(target)} untagged judged speeches, {about} about a final article")
    print("threshold |   n | right | precision | recall")
    for t in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
        hits = [(r, pred[r["id"]][0]) for r in target if r["id"] in pred and pred[r["id"]][1] >= t]
        right = sum(1 for r, p in hits if same(p, r["label"]))
        print(f"   {t:.2f}   | {len(hits):3} | {right:5} | {right / len(hits) if hits else 0:9.2f} | {right / about if about else 0:6.2f}")
    judged = [r for r in rows if r["source"] == "tag_gold"]
    good = [r for r in judged if not r["label"].startswith("NOT ")]
    bad = [r for r in judged if r["label"].startswith("NOT ")]
    rep = sum(1 for r in good if r["id"] in pred and same(pred[r["id"]][0], r["label"]))
    rep_bad = sum(1 for r in bad if r["id"] in pred and same(pred[r["id"]][0], r["label"][4:]))
    print(f"judged tags: reproduces {rep}/{len(good)} right tags, repeats {rep_bad}/{len(bad)} wrong ones (any score)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
