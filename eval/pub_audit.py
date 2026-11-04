#!/usr/bin/env python3
"""The panel of the publication audit: each speech of the sample (eval/pub_audit_sample.py) beside its scan, judged in every
field at once (the guide: docs/audit_guide_pl.md). Each annotator answers under their own name, in a file of their own, and
does not see the others' answers.

  python3 eval/pub_audit.py --dir eval/pub_audit/<name> [--port 8438]     # then http://127.0.0.1:8438/?judge=<name>

On a server (deploy/docker-compose.yml, service travaux-audit, behind api/server.py's /audit/): HOST=0.0.0.0, the scans in
AUDIT_OCR, and AUDIT_PASSWORD, which a form asks for once and a cookie then carries (the password is never stored in the repository).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from common import safe_name  # noqa: E402

HTML = ROOT / "eval" / "pub_audit.html"
OCR = Path(os.environ.get("AUDIT_OCR") or ROOT / "data" / "ocr")
PASSWORD = os.environ.get("AUDIT_PASSWORD", "")
TOKEN = hmac.new(PASSWORD.encode(), b"travaux-audit", hashlib.sha256).hexdigest() if PASSWORD else ""
LOGIN = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Audyt publikacyjny</title>
<body style="font-family:Georgia,serif;max-width:28em;margin:4em auto;padding:0 1em"><h1>Audyt publikacyjny</h1>
<form method="post" action="login"><p><label>Hasło <input type="password" name="password" autofocus></label> <button>Wejdź</button></p></form>%s"""
DIR: Path = ROOT / "eval" / "pub_audit" / "dev"
# every answer has these fields, with these values (the guide explains each)
FIELDS = {
    "boundaries": {"ok", "starts_wrong", "ends_wrong", "both_wrong", "not_a_speech", "unsure"},
    "speaker": {"ok", "wrong", "missing", "unsure"},
    "delegation": {"ok", "wrong", "unsure"},
    "page": {"ok", "wrong"},
    "article": {"ok", "wrong", "one_article", "not_one", "unsure"},
    "topic": {"ok", "wrong", "missing", "na", "unsure"},
}
JUDGE_RE = re.compile(r"^[a-z][a-z0-9_-]{1,20}$")


def answers(judge: str) -> dict:
    path = DIR / f"answers_{judge}.jsonl"
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
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

    def allowed(self) -> bool:
        if not PASSWORD:
            return True
        cookie = self.headers.get("Cookie") or ""
        return any(hmac.compare_digest(c.strip(), f"audit={TOKEN}") for c in cookie.split(";"))

    def do_GET(self) -> None:
        u = urlparse(self.path)
        if not self.allowed():
            return self._send(200 if u.path in ("/", "/index.html") else 401, (LOGIN % "").encode(), "text/html; charset=utf-8")
        if u.path in ("/", "/index.html"):
            return self._send(200, HTML.read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/items":
            judge = (parse_qs(u.query).get("judge") or [""])[0]
            if not JUDGE_RE.match(judge):
                return self._send(400, b"give ?judge=<name> (small letters)", "text/plain")
            items, done = json.loads((DIR / "items.json").read_text())["items"], answers(judge)
            for it in items:
                it["images"] = [f"{safe_name(it['symbol'])}/img/page-{p:03d}.png"
                                for p in range(max(1, it["page_start"] - 1), it["page_end"] + 2)
                                if (OCR / safe_name(it["symbol"]) / "img" / f"page-{p:03d}.png").exists()]
                it["saved"] = done.get(it["id"])
            return self._send(200, json.dumps(items, ensure_ascii=False).encode(), "application/json; charset=utf-8")
        if u.path.startswith("/img/"):
            img = (OCR / unquote(u.path[len("/img/"):])).resolve()
            if OCR.resolve() in img.parents and img.suffix == ".png" and img.exists():
                return self._send(200, img.read_bytes(), "image/png")
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if urlparse(self.path).path == "/login":
            given = parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode())
            if PASSWORD and hmac.compare_digest((given.get("password") or [""])[0], PASSWORD):
                self.send_response(303)
                self.send_header("Set-Cookie", f"audit={TOKEN}; Path=/; Max-Age=2592000; HttpOnly; Secure; SameSite=Strict")
                self.send_header("Location", "./")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            return self._send(401, (LOGIN % "<p>Złe hasło.</p>").encode(), "text/html; charset=utf-8")
        if not self.allowed():
            return self._send(401, b"log in first", "text/plain")
        if urlparse(self.path).path != "/api/answer":
            return self._send(404, b"not found", "text/plain")
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        ids = {it["id"] for it in json.loads((DIR / "items.json").read_text())["items"]}
        judge = body.get("judge") or ""
        if not JUDGE_RE.match(judge) or body.get("id") not in ids:
            return self._send(400, b"unknown judge or item", "text/plain")
        bad = [k for k, ok in FIELDS.items() if body.get(k) not in ok]
        words = body.get("words_wrong")
        if bad or not (isinstance(words, int) and 0 <= words <= 100):
            return self._send(400, ("missing or unknown: " + ", ".join(bad + ([] if isinstance(words, int) else ["words_wrong"]))).encode(),
                              "text/plain; charset=utf-8")
        rec = {"id": body["id"], "judge": judge, **{k: body[k] for k in FIELDS}, "words_wrong": words,
               "speaker_should": (body.get("speaker_should") or "").strip()[:80],
               "article_should": (body.get("article_should") or "").strip()[:40],
               "note": (body.get("note") or "").strip()[:1000], "at": dt.datetime.now().isoformat(timespec="seconds")}
        with (DIR / f"answers_{judge}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._send(200, json.dumps(rec, ensure_ascii=False).encode(), "application/json; charset=utf-8")


def main() -> int:
    global DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--port", type=int, default=8438)
    args = ap.parse_args()
    DIR = args.dir if args.dir.is_absolute() else ROOT / args.dir
    host = os.environ.get("HOST", "127.0.0.1")
    if host not in ("127.0.0.1", "localhost") and not PASSWORD:
        raise SystemExit("serving beyond this machine needs AUDIT_PASSWORD")
    print(f"http://{host}:{args.port}/?judge=<name>", flush=True)
    ThreadingHTTPServer((host, args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
