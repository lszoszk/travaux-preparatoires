#!/usr/bin/env python3
"""The UVA Law Library's travaux database (hr-travaux.law.virginia.edu): its item lists for the ICCPR and the ICESCR.

Reads the public taxonomy listing pages (allowed by the site's robots.txt), one request every 6 seconds, and keeps
title, page count, document type and node link of each item in data/private/uva/items.json (a third party's index:
kept out of the repository). eval/compare_uva.py matches the items to the database.

Usage: python3 eval/uva_list.py
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "private" / "uva" / "items.json"
BASE = "http://hr-travaux.law.virginia.edu"
TERMS = {"ICCPR": 10, "ICESCR": 848}
UA = "travaux-research/0.1 (academic; contact via the UVA Law Library)"


def fetch(url: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def items(page: str) -> list[dict]:
    out = []
    for block in page.split('class="gva-grid-item"')[1:]:
        m = re.search(r'<a href="(/node/\d+)"[^>]*>(.*?)</a>', block, re.S)
        if not m:
            continue
        text = re.sub(r"<!--.*?-->|<[^>]+>", " ", block, flags=re.S)
        text = " ".join(html.unescape(text).split())
        pc = re.search(r"Page Count:\s*(\d+)\s*p", text)
        dt = re.search(r"Document Type:\s*(.+?)(?:$| Page Count)", text)
        out.append({"node": m.group(1), "title": " ".join(html.unescape(re.sub("<[^>]+>", "", m.group(2))).split()),
                    "pages": int(pc.group(1)) if pc else None, "type": dt.group(1).strip() if dt else None})
    return out


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    got = json.loads(OUT.read_text()) if OUT.exists() else {}
    for inst, term in TERMS.items():
        first = fetch(f"{BASE}/taxonomy/term/{term}")
        last = max([int(x) for x in re.findall(r"\?page=(\d+)", first)] or [0])
        pages = {0: first}
        for p in range(1, last + 1):
            if f"{inst}:{p}" in got.get("_done", []):
                continue
            time.sleep(6)
            pages[p] = fetch(f"{BASE}/taxonomy/term/{term}?page={p}")
            print(f"  {inst} page {p}/{last}", file=sys.stderr)
        for p, page in pages.items():
            for it in items(page):
                rec = got.setdefault(it["node"], {**it, "instruments": []})
                if inst not in rec["instruments"]:
                    rec["instruments"].append(inst)
            got.setdefault("_done", []).append(f"{inst}:{p}")
        OUT.write_text(json.dumps(got, indent=1, ensure_ascii=False))
        time.sleep(6)
    n = sum(1 for k in got if k != "_done")
    print(f"{n} items -> {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
