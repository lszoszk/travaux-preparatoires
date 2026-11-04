#!/usr/bin/env python3
"""How much of the drafting record the database holds, in three tiers, from the UN's own lists.

1. Meeting records: those the lists name (the UN Library's UDHR guide, the finding aids of the drafting
   history, the Covenants' meeting series) and that are about the instruments. A record of the Covenants'
   series that the first two pages show not to be about them (pipeline/ocr_all.py relevance check) is
   left out of the count and reported apart.
2. Other documents the same lists name (reports, drafts, working papers, resolutions).
3. Documents the records cite that no list names (mostly amendments, the L-series): how many of the
   distinct symbols and of the citations point to a document the database holds.

Numbers only, no text of any printed compilation. Writes eval/coverage.json and docs/coverage.md.

Usage: python3 eval/coverage.py
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from missing_documents import ALTERNATE  # noqa: E402

DB = ROOT / "data" / "travaux.sqlite3"
MAN = ROOT / "data" / "manifest"
OUT_JSON = ROOT / "eval" / "coverage.json"
OUT_MD = ROOT / "docs" / "coverage.md"
CORPORA = [("udhr", "UDHR: the UN Library's drafting guide"),
           ("udhr_supplement", "UDHR: further documents named in the finding aids"),
           ("covenants", "ICCPR and ICESCR: the meeting series and known documents")]


def is_record(d: dict) -> bool:
    return d.get("doc_type") in ("summary_record", "verbatim_record")


def held_symbols(con: sqlite3.Connection) -> set[str]:
    held = {r[0].upper() for r in con.execute("SELECT symbol FROM documents")}
    # a report the harvest fetched under its Commission symbol (E/2573 is held as E/CN.4/705)
    return held | {a for a, b in ALTERNATE.items() if b.upper() in held}


def manifest_tiers(held: set[str]) -> tuple[list[dict], dict]:
    logs: dict[str, dict] = {}
    for p in glob.glob(str(MAN / "harvest_*.json")):
        for sym, e in json.loads(Path(p).read_text()).items():
            if sym not in logs or e.get("status") == "ok":
                logs[sym] = e
    irrelevant = {s for p in glob.glob(str(MAN / "relevance_covenants_*.json"))
                  for s, v in json.loads(Path(p).read_text()).items() if not v.get("relevant", True)}
    seen: set[str] = set()
    rows = []
    for name, label in CORPORA:
        docs = json.loads((MAN / f"{name}.json").read_text())["documents"]
        if name == "udhr":  # the pilot's and the alternates' extra documents belong with their corpus
            docs += json.loads((MAN / "pilot_udhr_18_19.json").read_text())["documents"]
        if name == "covenants":
            docs += json.loads((MAN / "covenants_alt.json").read_text())["documents"]
        for kind, want in (("records", True), ("documents", False)):
            sel = [d for d in docs if is_record(d) == want and d["symbol"] not in seen]
            seen.update(d["symbol"] for d in sel)
            out_scope = [d for d in sel if d["symbol"] in irrelevant]
            scope = [d for d in sel if d["symbol"] not in irrelevant]
            have = [d for d in scope if d["symbol"].upper() in held]
            gone = Counter("not on the UN's document server (ODS)" if logs.get(d["symbol"], {}).get("status") == "ods_unavailable"
                           else "other" for d in scope if d["symbol"].upper() not in held)
            rows.append({"corpus": label, "kind": kind, "expected": len(scope), "held": len(have),
                         "pct": round(100 * len(have) / len(scope), 1) if scope else None,
                         "missing": dict(gone), "left_out_not_about_the_instruments": len(out_scope)})
    return rows, {"records_left_out": sum(r["left_out_not_about_the_instruments"] for r in rows)}


def family(s: str) -> str:
    for pat, name in ((r"A/C\.3/L\.", "Third Committee drafts and amendments (A/C.3/L.n)"),
                      (r"E/CN\.4/L\.", "Commission drafts and amendments (E/CN.4/L.n)"),
                      (r"(?:E/CN\.4|E/CN\.4/AC\.\d)/SR\.", "Commission meeting records"),
                      (r"A/C\.3/SR\.", "Third Committee meeting records"),
                      (r"E/CN\.4/", "Commission documents (E/CN.4/n)"),
                      (r"A/C\.3/", "Third Committee documents (A/C.3/n)"),
                      (r"E/\d", "Council documents (E/n)"),
                      (r"A/\d", "Assembly documents (A/n)")):
        if re.match(pat, s):
            return name
    return "other bodies' documents"


def cited_tier(con: sqlite3.Connection, held: set[str]) -> dict:
    cited = {s: n for s, n in con.execute("SELECT upper(ref_symbol), COUNT(DISTINCT segment_id) FROM refs GROUP BY 1")}
    fam: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for s, n in cited.items():
        if s.startswith("A/RES/"):
            continue  # adopted texts, not documents to fetch
        f = fam[family(s)]
        f[0] += 1
        f[2] += n
        if s in held:
            f[1] += 1
            f[3] += n
    rows = [{"family": k, "distinct": v[0], "held": v[1], "pct": round(100 * v[1] / v[0]), "citations": v[2],
             "citations_to_held": v[3], "citations_pct": round(100 * v[3] / v[2])} for k, v in fam.items()]
    rows.sort(key=lambda r: -r["distinct"])
    tot = [sum(r[k] for r in rows) for k in ("distinct", "held", "citations", "citations_to_held")]
    return {"families": rows, "distinct": tot[0], "held": tot[1], "pct": round(100 * tot[1] / tot[0]),
            "citations": tot[2], "citations_to_held": tot[3], "citations_pct": round(100 * tot[3] / tot[2])}


def main() -> int:
    con = sqlite3.connect(DB)
    held = held_symbols(con)
    rows, extra = manifest_tiers(held)
    rec = [r for r in rows if r["kind"] == "records"]
    doc = [r for r in rows if r["kind"] == "documents"]
    tot = lambda rs: {"expected": sum(r["expected"] for r in rs), "held": sum(r["held"] for r in rs),  # noqa: E731
                      "pct": round(100 * sum(r["held"] for r in rs) / sum(r["expected"] for r in rs), 1)}
    result = {"generated": dt.date.today().isoformat(), "records": tot(rec), "documents": tot(doc), "tiers": rows,
              "cited": cited_tier(con, held), **extra,
              "held_in_database": con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]}
    OUT_JSON.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    write_md(result)
    print(f"records {result['records']['held']}/{result['records']['expected']} ({result['records']['pct']}%), "
          f"documents {result['documents']['held']}/{result['documents']['expected']} ({result['documents']['pct']}%), "
          f"cited {result['cited']['held']}/{result['cited']['distinct']} ({result['cited']['pct']}%; "
          f"{result['cited']['citations_pct']}% of citations)", file=sys.stderr)
    return 0


def write_md(r: dict) -> None:
    c = r["cited"]
    lines = [f"# Coverage: how much of the drafting record the database holds", "",
             f"Measured {r['generated']} by `eval/coverage.py`, from the UN's own lists. The database holds "
             f"{r['held_in_database']} documents.", "",
             "## 1. Meeting records and 2. other documents that the lists name", "",
             "| Corpus | Kind | Named | Held | Share | Missing |", "|---|---|---|---|---|---|"]
    for t in r["tiers"]:
        miss = ", ".join(f"{v} {k}" for k, v in t["missing"].items()) or "none"
        lines.append(f"| {t['corpus']} | {t['kind']} | {t['expected']} | {t['held']} | {t['pct']}% | {miss} |")
    lines += ["", f"**Meeting records: {r['records']['held']} of {r['records']['expected']} ({r['records']['pct']}%). "
              f"Other documents named: {r['documents']['held']} of {r['documents']['expected']} ({r['documents']['pct']}%).**", "",
              f"Left out of the count: {r['records_left_out']} records of the Covenants' meeting series whose first two pages "
              "show they are not about the Covenants (other items of the Third Committee's agenda). That verdict was read "
              "from the text layer of two pages, so it is a judgment, not a check.", "",
              "## 3. Documents the records cite that no list names", "",
              "| Family | Cited (distinct) | Held | Share | Citations | To a held document |", "|---|---|---|---|---|---|"]
    for f in c["families"]:
        lines.append(f"| {f['family']} | {f['distinct']} | {f['held']} | {f['pct']}% | {f['citations']} | {f['citations_pct']}% |")
    lines += ["", f"**{c['held']} of {c['distinct']} distinct cited documents ({c['pct']}%); "
              f"{c['citations_to_held']} of {c['citations']} citations ({c['citations_pct']}%) point to a held document.**", "",
              "Resolutions (A/RES) are not counted: their texts are adopted texts, not documents to fetch. The cited "
              "symbols include documents outside the drafting record, so this share is a floor for what a reader "
              "following a citation will not find.", "",
              "The gap is the L-series (amendments and draft resolutions), which the lists do not name and the harvest "
              "did not fetch: the speeches cite them, but the text of the amendment itself is not here. Their sponsors "
              "are read from the records (the amendments view), not from the documents.", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
