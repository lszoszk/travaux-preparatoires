#!/usr/bin/env python3
"""Jev's choice of a question of general debate for the speeches no article tag fits.

Most untagged speeches sit in general debates: the Third Committee's of 1950-54 on the covenants, the Commission's on
measures of implementation, the 1947 debates on the form of the bill. They are about questions that run across the
articles (self-determination, one covenant or two, the federal and territorial clauses, reservations, petitions), and an
article tag would be wrong for most of them. For each untagged speech over 150 characters Jev chooses one of the questions
in data/concordance/topics.csv, "general" (the instrument as a whole, or several questions at once, none of them
dominating) or "none" (procedure, one particular article, another item). Answers are cached by speech
(data/cache/jev_topics.json); api/build_db.py gives a speech its question at THRESHOLD or more.

  python3 pipeline/topics.py            # count the candidates and the answers cached
  python3 pipeline/topics.py --jev      # ask Jev about every candidate not yet asked (sends the speeches to TypeSafe)
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jev  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TOPICS = ROOT / "data" / "concordance" / "topics.csv"
CACHE = ROOT / "data" / "cache" / "jev_topics.json"
GENERAL, NONE = "general", "none"
# a speech is given its question at this probability or more: on the blind check of round 70 (data/gold/topics.jsonl)
# 87 of 90 picks at 0.9 or more were right, 40 of 54 between 0.8 and 0.9
THRESHOLD = 0.9
SPEECH_CHARS = 1500
INSTRUCTIONS = ("Consider only {key} in the state: a speech in a UN meeting record on the drafting of the Universal "
                "Declaration of Human Rights or the International Covenants, with its record and the passage before it. "
                "Which one of the questions in the state is the speech mainly about? Choose '" + GENERAL + "' if it is a "
                "statement on the declaration or the covenant(s) as a whole, or ranges over several of the questions without "
                "one of them dominating. Choose '" + NONE + "' if it is about procedure or the order of work, about one "
                "particular article's content or wording, about another agenda item, or about anything else.")


def load_topics() -> list[dict]:
    return list(csv.DictReader(TOPICS.open()))


def all_topics() -> list[dict]:
    """The questions as the database lists them: topics.csv and "general"."""
    return load_topics() + [{"topic": GENERAL, "label": "General debate",
                             "description": "the declaration or the covenant(s) as a whole, or several of these questions at once",
                             "articles": ""}]


def options() -> dict[str, str]:
    out = {t["topic"]: f"{t['label']}: {t['description']}" for t in load_topics()}
    out[GENERAL] = "General debate: the declaration or the covenant(s) as a whole, or several of these questions at once"
    out[NONE] = "None of these: procedure or the order of work, one particular article, another agenda item, anything else"
    return out


def candidates(con: sqlite3.Connection) -> list[dict]:
    docs = {r[0]: r[1:] for r in con.execute("SELECT symbol, body, session, meeting_date FROM documents")}
    out = []
    for sid, sym, seq, text in con.execute("SELECT id, symbol, seq, text FROM segments WHERE kind = 'speech' "
                                           "AND final_article IS NULL AND length(text) > 150 ORDER BY id"):
        body, sess, date = docs[sym]
        before = con.execute("SELECT text FROM segments WHERE symbol = ? AND seq < ? AND kind IN ('heading', 'chair', "
                             "'procedural', 'masthead') ORDER BY seq DESC LIMIT 1", (sym, seq)).fetchone()
        out.append({"id": sid, "record": f"{sym}, {body}, {sess or ''}, {date or ''}".strip(", "),
                    "before": " ".join((before[0] if before else "").split())[:400],
                    "speech": " ".join(text.split())[:SPEECH_CHARS]})
    return out


def ask_batch(items: list[dict], opts: dict[str, str]) -> dict[str, dict]:
    state = {f"S{j}": {k: x[k] for k in ("record", "before", "speech")} for j, x in enumerate(items)}
    qs = {f"S{j}": jev.choice(INSTRUCTIONS.format(key=f"S{j}"), opts) for j in range(len(items))}
    answers = jev.ask({"speeches": state}, qs, task="topic_choice")
    out = {}
    for j, x in enumerate(items):
        a = answers.get(f"S{j}") or {}
        probs = a.get("probabilities") or {}
        pick = a.get("choice")
        if pick in opts:
            top = sorted(probs.items(), key=lambda kv: -kv[1])[:3]
            out[x["id"]] = {"pick": pick, "p": round(float(probs.get(pick, 0.0)), 3),
                            "top": {k: round(float(v), 3) for k, v in top}}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jev", action="store_true", help="call TypeSafe (sends the speeches)")
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    cands = candidates(con)
    todo = [c for c in cands if c["id"] not in cache]
    print(f"{len(cands)} candidates, {len(cands) - len(todo)} answered, {len(todo)} to ask", file=sys.stderr)
    if args.limit:
        todo = todo[:args.limit]
    if args.jev and todo:
        opts = options()
        for k in range(0, len(todo), args.batch):
            got = ask_batch(todo[k:k + args.batch], opts)
            if not got:
                raise SystemExit("Jev returned no answers: stopping (check the key)")
            cache.update(got)
            CACHE.write_text(json.dumps(cache))
            if k // args.batch % 25 == 0:
                print(f"  {k + len(todo[k:k + args.batch])}/{len(todo)}", file=sys.stderr)
    print(Counter(v["pick"] for v in cache.values()).most_common(), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
