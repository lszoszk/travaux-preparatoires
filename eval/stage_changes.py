#!/usr/bin/env python3
"""What changed in a UDHR article from each drafting stage to the next (preregistered in docs/devlog.md, 20 Oct; it replaces
the one-graph collation of eval/collation_pilot.py, which failed on alignment).

For each article: the eight stages of draft_texts in drafting order, then the adopted text (A/RES/217(III),
data/concordance/udhr_final.json); each stage against the next one that has the article. A stage's text is the vision reader's
reading of the same passage (pages p and p+1, fuzzy alignment >= 80) where it has read the page, else the OCR's; editorial
notes are cut ("(Geneva text)", "(formerly Article 8)", "The Drafting Committee did not have time to consider this Article").
The two texts are compared word by word (case, punctuation, paragraph numbers and a spilled "Article" heading ignored):
every replaced, added or dropped run of words is a change; a dropped run and an added run of at least four words that read
the same are one "moved" change. (A first version split the texts into clauses and paired them; the OCR's stray full stops,
"dignity ..and.", cut clauses in the middle, so it was dropped on the development articles before the held-out run.)

  python3 eval/stage_changes.py --articles 1 4 18 24 [--out eval/stage_changes]
Writes <out>/art-NN.json (texts, sources, changes) and <out>/art-NN.md (readable).
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sqlite3
import sys
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from build_concordance import LEAD_NOTE_RE, is_french  # noqa: E402

STAGES = [("secretariat_outline", "Secretariat outline (E/CN.4/AC.1/3)"), ("cassin_draft", "Cassin draft (E/CN.4/AC.1/W.2/Rev.2)"),
          ("drafting_committee_1", "Drafting Committee (E/CN.4/21)"), ("e_cn4_57", "Geneva working group (E/CN.4/57)"),
          ("geneva_draft", "Commission, 2nd session (E/600)"), ("drafting_committee_2", "Drafting Committee, 2nd session (E/CN.4/95)"),
          ("chr_3", "Commission, 3rd session (E/800)"), ("a777", "Third Committee (A/777)"), ("final", "Adopted (A/RES/217(III))")]
DC_NOTE = re.compile(r"\(?\s*The\s+Drafting\s+Committee\s+did\s+not\s+h\w+\s+(?:the\s+)?time\b.*$")
# a catchword: the first words of the next page, printed at the foot of this one ("/placed" ... "placed on the exercise")
CATCHWORD = re.compile(r"/\s*((?:[\w'-]+\s+){0,3}[\w'-]+)\s+(?=\1\b)", re.I)


def clean(text: str) -> str:
    t = " ".join(text.split())
    t = re.sub(r"^[\W_]*?(?=\(?\d|[A-Z])", "", t)
    t = re.sub(r"^\(?\d{1,2}\)?\s+(?=[A-Z])", "", t)  # (an article number before the text: "20 There shall be")
    while (lead := LEAD_NOTE_RE.match(t)) and lead.end():
        t = t[lead.end():]
    m = DC_NOTE.search(t)
    if m and m.start() >= 40:
        t = t[:m.start()]
    return CATCHWORD.sub("", t).strip()


def words(text: str) -> list[str]:
    t = text.lower().replace("’", "'").replace("‘", "'")
    t = re.sub(r"^\(?\d{1,2}\s*[.),]\s*|^\(?[a-z]\)\s*", "", t.strip())  # (a paragraph number is not wording)
    return re.findall(r"[a-z0-9]+(?:['-][a-z0-9]+)*", t)


def from_reader(symbol: str, page: int, text: str) -> str | None:
    d = ROOT / "data" / "ocr" / symbol.replace("/", "_") / "chandra"
    pages = [d / f"page-{p:03d}.txt" for p in (page, page + 1)]
    if not pages[0].exists():
        return None
    page_text = " ".join(" ".join(f.read_text(encoding="utf-8").split()) for f in pages if f.exists())
    t = " ".join(text.split())
    al = fuzz.partial_ratio_alignment(t.lower(), page_text.lower())
    if not al or al.score < 80:
        return None
    a, b = al.dest_start, al.dest_end
    # (the best window can start or end a word or two inside the passage: widen it to the text's first and last words)
    low = page_text.lower()
    first, last = " ".join(t.lower().split()[:2]), " ".join(t.lower().split()[-2:])
    k = low.rfind(first, max(0, a - 40), a + len(first))
    a = k if k >= 0 else a
    k = low.find(last, max(0, b - len(last) - 40), b + 40)
    b = k + len(last) if k >= 0 else b
    while a > 0 and page_text[a - 1].isalnum():
        a -= 1
    while b < len(page_text) and page_text[b].isalnum():
        b += 1
    return page_text[a:b]


PARA_NO = re.compile(r"(?:(?<=\s)|^)\(?(?:\d{1,2}|[a-z])\s*[.)]\s")
HEADING_SPILL = re.compile(r"^\s*articles?\s*\d*\s*[.:]?\s*|\s*articles?\s*\d*\s*$", re.I)


def tokens(text: str) -> list[str]:
    """The text's words, without paragraph numbers, and without an article number or heading at its edges (a bare number,
    or "article N" with up to two words of the previous article before it, "character article 17")."""
    t = HEADING_SPILL.sub(" ", PARA_NO.sub(" ", " " + text + " "))
    w = words(t)
    for k in range(min(3, len(w) - 1)):
        if w[k] == "article" and k + 1 < len(w) and w[k + 1].isdigit():
            w = w[k + 2:]
            break
    while w and w[0].isdigit():
        w = w[1:]
    for k in range(len(w) - 1, max(len(w) - 4, 0), -1):
        if w[k - 1] in ("article", "articles") and w[k].isdigit() or w[k] in ("article", "articles"):
            w = w[:k - 1] if w[k - 1] in ("article", "articles") else w[:k]
            break
    while w and w[-1].isdigit():
        w = w[:-1]
    return w


def compare(old: str, new: str) -> list[dict]:
    """Word differences between two stages' texts; a dropped run and an added run of at least four words that read the same
    (ratio >= 85) are one move."""
    wa, wb = tokens(old), tokens(new)
    sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
    changes = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        ctx = " ".join(wb[max(0, j1 - 4):j2 + 4]) if op != "delete" else " ".join(wa[max(0, i1 - 4):i2 + 4])
        changes.append({"kind": {"replace": "replaced", "insert": "added", "delete": "dropped"}[op],
                        "old": " ".join(wa[i1:i2]), "new": " ".join(wb[j1:j2]), "context": ctx})
    drops = [c for c in changes if c["kind"] == "dropped" and len(c["old"].split()) >= 4]
    for d in drops:
        add = max((c for c in changes if c["kind"] == "added" and len(c["new"].split()) >= 4),
                  key=lambda c: fuzz.ratio(c["new"], d["old"]), default=None)
        if add and fuzz.ratio(add["new"], d["old"]) >= 85:
            changes.remove(add)
            d.update({"kind": "moved", "new": add["new"], "context": ""})
    return changes


def corrected_texts() -> dict:
    """(stage, draft article) -> (text, page) as the corrected concordance cuts them, until the database is rebuilt: the
    hand-cut 1947 texts first, as api/build_db.py takes them."""
    seg = ROOT / "data" / "segments"
    out = {}
    for name in ("_draft_texts.json", "_draft_texts_early.json"):
        f = seg / name
        if f.exists():
            for d in json.loads(f.read_text()):
                out[(d["stage"], str(d["draft_article"]))] = (d["text"], d["page"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--articles", nargs="+", type=int, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "eval" / "stage_changes")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    final = json.loads((ROOT / "data" / "concordance" / "udhr_final.json").read_text())["articles"]
    corrected = corrected_texts()
    for art in args.articles:
        rows = con.execute("SELECT stage, stage_symbol, draft_article, page, text FROM draft_texts "
                           "WHERE instrument = 'UDHR' AND final_article = ? ORDER BY rowid", (art,)).fetchall()
        texts, sources = {}, {}
        for stage, _ in STAGES:
            if stage == "final":
                texts[stage] = final[str(art)]
                sources[stage] = [{"symbol": "A/RES/217(III)", "text_from": "un.org"}]
                continue
            parts, src = [], []
            for st, sym, draft, page, text in rows:
                if st != stage:
                    continue
                text, page = corrected.get((st, str(draft)), (text, page))
                if is_french(text):  # (no English text of this stage: left out, not compared)
                    continue
                t = clean(text)
                r = from_reader(sym, page, t)
                parts.append(clean(r) if r else t)
                src.append({"symbol": sym, "draft_article": draft, "page": page, "text_from": "vision reader" if r else "OCR"})
            if parts:
                texts[stage], sources[stage] = " ".join(parts), src
        names = dict(STAGES)
        present = [s for s, _ in STAGES if s in texts]
        steps = []
        for s, t in zip(present, present[1:]):
            ch = compare(texts[s], texts[t])
            for k, c in enumerate(ch, 1):
                c["n"] = f"{s}>{t}#{k}"
            steps.append({"from": s, "to": t, "changes": ch})
        (args.out / f"art-{art:02d}.json").write_text(json.dumps({"article": art, "texts": texts, "sources": sources, "steps": steps},
                                                                  ensure_ascii=False, indent=1) + "\n")
        md = [f"# Article {art}: what changed at each stage\n"]
        for st in steps:
            md.append(f"\n## {names[st['from']]} → {names[st['to']]}\n")
            if not st["changes"]:
                md.append("No change.\n")
            for c in st["changes"]:
                md.append(f"- {c['n'].split('#')[1]}. **{c['kind']}**: " + (f"“{c['old']}”" if c["old"] else "")
                          + (" → " if c["old"] and c["new"] else "") + (f"“{c['new']}”" if c["new"] else "")
                          + (f" (… {c['context']} …)" if c.get("context") else ""))
        (args.out / f"art-{art:02d}.md").write_text("\n".join(md) + "\n")
        n_reader = sum(x["text_from"] == "vision reader" for v in sources.values() for x in v)
        print(f"article {art}: {len(present)} stages ({n_reader} texts from the vision reader), "
              f"{sum(len(s['changes']) for s in steps)} changes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
