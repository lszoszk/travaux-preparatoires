#!/usr/bin/env python3
"""The evaluation set for an article tagger of untagged speeches (docs/codex_task_article_tagger.md).

From the hand-judged speeches:
- data/gold/coverage.jsonl (untagged speeches judged for whether they are about one article; rounds
  31-43): label "INST N" (the final article, parsed from the judge's note), "NO_FINAL" (about an
  article or proposal with no final article) or "NONE" (not about one article);
- data/gold/article_tags.jsonl (tagged speeches judged right or wrong, latest judgment of each):
  label "INST N" for a right tag, "NOT INST N" for a wrong one (the true article is unknown).
Each record carries the speech's current tag in the database and a split by meeting record: "test"
for about a fifth of the records (by a hash of the symbol), "dev" for the rest. Tune on dev only.

Writes data/gold/tagger_eval.jsonl.

  python3 eval/tagger_eval_build.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "gold"
OUT = GOLD / "tagger_eval.jsonl"
LABEL_RE = re.compile(r"\b(ICCPR|ICESCR|UDHR)\s*(?:art(?:icle)?s?\.?\s*)?(\d{1,2})\b", re.I)
FINAL_RE = re.compile(r"final\s+(ICCPR|ICESCR|UDHR)\s*(?:art(?:icle)?s?\.?\s*)?(\d{1,2})\b", re.I)
TAG_RE = re.compile(r"^(ICCPR\+ICESCR|ICCPR|ICESCR|UDHR) art\. (\d{1,2})\b")


def split(symbol: str) -> str:
    return "test" if int(hashlib.md5(symbol.encode()).hexdigest(), 16) % 5 == 0 else "dev"


def label_of(note: str) -> str:
    m = FINAL_RE.search(note)
    if not m:
        found = LABEL_RE.findall(note)
        m = found[-1] if found else None
        return f"{m[0].upper()} {int(m[1])}" if m else "NO_FINAL"
    return f"{m.group(1).upper()} {int(m.group(2))}"


def main() -> int:
    con = sqlite3.connect(f"file:{ROOT / 'data' / 'travaux.sqlite3'}?mode=ro", uri=True)
    now = {r[0]: (f"{r[1]} {r[2]}" if r[2] is not None else None, r[3]) for r in con.execute(
        "SELECT id, article_instrument, final_article, symbol FROM segments WHERE kind = 'speech'")}
    out = {}
    for line in (GOLD / "coverage.jsonl").read_text().splitlines():
        g = json.loads(line)
        if g["id"] not in now:
            continue
        label = label_of(g["article"]) if g["about_article"] else "NONE"
        out[g["id"]] = {"id": g["id"], "symbol": g["symbol"], "source": "coverage", "label": label,
                        "current_tag": now[g["id"]][0], "round": g["round"], "split": split(g["symbol"])}
    for line in (GOLD / "article_tags.jsonl").read_text().splitlines():
        g = json.loads(line)
        m = TAG_RE.match(g.get("tag") or "")
        if g["id"] not in now or not m or g["id"] in out and out[g["id"]]["source"] == "coverage":
            continue
        tag = f"{m.group(1)} {int(m.group(2))}"
        out[g["id"]] = {"id": g["id"], "symbol": g["symbol"], "source": "tag_gold", "label": tag if g["correct"] else f"NOT {tag}",
                        "current_tag": now[g["id"]][0], "round": g["round"], "split": split(g["symbol"])}
    OUT.write_text("".join(json.dumps(r) + "\n" for r in out.values()))
    rows = list(out.values())
    print(f"{len(rows)} judged speeches -> {OUT.relative_to(ROOT)}: "
          f"{sum(r['source'] == 'coverage' for r in rows)} from the coverage audits "
          f"({sum(r['source'] == 'coverage' and r['current_tag'] is None for r in rows)} still untagged), "
          f"{sum(r['source'] == 'tag_gold' for r in rows)} judged tags; test split {sum(r['split'] == 'test' for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
