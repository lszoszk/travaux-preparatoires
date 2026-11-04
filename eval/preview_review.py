#!/usr/bin/env python3
"""Blind review by hand of the preview against the current database (eval/preview_review_build.py): a local page
(eval/preview_review.html) shows the scan and two versions, A and B, of a page's turns or of a speech's speaker; the reviewer
says which is right on the scan. The page never gets eval/preview_review/key.json (which version is the preview); each answer is
appended to eval/preview_review/answers.jsonl at once (the last answer for an item counts). eval/preview_review_score.py scores it.

Local only (127.0.0.1): the records are not to be published before the UN Library's approval.

  python3 eval/preview_review.py [--port 8433]     # then open http://127.0.0.1:8433/
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "eval" / (sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else "preview_review")
ITEMS = DIR / "items.json"
ANSWERS = DIR / "answers.jsonl"
HTML = ROOT / "eval" / "preview_review.html"
OCR = ROOT / "data" / "ocr"
CHOICES = {"A", "B", "both good", "both wrong", "unsure"}


def answers() -> dict:
    out = {}
    if ANSWERS.exists():
        for line in ANSWERS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                a = json.loads(line)
                out[a["id"]] = a
    return out


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
        if path == "/api/items":
            items, done = json.loads(ITEMS.read_text())["items"], answers()
            for it in items:
                it["image"] = f"data/ocr/{it['symbol'].replace('/', '_')}/img/page-{it['page']:03d}.png"
                it["saved"] = done.get(it["id"])
            return self._send(200, json.dumps(items, ensure_ascii=False).encode(), "application/json; charset=utf-8")
        if path.startswith("/img/"):
            img = (ROOT / unquote(path[len("/img/"):])).resolve()
            if OCR.resolve() in img.parents and img.suffix == ".png" and img.exists():
                return self._send(200, img.read_bytes(), "image/png")
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/answer":
            return self._send(404, b"not found", "text/plain")
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        ids = {it["id"] for it in json.loads(ITEMS.read_text())["items"]}
        if body.get("id") not in ids or body.get("choice") not in CHOICES:
            return self._send(400, b"unknown item or choice", "text/plain")
        rec = {"id": body["id"], "choice": body["choice"], "note": (body.get("note") or "").strip(),
               "at": dt.datetime.now().isoformat(timespec="seconds")}
        with ANSWERS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._send(200, json.dumps(rec, ensure_ascii=False).encode(), "application/json; charset=utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8433)
    ap.add_argument("--dir", default="preview_review", help="the round: a folder under eval/")
    args = ap.parse_args()
    print(f"http://127.0.0.1:{args.port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
