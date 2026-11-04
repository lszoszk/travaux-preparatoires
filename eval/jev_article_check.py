#!/usr/bin/env python3
"""Does Jev tell a speech about its tagged article from one that is not? Measured on the
hand-judged article tags (data/gold/article_tags.jsonl).

For each judged tag Jev gets the article (instrument, number, title, the adopted text) and
the opening of the speech, and answers yes or no, with a probability: is the speech about
that article? Answers are cached (data/cache/jev_article_check.json), so a rerun costs
nothing. The report gives, for each threshold, how many correct tags would be kept, how
many wrong ones dropped, and the precision that would result.

Sends the UN records' text to TypeSafe: run only with --jev.

Version 2 names the draft number the record uses (version 1, final numbers only, turned down
correct tags whose speech said "article 17" for the Declaration's article 19).

Usage: python3 eval/jev_article_check.py --jev [--limit 40] [--batch 20]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import jev  # noqa: E402

CACHE = ROOT / "data" / "cache" / "jev_article_check_v2.json"
SPEECH_CHARS = 1500
QUESTION = ("Is this speech about the article named with it: its substance, its wording, amendments to it, or "
            "the vote on it (explaining a vote on it, or asking for a separate vote on its words, counts)?")
TRUE = ("Yes: the speaker discusses that article (its content, wording, amendments to it, or the vote on it).")
FALSE = ("No: the speech is about something else: the procedure or the order of work, another article or another "
         "instrument, the covenants or the declaration as a whole, or a personal exchange between delegates.")


def final_texts() -> dict[tuple[str, int], str]:
    out = {}
    udhr = json.loads((ROOT / "data/concordance/udhr_final.json").read_text())["articles"]
    out.update({("UDHR", int(k)): v for k, v in udhr.items()})
    cov = json.loads((ROOT / "data/concordance/covenants_final.json").read_text())["instruments"]
    for inst in ("ICCPR", "ICESCR"):
        out.update({(inst, int(k)): v for k, v in cov[inst].items()})
    return out


def judged() -> list[dict]:
    """The judged tags, one per speech (the first judgement), with the speech's text."""
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    seen, out = set(), []
    for line in (ROOT / "data/gold/article_tags.jsonl").read_text().splitlines():
        x = json.loads(line)
        if x["id"] in seen:
            continue
        seen.add(x["id"])
        row = con.execute("SELECT text FROM segments WHERE id = ? AND kind = 'speech'", (x["id"],)).fetchone()
        m = re.match(r"(UDHR|ICCPR|ICESCR)(?:\+ICESCR)? art\. (\d+) \((.*)\)", x["tag"])
        if row and m:
            out.append({**x, "text": row[0], "inst": m.group(1), "art": int(m.group(2)), "title": m.group(3)})
    return out


def ask_batch(items: list[dict], texts: dict) -> dict[str, float | None]:
    state, questions = {}, {}
    for i, x in enumerate(items):
        key = f"item_{i}"
        final = texts.get((x["inst"], x["art"]), "")[:500]
        # the records number the articles as the draft before them did ("article 17" of the draft is
        # the Declaration's article 19): Jev must know the number the speech itself will use
        numbered = (f" In this record it is numbered article {x['draft']} (the numbering of the draft then under "
                    f"discussion); speakers call it that.") if x.get("draft") and str(x["draft"]) != str(x["art"]) else ""
        state[key] = {"article": f"{x['inst']} article {x['art']} ({x['title']}).{numbered} Adopted text: {final}",
                      "speech": " ".join(x["text"].split())[:SPEECH_CHARS]}
        questions[key] = jev.noul(f"Consider only {key} in the state: its article and its speech. {QUESTION}", TRUE, FALSE)
    answers = jev.ask({"items": state}, questions, task="article_check")
    out = {}
    for i, x in enumerate(items):
        a = answers.get(f"item_{i}") or {}
        p = a.get("noul")
        out[x["id"]] = float(p) if isinstance(p, (int, float)) else None
    return out


def report(items: list[dict], probs: dict[str, float | None]) -> None:
    scored = [(probs[x["id"]], x["correct"]) for x in items if probs.get(x["id"]) is not None]
    n_ok = sum(1 for _, c in scored if c)
    n_bad = len(scored) - n_ok
    print(f"{len(scored)} judged tags scored ({n_ok} correct, {n_bad} wrong); precision as they stand {n_ok / len(scored):.1%}")
    print("threshold  correct kept   wrong dropped   precision of what is kept")
    for t in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
        kept = [(p, c) for p, c in scored if p >= t]
        ok = sum(1 for _, c in kept if c)
        print(f"   {t:.2f}    {ok:4d}/{n_ok} ({ok / n_ok:5.1%})   {n_bad - (len(kept) - ok):3d}/{n_bad} ({(n_bad - (len(kept) - ok)) / n_bad:5.1%})"
              f"   {ok / len(kept):.1%}" if kept else f"   {t:.2f}   nothing kept")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jev", action="store_true", help="call TypeSafe (sends the records' text)")
    ap.add_argument("--limit", type=int, default=0, help="only the first N judged tags")
    ap.add_argument("--batch", type=int, default=20)
    args = ap.parse_args()
    items = judged()[:args.limit or None]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [x for x in items if x["id"] not in cache]
    if todo and not args.jev:
        print(f"{len(todo)} tags not scored yet; rerun with --jev to ask Jev", file=sys.stderr)
    elif todo:
        texts = final_texts()
        for k in range(0, len(todo), args.batch):
            cache.update(ask_batch(todo[k:k + args.batch], texts))
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache, indent=0))
            print(f"  scored {min(k + args.batch, len(todo))}/{len(todo)}", file=sys.stderr)
    report(items, cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
