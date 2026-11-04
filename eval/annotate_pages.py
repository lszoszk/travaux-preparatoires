#!/usr/bin/env python3
"""Hand annotation of the pages in eval/gold_pages/pages.json: a local page (eval/annotate_pages.html) shows the scan next to the
OCR lines, with the database's turns marked; the annotator corrects where each turn starts, its kind and speaker, and marks
lines that are not the record's text. Each change is saved to data/gold/segment_pages.json at once.

Local only (127.0.0.1): the records are not to be published before the UN Library's approval.

  python3 eval/annotate_pages.py [--port 8431]     # then open http://127.0.0.1:8431/
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "eval" / "gold_pages" / "pages.json"
HTML = ROOT / "eval" / "annotate_pages.html"
GOLD = ROOT / "data" / "gold" / "segment_pages.json"
OCR = ROOT / "data" / "ocr"


def load_gold() -> dict:
    return json.loads(GOLD.read_text()) if GOLD.exists() else {}


def save_gold(gold: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=GOLD.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(gold, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, GOLD)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # (quiet)
        pass

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, HTML.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/pages":
            pages, gold = json.loads(PAGES.read_text()), load_gold()
            for p in pages:
                p["saved"] = gold.get(p["id"])
            return self._send(200, json.dumps(pages, ensure_ascii=False).encode(), "application/json; charset=utf-8")
        if path.startswith("/img/"):
            img = (ROOT / unquote(path[len("/img/"):])).resolve()
            if OCR.resolve() in img.parents and img.suffix == ".png" and img.exists():
                return self._send(200, img.read_bytes(), "image/png")
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/save":
            return self._send(404, b"not found", "text/plain")
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        pages = {p["id"]: p for p in json.loads(PAGES.read_text())}
        page = pages.get(body.get("id"))
        if not page:
            return self._send(400, b"unknown page", "text/plain")
        gold = load_gold()
        gold[page["id"]] = {
            "symbol": page["symbol"], "page": page["page"], "stratum": page["stratum"],
            "status": "done" if body.get("status") == "done" else "draft",
            "starts": sorted(body.get("starts") or [], key=lambda s: (s["line"], s.get("offset", 0))),
            "junk_lines": sorted(set(body.get("junk_lines") or [])),
            "note": body.get("note") or "",
            "lines": len(page["lines"]),
            "db_starts": page["starts"],  # (what the database had when the page was drawn)
            "saved": dt.datetime.now().isoformat(timespec="seconds"),
        }
        save_gold(gold)
        done = sum(g["status"] == "done" for g in gold.values())
        self._send(200, json.dumps({"ok": True, "done": done}).encode(), "application/json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8431)
    args = ap.parse_args()
    print(f"http://127.0.0.1:{args.port}/  ({PAGES.relative_to(ROOT)} -> {GOLD.relative_to(ROOT)})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
