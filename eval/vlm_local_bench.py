#!/usr/bin/env python3
"""The local arm of the vision-reader pilot (docs/vlm_pilot_plan.md): a vision OCR model run on this Mac with Apple's MLX
(mlx-vlm), on page images the project already has (data/ocr/<doc>/img/page-NNN.png). It writes the reading as one more
engine, data/ocr/<doc>/<engine>/page-NNN.txt, so eval/ocr_bench.py and the segmenter can read it like the others, and logs
the time per page. The image is passed as a path: no new image is written (the disk is nearly full).

  python3 eval/vlm_local_bench.py E/CN.4/SR.50 --pages 2 3          # a smoke test on two pages
  python3 eval/vlm_local_bench.py --sample eval/vlm_pilot/dev_set.json            # the development set (20 pages)
  python3 eval/vlm_local_bench.py --sample eval/vlm_pilot/sample.json --block B   # the pilot's block B (60 pages)
  python3 eval/vlm_local_bench.py --convert-only --sample ...                      # the text again from the saved HTML

The model answers in HTML with layout labels (<div data-label="Page-Header">...); the answer is kept as page-NNN.html and
its text, without the page's running heads and footers, is page-NNN.txt.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from common import safe_name  # noqa: E402

MODEL = "1qh/chandra-ocr-2-oq5-mlx"
ENGINE = "chandra"
LOG = ROOT / "data" / "logs" / "vlm_local_bench.jsonl"
# (a transcription, not a summary: the record's text as printed, line by line, nothing added)
PROMPT = ("Transcribe all the text on this page exactly as printed, line by line, in reading order. Keep the original "
          "spelling, capitalisation, punctuation and paragraph numbers; do not correct, complete or summarise anything. "
          "If the page has two columns, give the left column, then the right column. Output plain text only.")


# layout labels that are not the record's text at that place (the running head, the page number, the footer) and the
# model's own descriptions of pictures ("Image": "The emblem of the United Nations featuring a world map ...", 16 Oct 2026)
FURNITURE = {"Page-Header", "Page-Footer", "Page-Number", "Image"}
BLOCK_RE = re.compile(r'<div[^>]*data-label="(?P<label>[^"]*)"[^>]*>(?P<body>.*?)</div>', re.S)


def to_text(answer: str) -> str:
    """The text of the model's HTML answer, block by block, without the furniture blocks."""
    blocks = list(BLOCK_RE.finditer(answer))
    if not blocks:  # (an answer in plain text)
        return answer.strip()
    out = []
    for m in blocks:
        if m.group("label") in FURNITURE:
            continue
        body = re.sub(r"<br\s*/?>|</p>|</li>|</tr>|</h\d>", "\n", m.group("body"))
        body = html.unescape(re.sub(r"<[^>]+>", " ", body))
        out.append("\n".join(" ".join(line.split()) for line in body.splitlines() if line.strip()))
    return "\n".join(x for x in out if x).strip()


def pages_to_read(args) -> list[tuple[str, int]]:
    if args.sample:
        data = json.loads(Path(args.sample).read_text())
        if isinstance(data, dict) and "documents" in data:  # (eval/vlm_pilot/dev_set.json)
            return [(d["symbol"], p) for d in data["documents"] for p in d["pages"]]
        items = data["pages"] if isinstance(data, dict) else data  # (eval/vlm_pilot/sample.json)
        return [(x["symbol"], x["page"]) for x in items if not args.block or x.get("block") == args.block]
    return [(args.symbol, p) for p in args.pages]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol", nargs="?")
    ap.add_argument("--pages", type=int, nargs="*", default=[1])
    ap.add_argument("--sample")
    ap.add_argument("--block")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--force", action="store_true", help="read again pages already read")
    ap.add_argument("--convert-only", action="store_true", help="write the text again from the saved HTML, no model")
    args = ap.parse_args()
    if args.convert_only:
        for symbol, page in pages_to_read(args):
            d = ROOT / "data" / "ocr" / safe_name(symbol) / ENGINE
            src = d / f"page-{page:03d}.html"
            if src.exists():
                (d / f"page-{page:03d}.txt").write_text(to_text(src.read_text(encoding="utf-8")) + "\n", encoding="utf-8")
        return 0
    from mlx_vlm import generate, load
    from mlx_vlm.prompt_utils import apply_chat_template

    t0 = time.time()
    model, processor = load(MODEL)
    prompt = apply_chat_template(processor, model.config, PROMPT, num_images=1)
    print(f"model loaded in {time.time() - t0:.0f} s", file=sys.stderr)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    stop = ROOT / "data" / "logs" / "chandra.STOP"  # (touch it to stop after the current page)
    for symbol, page in pages_to_read(args):
        if stop.exists():
            print("stopped: data/logs/chandra.STOP exists", file=sys.stderr)
            break
        img = ROOT / "data" / "ocr" / safe_name(symbol) / "img" / f"page-{page:03d}.png"
        out = img.parent.parent / ENGINE / f"page-{page:03d}.txt"
        if not img.exists() or (out.exists() and not args.force):
            continue
        t = time.time()
        res = generate(model, processor, prompt, image=str(img), max_tokens=args.max_tokens, temperature=0.0, verbose=False)
        # (a reading that stops at the limit is cut short: once more with twice the room; A/C.3/SR.904 p. 3, a back cover
        # in small type, stopped at 4,000 tokens in the middle of its list)
        truncated = (getattr(res, "generation_tokens", 0) or 0) >= args.max_tokens
        if truncated:
            res = generate(model, processor, prompt, image=str(img), max_tokens=2 * args.max_tokens, temperature=0.0, verbose=False)
            truncated = (getattr(res, "generation_tokens", 0) or 0) >= 2 * args.max_tokens
        # (still at the limit: the model has run away, repeating itself; E/CN.4/SR.8 p. 1 wrote 60,090 characters and lost the
        # page's text. The reading is kept for the record but marked failed, and the pipeline keeps the vote there)
        out.parent.mkdir(exist_ok=True)
        if truncated:
            (out.parent / f"page-{page:03d}.failed").write_text("runaway: the answer reached the token limit twice\n")
        secs = time.time() - t
        text = res.text if hasattr(res, "text") else str(res)
        out.parent.mkdir(exist_ok=True)
        out.with_suffix(".html").write_text(text, encoding="utf-8")
        out.write_text(to_text(text) + "\n", encoding="utf-8")
        row = {"symbol": symbol, "page": page, "model": MODEL, "seconds": round(secs, 1),
               "tokens": getattr(res, "generation_tokens", None), "chars": len(text), "truncated": truncated}
        with LOG.open("a") as f:
            f.write(json.dumps(row) + "\n")
        print(f"{symbol} p{page}: {secs:.0f} s, {row['tokens']} tokens, {len(text)} chars", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
