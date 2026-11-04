#!/usr/bin/env python3
"""Render the title and end cards (media/teaser/cards.html, in the app's fonts) to PNG, with the corpus figures read from
the running API (/api/quality, /api/facets).

  python3 media/teaser/cards.py [--base http://localhost:8430] [--who "Łukasz Szoszkiewicz"]
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dist" / "teaser"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8430")
    ap.add_argument("--who", default="Łukasz Szoszkiewicz")
    args = ap.parse_args()
    q = json.loads(urllib.request.urlopen(args.base + "/api/quality").read())
    facets = json.loads(urllib.request.urlopen(args.base + "/api/facets").read())
    figs = {"records": sum(c["documents"] for c in q["counts"]), "speeches": sum(c["speeches"] for c in q["counts"]),
            "votes": next((t["n"] for t in facets["totals"] if t["v"] == "vote"), 0)}
    page_url = (ROOT / "media" / "teaser" / "cards.html").as_uri()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for card in ("title", "end"):
            params = urllib.parse.urlencode({"card": card, "figs": json.dumps(figs), "who": args.who})
            pg.goto(f"{page_url}?{params}")
            pg.wait_for_timeout(800)
            pg.screenshot(path=str(OUT / f"card_{card}.png"))
        b.close()
    print(figs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
