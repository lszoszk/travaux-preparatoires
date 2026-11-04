#!/usr/bin/env python3
"""Speaker attribution audit on the page images: is the speaker and delegation of a speech the one printed on the scan?

The reference sets of eval/speaker_eval.py cover 13 records, mostly of 1947-49. This audit draws speeches from every kind
of record (the strata of eval/segment_audit_sample.py), and has readers who do not see the database's answer read the
speaker and the delegation from the page image.

  sample   python3 eval/speaker_audit.py sample OUT.json [--per 30] [--seed 67]
  compare  python3 eval/speaker_audit.py compare SAMPLE.json READERS.json DISPUTES.json
             readers: [{"model": ..., "answers": [{"id", "speaker", "delegation"}]}] from two readers per item;
             writes the items where the two readers and the database do not all agree (for a verifier who sees all three)
  record   python3 eval/speaker_audit.py record SAMPLE.json READERS.json VERDICTS.json --round 67 --checked "..."
             an item is right when both readers agree with the database, or the verifier says the database is right;
             writes data/gold/speakers_audit.jsonl and prints precision by kind of record

A speaker is the same when the surnames agree after folding case and accents and allowing an OCR misreading (similarity of
85 or more) and the delegations name the same state or body (similarity of 85 or more, or one contains the other).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "eval"))
from ocr import page_image, safe_name, scan_pdf  # noqa: E402
from segment_audit_sample import stratum  # noqa: E402

GOLD = ROOT / "data" / "gold" / "speakers_audit.jsonl"


def fold(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "").upper()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^A-Z ]", " ", s).split())


def same_speaker(a: str | None, b: str | None) -> bool:
    a, b = fold(a), fold(b)
    return bool(a and b) and (fuzz.ratio(a, b) >= 85 or a in b.split() or b in a.split() or a in b or b in a)


def same_delegation(a: str | None, b: str | None) -> bool:
    a, b = fold(a), fold(b)
    if not a or not b:
        return False
    return fuzz.ratio(a, b) >= 85 or fuzz.token_set_ratio(a, b) >= 90 or a in b or b in a


def sample(out: Path, per: int, seed: int) -> None:
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    con.row_factory = sqlite3.Row
    pool = defaultdict(list)
    for r in con.execute("SELECT s.id, s.symbol, s.page_start, s.speaker, s.delegation, s.speaker_method, s.text, d.instrument, d.body, "
                         "d.session FROM segments s JOIN documents d USING(symbol) WHERE s.kind = 'speech' AND length(s.text) > 100"):
        st = stratum(r["instrument"], r["body"], r["session"], r["symbol"])
        if st and scan_pdf(r["symbol"]):
            pool[st].append((r, None))
    rnd = random.Random(seed)
    items = []
    for st in sorted(pool):
        for r, _ in rnd.sample(pool[st], min(per, len(pool[st]))):
            img = page_image(r["symbol"], r["page_start"])  # (rendered from the PDF if the image is not on disk)
            items.append({"id": r["id"], "stratum": st, "symbol": r["symbol"], "page": r["page_start"], "image": str(img),
                          "opening": " ".join(r["text"].split())[:140],
                          "db_speaker": r["speaker"], "db_delegation": r["delegation"], "db_method": r["speaker_method"]})
    out.write_text(json.dumps(items, ensure_ascii=False, indent=1))
    print(f"{len(items)} speeches: " + ", ".join(f"{k} {min(per, len(v))} of {len(v)}" for k, v in sorted(pool.items())), file=sys.stderr)


def readers_by_id(readers: list[dict]) -> dict[str, list[dict]]:
    by = defaultdict(list)
    for r in readers:
        for a in r["answers"]:
            by[a["id"]].append({**a, "model": r["model"]})
    return by


def judge(item: dict, reads: list[dict]) -> str:
    """'right' | 'unresolved' | 'dispute'."""
    if not item["db_speaker"]:
        return "unresolved"
    ok = [same_speaker(item["db_speaker"], x["speaker"]) and same_delegation(item["db_delegation"], x["delegation"]) for x in reads]
    return "right" if len(reads) >= 2 and all(ok) else "dispute"


def compare(sample_p: Path, readers_p: Path, out: Path) -> None:
    items = json.loads(sample_p.read_text())
    res = json.loads(readers_p.read_text())
    res = res.get("result", res) if isinstance(res, dict) else res
    by = readers_by_id([r for r in res if r])
    disputes = []
    for it in items:
        if judge(it, by.get(it["id"], [])) == "dispute":
            disputes.append({**it, "reads": [{k: x[k] for k in ("model", "speaker", "delegation")} for x in by.get(it["id"], [])]})
    out.write_text(json.dumps(disputes, ensure_ascii=False, indent=1))
    print(f"{len(items)} speeches: {len(disputes)} to a verifier (the readers and the database do not all agree)", file=sys.stderr)


def record(sample_p: Path, readers_p: Path, verdicts_p: Path | None, rnd: int, checked: str) -> None:
    items = json.loads(sample_p.read_text())
    res = json.loads(readers_p.read_text())
    res = res.get("result", res) if isinstance(res, dict) else res
    by = readers_by_id([r for r in res if r])
    ver = {}
    if verdicts_p:
        v = json.loads(verdicts_p.read_text())
        v = v.get("result", v) if isinstance(v, dict) else v
        for b in v:
            for a in (b or {}).get("answers", []):
                ver[a["id"]] = a
    rows, tally = [], defaultdict(lambda: [0, 0, 0])  # right, checked, unresolved
    for it in items:
        j = judge(it, by.get(it["id"], []))
        note, right = "", None
        if j == "unresolved":
            right, note = False, "no speaker given"
        elif j == "right":
            right = True
        else:
            a = ver.get(it["id"])
            if a is None:
                continue
            right, note = bool(a["database_right"]), a["note"]
        t = tally[it["stratum"]]
        t[1] += 1
        t[0] += bool(right)
        t[2] += j == "unresolved"
        rows.append({"id": it["id"], "symbol": it["symbol"], "page": it["page"], "stratum": it["stratum"], "db_speaker": it["db_speaker"],
                     "db_delegation": it["db_delegation"], "db_method": it["db_method"], "right": right, "unresolved": j == "unresolved",
                     "note": note, "round": rnd, "checked": checked})
    with GOLD.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tr = sum(t[0] for t in tally.values())
    tc = sum(t[1] for t in tally.values())
    for k, (a, n, u) in sorted(tally.items()):
        print(f"{k:28} {a:3}/{n:3} = {100 * a / n:5.1f}%  (unresolved {u})")
    print(f"all kinds, unweighted: {tr}/{tc} = {100 * tr / tc:.1f}%")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("out", type=Path)
    s.add_argument("--per", type=int, default=30)
    s.add_argument("--seed", type=int, default=67)
    c = sub.add_parser("compare")
    c.add_argument("sample", type=Path)
    c.add_argument("readers", type=Path)
    c.add_argument("out", type=Path)
    r = sub.add_parser("record")
    r.add_argument("sample", type=Path)
    r.add_argument("readers", type=Path)
    r.add_argument("verdicts", type=Path)
    r.add_argument("--round", type=int, required=True)
    r.add_argument("--checked", required=True)
    a = ap.parse_args()
    if a.cmd == "sample":
        sample(a.out, a.per, a.seed)
    elif a.cmd == "compare":
        compare(a.sample, a.readers, a.out)
    else:
        record(a.sample, a.readers, a.verdicts, a.round, a.checked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
