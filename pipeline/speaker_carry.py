#!/usr/bin/env python3
"""Keep the speakers of the database as they were when the vision reader's text replaces the OCR's (the user's decision of
21 October 2026: the vision reader gives the text and the division into speeches, the speakers stay with the OCR engines'
resolution; preregistered in docs/devlog.md).

Each record whose segments changed is aligned word by word, old against new. A new speech whose opening is an old speech's
opening (the first words it shares with the old text stand at the same place in both) continues that speech: if its speaker
or delegation differs, the old ones are written to data/gazetteer/speaker_kept.csv, which api/build_db.py applies (before
the hand fixes of speaker_fixes.csv). A new speech whose opening falls inside an old segment is a new turn (the vision text
split it off): it keeps the resolution's speaker and is counted. Old speeches whose opening falls inside a new speech
(merged) are counted.

  python3 pipeline/speaker_carry.py OLD.sqlite3 [--root DIR] [--dry-run]
DIR is the project (or a copy of it) whose data/travaux.sqlite3 is the new database.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORD_RE = re.compile(r"\w+")
LOOK = 8  # words of a speech's opening in which to find one the old text shares
SLACK = 2  # how far that word may stand from the same place in the old speech


def words(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text or "")]


def segments(con: sqlite3.Connection) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for r in con.execute("SELECT id, symbol, seq, kind, speaker, delegation, speaker_method, text FROM segments ORDER BY symbol, seq"):
        out[r[1]].append({"id": r[0], "kind": r[3], "speaker": r[4], "delegation": r[5], "method": r[6], "text": r[7]})
    return out


def match(old: list[dict], new: list[dict]) -> tuple[list[tuple[int, int | None, str]], int]:
    """For each new speech (its index), the old segment its opening comes from and how: "continues" (the old speech's
    opening), "split" (from inside an old speech), "was <kind>" (an old segment of another kind), "unaligned". And the
    number of old speeches whose opening falls inside a new speech (merged)."""
    ow, oseg, ostart, nw, nseg, nstart = [], [], [], [], [], []
    for k, s in enumerate(old):
        ostart.append(len(ow))
        w = words(s["text"])
        ow += w
        oseg += [k] * len(w)
    for k, s in enumerate(new):
        nstart.append(len(nw))
        w = words(s["text"])
        nw += w
        nseg += [k] * len(w)
    n2o = {}
    for a, b, size in difflib.SequenceMatcher(None, ow, nw, autojunk=False).get_matching_blocks():
        for i in range(size):
            n2o[b + i] = a + i
    o2n = {v: k for k, v in n2o.items()}
    out = []
    for k, s in enumerate(new):
        if s["kind"] != "speech":
            continue
        first = next(((j, n2o[nstart[k] + j]) for j in range(LOOK) if nstart[k] + j in n2o and nseg[nstart[k] + j] == k), None)
        if first is None:
            out.append((k, None, "unaligned"))
            continue
        j, p = first
        o = old[oseg[p]]
        how = ("continues" if abs((p - ostart[oseg[p]]) - j) <= SLACK else "split") if o["kind"] == "speech" else f"was {o['kind']}"
        out.append((k, oseg[p], how))
    merged = 0
    for k, o in enumerate(old):
        if o["kind"] == "speech":
            p = next((ostart[k] + j for j in range(LOOK) if ostart[k] + j in o2n and oseg[ostart[k] + j] == k), None)
            if p is not None and nstart[nseg[o2n[p]]] < o2n[p] - LOOK:
                merged += 1
    return out, merged


def carry(old: list[dict], new: list[dict]) -> tuple[list[dict], Counter, list[dict]]:
    """(rows for speaker_kept.csv, counts, the new turns) for one record."""
    pairs, merged = match(old, new)
    rows, n, turns = [], Counter(), []
    for k, i, how in pairs:
        s = new[k]
        n["speeches"] += 1
        if how == "unaligned":
            n["opening not aligned"] += 1
            continue
        o = old[i]
        if how == "continues":
            n["continues an old speech"] += 1
            if (s["speaker"], s["delegation"]) != (o["speaker"], o["delegation"]):
                n["of which speaker carried back"] += 1
                rows.append({"segment_id": s["id"], "speaker": o["speaker"] or "", "delegation": o["delegation"] or "",
                             "speaker_method": o["method"] or "", "note": f"kept from {o['id']} (was {s['speaker']}, {s['delegation']})"})
        else:
            n["new turn (split from an old speech)" if how == "split" else f"new speech where the old text had a {o['kind']}"] += 1
            turns.append({"id": s["id"], "speaker": s["speaker"], "delegation": s["delegation"], "from": o["id"]})
    if merged:
        n["old speech merged into another"] += merged
    return rows, n, turns


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old", type=Path)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    old = segments(sqlite3.connect(f"file:{args.old}?mode=ro", uri=True))
    new = segments(sqlite3.connect(f"file:{args.root / 'data' / 'travaux.sqlite3'}?mode=ro", uri=True))
    rows, total, turns, changed = [], Counter(), [], 0
    for sym, segs in new.items():
        before = old.get(sym, [])
        if [(s["id"], s["text"]) for s in segs] == [(s["id"], s["text"]) for s in before]:
            if any((a["speaker"], a["delegation"]) != (b["speaker"], b["delegation"]) for a, b in zip(segs, before) if a["kind"] == "speech"):
                # (the text is the same and a speaker moved: the resolution's pooled lists, changed by another record)
                for a, b in zip(segs, before):
                    if a["kind"] == "speech" and (a["speaker"], a["delegation"]) != (b["speaker"], b["delegation"]):
                        total["same text, speaker carried back"] += 1
                        rows.append({"segment_id": a["id"], "speaker": b["speaker"] or "", "delegation": b["delegation"] or "",
                                     "speaker_method": b["method"] or "", "note": f"kept (was {a['speaker']}, {a['delegation']})"})
            continue
        changed += 1
        r, n, t = carry(before, segs)
        rows += r
        total.update(n)
        turns += t
    print(f"records with changed segments: {changed}", file=sys.stderr)
    for k, v in sorted(total.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}", file=sys.stderr)
    print(f"speakers carried back: {len(rows)}; new turns with a speaker of their own: {len(turns)}", file=sys.stderr)
    if not args.dry_run:
        path = args.root / "data" / "gazetteer" / "speaker_kept.csv"
        # (the rows of earlier merges are already in force in both databases, so they show no difference: kept, 28 Oct 2026)
        ids = {r["segment_id"] for r in rows}
        if path.exists():
            rows = [r for r in csv.DictReader(path.open(encoding="utf-8")) if r["segment_id"] not in ids] + rows
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["segment_id", "speaker", "delegation", "speaker_method", "note"])
            w.writeheader()
            w.writerows(rows)
        print(f"-> {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
