#!/usr/bin/env python3
"""A fixed set of tasks to run every new model on, with answers to score against: eval/model_bench/.

The history of the database mixes three things: the models, the work done so far and the specification. To follow
a model's progress apart from them, the same items are put to each model and scored against the same answers.

Four tasks, all from the project's own checked sets (data/gold), 30-40 items each, drawn with a fixed seed:
  speaker    read the speaker and delegation of a speech on the page image
  vote       give the outcome and the figures of a vote from the passage that reports it
  sponsor    name the delegation(s) that proposed a document, as the passage says
  tag        say whether a speech is about the article it was tagged with (with the heading or chair's line before it)

Version 2 (30 September 2026): the first draft cut the passages, did not give the tag task the line before the speech and
did not say that 'rejected by 8 votes to 7' is 7 for and 8 against: all four models then scored alike, on the items, not
on themselves. Those results were discarded.

The answers come from the project's hand-checked rounds, in which two blind model judges checked each item and the
researcher checked samples: they are checked, not infallible. Writes items.json (what the model sees) and gold.json.

Usage: python3 eval/model_bench_build.py
"""
from __future__ import annotations

import json
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from ocr import page_image  # noqa: E402

GOLD = ROOT / "data" / "gold"
OUT = ROOT / "eval" / "model_bench"
SEED = 2026
N = {"speaker": 29, "vote": 30, "sponsor": 30, "tag": 40}


def lines(name: str) -> list[dict]:
    return [json.loads(l) for l in (GOLD / name).read_text().splitlines() if l.strip()]


def main() -> int:
    rng = random.Random(SEED)
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    text = lambda sid: (con.execute("SELECT text FROM segments WHERE id = ?", (sid,)).fetchone() or [None])[0]  # noqa: E731
    items, gold = [], {}

    speakers = lines("speakers_images.jsonl")
    for i, r in enumerate(speakers[:N["speaker"]]):
        img = page_image(r["symbol"], r["page"])  # (rendered from the PDF if the image is not on disk)
        if not img:
            continue
        iid = f"speaker-{i:02d}"
        items.append({"id": iid, "task": "speaker", "image": str(img), "opening": r["opening"]})
        gold[iid] = {"speaker": r["speaker"], "delegation": r["delegation"]}

    votes = [r for r in lines("decisions.jsonl") if r.get("is_decision") and r.get("outcome_correct") and r.get("figures_correct")
             and r.get("yes") is not None and r.get("outcome") in ("adopted", "rejected")]
    rng.shuffle(votes)
    for i, r in enumerate(votes[:N["vote"]]):
        t = text(r["segment"])
        if not t:
            continue
        iid = f"vote-{i:02d}"
        items.append({"id": iid, "task": "vote", "passage": t[:6000], "subject": r["subject"][:300]})
        gold[iid] = {"outcome": r["outcome"], "yes": r["yes"], "no": r["no"], "abstentions": r["abstentions"]}

    refs = [r for r in lines("refs.jsonl") if r.get("symbol_ok") and r.get("proposers_ok") and r.get("proposers")]
    rng.shuffle(refs)
    for i, r in enumerate(refs[:N["sponsor"]]):
        t = text(r["segment"])
        if not t:
            continue
        iid = f"sponsor-{i:02d}"
        items.append({"id": iid, "task": "sponsor", "passage": t[:6000], "document": r["symbol"]})
        gold[iid] = {"proposers": r["proposers"]}

    tags = [r for r in lines("article_tags.jsonl") if isinstance(r.get("correct"), bool)]
    yes = [r for r in tags if r["correct"]]
    no = [r for r in tags if not r["correct"]]
    rng.shuffle(yes)
    rng.shuffle(no)
    pick = yes[:N["tag"] // 2] + no[:N["tag"] // 2]
    rng.shuffle(pick)
    for i, r in enumerate(pick):
        t = text(r["id"])
        if not t:
            continue
        iid = f"tag-{i:02d}"
        # the heading or chair's line before the speech, which the judges had (the article is set by it)
        ctx = con.execute("SELECT s2.text FROM segments s2 JOIN segments s1 ON s1.symbol = s2.symbol AND s2.seq < s1.seq "
                          "WHERE s1.id = ? AND (s2.kind = 'heading' OR (s2.kind IN ('chair', 'procedural', 'vote') "
                          "AND lower(s2.text) LIKE '%article%')) ORDER BY s2.seq DESC LIMIT 1", (r["id"],)).fetchone()
        items.append({"id": iid, "task": "tag", "passage": t[:1500], "tagged_as": r["tag"],
                      "context_before": (ctx[0][:300] if ctx else "")})
        gold[iid] = {"about": r["correct"]}

    OUT.mkdir(exist_ok=True)
    (OUT / "items.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    (OUT / "gold.json").write_text(json.dumps(gold, indent=1, ensure_ascii=False))
    counts = {t: sum(1 for x in items if x["task"] == t) for t in N}
    print(f"{len(items)} items {counts} -> {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
