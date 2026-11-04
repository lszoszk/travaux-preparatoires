"""The semantic-search benchmark's raw material: the meeting records two commentaries cite, with the text around each citation.

Nowak's CCPR Commentary (2005, tesseract OCR of the book wiki) and Saul, Kinley and Mowbray's ICESCR Commentary (OPIL print to
PDF) cite meeting records in their notes. For each note that cites a record we keep the note and the text it supports, so
that a model can restate the claim as a search query (eval/semantic_queries.py) and the cited records become the relevant set.
The books are copyrighted: everything written here goes to eval/private/semantic/ (gitignored); only counts leave it.

  python3 eval/semantic_extract.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "private" / "semantic"
WIKI = Path.home() / "Desktop" / "The Book" / "00_PROJECT" / "wiki"
NOWAK = WIKI / "sources" / "nowak-2005-ocr" / "full" / "nowak-full.txt"
SAUL = WIKI / "inbox" / "saul-kinley-mowbray-icescr-commentary" / "original.pdf"

RECORD = r"(?:E/CN\.4/(?:AC\.\d+/|Sub\.2/)?SR\.\d+|A/C\.3/SR\.\d+|E/SR\.\d+|A/PV\.\d+)"
RECORD_RE = re.compile(RECORD, re.I)
# a record and the pinpoint after it: "E/CN.4/SR.319, 13", "A/C.3/SR.640, § 21", "A/C.3/SR.729 (14 January 1957), 242",
# "E/CN.4/SR.248, [12]" (Saul's paragraphs are in brackets)
CITE_RE = re.compile(RECORD + r"(?:\s*\([^)]{4,30}\))?(?:,\s*(?:at\s+)?(?P<para>§§?\s*|\[)?(?P<pin>\d+)(?:\s*[-–]\s*(?P<pin2>\d+))?)?", re.I)
PAGE_MARK_RE = re.compile(r"^=== \[(.*?)\] ===$", re.M)


def cites(note: str) -> list[dict]:
    """The records a note cites, each with its pinpoint: a paragraph (§ or [n]), a page, or none."""
    out = []
    for m in CITE_RE.finditer(note):
        sym = RECORD_RE.match(m.group(0)).group(0).upper().replace("SUB.2", "Sub.2")
        pin = None
        if m.group("pin"):
            pin = {"type": "para" if m.group("para") else "page", "from": int(m.group("pin")),
                   "to": int(m.group("pin2") or m.group("pin"))}
        out.append({"symbol": sym, "pin": pin})
    return out


def nowak() -> list[dict]:
    """One item per printed page whose notes cite a record: the page's text (body and notes) and the citing notes."""
    text = NOWAK.read_text()
    marks = list(PAGE_MARK_RE.finditer(text))
    items = []
    for i, m in enumerate(marks):
        page = text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        notes = []
        # a note starts a line with its number; continuation lines are indented
        for nm in re.finditer(r"^\s{0,3}(\d{1,3})\s{1,8}(\S.*(?:\n\s{3,}\S.*)*)", page, re.M):
            c = cites(nm.group(2))
            if c:
                notes.append({"note": int(nm.group(1)), "text": " ".join(nm.group(2).split()), "cites": c})
        if notes:
            items.append({"source": "nowak", "page": m.group(1).split()[-1] if m.group(1).split() else m.group(1),
                          "head": " ".join(m.group(1).split()), "text": page.strip(), "notes": notes})
    return items


def decode(t: str) -> str:
    """Undo the shifted glyph codes of the OPIL print in the runs of a span that carry them (no lowercase, no plain space)."""
    def fix(m):
        d = "".join(chr(ord(c) + 29) if 0 < ord(c) < 94 else c for c in m.group(0))
        return d if sum(c.islower() or c == " " for c in d) >= 0.7 * len(d) else m.group(0)
    return re.sub(r"[^a-z ]{5,}", fix, t)


def saul() -> list[dict]:
    """One item per endnote that cites a record: the note and the body text around its superscript marker.

    The OPIL print sets some passages in a font whose glyph codes are shifted by 29 (decoded here); superscripts are note
    markers. Notes are numbered per chapter and printed at the chapter's end, so a marker is matched to the next block of
    notes that carries its number."""
    import fitz
    doc = fitz.open(SAUL)
    body, notes = [], []  # body: (page, text with [^n] markers); notes: (page, n, text)
    for pno in range(doc.page_count):
        lines, sup = [], False
        for b in doc[pno].get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                parts = []
                for s in line["spans"]:
                    t = s["text"]
                    if s["size"] < 8 and t.strip().isdigit():
                        # a superscript is a marker in the body; a bare small number on its own line numbers a note
                        sup |= bool(s["flags"] & 1)
                        t = f"[^{t.strip()}]" if s["flags"] & 1 else f"[#{t.strip()}]"
                    else:
                        t = decode(t)
                    parts.append(t)
                lines.append("".join(parts))
        text = "\n".join(l for l in lines if not l.startswith(("From: Oxford Public", "Subscriber:")))
        if sup:
            body.append((pno, re.sub(r"\[#\d+\]", "", text)))
        else:
            text = re.sub(r"^b\s*$\n?", "", text, flags=re.M)
            for nm in re.finditer(r"^\[#(\d+)\](.*?)(?=^\[#\d+\]|\Z)", text, re.M | re.S):
                notes.append((pno, int(nm.group(1)), " ".join(nm.group(2).split())))
    items = []
    used = set()
    for npno, n, note in notes:
        c = cites(note)
        if not c:
            continue
        # the marker [^n] on the nearest body page before the note's page
        for bpno, text in reversed([b for b in body if b[0] < npno]):
            k = text.find(f"[^{n}]")
            if k >= 0 and (bpno, n) not in used:
                used.add((bpno, n))
                ctx = " ".join(text[max(0, k - 1500): k + 300].split())
                items.append({"source": "saul", "page": str(bpno + 1), "note": n, "text": ctx, "note_text": note,
                              "cites": c})
                break
    return items


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    nw, sl = nowak(), saul()
    for name, items in (("nowak", nw), ("saul", sl)):
        with open(OUT / f"{name}_raw.jsonl", "w") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
    n_notes = sum(len(i["notes"]) for i in nw)
    n_cites = sum(len(n["cites"]) for i in nw for n in i["notes"])
    print(f"Nowak: {len(nw)} pages, {n_notes} notes, {n_cites} record citations")
    print(f"Saul: {len(sl)} notes with a body marker, {sum(len(i['cites']) for i in sl)} record citations")


if __name__ == "__main__":
    sys.exit(main())
