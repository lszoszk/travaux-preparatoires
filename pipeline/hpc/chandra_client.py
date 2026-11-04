#!/usr/bin/env python3
"""The local vision model's corpus run on a GPU cluster (PLGrid): the same reading as eval/vlm_local_bench.py, but the
model is the original Chandra OCR 2 served by vLLM (datalab-to/chandra-ocr-2, OpenAI-compatible API on the node) and the
pages are rendered from the PDFs on the cluster, as pipeline/ocr.py renders them (300 dpi, greyscale), in memory.

Reads the queue (data/logs/chandra_queue.json: {"pages": [{"symbol", "page", ...}]} in the order to read), skips pages
already read, and writes for each page OUT/<safe symbol>/chandra/page-NNN.html (the model's answer), page-NNN.txt (its
text without running heads, footers and picture descriptions: eval/vlm_local_bench.py to_text), a page-NNN.failed marker
when the answer reaches the token limit twice (a runaway reading), and one JSON line per page in OUT/chandra_run.jsonl.
OUT mirrors data/ocr, so the results are copied back with rsync into data/ocr.

  python3 pipeline/hpc/chandra_client.py --queue data/logs/chandra_queue.json --raw data/raw --out results \
      [--workers 24] [--limit N] [--hours 11] [--api http://localhost:8000/v1]
Stops after the current pages when OUT/chandra.STOP exists.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "eval"))
from common import safe_name  # noqa: E402
from vlm_local_bench import PROMPT, to_text  # noqa: E402  (the same prompt and the same conversion as on the laptop)

DPI = 300  # (pipeline/ocr.py)
MODEL = "chandra"  # (the name vLLM serves datalab-to/chandra-ocr-2 under: --served-model-name chandra)


def render_png(pdf_path: Path, page: int) -> bytes:
    import fitz
    with fitz.open(pdf_path) as pdf:
        return pdf[page - 1].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY).tobytes("png")


def pdf_of(raw: Path, symbol: str) -> Path | None:
    for lang in ("EN", "FR"):  # (pipeline/ocr.py scan_pdf)
        p = raw / f"{safe_name(symbol)}-{lang}.pdf"
        if p.exists():
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", type=Path, required=True)
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--api", default="http://localhost:8000/v1")
    ap.add_argument("--workers", type=int, default=24, help="requests in flight (vLLM batches them on the GPU)")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--limit", type=int, default=0, help="read at most N pages (0: all)")
    ap.add_argument("--shard", default="0/1", help="K/N: read only every N-th page of the queue from the K-th (a SLURM array task)")
    ap.add_argument("--hours", type=float, default=0, help="start no new page after this many hours (a Kaggle session ends at 12)")
    ap.add_argument("--timeout", type=float, default=1800, help="seconds to wait for one answer (the OpenAI client's 600 s default "
                    "timed out 25 of 1,986 pages with 16 in flight on two T4s)")
    args = ap.parse_args()
    from openai import OpenAI

    client = OpenAI(base_url=args.api, api_key="local", timeout=args.timeout)
    log = args.out / "chandra_run.jsonl"
    args.out.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    t0 = time.time()
    stop = args.out / "chandra.STOP"

    todo = []
    k, n = map(int, args.shard.split("/"))
    for x in json.loads(args.queue.read_text())["pages"][k::n]:
        out = args.out / safe_name(x["symbol"]) / "chandra" / f"page-{x['page']:03d}.txt"
        if not out.exists():
            todo.append((x["symbol"], x["page"]))
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(todo)} pages to read", file=sys.stderr, flush=True)

    def ask(png: bytes, max_tokens: int):
        r = client.chat.completions.create(
            model=MODEL, temperature=0.0, max_tokens=max_tokens,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()}},
                {"type": "text", "text": PROMPT}]}])
        return r.choices[0].message.content or "", r.usage.completion_tokens, r.choices[0].finish_reason

    def read(item: tuple[str, int]) -> bool:
        if stop.exists() or (args.hours and time.time() - t0 > args.hours * 3600):
            return False  # (skipped: not counted as read)
        symbol, page = item
        pdf = pdf_of(args.raw, symbol)
        row = {"symbol": symbol, "page": page, "model": "datalab-to/chandra-ocr-2 (vLLM)"}
        if not pdf:
            row["error"] = "no PDF"
        else:
            t = time.time()
            try:
                png = render_png(pdf, page)
                text, tokens, finish = ask(png, args.max_tokens)
                truncated = finish == "length"
                if truncated:  # (once more with twice the room; a second stop at the limit is a runaway reading)
                    text, tokens, finish = ask(png, 2 * args.max_tokens)
                    truncated = finish == "length"
                d = args.out / safe_name(symbol) / "chandra"
                d.mkdir(parents=True, exist_ok=True)
                if truncated:
                    (d / f"page-{page:03d}.failed").write_text("runaway: the answer reached the token limit twice\n")
                (d / f"page-{page:03d}.html").write_text(text, encoding="utf-8")
                (d / f"page-{page:03d}.txt").write_text(to_text(text) + "\n", encoding="utf-8")
                row.update({"seconds": round(time.time() - t, 1), "tokens": tokens, "chars": len(text), "truncated": truncated})
            except Exception as e:  # (one page's failure is logged, the run goes on)
                row["error"] = f"{type(e).__name__}: {e}"[:300]
        with lock:
            with log.open("a") as f:
                f.write(json.dumps(row) + "\n")
        return True

    done = 0
    with ThreadPoolExecutor(args.workers) as pool:
        for asked in pool.map(read, todo):
            done += asked
            if asked and done % 100 == 0:
                print(f"{done} pages, {(time.time() - t0) / done:.2f} s a page", file=sys.stderr, flush=True)
    print(f"{done} pages in {(time.time() - t0) / 3600:.2f} h", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
