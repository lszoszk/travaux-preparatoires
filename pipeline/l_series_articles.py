#!/usr/bin/env python3
"""The article each draft or amendment of the L series concerns (A/C.3/L.n, E/CN.4/L.n), from two independent readers.

The readers (agents that read the document's text and the passages of the debates that cite it, one shown nothing of
the other's answer) are recorded in data/concordance/l_series_readers.json: per base document, the first reader's and
the second reader's answer. This script keeps a document's article when

  - both readers give the same instrument and article; or
  - they differ, but the speeches that cite the document, tagged by the pipeline, agree with one of them (at least two
    tagged speeches, at least 60% on that article);

and leaves the others without an article. Where two blind judges (a Sonnet and an Opus, who saw neither reader's answer)
also read the document (the "judges" of the record), an article is kept only when at least three of the four independent
readers give it. Article 1 is one text in both Covenants and gets the instrument "ICCPR+ICESCR". It writes data/concordance/l_series_articles.csv, which api/build_db.py applies
to the document's paragraphs (with its Rev, Add and Corr versions).

Usage: python3 pipeline/l_series_articles.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READERS = ROOT / "data" / "concordance" / "l_series_readers.json"
OUT = ROOT / "data" / "concordance" / "l_series_articles.csv"


def key(a: dict) -> tuple[str, int | None]:
    if a["instrument"] != "none" and a.get("final_article") == 1 and a["instrument"] in ("ICCPR", "ICESCR", "ICCPR+ICESCR"):
        return ("ICCPR+ICESCR", 1)
    return (a["instrument"], a["final_article"] if a["instrument"] != "none" else None)


def label(a: dict) -> str:
    if a["instrument"] == "none" or not a.get("final_article"):
        return "none"
    if a["final_article"] == 1 and a["instrument"] in ("ICCPR", "ICESCR", "ICCPR+ICESCR"):
        return "ICCPR+ICESCR 1"
    return f"{a['instrument']} {a['final_article']}"


def main() -> int:
    data = json.loads(READERS.read_text())
    rows_left: list = []
    rows, stats = [], {"agree": 0, "citing decided": 0, "none": 0, "disagree, left out": 0}
    for d in data:
        a, b, tally = d["first"], d["second"], d.get("citing_tag_tally") or {}
        if not a or not b:
            continue
        pick, how = None, ""
        if key(a) == key(b) and a["instrument"] != "none":
            pick, how = a, "two readers agree"
            stats["agree"] += 1
        elif {key(a), key(b)} == {("ICESCR", 28), ("ICCPR", 50)}:
            pick, how = (a if key(a) == ("ICESCR", 28) else b), "two readers agree"
            stats["agree"] += 1
        elif key(a) == key(b):
            stats["none"] += 1
            continue
        else:
            tagged = sum(tally.values())
            for cand in (a, b):
                if cand["instrument"] != "none" and tagged >= 2 and tally.get(f"{cand['instrument']} {cand['final_article']}", 0) / tagged >= 0.6:
                    pick, how = cand, "the readers differ; the citing speeches decide"
                    stats["citing decided"] += 1
                    break
            if not pick:
                stats["disagree, left out"] += 1
                continue
        inst = "ICCPR+ICESCR" if label(pick) == "ICCPR+ICESCR 1" else pick["instrument"]
        judges = list((d.get("judges") or {}).values())
        if judges:
            votes = [label(x) for x in (a, b, *judges)]
            if votes.count(label(pick)) < 3:
                stats["judges disagree, left out"] = stats.get("judges disagree, left out", 0) + 1
                rows_left.append((d["base"], label(pick), votes))
                continue
        rows.append({"base": d["base"], "instrument": inst, "final_article": pick["final_article"],
                     "draft_article": pick.get("draft_article") or "", "note": f"{pick['subject'][:110]} ({how})".replace("\n", " ")})
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["base", "instrument", "final_article", "draft_article", "note"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["base"]))
    print(f"{len(rows)} documents given an article {stats}", file=__import__("sys").stderr)
    for base, chosen, votes in rows_left:
        print(f"  left out: {base} ({chosen}); the four readers: {votes}", file=__import__("sys").stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
