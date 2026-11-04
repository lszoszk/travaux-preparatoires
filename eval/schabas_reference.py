#!/usr/bin/env python3
"""Extract per-page reference text from Schabas (2013) for OCR evaluation. PRIVATE OUTPUT.

Schabas, The Universal Declaration of Human Rights: The Travaux Préparatoires (CUP 2013)
retypesets the UN records and marks the original page breaks as "[10]". That gives a
clean reference for each original UN page, which is what the OCR benchmark scores
against. The book is copyrighted: the output goes to eval/private/ (gitignored) and is
never published or committed. This script contains no text from the book.

Output: eval/private/reference/<safe symbol>.json = {"symbol", "pdf_pages", "pages": {"10": text, ...}}
  --all  every document the book reproduces, not only the given symbols
  --md   also eval/private/schabas_md/<safe symbol>.md, with [p. N] markers (for reading/diffing)
  --toc  parse the book's Table of documents to data/private/schabas_toc.json (symbols and pages only)
A document reproduced in several places (excerpts) is merged, in book order.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from common import canon, safe_name  # noqa: E402
OUT = ROOT / "eval" / "private" / "reference"
MD_OUT = ROOT / "eval" / "private" / "schabas_md"
TOC_OUT = ROOT / "data" / "private" / "schabas_toc.json"
# which UN page(s) of a document each book page holds: {symbol: {book page: [UN page]}} (PRIVATE; book page = 0-based PDF
# index - 126). The text before a document's first "[N]" marker is UN page N - 1 when N > 2 (a printed record opening on
# a page it shares with the record before), else page 1.
PAGEMAP_OUT = ROOT / "data" / "private" / "schabas_pagemap.json"
BOOK_OFFSET = 126
TOC_PAGES = range(47, 71)  # 0-based PDF pages of the Table of documents
SCHABAS = Path(os.environ.get(
    "SCHABAS_PDF",
    "/Users/lszoszk/Downloads/ William A. Schabas - The Universal Declaration Of Human Rights_ "
    "The Travaux Préparatoires 3-Vol Set (2013, Cambridge University Press).pdf",
))
FIRST_DOC_PAGE, LAST_DOC_PAGE = 127, 3226  # 0-based PDF pages holding the reproduced documents
BODY_MIN_SIZE = 10.5  # body text is 11 pt; footnotes and running heads are smaller
HEAD_ZONE = 50        # points from the top: running head with symbol and page number

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
# A document opens with its symbol on a line of its own, then the date. Editorial footnote
# numbers can be glued to the symbol ("A/C.3/SR.11675" = SR.116 + note 75).
START_RE = re.compile(rf"^\s*((?:A|E|PC)/[A-Za-z0-9./()]+)\s*\n\s*(?:\d{{1,2}} )?(?:{MONTHS}) ?\d{{0,2}},? \d{{4}}", re.M)
PAGE_MARK_RE = re.compile(r"\[(\d{1,3})\]")


def head_text(page) -> str:
    """Running head of a page ("E/CN.4/SR.15 205"), whitespace collapsed but kept:
    without it the symbol runs into the page number."""
    return " ".join(page.get_text(clip=fitz.Rect(0, 0, page.rect.width, HEAD_ZONE)).split())


def resolve(raw: str, heads: str) -> str:
    """Strip editorial footnote digits glued to a symbol ("A/C.3/SR.11675" = SR.116 + note 75).

    The running heads of the following pages print the true symbol, so a candidate is
    accepted when a running head confirms it. Without confirmation the raw form is kept:
    guessing a shorter known symbol turned E/CN.4/SR.15 into SR.1.
    """
    raw = canon(raw)
    cands = [raw] + [raw[:-cut] for cut in (1, 2, 3) if raw[-cut:].isdigit()]
    for c in cands:
        if re.search(r"(?<!\S)" + re.escape(c) + r"(?!\S)", heads, re.I):
            return c
    return raw


def body_text(page) -> str:
    """Page text without running head and footnotes (by font size and position)."""
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["size"] >= BODY_MIN_SIZE and s["bbox"][1] > HEAD_ZONE]
            if spans:
                lines.append("".join(s["text"] for s in spans))
    return "\n".join(lines)


def toc() -> list[dict]:
    """Table of documents: '  E/CN.4/SR.9      177' rows, grouped under organ headings."""
    out, section = [], None
    row = re.compile(r"^\s+((?:A|E|PC|ST)/\S+)\s+(\d{1,4}(?:\s*,\s*\d{1,4})*)\s*$")
    # PyMuPDF separates the symbol and page columns; pdftotext -layout keeps rows intact.
    import subprocess
    txt = subprocess.run(["pdftotext", "-layout", "-f", str(TOC_PAGES.start + 1), "-l", str(TOC_PAGES.stop),
                          str(SCHABAS), "-"], capture_output=True, text=True, check=True).stdout
    for line in txt.splitlines():
        m = row.match(line)
        if m:
            out.append({"symbol": canon(m.group(1)), "pages": [int(x) for x in re.split(r"\s*,\s*", m.group(2))],
                        "section": section})
        elif line.strip() and not line.startswith("  ") and len(line.strip()) < 80:
            section = line.strip()
    return out


def main(symbols: list[str], everything: bool = False, md: bool = False) -> int:
    wanted = {canon(s) for s in symbols}
    doc = fitz.open(SCHABAS)

    # 1. find every document start in the reproduced-documents part of the book
    starts: list[tuple[int, int, str]] = []  # (page, offset in body text, symbol)
    texts: dict[int, str] = {}
    heads = {pno: head_text(doc[pno]) for pno in range(FIRST_DOC_PAGE, LAST_DOC_PAGE + 3)}
    for pno in range(FIRST_DOC_PAGE, LAST_DOC_PAGE):
        text = body_text(doc[pno])
        texts[pno] = text
        for m in START_RE.finditer(text):
            nearby = "".join(heads.get(p, "") for p in range(pno, pno + 4))
            starts.append((pno, m.start(), resolve(m.group(1), nearby)))
    print(f"{len(starts)} document starts found", file=sys.stderr)

    # 2. cut out each wanted document and split it at the original page markers
    OUT.mkdir(parents=True, exist_ok=True)
    if md:
        MD_OUT.mkdir(parents=True, exist_ok=True)
    found: dict[str, dict] = {}
    pagemap: dict[str, dict] = json.loads(PAGEMAP_OUT.read_text()) if PAGEMAP_OUT.exists() and not everything else {}
    for symbol in wanted:
        pagemap.pop(symbol, None)
    for i, (pno, off, symbol) in enumerate(starts):
        if not everything and symbol not in wanted:
            continue
        end_p, end_off = (starts[i + 1][0], starts[i + 1][1]) if i + 1 < len(starts) else (LAST_DOC_PAGE, None)
        chunks = []
        for p in range(pno, end_p + 1):
            t = texts.get(p, "")
            a = off if p == pno else 0
            b = end_off if (p == end_p and end_off is not None) else len(t)
            chunks.append(t[a:b])
        full = "\n".join(chunks)
        # the book pages of this excerpt, with the UN pages on each
        cur, pmap = None, {}
        for p, t in zip(range(pno, end_p + 1), chunks):
            labels, pos = [], 0
            for m in PAGE_MARK_RE.finditer(t):
                if t[pos:m.start()].strip():
                    labels.append(cur)
                cur, pos = m.group(1), m.end()
            if t[pos:].strip():
                labels.append(cur)
            if labels:
                pmap[p - BOOK_OFFSET] = list(dict.fromkeys(labels))
        first = PAGE_MARK_RE.search(full)
        pre = str(int(first.group(1)) - 1) if first and int(first.group(1)) > 2 else "1"
        pmap = {bp: list(dict.fromkeys(pre if x is None else x for x in v)) for bp, v in pmap.items()}
        pages: dict[str, str] = {}
        current = "1"
        pos = 0
        for m in PAGE_MARK_RE.finditer(full):
            pages[current] = pages.get(current, "") + full[pos:m.start()]
            current, pos = m.group(1), m.end()
        pages[current] = pages.get(current, "") + full[pos:]
        rec = found.setdefault(symbol, {"symbol": symbol, "pdf_pages": [], "elisions": 0, "pages": {}})
        book = pagemap.setdefault(symbol, {})
        for bp, v in pmap.items():
            book[str(bp)] = list(dict.fromkeys(book.get(str(bp), []) + v))
        rec["pdf_pages"].append([pno + 1, end_p + 1])
        rec["elisions"] += full.count("…") + full.count(". . .")
        for k, v in pages.items():  # excerpts in several places: merge in book order
            rec["pages"][k] = (rec["pages"].get(k, "") + "\n" + v).strip()
    for symbol, rec in found.items():
        (OUT / f"{safe_name(symbol)}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        if md:
            body = "\n\n".join(f"[p. {k}]\n{v.strip()}" for k, v in rec["pages"].items())
            (MD_OUT / f"{safe_name(symbol)}.md").write_text(
                f"# {symbol}\n\n<!-- Schabas 2013, PDF pp. {rec['pdf_pages']}: PRIVATE, do not publish -->\n\n{body}\n",
                encoding="utf-8")
    PAGEMAP_OUT.parent.mkdir(parents=True, exist_ok=True)
    PAGEMAP_OUT.write_text(json.dumps(pagemap, indent=1), encoding="utf-8")
    n_book = sum(len(v) for v in pagemap.values())
    n_un = sum(len(x) for v in pagemap.values() for x in v.values())
    print(f"{len(found)} documents written" + (" (+ Markdown)" if md else "")
          + f"; pagemap: {len(pagemap)} documents, {n_book} book pages, {n_un / max(n_book, 1):.2f} UN pages per book page",
          file=sys.stderr)
    missing = sorted(wanted - set(found))
    if missing:
        print(f"not reproduced in Schabas (or start not detected): {missing}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if "--toc" in flags:
        rows = toc()
        TOC_OUT.parent.mkdir(parents=True, exist_ok=True)
        TOC_OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"table of documents: {len(rows)} entries -> {TOC_OUT.relative_to(ROOT)}", file=sys.stderr)
    if args and args[0].endswith(".json"):
        syms = [d["symbol"] for d in json.loads(Path(args[0]).read_text())["documents"]]
    else:
        syms = args
    if syms or "--all" in flags:
        raise SystemExit(main(syms, everything="--all" in flags, md="--md" in flags))
