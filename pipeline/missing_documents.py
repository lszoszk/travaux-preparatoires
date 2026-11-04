#!/usr/bin/env python3
"""The documents the harvest could not fetch, as a list to download by hand, and a way back in.

documents.un.org (ODS) answers some symbols with a web page instead of a PDF, mostly
corrigenda, some 1946-47 records and reports filed under another symbol. Their only other
source is the UN Digital Library, which sits behind a bot check: they have to be fetched by
hand in a browser.

  python3 pipeline/missing_documents.py          write docs/missing_documents.md and .csv
  python3 pipeline/missing_documents.py --add    take in the PDFs saved by hand in data/raw/
                                                 (named <symbol with / as _>-EN.pdf, e.g.
                                                 E_CN.4_SR.52-EN.pdf): checked, logged as
                                                 "added_by_hand", ready for pipeline/ocr_all.py
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
import urllib.parse
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import safe_name  # noqa: E402
from sessions import body_from_symbol  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "data" / "manifest"
RAW = ROOT / "data" / "raw"
OUT_MD = ROOT / "docs" / "missing_documents.md"
OUT_CSV = ROOT / "docs" / "missing_documents.csv"
# queued under their Commission symbols (pipeline/build_covenant_manifest.py ALTERNATES)
ALTERNATE = {"E/1371": "E/CN.4/350", "E/1681": "E/CN.4/507", "E/2256": "E/CN.4/669", "E/2447": "E/CN.4/689",
             "E/2573": "E/CN.4/705"}
# only a French copy exists in the Digital Library (the corrigenda "FRENCH ONLY" and some Rev.); kept in data/raw/ as <symbol>-FR.pdf and machine-translated (pipeline/translations.py),
# the translation enters the database flagged as such
FRENCH_ONLY = {"E/CN.4/SR.25/Corr.1", "A/C.3/251/Corr.1", "A/C.3/278/Corr.1", "A/C.3/308/Corr.1", "A/C.3/309/Rev.1",
               "A/C.3/319/Rev.1", "E/CN.4/1/Rev.1/Corr.1", "E/CN.4/122/Rev.1", "E/CN.4/53/Corr.1", "E/CN.4/97/Corr.1"}


# record pages found in the Digital Library (English PDF listed there), opened and read on 2026-09-29; the Digital
# Library writes these symbols with a slash before the number ("E/CN.4/Sub.2/SR/1"), so its symbol search finds nothing
KNOWN_RECORDS = {"E/CN.4/SUB.2/SR.1": "https://digitallibrary.un.org/record/722160",
                 "E/CONF.6/SR.10": "https://digitallibrary.un.org/record/3937221"}


def harvest_logs() -> dict[str, dict]:
    """Every harvest log, by name."""
    return {p.stem.replace("harvest_", ""): json.loads(p.read_text()) for p in sorted(MAN.glob("harvest_*.json"))}


def describe() -> dict[str, dict]:
    """What each symbol is, from the manifests."""
    out: dict[str, dict] = {}
    guide = json.loads((MAN / "udhr.json").read_text())["documents"]
    for d in guide:
        m = (d.get("mentions") or [{}])[0]
        out[d["symbol"]] = {"corpus": "UDHR (UN Library guide)", "body": m.get("body"), "session": m.get("session"),
                            "date": d.get("meeting_date"), "what": d.get("doc_type")}
    for name, corpus in (("udhr_supplement.json", "UDHR (cited by Schabas)"), ("covenants.json", "Covenants")):
        path = MAN / name
        if path.exists():
            for d in json.loads(path.read_text())["documents"]:
                out.setdefault(d["symbol"], {"corpus": corpus, "body": d.get("body"), "session": d.get("session"),
                                             "date": None, "what": d.get("note") or d.get("doc_type")})
    return out


def missing() -> list[dict]:
    logs = harvest_logs()
    ok = {sym for log in logs.values() for sym, e in log.items() if e.get("status") == "ok"}
    comp = ROOT / "eval" / "completeness_udhr.json"
    in_book = {r["symbol"] for r in json.loads(comp.read_text())} if comp.exists() else set()
    info = describe()
    rows = {}
    for name, log in logs.items():
        for sym, e in log.items():
            if e.get("status") == "ok" or sym in ok or sym in rows or sym in FRENCH_ONLY:
                continue
            d = info.get(sym, {})
            rows[sym] = {"symbol": sym, "corpus": d.get("corpus", name), "body": d.get("body") or body_from_symbol(sym) or "",
                         "session": d.get("session") or "", "date": d.get("date") or "", "what": d.get("what") or "",
                         "reproduced_by_schabas": sym in in_book, "problem": e.get("status"),
                         "alternate_symbol": ALTERNATE.get(sym, ""),
                         "save_as": f"data/raw/{safe_name(sym)}-EN.pdf",
                         "digital_library": KNOWN_RECORDS.get(sym) or "https://digitallibrary.un.org/search?" + urllib.parse.urlencode({"p": sym, "ln": "en"})}
    # records first, then what the book reproduces, then the rest
    return sorted(rows.values(), key=lambda r: ("/SR." not in r["symbol"] and "/PV." not in r["symbol"],
                                                not r["reproduced_by_schabas"], r["corpus"], r["symbol"]))


def write_list() -> None:
    rows = missing()
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["symbol"])
        w.writeheader()
        w.writerows(rows)
    n_records = sum(1 for r in rows if "/SR." in r["symbol"] or "/PV." in r["symbol"])
    lines = [
        "# Documents to fetch by hand", "",
        f"Generated {dt.date.today().isoformat()} by `pipeline/missing_documents.py`. "
        f"**{len(rows)} documents** that documents.un.org does not serve as a PDF ({n_records} meeting records). "
        "The same list is in `missing_documents.csv`.", "",
        "## How", "",
        "1. Open the Digital Library link, open the record and download the **English** PDF.",
        "2. Save it under the name in the *Save as* column (the symbol with `/` replaced by `_`, then `-EN.pdf`).",
        "3. When you have a batch, run `python3 pipeline/missing_documents.py --add`, then "
        "`python3 pipeline/ocr_all.py data/manifest/harvest_<corpus>.json` and `python3 pipeline/build_all.py data/manifest/harvest_*.json`.",
        "", "The harvest will not fetch these itself: the Digital Library sits behind a bot check, which it does not get round.",
        "Documents marked *alternate queued* are being fetched under their Commission symbol instead; skip them unless that fails.",
        "", f"{len(FRENCH_ONLY)} more exist only in French and are left out (`data/raw/*-FR.pdf`, machine-translated, see pipeline/translations.py): " + ", ".join(sorted(FRENCH_ONLY)) + ".",
        "", "| Symbol | What | Body / session | In Schabas | Save as | Link |", "|---|---|---|---|---|---|"]
    for r in rows:
        what = r["what"] + (f" (alternate queued: {r['alternate_symbol']})" if r["alternate_symbol"] else "")
        where = " / ".join(x for x in (r["body"], r["session"], r["date"]) if x)
        lines.append(f"| {r['symbol']} | {what} | {where} | {'yes' if r['reproduced_by_schabas'] else ''} | "
                     f"`{Path(r['save_as']).name}` | [{'record' if r['symbol'] in KNOWN_RECORDS else 'search'}]({r['digital_library']}) |")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(rows)} missing documents -> {OUT_MD.relative_to(ROOT)}, {OUT_CSV.relative_to(ROOT)}", file=sys.stderr)


def add_by_hand() -> None:
    """Log the PDFs saved by hand as fetched, in the harvest log that listed them."""
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    added = 0
    for path in sorted(MAN.glob("harvest_*.json")):
        run_log = ROOT / "data" / "logs" / f"{path.stem}.log"
        if run_log.exists() and "HARVEST EXIT" not in run_log.read_text():
            print(f"  {path.name}: its harvest is still running; try again when it has finished", file=sys.stderr)
            continue
        log = json.loads(path.read_text())
        changed = False
        for sym, e in log.items():
            if e.get("status") == "ok":
                continue
            pdf = RAW / f"{safe_name(sym)}-EN.pdf"
            if not pdf.exists():
                continue
            data = pdf.read_bytes()
            if data[:4] != b"%PDF":
                print(f"  !! {pdf.name}: not a PDF, skipped", file=sys.stderr)
                continue
            with fitz.open(pdf) as doc:
                pages = doc.page_count
                chars = sum(len(p.get_text()) for p in doc)
            log[sym] = {"status": "ok", "via": "added_by_hand", "file": str(pdf.relative_to(ROOT)), "pages": pages,
                        "text_chars": chars, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                        "fetched_at": now, "earlier_problem": e.get("status")}
            changed = True
            added += 1
            print(f"  ok  {sym}: {pages}pp (by hand)", file=sys.stderr)
        if changed:
            path.write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{added} documents added by hand", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", action="store_true", help="take in PDFs saved by hand in data/raw/")
    args = ap.parse_args()
    if args.add:
        add_by_hand()
    write_list()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
