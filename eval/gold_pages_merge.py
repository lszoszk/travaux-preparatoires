#!/usr/bin/env python3
"""The three model annotators of each page in eval/gold_pages/pages.json, merged: a start, a kind, a speaker, a delegation or a
line marked as not the record's counts when two of the three give it; a page whose three annotators agree on everything is
"unanimous", the others list what they disagree on, for a hand decision in eval/annotate_pages.py.

  python3 eval/gold_pages_merge.py RESULT.json     # a workflow result: [{key: "g<i>", reader, starts, junk_lines, note}]
  -> data/gold/segment_pages_models.json
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "eval" / "gold_pages" / "pages.json"
OUT = ROOT / "data" / "gold" / "segment_pages_models.json"


def key(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", text.lower())


def offset(line: str, words: str) -> int:
    """Where the annotator's first words begin in the line (0 when they open it or cannot be found)."""
    w = re.sub(r"^[\W_]+", "", words or "")[:25]
    k = line.find(w) if w else -1
    return 0 if k < 0 or not line[:k].strip(" \t\"“”'‘’.,;:|-—_") else k


def main() -> int:
    data = json.loads(Path(sys.argv[1]).read_text())
    rows = data["result"] if isinstance(data, dict) and "result" in data else data
    rows = json.loads(rows) if isinstance(rows, str) else rows
    pages = json.loads(PAGES.read_text())
    by = defaultdict(list)
    for r in rows:
        by[int(r["key"][1:])].append(r)
    out = {}
    for i, p in enumerate(pages):
        readers = by.get(i, [])
        n = len(readers)
        clusters: list[dict] = []
        for r in readers:
            for s in r["starts"]:
                ln = s["line"] - 1
                if not 0 <= ln < len(p["lines"]):
                    continue
                off = offset(p["lines"][ln], s["words"])
                c = next((c for c in clusters if c["line"] == ln and abs(c["offset"] - off) <= 15 and r["reader"] not in c["readers"]), None)
                if c is None:
                    c = {"line": ln, "offset": off, "readers": [], "kinds": [], "speakers": [], "delegations": []}
                    clusters.append(c)
                c["readers"].append(r["reader"])
                c["kinds"].append(s["kind"])
                c["speakers"].append(s["speaker"].strip())
                c["delegations"].append(s["delegation"].strip())
        starts, disputes = [], []
        for c in sorted(clusters, key=lambda c: (c["line"], c["offset"])):
            votes = len(c["readers"])
            kind, kv = Counter(c["kinds"]).most_common(1)[0]
            spk = Counter(key(x) for x in c["speakers"]).most_common(1)[0]
            spk_name = next(x for x in c["speakers"] if key(x) == spk[0])
            dlg = Counter(key(x) for x in c["delegations"]).most_common(1)[0]
            dlg_name = next(x for x in c["delegations"] if key(x) == dlg[0])
            entry = {"line": c["line"], "offset": c["offset"], "words": p["lines"][c["line"]][c["offset"]:c["offset"] + 40],
                     "kind": kind, "speaker": spk_name.upper() if kind == "speech" else spk_name, "delegation": dlg_name,
                     "votes": votes, "variants": {"kind": c["kinds"], "speaker": c["speakers"], "delegation": c["delegations"]}}
            if votes * 2 > n:
                starts.append(entry)
            if votes < n or kv < votes or spk[1] < votes or dlg[1] < votes:
                disputes.append(entry)
        jv = Counter(j - 1 for r in readers for j in r["junk_lines"])
        junk = sorted(j for j, v in jv.items() if v * 2 > n and 0 <= j < len(p["lines"]))
        junk_disputed = sorted(j for j, v in jv.items() if v < n and 0 <= j < len(p["lines"]))
        out[p["id"]] = {"symbol": p["symbol"], "page": p["page"], "stratum": p["stratum"], "readers": n,
                        "unanimous": not disputes and not junk_disputed, "starts": starts, "junk_lines": junk,
                        "disputes": disputes, "junk_disputed": junk_disputed, "notes": [r["note"] for r in readers if r.get("note")]}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    u = sum(v["unanimous"] for v in out.values())
    print(f"{len(out)} pages -> {OUT.relative_to(ROOT)}: {u} unanimous, {len(out) - u} with disputes "
          f"({sum(len(v['disputes']) for v in out.values())} starts, {sum(len(v['junk_disputed']) for v in out.values())} lines)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
