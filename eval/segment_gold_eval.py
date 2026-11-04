#!/usr/bin/env python3
"""The database's division of the pages annotated by hand (data/gold/segment_pages.json, eval/annotate_pages.py) against the
annotation: where turns start, their kind, speaker and delegation, and the lines that are not the record's text.

A start is matched on its line (and, for one inside a line, an offset within 15 characters). Reported:
- starts: precision (the database's starts the annotator kept) and recall (the annotator's starts the database has);
  a missed start is a turn inside another, a start too many a false split;
- kind, speaker and delegation of the matched starts (speaker and delegation compared without case, accents or spaces;
  a speaker counts only where the annotator gave one);
- pages wholly right (every start, kind, speaker and delegation; no line marked as not the record's);
by kind of record. --audit FILE compares a page-image audit (eval/segment_audit_*.json or a workflow's result) on the same pages
with the annotation: how many of its missed turns and false splits the annotator confirms.

  python3 eval/segment_gold_eval.py [--db data/travaux.sqlite3] [--audit FILE] [--list]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "eval"))
from gold_pages_build import norm, starts_on_page  # noqa: E402

GOLD = ROOT / "data" / "gold" / "segment_pages.json"
PAGES = ROOT / "eval" / "gold_pages" / "pages.json"


def key(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", text.lower())


def starts_on_page_fuzzy(lines: list[str], segs: list[dict], cutoff: float = 85) -> list[dict]:
    """starts_on_page, with a fuzzy fallback for a database whose text is not the annotated OCR's (the vision reader's pages):
    a segment whose first words match no line exactly is placed on the first line from where the last one stood that holds
    its first 30 characters at a partial ratio of at least `cutoff`."""
    from rapidfuzz import fuzz
    out, at = [], 0
    for s in segs:
        head = norm(s["text"])[:40]
        found = None
        for k in range(at, len(lines)):
            line = norm(lines[k])
            if line and (head.startswith(line[:40]) or line.startswith(head[:30])):
                found, offset = k, 0
                break
            if head[:30] and head[:30] in line:
                found, offset = k, line.index(head[:30])
                break
        if found is None and head[:30]:
            for k in range(at, len(lines)):
                al = fuzz.partial_ratio_alignment(head[:30], norm(lines[k]))
                if al and al.score >= cutoff:
                    found, offset = k, al.dest_start
                    break
        if found is None:
            continue
        at = found
        out.append({"line": found, "offset": offset, "kind": s["kind"], "speaker": s["speaker"] or "",
                    "delegation": s["delegation"] or "", "words": head})
    return out


def same_start(a: dict, b: dict) -> bool:
    return a["line"] == b["line"] and abs((a.get("offset") or 0) - (b.get("offset") or 0)) <= 15


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=ROOT / "data" / "travaux.sqlite3")
    ap.add_argument("--audit", type=Path)
    ap.add_argument("--list", action="store_true", help="list each disagreement")
    ap.add_argument("--fuzzy", action="store_true", help="place the database's starts on the annotated lines by fuzzy match too "
                                                         "(for a database built on another reading of the pages)")
    ap.add_argument("--gold", type=Path, default=GOLD, help="the annotation (default the hand one; data/gold/segment_pages_models.json: "
                                                            "the model annotators' majority)")
    args = ap.parse_args()
    gold = {k: v for k, v in json.loads(args.gold.read_text()).items() if v.get("status", "done") == "done"} if args.gold.exists() else {}
    if not gold:
        print("no page annotated yet", file=sys.stderr)
        return 1
    pages = {p["id"]: p for p in json.loads(PAGES.read_text())}
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    tot = defaultdict(lambda: defaultdict(int))
    found: dict[str, dict] = {}
    for pid, g in sorted(gold.items()):
        p = pages[pid]
        segs = [dict(s) for s in con.execute("SELECT * FROM segments WHERE symbol = ? AND page_start = ? AND kind NOT IN "
                                             "('masthead', 'footnote') ORDER BY seq", (p["symbol"], p["page"]))]
        db = (starts_on_page_fuzzy if args.fuzzy else starts_on_page)(p["lines"], segs)
        hand = g["starts"]
        matched = [(h, next((d for d in db if same_start(h, d)), None)) for h in hand]
        missed = [h for h, d in matched if d is None]
        extra = [d for d in db if not any(same_start(h, d) for h in hand)]
        pairs = [(h, d) for h, d in matched if d]
        kind_bad = [(h, d) for h, d in pairs if h["kind"] != d["kind"]]
        sp = [(h, d) for h, d in pairs if h["kind"] in ("speech", "chair") and h.get("speaker")]
        sp_bad = [(h, d) for h, d in sp if key(h["speaker"]) not in key(d["speaker"]) and key(d["speaker"]) not in key(h["speaker"])
                  or not d["speaker"]]
        dl = [(h, d) for h, d in pairs if h["kind"] == "speech" and h.get("delegation")]
        dl_bad = [(h, d) for h, d in dl if key(h["delegation"]) != key(d["delegation"])]
        ok = not (missed or extra or kind_bad or sp_bad or dl_bad or g["junk_lines"])
        found[pid] = {"missed": missed, "extra": extra}
        for t in (tot["all"], tot[g["stratum"]]):
            t["pages"] += 1; t["ok"] += ok; t["hand"] += len(hand); t["db"] += len(db); t["missed"] += len(missed)
            t["extra"] += len(extra); t["pairs"] += len(pairs); t["kind_bad"] += len(kind_bad); t["sp"] += len(sp)
            t["sp_bad"] += len(sp_bad); t["dl"] += len(dl); t["dl_bad"] += len(dl_bad); t["junk"] += len(g["junk_lines"])
        if args.list:
            for h in missed:
                print(f"{pid} | missed start, line {h['line'] + 1} | {h['kind']} {h.get('speaker', '')} | {p['lines'][h['line']][:70]}")
            for d in extra:
                print(f"{pid} | start too many, line {d['line'] + 1} | {d['kind']} {d['speaker']} | {p['lines'][d['line']][:70]}")
            for h, d in kind_bad:
                print(f"{pid} | kind {d['kind']} for {h['kind']}, line {h['line'] + 1}")
            for h, d in sp_bad + dl_bad:
                print(f"{pid} | {d['speaker']} ({d['delegation']}) for {h['speaker']} ({h.get('delegation', '')}), line {h['line'] + 1}")
            for k in g["junk_lines"]:
                print(f"{pid} | not the record's text, line {k + 1} | {p['lines'][k][:70]}")
    for name, t in sorted(tot.items(), key=lambda x: x[0] != "all"):
        prec = (t["db"] - t["extra"]) / t["db"] if t["db"] else 1
        rec = (t["hand"] - t["missed"]) / t["hand"] if t["hand"] else 1
        print(f"{name}: pages {t['pages']}, wholly right {t['ok']} ({t['ok'] / t['pages']:.0%}); starts: precision {prec:.3f}, "
              f"recall {rec:.3f} ({t['missed']} missed, {t['extra']} too many); kind {1 - t['kind_bad'] / max(t['pairs'], 1):.3f}; "
              f"speaker {1 - t['sp_bad'] / max(t['sp'], 1):.3f} ({t['sp']}); delegation {1 - t['dl_bad'] / max(t['dl'], 1):.3f}; "
              f"lines not the record's {t['junk']}")
    if args.audit:
        data = json.loads(args.audit.read_text())
        rows = data["results"] if isinstance(data, dict) else data
        items = data.get("pages") if isinstance(data, dict) else None
        conf = defaultdict(lambda: [0, 0])
        for r in rows:
            pid = r.get("id") or (items[r["i"]]["id"] if items else None) or f"{r.get('symbol')} p{r.get('page')}"
            if pid not in found:
                continue
            for e in r.get("errors", []):
                if e["type"] in ("missed_turn", "false_split"):
                    conf[e["type"]][0] += 1
            conf["missed_turn"][1] += len(found[pid]["missed"])
            conf["false_split"][1] += len(found[pid]["extra"])
        for t, (a, h) in conf.items():
            print(f"audit {t}: the readers report {a}, the annotation has {h}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
