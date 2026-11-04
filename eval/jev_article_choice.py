#!/usr/bin/env python3
"""Jev's choice for untagged speeches: which of the meeting's articles is a speech about?

The coverage audits found most of the untagged speeches about an article in meetings whose
record gives no article context (several articles at once, no headings between them). Where
the session's report lists the meeting's articles (covenant_drafts_chr.csv, covenant_drafts_tc.csv),
Jev is asked to choose among those articles, or "none" (procedure, general debate, several
articles, another item), for each untagged speech over 150 characters whose tag no Jev check
has already dropped. The Third Committee's 1948 report on the Declaration (A/777) lists no
meetings by article: there the options are the articles the record's own headings and chair
give the meeting, with "another article" (one not listed, a new article, the preamble); a
speech Jev judged not about its article is asked too where the meeting had others. One request
per meeting: its articles are the options. Answers are cached by speech
(data/cache/jev_article_choice.json); api/build_db.py tags a speech with the chosen article at
CHOICE_THRESHOLD or more.

  python3 eval/jev_article_choice.py --jev --gold   # the speeches the coverage audits judged
  python3 eval/jev_article_choice.py --jev          # every candidate

Sends the records' text to TypeSafe: run only with --jev.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "api"))
import jev  # noqa: E402

CACHE = ROOT / "data" / "cache" / "jev_article_choice.json"
NONE = "none"
INSTRUCTIONS = ("Consider only {key} in the state: the passage before it and its speech, at a meeting whose articles are listed "
                "in the state. Which one of those articles is this speech mainly about: its content, its wording, amendments "
                "to it, or the vote on it? Choose 'none' if the speech is about procedure or the order of work, is a general "
                "statement on the covenant or on several articles at once, or is about another item.")
# the Third Committee's 1948 debate on the draft declaration (E/800): no report lists its meetings' articles
# (A/777 gives only ranges); the options are the articles the record's own headings and chair give the meeting
INSTRUCTIONS_1948 = ("Consider only {key} in the state: the passage before it and its speech, at a meeting of the Third Committee "
                     "(1948) on the draft declaration of human rights, whose articles are listed in the state. Which one of those "
                     "articles is this speech mainly about: its content, its wording, amendments to it, or the vote on it? Choose "
                     "'another article' if it is mainly about an article or proposal not listed, and 'none' if it is about "
                     "procedure or the order of work, is a general statement on the declaration or on several articles at once, "
                     "or is about another item.")
OTHER = "marker:other"
# the other meeting records (1947-66) that no report's meeting list covers: the record's own articles
INSTRUCTIONS_RECORD = ("Consider only {key} in the state: the passage before it and its speech, at a meeting on the draft "
                       "declaration or the draft covenant(s) whose articles are listed in the state. Which one of those articles "
                       "is this speech mainly about: its content, its wording, amendments to it, or the vote on it? Choose "
                       "'another article' if it is mainly about an article or proposal not listed, and 'none' if it is about "
                       "procedure or the order of work, is a general statement or about several articles at once, or is about "
                       "another item.")


def candidates(con: sqlite3.Connection, cov: dict, b) -> list[dict]:
    docs = {r[0]: r[1:] for r in con.execute("SELECT symbol, body, session, meeting_date FROM documents")}
    listed_by = {}
    out = []
    for sid, sym, seq, text, mapping in con.execute(
            "SELECT id, symbol, seq, text, article_mapping FROM segments WHERE kind='speech' AND final_article IS NULL "
            "AND length(text) > 150 AND (symbol GLOB 'E/CN.4/SR.*' OR symbol GLOB 'A/C.3/SR.*')"):
        if sym not in docs or "Jev judged" in (mapping or "") or "blind check found" in (mapping or "") \
                or "organisation of work" in (mapping or ""):
            continue
        body, sess, date = docs[sym]
        stage = b.covenant_stage(body, date, sess)
        if not stage or stage == "e2573":
            continue
        m = int(sym.rsplit(".", 1)[1])
        if (stage, m) not in listed_by:
            listed_by[(stage, m)] = sorted({(k[2], k[3]) for k, v in cov.items()
                                            if len(k) == 4 and k[:2] == (stage, "meetings") and m in v and k[3].isdigit()},
                                           key=lambda t: (t[0], int(t[1])))
        if listed_by[(stage, m)]:
            out.append({"id": sid, "symbol": sym, "seq": seq, "text": text, "stage": stage, "articles": listed_by[(stage, m)]})
    return out


def candidates_1948(con: sqlite3.Connection) -> list[dict]:
    """Untagged speeches over 150 characters in the 1948 records (A/C.3/SR.88-179) whose headings or chair give the
    meeting at least one article. A speech Jev judged not about its article is asked only where there are others."""
    arts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for sym, fin, draft in con.execute(
            "SELECT symbol, final_article, draft_article FROM segments WHERE article_instrument = 'UDHR' AND final_article IS NOT NULL "
            "AND article_mapping NOT GLOB '*reader*' "
            "AND symbol GLOB 'A/C.3/SR.*' AND CAST(substr(symbol, 10) AS INT) BETWEEN 88 AND 179"):
        arts[sym][fin][draft] += 1
    out = []
    for sid, sym, seq, text, mapping in con.execute(
            "SELECT id, symbol, seq, text, article_mapping FROM segments WHERE kind='speech' AND final_article IS NULL "
            "AND length(text) > 150 AND symbol GLOB 'A/C.3/SR.*' AND CAST(substr(symbol, 10) AS INT) BETWEEN 88 AND 179"):
        if not arts.get(sym) or "organisation of work" in (mapping or "") or "blind check found" in (mapping or "") \
                or ("Jev judged" in (mapping or "") and len(arts[sym]) < 2):
            continue
        listed = [(fin, max(d, key=d.get)) for fin, d in sorted(arts[sym].items())]
        out.append({"id": sid, "symbol": sym, "seq": seq, "text": text, "stage": "tc1948", "articles": listed})
    return out


def candidates_records(con: sqlite3.Connection, taken: set[str]) -> list[dict]:
    """The same question for every other meeting record of the Commission, its Drafting Committee and working groups,
    and the Third Committee (1947-66) that no report's meeting list covers: the options are the articles its own
    headings, chair and context give the meeting (Declaration or Covenant articles, as tagged)."""
    arts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    where = "(symbol GLOB 'E/CN.4/SR.*' OR symbol GLOB 'A/C.3/SR.*' OR symbol GLOB 'E/CN.4/AC.*')"
    for sym, inst, fin, draft in con.execute(
            f"SELECT symbol, article_instrument, final_article, draft_article FROM segments WHERE final_article IS NOT NULL "
            f"AND article_mapping NOT GLOB '*reader*' AND {where}"):
        arts[sym][(inst, fin)][draft or ""] += 1
    # a heading over several articles ("Articles 20, 21 and 22", E/CN.4/SR.268) sets the first; the others are the
    # meeting's too (the Commission's Covenant records, 1949-54)
    import build_db as b
    cov = b.load_covenant_concordance()
    for sym, text, body, date, session in con.execute(
            "SELECT s.symbol, s.text, d.body, d.meeting_date, d.session FROM segments s JOIN documents d ON d.symbol = s.symbol "
            "WHERE s.kind = 'heading' AND s.symbol GLOB 'E/CN.4/SR.*' AND s.text GLOB '[Aa][Rr][Tt][Ii][Cc][Ll][Ee][Ss] *'"):
        stage = b.covenant_stage(body, date, session)
        for n in re.findall(r"\d+", text):
            fin, _, inst = b.covenant_article(stage, None, n, cov)
            if fin and (inst, fin) not in arts[sym]:
                arts[sym][(inst, fin)][n] += 1
    out = []
    for sid, sym, seq, text, mapping in con.execute(
            f"SELECT id, symbol, seq, text, article_mapping FROM segments WHERE kind='speech' AND final_article IS NULL "
            f"AND length(text) > 150 AND {where}"):
        if sid in taken or not arts.get(sym) or "organisation of work" in (mapping or "") or "blind check found" in (mapping or "") \
                or ("Jev judged" in (mapping or "") and len(arts[sym]) < 2):
            continue
        listed = [(inst, fin, max(d, key=d.get)) for (inst, fin), d in sorted(arts[sym].items())]
        out.append({"id": sid, "symbol": sym, "seq": seq, "text": text, "stage": "record", "articles": listed})
    return out


def options_record(articles: list[tuple[str, int, str]], titles: dict) -> dict[str, str]:
    opts = {}
    for inst, fin, draft in articles:
        named = f"draft article {draft}" if draft else "an article"
        opts[f"{inst} {fin}"] = f"{named} ({titles.get((inst.split('+')[0], str(fin)), '')}; final {inst} article {fin})"
    opts[OTHER] = "another article: an article of the draft not listed here, a proposed new article, or the preamble"
    opts[NONE] = "none of these: procedure or the order of work, a general statement, several articles at once, or another item"
    return opts


def options_1948(articles: list[tuple[int, str]], titles: dict) -> dict[str, str]:
    opts = {f"UDHR {fin}": f"draft article {draft} of E/800 ({titles.get(('UDHR', str(fin)), '')}; final article {fin} of the Declaration)"
            for fin, draft in articles}
    opts[OTHER] = "another article: an article of the draft declaration not listed here, a proposed new article, or the preamble"
    opts[NONE] = "none of these: procedure or the order of work, a general statement, several articles at once, or another item"
    return opts


def markers(stage: str, meeting: int) -> dict[str, str]:
    """The meeting's listed texts that are no Covenant article (deleted drafts, proposals, the preamble), as options
    that take a speech away from the articles: "former-28" is draft article 28 (deleted)."""
    out = {}
    for name in ("covenant_drafts_chr.csv", "covenant_drafts_tc.csv"):
        for r in csv.DictReader((ROOT / "data" / "concordance" / name).open()):
            fin = r["final_article"]
            if r["stage"] != stage or fin.isdigit() or fin == "general" or meeting not in {int(m) for m in r["meetings"].split()}:
                continue
            if fin.startswith("former-"):
                out[f"marker:{fin}"] = f"draft article {fin[7:]} (not in the Covenant as adopted)"
            else:
                out[f"marker:{fin}"] = r["note"].split(":")[0][:120] + " (not an article of the Covenant as adopted)"
    return out


def options_for(stage: str, meeting: int, articles: list[tuple[str, str]], cov: dict, titles: dict) -> dict[str, str]:
    """The options, named as the record numbers the articles (the final article in brackets)."""
    opts = {}
    for inst, fin in articles:
        drafts = sorted({k[2] for k, v in cov.items() if len(k) == 3 and k[:2] == (stage, inst) and str(v) == fin}, key=int)
        named = f"draft article {' or '.join(drafts)}" if drafts else "an article proposed at the session"
        opts[f"{inst} {fin}"] = f"{named} ({titles.get((inst, fin), '')}; final {inst} article {fin})"
    opts.update(markers(stage, meeting))
    opts[NONE] = "none of these: procedure or the order of work, a general statement, several articles at once, or another item"
    return opts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jev", action="store_true", help="call TypeSafe (sends the records' text)")
    ap.add_argument("--gold", action="store_true", help="only the speeches the coverage audits judged")
    args = ap.parse_args()
    import build_db as b
    cov = b.load_covenant_concordance()
    titles = {(r["instrument"], r["article"]): r["short_title"] for r in csv.DictReader((ROOT / "data/concordance/articles.csv").open())}
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    cands = candidates(con, cov, b) + candidates_1948(con)
    cands += candidates_records(con, {c["id"] for c in cands})
    judged = {}
    for line in (ROOT / "data" / "gold" / "coverage.jsonl").read_text().splitlines():
        g = json.loads(line)
        judged[g["id"]] = g
    if args.gold:
        cands = [c for c in cands if c["id"] in judged]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [c for c in cands if c["id"] not in cache]
    print(f"{len(cands)} candidates; {len(todo)} to ask", file=sys.stderr)
    if todo and not args.jev:
        print("rerun with --jev to ask Jev (sends the records' text to TypeSafe)", file=sys.stderr)
        return 0
    by_meeting = defaultdict(list)
    for c in todo:
        by_meeting[(c["symbol"], c["stage"])].append(c)
    done = 0
    for (sym, stage), items in by_meeting.items():
        if stage == "tc1948":
            opts, instructions = options_1948(items[0]["articles"], titles), INSTRUCTIONS_1948
        elif stage == "record":
            opts, instructions = options_record(items[0]["articles"], titles), INSTRUCTIONS_RECORD
        else:
            opts, instructions = options_for(stage, int(sym.rsplit('.', 1)[1]), items[0]["articles"], cov, titles), INSTRUCTIONS
        for k in range(0, len(items), 15):
            chunk = items[k:k + 15]
            state = {"articles_of_this_meeting": list(opts.values()), "speeches": {}}
            for j, c in enumerate(chunk):
                prev = con.execute("SELECT text FROM segments WHERE symbol = ? AND seq < ? ORDER BY seq DESC LIMIT 1", (sym, c["seq"])).fetchone()
                state["speeches"][f"S{j}"] = {"passage_before": " ".join((prev[0] if prev else "").split())[-500:],
                                              "speech": " ".join(c["text"].split())[:1500]}
            qs = {f"S{j}": jev.choice(instructions.format(key=f"S{j}"), opts) for j in range(len(chunk))}
            try:
                answers = jev.ask(state, qs, task="article_choice")
            except RuntimeError as exc:
                print(f"  {sym}: {exc}", file=sys.stderr)
                continue
            for j, c in enumerate(chunk):
                a = answers.get(f"S{j}") or {}
                pick = a.get("choice")
                p = (a.get("probabilities") or {}).get(pick)
                cache[c["id"]] = {"pick": pick, "p": round(float(p), 3) if isinstance(p, (int, float)) else None,
                                  "options": [o for o in opts if o != NONE and not o.startswith("marker:")]}
                if stage == "tc1948":  # the record's number of each option, for the tag's draft article
                    cache[c["id"]]["drafts"] = {f"UDHR {fin}": draft for fin, draft in c["articles"]}
                elif stage == "record":
                    cache[c["id"]]["drafts"] = {f"{inst} {fin}": draft for inst, fin, draft in c["articles"]}
            done += len(chunk)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache))
        print(f"  asked {done}/{len(todo)}", file=sys.stderr, flush=True)
    if args.gold:
        print("id | judged about one article | judged article | Jev's pick (p)")
        for c in cands:
            g, a = judged[c["id"]], cache.get(c["id"]) or {}
            print(f"{c['id']} | {g['about_article']} | {g['article'][:70]} | {a.get('pick')} ({a.get('p')}) of {a.get('options')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
