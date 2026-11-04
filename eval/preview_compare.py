#!/usr/bin/env python3
"""Two builds of the database side by side: the current one and a preview (pipeline/preview_mixed.py), overall and for the
records whose pages the vision reader read. Counts of segments by kind; speeches with a speaker (and how it was found), with a
delegation, with an article; meeting dates; and the records that changed most in their number of speeches.

  python3 eval/preview_compare.py OLD.sqlite3 NEW.sqlite3 [--manifest <preview>/preview_manifest.json] [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path


def stats(db: Path, only: set[str] | None) -> dict:
    con = sqlite3.connect(db)
    rows = con.execute("SELECT symbol, kind, speaker, delegation, speaker_method, final_article FROM segments").fetchall()
    rows = [r for r in rows if only is None or r[0] in only]
    sp = [r for r in rows if r[1] == "speech"]
    per_doc = Counter(r[0] for r in sp)
    dates = dict(con.execute("SELECT symbol, meeting_date FROM documents").fetchall())
    return {"segments": len(rows), "by_kind": dict(Counter(r[1] for r in rows).most_common()), "speeches": len(sp),
            "with_speaker": sum(bool(r[2]) for r in sp), "with_delegation": sum(bool(r[3]) for r in sp),
            "unresolved": sum(r[4] == "unresolved" for r in sp), "with_article": sum(bool(r[5]) for r in sp),
            "methods": dict(Counter(r[4] for r in sp).most_common()), "per_doc": per_doc,
            "dates": {k: v for k, v in dates.items() if only is None or k in only}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old", type=Path)
    ap.add_argument("new", type=Path)
    ap.add_argument("--manifest", type=Path, help="restrict the second table to the records with pages of the vision reader")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    out = {}
    scopes = [("all records", None)]
    if args.manifest:
        safes = {p.split("/")[0] for p in json.loads(args.manifest.read_text())["pages"]}
        con = sqlite3.connect(args.old)
        syms = {s for (s,) in con.execute("SELECT symbol FROM documents")
                if s.replace("/", "_") in safes}
        scopes.append((f"records with vision-reader pages ({len(syms)})", syms))
    for name, only in scopes:
        a, b = stats(args.old, only), stats(args.new, only)
        print(f"\n== {name}", file=sys.stderr)
        for k in ("segments", "speeches", "with_speaker", "with_delegation", "unresolved", "with_article"):
            print(f"  {k:16} {a[k]:7} -> {b[k]:7}  ({b[k] - a[k]:+d})", file=sys.stderr)
        for k in sorted(set(a["by_kind"]) | set(b["by_kind"])):
            print(f"  kind {k:11} {a['by_kind'].get(k, 0):7} -> {b['by_kind'].get(k, 0):7}", file=sys.stderr)
        changed_dates = sorted(s for s in a["dates"] if a["dates"][s] != b["dates"].get(s))
        print(f"  meeting dates changed: {len(changed_dates)} {changed_dates[:8]}", file=sys.stderr)
        diff = sorted(((b["per_doc"].get(s, 0) - a["per_doc"].get(s, 0), s) for s in set(a["per_doc"]) | set(b["per_doc"])),
                      key=lambda x: -abs(x[0]))
        print("  most changed (speeches): " + ", ".join(f"{s} {d:+d}" for d, s in diff[:12] if d), file=sys.stderr)
        out[name] = {"old": {k: v for k, v in a.items() if k not in ("per_doc", "dates")},
                     "new": {k: v for k, v in b.items() if k not in ("per_doc", "dates")},
                     "dates_changed": changed_dates, "most_changed": [(s, d) for d, s in diff[:40] if d]}
    if args.json:
        args.json.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
