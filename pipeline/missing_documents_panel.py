#!/usr/bin/env python3
"""A local page for downloading by hand, in a browser, the documents documents.un.org (ODS) does not serve
(docs/un_library_attachment_missing.csv, in order of priority). The Digital Library may not be downloaded from by a
script without the Library's approval (its terms of use) and sits behind a bot check: a person opens each record, saves
the PDF, and this page keeps the list, the name to save under, and what is done.

- each row links to the Digital Library's search for the symbol and gives the file name to save as
  (<symbol with / as _>-EN.pdf, the name pipeline/missing_documents.py --add expects);
- "Zbierz z Pobranych" moves the PDFs saved in ~/Downloads under such a name (or the Digital Library's own name for the
  same symbol) into data/raw/; then `python3 pipeline/missing_documents.py --add` takes them in;
- a row can be marked "nie ma w DL", "tylko po francusku" or "pomiń", with a note; marks are kept in
  data/logs/missing_documents_panel.json.

Local only (127.0.0.1).

  python3 pipeline/missing_documents_panel.py [--port 8437]     # then open http://127.0.0.1:8437/
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import shutil
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
LIST = ROOT / "docs" / "un_library_attachment_missing.csv"
HTML = ROOT / "pipeline" / "missing_documents_panel.html"
RAW = ROOT / "data" / "raw"
MARKS = ROOT / "data" / "logs" / "missing_documents_panel.json"
DOWNLOADS = Path.home() / "Downloads"
MARK_KINDS = {"not in DL", "French only", "skip", ""}


def safe_name(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", symbol).strip("_")


def load_marks() -> dict:
    return json.loads(MARKS.read_text()) if MARKS.exists() else {}


def save_marks(marks: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=MARKS.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(marks, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, MARKS)


def downloads() -> dict[str, Path]:
    """The PDFs in ~/Downloads by the name they could be saved under for a symbol, lower case: the name to save as, or the
    Digital Library's own name for the English file (A_C.3_L.88-EN.pdf); a browser's " (1)" copy is accepted too."""
    out = {}
    for p in DOWNLOADS.glob("*.pdf"):
        stem = re.sub(r"\s*\(\d+\)$", "", p.stem).lower()
        for suffix in ("-en", "_en", "-e"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        out.setdefault(stem, p)
    return out


def downloaded(safe: str, found: dict[str, Path]) -> Path | None:
    return found.get(safe.lower())


def rows() -> list[dict]:
    marks, found = load_marks(), downloads()
    out = []
    for r in csv.DictReader(LIST.open(encoding="utf-8")):
        safe = safe_name(r["symbol"])
        status = "saved" if (RAW / f"{safe}-EN.pdf").exists() else "in Downloads" if downloaded(safe, found) else ""
        out.append({**r, "save_as": f"{safe}-EN.pdf", "status": status, "mark": marks.get(r["symbol"], {})})
    return out


def collect() -> list[str]:
    moved, found = [], downloads()
    for r in csv.DictReader(LIST.open(encoding="utf-8")):
        safe = safe_name(r["symbol"])
        target = RAW / f"{safe}-EN.pdf"
        src = downloaded(safe, found)
        if target.exists() or src is None or src.read_bytes()[:4] != b"%PDF":
            continue
        shutil.move(str(src), target)
        moved.append(r["symbol"])
    return moved


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj) -> None:
        self._send(200, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def log_message(self, *args) -> None:  # (quiet)
        pass

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, HTML.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/list":
            return self._json(rows())
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if path == "/api/collect":
            return self._json({"moved": collect()})
        if path == "/api/mark":
            if body.get("mark", "") not in MARK_KINDS:
                return self._send(400, b"unknown mark", "text/plain")
            marks = load_marks()
            if body.get("mark") or body.get("note"):
                marks[body["symbol"]] = {"mark": body.get("mark", ""), "note": (body.get("note") or "").strip(),
                                         "at": dt.datetime.now().isoformat(timespec="seconds")}
            else:
                marks.pop(body["symbol"], None)
            save_marks(marks)
            return self._json(marks.get(body["symbol"], {}))
        self._send(404, b"not found", "text/plain")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8437)
    args = ap.parse_args()
    print(f"http://127.0.0.1:{args.port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
