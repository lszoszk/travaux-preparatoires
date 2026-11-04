#!/usr/bin/env python3
"""Fetch, from the UVA Law Library's public copy of its travaux collection (uvallsc.s3.amazonaws.com/travaux/), the
documents of a manifest that the UN's document server (documents.un.org) did not serve.

The manifest's documents carry "uva_file" (the link read from the item's node page, eval/uva_nodes.py), which marks
the items UVA holds; the file fetched is the one named after the symbol (E/CN.4/SR.98/Corr.1 -> E-CN_4-SR_98-Corr_1.pdf),
because UVA's item pages link the wrong file (4 Nov 2026: 12 of its 469 Covenant items link a file named after their own
symbol; /node/1779, E/CN.4/SR.98/Corr.1, links A/C.3/SR.289). Read page 1 of each file before it enters the database.
One request every 6 seconds, one at a time, each file once; the log is the same harvest log as pipeline/harvest.py's,
with "via": "uva_s3". A file that is not a PDF is not kept.

Usage: python3 pipeline/uva_fetch.py data/manifest/uva_extra.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import safe_name  # noqa: E402
from harvest import SSL_CTX  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UA = "travaux-research/0.1 (academic; contact via the UVA Law Library)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--delay", type=float, default=6.0)
    args = ap.parse_args()
    if args.delay < 5:
        ap.error("--delay below 5 s is not allowed")
    docs = json.loads(args.manifest.read_text())["documents"]
    log_path = ROOT / "data" / "manifest" / f"harvest_{args.manifest.stem}.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}
    todo = [d for d in docs if d.get("uva_file") and log.get(d["symbol"], {}).get("status") != "ok"]
    print(f"{len(todo)} to fetch of {len(docs)}", file=sys.stderr)
    for i, d in enumerate(todo, 1):
        if i > 1:
            time.sleep(args.delay)
        sym = d["symbol"]
        url = f"https://uvallsc.s3.amazonaws.com/travaux/{sym.replace('/', '-').replace('.', '_')}.pdf"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90, context=SSL_CTX) as r:
                data = r.read()
        except Exception as exc:  # noqa: BLE001
            log[sym] = {"status": "error", "via": "uva_s3", "official_url": url, "error": str(exc)[:200]}
            print(f"  !!  {sym}: {exc}", file=sys.stderr)
            continue
        if data[:4] != b"%PDF":
            log[sym] = {"status": "error", "via": "uva_s3", "official_url": url, "error": "not a PDF"}
            print(f"  !!  {sym}: not a PDF", file=sys.stderr)
            continue
        path = RAW / f"{safe_name(sym)}-EN.pdf"
        path.write_bytes(data)
        with fitz.open(path) as doc:
            pages, chars = doc.page_count, sum(len(p.get_text()) for p in doc)
        log[sym] = {"status": "ok", "via": "uva_s3", "official_url": url, "file": str(path.relative_to(ROOT)), "pages": pages,
                    "text_chars": chars, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                    "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        print(f"  ok  {sym}: {pages}pp, {chars} chars", file=sys.stderr)
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
