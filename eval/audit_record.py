#!/usr/bin/env python3
"""Record a quality-audit round's judgments (the workflow of eval/audit_sample.py's sample) in the gold sets.

  python3 eval/audit_record.py SAMPLE.json RESULTS.json --round 65 --checked "2026-10-03, round 65 audit (...)"

RESULTS.json: the workflow's list of batches {kind, a, c, third}: two blind judges, and a third on the items they split
on. An item's verdict is the two judges' when they agree, else the third's; an item without a verdict is left out.
Precision items go to data/gold/article_tags.jsonl, coverage items to data/gold/coverage.jsonl. Then run
eval/quality_audit.py, which writes data/gold/audit.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "gold"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sample", type=Path)
    ap.add_argument("results", type=Path)
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--checked", required=True)
    args = ap.parse_args()
    items = {x["id"]: x for x in json.loads(args.sample.read_text())}
    res = json.loads(args.results.read_text())
    if isinstance(res, dict) and "result" in res:
        res = res["result"]
    tags, cov, split, missing = [], [], 0, 0
    for b in res:
        if not b:
            continue
        key = "correct" if b["kind"] == "P" else "about_article"
        for iid in set(b["a"]) | set(b["c"]):
            one, two, third = b["a"].get(iid), b["c"].get(iid), (b.get("third") or {}).get(iid)
            if one and two and one[key] == two[key]:
                v = one
            elif third:
                v, split = third, split + 1
            else:
                missing += 1
                continue
            x = items[iid]
            if b["kind"] == "P":
                tags.append({"id": iid, "symbol": x["symbol"], "page": x["page"], "stratum": x["stratum"], "tag": x["tag"],
                             "draft": x["draft"], "setter": x["setter"], "speech": x["speech"][:600], "correct": bool(v["correct"]),
                             "note": v["note"], "round": args.round, "checked": args.checked})
            else:
                cov.append({"id": iid, "symbol": x["symbol"], "page": x["page"], "sample": x["sample"], "stratum": x["stratum"],
                            "about_article": bool(v["about_article"]), "article": v.get("article", ""), "note": v["note"],
                            "untagged_because": x["untagged_because"], "round": args.round, "checked": args.checked})
    with (GOLD / "article_tags.jsonl").open("a", encoding="utf-8") as f:
        for t in tags:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    with (GOLD / "coverage.jsonl").open("a", encoding="utf-8") as f:
        for c in cov:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"{len(tags)} precision and {len(cov)} coverage judgments recorded ({split} settled by the third judge, {missing} without a verdict)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
