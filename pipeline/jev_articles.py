#!/usr/bin/env python3
"""Jev's check on the article tags: is a tagged speech about its article?

The tags come from headings, the chair and the reports' meeting lists; a speech under them can
still be about something else (an aside on another article, the order of work, the covenants
as a whole). For each tagged speech Jev gets the article (instrument, final number, title,
adopted text, and the draft number the record uses) and the opening of the speech, and answers
yes or no with a probability. api/build_db.py stores the probability with the speech and drops
the tag below THRESHOLD.

Measured on the hand-judged tags (eval/jev_article_check.py): at 0.5 it keeps 91.7% of the
correct tags and drops 64% of the wrong ones.

Answers are cached by speech and tag (data/cache/jev_articles.json): after a rebuild only new
or changed tags are asked. Sends the records' text to TypeSafe: run only with --jev.

Usage: python3 pipeline/jev_articles.py --jev [--batch 20] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jev  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "jev_articles.json"
THRESHOLD = 0.5
# the 1947-48 records lose more headings, and a stale article runs on: there a tag needs a clearer yes
# (set on the round 21 sample, measured on round 22)
THRESHOLD_EARLY = 0.7
SPEECH_CHARS = 1500
QUESTION = ("Is this speech about the article named with it: its substance, its wording, amendments to it, or "
            "the vote on it (explaining a vote on it, or asking for a separate vote on its words, counts)?")
TRUE = "Yes: the speaker discusses that article (its content, wording, amendments to it, or the vote on it)."
FALSE = ("No: the speech is about something else: the procedure or the order of work, another article or another "
         "instrument, the covenants or the declaration as a whole, or a personal exchange between delegates.")


def key(seg_id: str, inst: str, final: int, draft) -> str:
    return f"{seg_id}|{inst}|{final}|{draft or ''}"


def final_texts() -> dict[tuple[str, int], str]:
    out = {}
    udhr = json.loads((ROOT / "data/concordance/udhr_final.json").read_text())["articles"]
    out.update({("UDHR", int(k)): v for k, v in udhr.items()})
    cov = json.loads((ROOT / "data/concordance/covenants_final.json").read_text())["instruments"]
    for inst in ("ICCPR", "ICESCR"):
        out.update({(inst, int(k)): v for k, v in cov[inst].items()})
    return out


def titles() -> dict[tuple[str, int], str]:
    import csv
    return {(r["instrument"], int(r["article"])): r["short_title"]
            for r in csv.DictReader((ROOT / "data/concordance/articles.csv").open()) if r["article"].isdigit()}


def item_state(inst: str, final: int, draft, text: str, title: str, final_text: str) -> dict:
    # the records number the articles as the draft before them did ("article 17" of the draft is the
    # Declaration's article 19): Jev must know the number the speech itself will use
    numbered = (f" In this record it is numbered article {draft} (the numbering of the draft then under discussion); "
                f"speakers call it that.") if draft and str(draft) != str(final) else ""
    return {"article": f"{inst} article {final} ({title}).{numbered} Adopted text: {final_text[:500]}",
            "speech": " ".join(text.split())[:SPEECH_CHARS]}


def ask_batch(items: list[dict]) -> dict[str, float | None]:
    """items: {"key", "state"}. Returns key -> probability that the speech is about its article."""
    state = {f"item_{i}": x["state"] for i, x in enumerate(items)}
    questions = {k: jev.noul(f"Consider only {k} in the state: its article and its speech. {QUESTION}", TRUE, FALSE)
                 for k in state}
    answers = jev.ask({"items": state}, questions, task="article_check")
    out = {}
    for i, x in enumerate(items):
        p = (answers.get(f"item_{i}") or {}).get("noul")
        out[x["key"]] = float(p) if isinstance(p, (int, float)) else None
    return out


def load_cache() -> dict[str, float | None]:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jev", action="store_true", help="call TypeSafe (sends the records' text)")
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    rows = con.execute("SELECT id, article_instrument, final_article, draft_article, text FROM segments "
                       "WHERE kind = 'speech' AND final_article IS NOT NULL ORDER BY id").fetchall()
    cache = load_cache()
    texts, names = final_texts(), titles()
    todo = []
    for seg_id, inst, final, draft, text in rows:
        inst1 = inst.split("+")[0]
        k = key(seg_id, inst, final, draft)
        if k not in cache or cache[k] is None:
            todo.append({"key": k, "state": item_state(inst1, final, draft, text, names.get((inst1, final), ""),
                                                        texts.get((inst1, final), ""))})
    todo = todo[:args.limit or None]
    print(f"{len(rows)} tagged speeches; {len(rows) - len(todo)} already checked; {len(todo)} to ask", file=sys.stderr)
    if todo and not args.jev:
        print("rerun with --jev to ask Jev (sends the records' text to TypeSafe)", file=sys.stderr)
        return 0
    for k in range(0, len(todo), args.batch):
        try:
            cache.update(ask_batch(todo[k:k + args.batch]))
        except RuntimeError as exc:  # a failed batch is asked again on the next run
            print(f"  batch {k // args.batch}: {exc}", file=sys.stderr)
            continue
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache))
        print(f"  asked {min(k + args.batch, len(todo))}/{len(todo)}", file=sys.stderr, flush=True)
    scored = [cache.get(key(r[0], r[1], r[2], r[3])) for r in rows]
    scored = [p for p in scored if p is not None]
    print(f"{len(scored)} checked; {sum(p < THRESHOLD for p in scored)} below {THRESHOLD}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
