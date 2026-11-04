#!/usr/bin/env python3
"""The sponsors of amendments and proposals, as the session reports list them.

The records name an amendment's sponsors in passing ("the Cuban amendment", "the amendment
submitted by the delegations of X and Y"), and the parser that reads them (decisions.proposers_of)
misses adjective lists, sub-amendments and footnotes. The reports list them plainly: "Amendments
were submitted by Colombia and Uruguay (A/C.3/L.644), France (A/C.3/L.645), the Philippines
(A/C.3/L.646)"; "The representative of Yugoslavia submitted an amendment (E/CN.4/L.232)". This
reads those lists from the reports' tagged paragraphs, strictly: a sponsor is read only where the
words between the previous symbol (or "by", or the start of the clause) and the symbol are state
names and joining words, or a body ("the Working Party").

Writes data/concordance/amendment_sponsors.csv (symbol, sponsors, the report and segment it was read
from, how many readings, other readings, and the hand check's verdict, from
amendment_sponsors_checked.csv); api/server.py and api/build_db.py prefer it to the sponsors read
from the records.

  python3 pipeline/amendment_sponsors.py            # write the table, print the comparison with the records
"""
from __future__ import annotations

import csv
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from decisions import ADJECTIVES, STATES, delegations_named  # noqa: E402

NAMES = sorted({*STATES, *ADJECTIVES}, key=len, reverse=True)

OUT = ROOT / "data" / "concordance" / "amendment_sponsors.csv"
CHECKED = ROOT / "data" / "concordance" / "amendment_sponsors_checked.csv"
# the Commission's and the Third Committee's series, as the OCR reads them ("A/¢.3/L.632", "a/c .3/L.632", "E/CN,4/L.110")
SERIES_RE = re.compile(r"(?:(?P<a>[Aa]\s*/\s*[CcÇ¢(]\s*\.?\s*3)|(?P<e>E\s*/\s*(?:C[NIl1]|[OA]N)\s*[.,]\s*[4U^hA]))\s*/\s*")
SYMBOL_RE = re.compile(r"(?:(?:[Aa]\s*/\s*[CcÇ¢(]\s*\.?\s*3|E\s*/\s*(?:C[NIl1]|[OA]N)\s*[.,]\s*[4U^hA])\s*/\s*)?"
                       r"[Ll1]\s*\.\s*(?P<n>\d{1,4})(?![\w])(?P<suffix>(?:\s*/\s*(?:Rev|Add|Corr)\s*\.\s*\d)*)")
BODY_RE = re.compile(r"\b(?:the\s+)?(Working\s+Party|Working\s+Group|Drafting\s+Committee|Sub-?Committee(?:\s+\d)?|Secretary-General|Chairman)\b", re.I)
BODY_AFTER_RE = re.compile(r"[^)]{0,30}\)\s*,\s*the\s+(Working\s+Party|Working\s+Group|Drafting\s+Committee|Sub-?Committee(?:\s+\d)?)\b", re.I)
FILLER_RE = re.compile(r"(?:[\s,;:]|\band\b|\bthe\b|\bjointly\b|\brepresentatives?\b|\bdelegations?\b|\bgovernments?\b|\bof\b|\bby\b)*", re.I)
# the clause that introduces a sponsor: "submitted by", "the amendment of", "the representative of X submitted an amendment"
LEAD_RE = re.compile(r"(?:\b(?:submitted|proposed|presented|sponsored|introduced|put\s+forward)\s+(?:jointly\s+)?by\b"
                     r"|\b(?:amendments?|proposals?|texts?|draft\s+resolution|sub-amendment)\s+(?:submitted\s+)?(?:jointly\s+)?(?:by|of)\b"
                     r"|\bby\b|:)", re.I)
REP_RE = re.compile(r"\b(?:the\s+)?(?:representatives?|delegations?)\s+of\s+(?P<who>[^.;()]{3,120}?)\s+(?:had\s+)?(?:jointly\s+)?"
                    r"(?:submitted|proposed|presented|introduced|put\s+forward)\s+(?:an?\s+|the\s+|a\s+joint\s+)?"
                    r"(?:revised\s+)?(?:amendments?|proposals?|texts?|draft\s+resolution|alternative\s+text)[^.;()]{0,40}$", re.I)
ADJ_RE = re.compile(r"\b(?:the\s+)?(?P<who>(?:[A-Z][a-z]+(?:\s*-\s*|\s+and\s+|,\s*)?){1,5})\s+(?:joint\s+)?(?:amendments?|proposals?|texts?|sub-amendment)\s*$")


def symbol(m: re.Match, series: str) -> str:
    suffix = re.sub(r"\s+", "", m.group("suffix") or "")
    return f"{series}/L.{int(m.group('n'))}{suffix}"


def only_states(text: str) -> list[str]:
    """The states a phrase names, if it names nothing but states and joining words."""
    names = delegations_named(text)
    if not names:
        return []
    rest = text
    for n in NAMES:
        if n in rest:
            rest = re.sub(rf"\b{re.escape(n)}\b", " ", rest)
    return names if FILLER_RE.fullmatch(rest) else []


def sponsors_before(text: str, start: int, prev_end: int) -> list[str] | None:
    """The sponsors the words before a symbol name, or None."""
    head = text[max(prev_end, start - 220):start]
    head = re.split(r"[.;]\s+(?=[A-Z])", head)[-1]  # this sentence only
    body = BODY_RE.search(head[-60:])
    if body and re.search(r"\b(?:report|text|proposal|suggestion)s?\s+(?:of|by|submitted\s+by)\s+(?:the\s+)?[\w\s,-]{0,22}$", head, re.I):
        return [re.sub(r"\s+", " ", body.group(1)).title().replace("-", "-")]
    m = REP_RE.search(head)
    if m and only_states(m.group("who")):
        return only_states(m.group("who"))
    # "the amendment of Costa Rica to the Netherlands amendment (L.648)": whose the symbol is, the words do not tell
    if re.search(r"\b(?:amendments?|proposals?|sub-amendments?)\b[^()]*\bto\s+(?:the\s+)?(?:[A-Z][\w-]*\s+){0,4}(?:joint\s+)?"
                 r"(?:amendments?|proposals?|texts?)\s*$", head):
        return None
    m = ADJ_RE.search(head)
    if m and delegations_named(m.group("who")) and only_states(m.group("who")):
        return only_states(m.group("who"))
    leads = list(LEAD_RE.finditer(head))
    # the list form: after the previous symbol, or after "submitted by", only states
    tail = head[leads[-1].end():] if leads else head
    if prev_end and prev_end >= start - 220 and not leads:
        tail = head
    return only_states(tail) or None


def main() -> int:
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    reports = sorted({r["symbol"] for r in csv.DictReader((ROOT / "data/concordance/report_sections.csv").open())})
    found: dict[str, Counter] = defaultdict(Counter)
    where: dict[str, tuple[str, str]] = {}
    for rep in reports:
        for sid, text in con.execute("SELECT id, text FROM segments WHERE symbol = ? ORDER BY seq", (rep,)):
            # a bare "L.645" is in the series of the last full symbol in the paragraph, else the report's own
            series = "A/C.3" if rep.startswith("A/") else "E/CN.4"
            text = " ".join(text.split())
            prev_end = 0
            for m in SYMBOL_RE.finditer(text):
                s = SERIES_RE.match(text, m.start())
                if s:
                    series = "A/C.3" if s.group("a") else "E/CN.4"
                sym = symbol(m, series)
                opened = text.rfind("(", max(0, m.start() - 3), m.start() + 1)
                who = sponsors_before(text, opened if opened >= 0 else m.start(), prev_end)
                # "In its report (A/C.3/L.655/Corr.1 and 2), the Working Party ..."
                after = BODY_AFTER_RE.match(text, m.end())
                if not who and after and re.search(r"\bits\s+(?:report|text)\s*\(?\s*$", text[max(0, m.start() - 30):m.start()], re.I):
                    who = [re.sub(r"\s+", " ", after.group(1)).title()]
                prev_end = text.find(")", m.end()) + 1 or m.end()
                if who:
                    # a corrigendum is its document's: the sponsors are the same
                    for s_ in dict.fromkeys([sym, re.sub(r"(?:/Corr\.\d)+$", "", sym)]):
                        found[s_][tuple(who)] += 1
                        where.setdefault(s_, (rep, sid))
    rows = []
    for sym, c in found.items():
        (who, k), *rest = c.most_common()
        rows.append({"symbol": sym, "sponsors": "|".join(who), "report": where[sym][0], "segment": where[sym][1],
                     "readings": sum(c.values()), "disagree": "; ".join("|".join(w) for w, _ in rest)})
    # the hand check (data/concordance/amendment_sponsors_checked.csv): corrections, symbols the OCR cut short, unclear rows
    by_sym = {r["symbol"]: r for r in rows}
    if CHECKED.exists():
        for c in csv.DictReader(CHECKED.open()):
            r = by_sym.get(c["symbol"])
            if c["verdict"] == "wrong" and not c["sponsors"]:
                # (a compilation of amendments has no sponsor: A/C.3/L.460); kept, with none, so that the records'
                # reading ("Brazil", whose amendment it holds) does not stand in
                by_sym[c["symbol"]] = {**(r or {"report": c["note"].split(";")[0], "segment": "", "readings": 0, "disagree": ""}),
                                       "symbol": c["symbol"], "sponsors": "", "checked": "no sponsor"}
            elif c["verdict"] in ("bad-symbol", "unclear"):
                by_sym.pop(c["symbol"], None)
                who = c["sponsors"] or (r or {}).get("sponsors")
                if c["verdict"] == "bad-symbol" and c["correct_symbol"] and who and r and c["correct_symbol"] not in by_sym:
                    by_sym[c["correct_symbol"]] = {**r, "symbol": c["correct_symbol"], "sponsors": who, "checked": "corrected"}
            elif c["verdict"] == "added" and c["sponsors"]:
                # (a document the reports list only in a table, or where the parser reads nothing; read by hand)
                by_sym[c["symbol"]] = {"symbol": c["symbol"], "sponsors": c["sponsors"], "report": c["note"].split(";")[0],
                                       "segment": "", "readings": 0, "disagree": "", "checked": "added"}
            elif r:
                r["checked"] = c["verdict"] if c["verdict"] == "right" else "corrected"
                if c["verdict"] != "right" and c["sponsors"]:
                    r["sponsors"] = c["sponsors"]
    rows = [{**r, "checked": r.get("checked", "")} for r in by_sym.values()]
    rows.sort(key=lambda r: (r["symbol"].split("/L.")[0] if "/L." in r["symbol"] else re.sub(r"/\d.*$", "", r["symbol"]),
                             int(re.search(r"(\d+)(?:/(?:Rev|Add|Corr)\.\d+)*$", r["symbol"]).group(1)), r["symbol"]))
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} amendments with sponsors from {len(reports)} reports -> {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
