#!/usr/bin/env python3
"""Jev's second question for the article tags: is a short tagged speech about procedure?

The hand checks found procedural speeches (the order of votes, whether to vote now, which text
is the basis, suspending the meeting) to be the commonest wrong tag left after Jev's article
check, which gives them middling probabilities (median 0.67) that a threshold cannot separate
from the right tags. This asks Jev about the organisation of work directly, for tagged speeches
under MAX_WORDS words, with the passage before each for context. The vote on the article's text
(a roll-call, a vote in parts, the order of the votes on its amendments, withdrawing an
amendment) counts as the article's, as in the hand checks. Answers are cached by speech
(data/cache/jev_procedure_v2.json; v1, which counted those as procedure, dropped as many right
tags as wrong ones); api/build_db.py drops a tag at PROCEDURE_THRESHOLD or more.

On the hand-judged short speeches (798; 35 wrong), v2 at 0.7 drops 10 wrong tags (all
procedural) and 13 judged right, most of them procedure the earlier rounds counted leniently
(taking a document as the basic text, merging amendments, deferring a vote). A hand check of 30
of the 159 tags it dropped at 0.7 (round 34) found the band 0.7-0.8 net harmful (3 wrong, 6
right, 3 split) and 0.8 and above almost all wrong (16 wrong, 0 right, 2 split): the threshold
is 0.8 (91 tags).

  python3 eval/jev_procedure_check.py --jev --gold   # the hand-judged tags: how well it separates
  python3 eval/jev_procedure_check.py --jev          # every short tagged speech
  python3 eval/jev_procedure_check.py --jev --kind chair   # the chair's short tagged turns (round 120)

Sends the records' text to TypeSafe: run only with --jev.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import jev  # noqa: E402

CACHE = ROOT / "data" / "cache" / "jev_procedure_v2.json"
MAX_WORDS = 200
QUESTION = ("Is this speech mainly about how the meeting organises its work, rather than about the article under discussion "
            "or the vote on its text?")
# the hand checks count the vote on the article's text as the article's (a roll-call, a vote in parts, the order of the
# votes on its amendments, withdrawing or maintaining an amendment): those are not "procedure" here
TRUE = ("Organisation of work: whether or when to take up, defer, postpone or re-open the article or a decision; the order "
        "in which articles or items are taken; which document is the basis of discussion; merging or co-ordinating "
        "amendments; suspending or adjourning the meeting; time-limits, the list of speakers, the rules of procedure or "
        "the chair's rulings; the report, the records or translations; without discussing the article's content or wording.")
FALSE = ("The article or the vote on its text: it discusses the article's content or wording; proposes, supports, opposes, "
         "withdraws or maintains an amendment to it; asks for a separate, roll-call or divided vote on it or its "
         "amendments, or for an order in which they are voted; or explains a vote on it.")


def ask_batch(items: list[dict]) -> dict[str, float | None]:
    state = {f"item_{i}": x["state"] for i, x in enumerate(items)}
    questions = {k: jev.noul(f"Consider only {k} in the state: the passage before it and its speech. {QUESTION}", TRUE, FALSE)
                 for k in state}
    answers = jev.ask({"items": state}, questions, task="procedure_check")
    out = {}
    for i, x in enumerate(items):
        p = (answers.get(f"item_{i}") or {}).get("noul")
        out[x["key"]] = float(p) if isinstance(p, (int, float)) else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jev", action="store_true", help="call TypeSafe (sends the records' text)")
    ap.add_argument("--gold", action="store_true", help="only the hand-judged tags, and report how well it separates them")
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--kind", default="speech", choices=("speech", "chair"))
    args = ap.parse_args()
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    segs = {r[0]: r[1:] for r in con.execute(
        "SELECT id, symbol, seq, text, article_instrument, final_article FROM segments WHERE kind = ? AND final_article IS NOT NULL", (args.kind,))}
    judged = {}
    for line in (ROOT / "data" / "gold" / "article_tags.jsonl").read_text().splitlines():
        g = json.loads(line)
        judged[g["id"]] = g  # the latest judgment of each speech
    ids = [i for i, s in segs.items() if len(s[2].split()) < MAX_WORDS]
    if args.gold:
        ids = [i for i in ids if i in judged and (judged[i]["tag"].startswith(f"{segs[i][3]} art. {segs[i][4]} ")
                                                  or judged[i]["tag"] == f"{segs[i][3]} {segs[i][4]}")]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = []
    for i in ids:
        if cache.get(i) is not None:
            continue
        sym, seq, text = segs[i][0], segs[i][1], segs[i][2]
        prev = con.execute("SELECT text FROM segments WHERE symbol = ? AND seq < ? ORDER BY seq DESC LIMIT 1", (sym, seq)).fetchone()
        todo.append({"key": i, "state": {"passage_before": " ".join((prev[0] if prev else "").split())[-600:],
                                          "speech": " ".join(text.split())[:1500]}})
    print(f"{len(ids)} {args.kind} segments under {MAX_WORDS} words; {len(todo)} to ask", file=sys.stderr)
    if todo and not args.jev:
        print("rerun with --jev to ask Jev (sends the records' text to TypeSafe)", file=sys.stderr)
        return 0
    for k in range(0, len(todo), args.batch):
        try:
            cache.update(ask_batch(todo[k:k + args.batch]))
        except RuntimeError as exc:
            print(f"  batch {k // args.batch}: {exc}", file=sys.stderr)
            continue
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache))
        print(f"  asked {min(k + args.batch, len(todo))}/{len(todo)}", file=sys.stderr, flush=True)
    if args.gold:
        rows = [(judged[i]["correct"], cache.get(i), judged[i].get("note") or "") for i in ids if cache.get(i) is not None]
        print("threshold | right tags dropped | wrong tags dropped (of which procedural)")
        for t in (0.5, 0.6, 0.7, 0.8, 0.9):
            right = sum(1 for c, p, n in rows if c and p >= t)
            wrong = [n for c, p, n in rows if not c and p >= t]
            proc = sum(1 for n in wrong if any(w in n.lower() for w in ("procedur", "order of", "vote", "suspen", "basic", "ruling")))
            print(f"  {t:.1f}     | {right:3} of {sum(1 for c, _, _ in rows if c)} | {len(wrong):2} of {sum(1 for c, _, _ in rows if not c)} ({proc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
