#!/usr/bin/env python3
"""Build the UDHR document manifest from the UN Library's drafting-history guide.

Source: https://research.un.org/en/undhr (Dag Hammarskjöld Library research guide).
Each guide page covers one body/session and links documents through undocs.org.
This script caches the pages, pulls every undocs.org link with the text around it,
and writes one manifest entry per UN symbol to data/manifest/udhr.json.

Only the guide pages are fetched here. No UN documents are downloaded.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import canon  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "undhr_guide"
OUT = ROOT / "data" / "manifest" / "udhr.json"
BASE = "https://research.un.org/en/undhr"
UA = "Mozilla/5.0 (research; travaux-db)"

# Guide page slug -> the body and session it documents. Dates are the session dates
# given on the guide pages themselves.
PAGES = {
    "introduction": {"body": None, "session": None},
    "nuclearcommission": {"body": "Nuclear Commission on Human Rights", "session": "1946"},
    "draftingcommittee": {"body": "CHR Drafting Committee", "session": None},
    "draftingcommittee/1": {"body": "CHR Drafting Committee", "session": "1st session (1947)"},
    "draftingcommittee/2": {"body": "CHR Drafting Committee", "session": "2nd session (1948)"},
    "chr/1": {"body": "Commission on Human Rights", "session": "1st session (1947)"},
    "chr/2": {"body": "Commission on Human Rights", "session": "2nd session (1947)"},
    "chr/3": {"body": "Commission on Human Rights", "session": "3rd session (1948)"},
    "ecosoc/2": {"body": "Economic and Social Council", "session": "2nd session (1946)"},
    "ecosoc/4": {"body": "Economic and Social Council", "session": "4th session (1947)"},
    "ecosoc/6": {"body": "Economic and Social Council", "session": "6th session (1948)"},
    "ecosoc/7": {"body": "Economic and Social Council", "session": "7th session (1948)"},
    "ga/thirdcommittee": {"body": "General Assembly Third Committee", "session": "3rd session (1948)"},
    "ga/plenary": {"body": "General Assembly plenary", "session": "3rd session (1948)"},
}


def fetch(slug: str) -> str:
    path = CACHE / (slug.replace("/", "_") + ".html")
    if path.exists() and path.stat().st_size > 0:
        return path.read_text(encoding="utf-8")
    CACHE.mkdir(parents=True, exist_ok=True)
    url = BASE if not slug else f"{BASE}/{slug}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        html = resp.read().decode("utf-8")
    path.write_text(html, encoding="utf-8")
    time.sleep(3)
    return html


SYMBOL_RE = re.compile(r"^(A|E|PC|ST)/[A-Z0-9.()/-]+$", re.I)


def symbol_from_href(href: str) -> tuple[str, str] | None:
    """Return (symbol, language) for an undocs.org link, else None."""
    parsed = urllib.parse.urlparse(href.strip())
    if not parsed.netloc.endswith("undocs.org"):
        return None
    path = urllib.parse.unquote(parsed.path).strip("/")
    lang = "en"
    m = re.match(r"^(en|fr|es|ru|zh|ar)/(.+)$", path)
    if m:
        lang, path = m.group(1), m.group(2)
    symbol = re.sub(r"\s+", "", path)
    return (symbol, lang) if symbol else None


def doc_type(symbol: str) -> str:
    s = symbol.upper()
    if re.search(r"/SR\.\d", s):
        return "summary_record"
    if re.search(r"/PV\.\d", s):
        return "verbatim_record"
    if "/RES/" in s or s.startswith("A/RES") or s.startswith("E/RES"):
        return "resolution"
    if re.search(r"/L\.\d", s):
        return "limited_proposal"
    if re.search(r"/W\.\d", s):
        return "working_paper"
    return "document"


def meeting_no(symbol: str) -> int | None:
    m = re.search(r"/(?:SR|PV)\.(\d+)", symbol, re.I)
    return int(m.group(1)) if m else None


def series(symbol: str) -> str:
    """Symbol prefix up to the document number, e.g. E/CN.4/AC.1/SR.12 -> E/CN.4/AC.1/SR."""
    m = re.match(r"^(.*?/)(?:(SR|PV|L|W)\.)?\d", symbol)
    if not m:
        return symbol
    return m.group(1) + (m.group(2) + "." if m.group(2) else "")


MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
# The guide writes meeting dates several ways: "Held on Friday 4 June 1948",
# "1st Meeting, Monday, 9 June 1947 :10/06/1947", "5 NovemBER 1948". The date after
# the colon is the issue date, so only the first written-out date counts.
DATE_RE = re.compile(rf"(\d{{1,2}})\s+({MONTHS})\s+(\d{{4}})", re.I)


def meeting_date(contexts: list[str]) -> str | None:
    """Meeting date as the guide states it, ISO format."""
    for c in contexts:
        m = DATE_RE.search(c.split(":")[0]) or DATE_RE.search(c)
        if m:
            day, month, year = m.group(1), m.group(2).title(), m.group(3)
            return time.strftime("%Y-%m-%d", time.strptime(f"{day} {month} {year}", "%d %B %Y"))
    return None


def series_gaps(docs: list[dict], min_linked: int = 10) -> dict[str, list[int]]:
    """Meeting numbers missing inside each meeting-record run the guide links densely.

    Series with fewer than `min_linked` records (ECOSOC plenary, GA plenary) are
    skipped: the guide links only the handful of meetings on the Declaration, so
    everything in between would show up as a false gap.
    """
    runs: dict[str, set[int]] = {}
    for d in docs:
        if d["meeting_no"] is not None and d["doc_type"] in ("summary_record", "verbatim_record"):
            runs.setdefault(d["series"], set()).add(d["meeting_no"])
    return {s: [n for n in range(min(ns), max(ns) + 1) if n not in ns]
            for s, ns in sorted(runs.items()) if len(ns) >= min_linked}


def box_title(tag) -> str | None:
    box = tag.find_parent(class_="s-lib-box")
    if not box:
        return None
    h2 = box.find(class_="s-lib-box-title")
    return " ".join(h2.get_text(" ", strip=True).split()) if h2 else None


def context_text(a) -> str:
    """The list item or paragraph the link sits in, whitespace-normalised."""
    holder = a.find_parent(["li", "p", "td"]) or a.parent
    return " ".join(holder.get_text(" ", strip=True).split())[:600]


def parse_page(slug: str, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find(id="s-lg-guide-main") or soup
    rows = []
    for a in main.find_all("a", href=True):
        hit = symbol_from_href(a["href"])
        if not hit:
            continue
        symbol, lang = hit
        anchor = " ".join(a.get_text(" ", strip=True).split())
        # A few guide links point at non-document paths (e.g. undocs.org/Home/Mobile)
        # while the visible text is the symbol. Trust the text in that case.
        if not SYMBOL_RE.match(symbol) and SYMBOL_RE.match(anchor.replace(" ", "")):
            symbol = anchor
        rows.append({
            "symbol": canon(symbol),
            "lang": lang,
            "anchor": anchor,
            "page": slug,
            "box": box_title(a),
            "context": context_text(a),
        })
    return rows


def main() -> int:
    mentions: list[dict] = []
    for slug in PAGES:
        html = fetch(slug)
        rows = parse_page(slug, html)
        print(f"{slug:22} {len(rows):4} links", file=sys.stderr)
        mentions.extend(rows)

    docs: dict[str, dict] = {}
    for m in mentions:
        d = docs.setdefault(m["symbol"], {
            "symbol": m["symbol"],
            "doc_type": doc_type(m["symbol"]),
            "series": series(m["symbol"]),
            "meeting_no": meeting_no(m["symbol"]),
            "guide_langs": [],
            "mentions": [],
        })
        if m["lang"] not in d["guide_langs"]:
            d["guide_langs"].append(m["lang"])
        info = PAGES[m["page"]]
        mention = {
            "page": m["page"],
            "body": info["body"],
            "session": info["session"],
            "box": m["box"],
            "anchor": m["anchor"],
            "context": m["context"],
        }
        if mention not in d["mentions"]:
            d["mentions"].append(mention)

    # Anchor text that disagrees with the link target is worth a human look:
    # either the guide has a typo in the URL or in the visible symbol.
    for d in docs.values():
        anchors = {canon(mm["anchor"]) for mm in d["mentions"]}
        d["anchor_mismatch"] = sorted(a for a in anchors if SYMBOL_RE.match(a)
                                      and a != d["symbol"])

        # Only meeting records have a date the guide states reliably; for other documents
        # the nearest date in the text is often an unrelated one.
        d["meeting_date"] = (meeting_date([mm["context"] for mm in d["mentions"]])
                             if d["meeting_no"] is not None else None)

    ordered = sorted(docs.values(), key=lambda d: (d["series"], d["meeting_no"] or 0, d["symbol"]))
    gaps = series_gaps(ordered)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": BASE,
        "description": "UDHR drafting documents linked from the UN Dag Hammarskjöld Library research guide",
        "count": len(ordered),
        "series_gaps": gaps,
        "documents": ordered,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    types = Counter(d["doc_type"] for d in ordered)
    ser = Counter(d["series"] for d in ordered)
    print(f"\n{len(ordered)} unique symbols from {len(mentions)} links -> {OUT.relative_to(ROOT)}", file=sys.stderr)
    print("by type:", dict(types.most_common()), file=sys.stderr)
    print("top series:", ser.most_common(12), file=sys.stderr)
    mism = [d for d in ordered if d["anchor_mismatch"]]
    print(f"anchor/link mismatches: {len(mism)}", file=sys.stderr)
    for d in mism[:15]:
        print(f"  {d['symbol']!r} anchor {d['anchor_mismatch']}", file=sys.stderr)
    records = [d for d in ordered if d["meeting_no"] is not None]
    dated = sum(1 for d in records if d["meeting_date"])
    print(f"meeting records with a date from the guide: {dated}/{len(records)}", file=sys.stderr)
    for s, missing in gaps.items():
        if missing:
            print(f"gaps in {s}: {missing}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
