#!/usr/bin/env python3
"""Fetch the English PDF of every document in a manifest, politely.

Source: the UN Official Document System resolver
(documents.un.org/api/symbol/access?s=SYMBOL&l=en&t=pdf), the same scans the UN
Digital Library serves. Adapted from GC_TRAVAUX_DASHBOARD/scripts/collect_human_rights_committee.py.

Pilot-scale only until the UN Library approves bulk retrieval (see
docs/un_library_permission_request.md): one request every --delay seconds (default 6),
each file fetched once, local copies reused first.

Writes PDFs to data/raw/ (gitignored) and a provenance log to data/manifest/harvest_<name>.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import safe_name  # noqa: E402

try:  # python.org builds don't use the macOS keychain; certifi supplies the CA bundle
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UA = "travaux-db research harvester (pilot; throttled)"

# PDFs already on disk from earlier hand-verified work; reused instead of re-fetched.
LOCAL_COPIES = {
    "E/CN.4/AC.1/SR.31": "/Users/lszoszk/Desktop/The Book/00_PROJECT/wiki/inbox/article-18-udhr-iccpr-travaux/E_CN.4_AC.1_SR.31-EN.pdf",
    "E/CN.4/SR.60": "/Users/lszoszk/Desktop/The Book/00_PROJECT/wiki/inbox/article-18-udhr-iccpr-travaux/E_CN.4_SR.60-EN.pdf",
    "E/CN.4/SR.164": "/Users/lszoszk/Desktop/The Book/00_PROJECT/wiki/inbox/article-18-udhr-iccpr-travaux/E_CN.4_SR.164-EN.pdf",
}


def symbol_url(symbol: str, lang: str = "en") -> str:
    query = urllib.parse.urlencode({"s": symbol, "l": lang, "t": "pdf"})
    return f"https://documents.un.org/api/symbol/access?{query}"


def download(url: str, retries: int = 3) -> tuple[bytes, str]:
    """Return (pdf bytes, final URL). Raises ValueError when the resolver answers with HTML."""
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=90, context=SSL_CTX) as response:
                data = response.read()
                final_url = response.geturl()
            if not data.startswith(b"%PDF"):
                # Not retryable: older records often have no ODS copy at all.
                raise ValueError(f"not a PDF ({data[:40]!r})")
            return data, final_url
        except ValueError:
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def pdf_facts(path: Path) -> dict:
    """Page count, text-layer size and the software that produced the text layer."""
    with fitz.open(path) as doc:
        chars = sum(len(p.get_text()) for p in doc)
        meta = doc.metadata or {}
        return {
            "pages": doc.page_count,
            "text_chars": chars,
            "producer": meta.get("producer") or None,
            "creator": meta.get("creator") or None,
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--delay", type=float, default=6.0, help="seconds between network requests")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    if args.delay < 5:
        ap.error("--delay below 5 s is not allowed before the UN Library approves bulk retrieval")

    manifest = json.loads(args.manifest.read_text())
    name = args.manifest.stem
    log_path = ROOT / "data" / "manifest" / f"harvest_{name}.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}
    RAW.mkdir(parents=True, exist_ok=True)

    todo = [d["symbol"] for d in manifest["documents"]]
    if args.limit:
        todo = todo[: args.limit]
    fetched = 0
    for symbol in todo:
        path = RAW / f"{safe_name(symbol)}-EN.pdf"
        entry = log.get(symbol, {})
        if path.exists() and entry.get("status") == "ok":
            continue
        url = symbol_url(symbol)
        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        if path.exists() and path.read_bytes()[:4] == b"%PDF":
            # fetched by an earlier harvest (e.g. the pilot): no new request
            entry = {"status": "ok", "via": "existing_file", "official_url": url, "fetched_at": now}
        elif symbol in LOCAL_COPIES and Path(LOCAL_COPIES[symbol]).exists():
            shutil.copyfile(LOCAL_COPIES[symbol], path)
            entry = {"status": "ok", "via": "local_copy", "local_source": LOCAL_COPIES[symbol],
                     "official_url": url, "fetched_at": now}
        else:
            if fetched:
                time.sleep(args.delay)
            fetched += 1
            try:
                data, final_url = download(url)
            except ValueError as exc:
                entry = {"status": "ods_unavailable", "official_url": url, "error": str(exc)[:120],
                         "fetched_at": now}
                log[symbol] = entry
                print(f"  --  {symbol}: no PDF from ODS", file=sys.stderr)
                continue
            except Exception as exc:  # noqa: BLE001
                entry = {"status": "error", "official_url": url, "error": str(exc)[:200], "fetched_at": now}
                log[symbol] = entry
                print(f"  !!  {symbol}: {exc}", file=sys.stderr)
                continue
            path.write_bytes(data)
            entry = {"status": "ok", "via": "ods", "official_url": url, "final_url": final_url,
                     "fetched_at": now}
        entry["file"] = str(path.relative_to(ROOT))
        entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        entry["bytes"] = path.stat().st_size
        entry.update(pdf_facts(path))
        log[symbol] = entry
        print(f"  ok  {symbol}: {entry['pages']}pp, {entry['text_chars']} chars, {entry['via']}", file=sys.stderr)
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")

    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    ok = sum(1 for s in todo if log.get(s, {}).get("status") == "ok")
    print(f"\n{ok}/{len(todo)} available -> {log_path.relative_to(ROOT)}", file=sys.stderr)
    missing = [s for s in todo if log.get(s, {}).get("status") != "ok"]
    if missing:
        print("not available from ODS (UN Digital Library fallback needs a browser session):", missing, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
