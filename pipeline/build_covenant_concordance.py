#!/usr/bin/env python3
"""Draft-to-final article concordance for the two Covenants, from the UN texts.

Final texts: GA resolution 2200 (XXI), whose annex holds the ICESCR, the ICCPR and the
Optional Protocol in that order; each is a run of articles numbered from 1.

Drafts: the Commission's 1954 texts (E/2573), which the Third Committee worked through
article by article from 1954 to 1966. E/2573 itself is not on ODS; the Secretary-General's
annotations (A/2929, 1955) reprint each draft article at the head of its commentary
("ARTICLE 9 / Liberty and security of person / 1. Everyone has ..."), under a chapter or a
heading that says which covenant it belongs to. Each draft is matched to the final article of
its covenant whose text is closest.

Outputs: data/concordance/covenants_final.json (the adopted texts, UN public text) and
data/concordance/covenant_drafts.csv (stage "e2573", draft -> final, with the similarity).

Usage: python3 pipeline/build_covenant_concordance.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_concordance import article_runs, pages_text  # noqa: E402
from common import safe_name  # noqa: E402
from normalize import strip_furniture  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OCR = ROOT / "data" / "ocr"
FINAL_OUT = ROOT / "data" / "concordance" / "covenants_final.json"
OUT = ROOT / "data" / "concordance" / "covenant_drafts.csv"
# draft texts are UN OCR text: kept with the segments (gitignored until publication is cleared)
DRAFT_TEXTS = ROOT / "data" / "segments" / "_covenant_draft_texts.json"
INSTRUMENTS = ["ICESCR", "ICCPR", "OP1"]
CCPR_RE = re.compile(r"civil\s+and\s+political", re.I)
ESCR_RE = re.compile(r"economic,?\s+social\s+and\s+cultural", re.I)
DRAFT_HEAD_RE = re.compile(r"^\W{0,3}ARTICLE\s+(?P<n>[\dIlOkhU]{1,2})\b(?P<rest>.*)$")


# The adopted texts as the OCR gives them carry page furniture and misread characters. They were checked against the page
# images by two readers (opus and sonnet, October 2026), page furniture removed by rule, and set out one paragraph or
# sub-paragraph to a line (structure()): the checked file is what the database uses, and it wins over the OCR.
CHECKED = ROOT / "data" / "concordance" / "covenants_final_checked.json"
ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]


def structure(text: str) -> str:
    """One numbered paragraph, lettered sub-paragraph "(a)" or roman sub-item "(i)" to a line, each marker taken only as the next
    of its series (2 after 1, (b) after (a), (ii) after (i)): a cross-reference in the text ("paragraph 2.") is not one."""
    out, pos, para, letter, roman = [], 0, 1, 0, 0
    for m in re.finditer(r"(?<=[.;:,] )(?:(\d{1,2})\. (?=[A-Z(\"“])|\(([a-z]|[ivx]{1,4})\) )", text):
        num, mark = m.group(1), m.group(2)
        if num and int(num) == para + 1:
            para, letter, roman, brk = para + 1, 0, 0, "\n"
        elif mark and len(mark) == 1 and ord(mark) - 96 == letter + 1 and not (mark == "i" and roman == 0 and letter != 8):
            letter, roman, brk = letter + 1, 0, "\n  "
        elif mark and mark in ROMAN and ROMAN.index(mark) == roman:
            roman, brk = roman + 1, "\n    "
        else:
            continue
        out.append(text[pos:m.start()].rstrip() + brk)
        pos = m.start()
    out.append(text[pos:])
    return "".join(out)


def final_texts() -> dict[str, dict[int, str]]:
    if CHECKED.exists():
        checked = json.loads(CHECKED.read_text(encoding="utf-8"))["instruments"]
        return {name: {int(n): t for n, t in arts.items()} for name, arts in checked.items()}
    runs = article_runs(pages_text("A/RES/2200(XXI)"), cap=None)  # the adopted texts whole (the longest run over 1,200 characters)
    out = {}
    for name, run in zip(INSTRUMENTS, runs):
        out[name] = {a["n"]: " ".join(a["text"].split()) for a in run}
    return out


def covenant_of(text: str) -> str | None:
    c, e = bool(CCPR_RE.search(text)), bool(ESCR_RE.search(text))
    return "ICCPR" if c and not e else "ICESCR" if e and not c else None


def a2929_drafts() -> list[dict]:
    """Draft articles reprinted in A/2929: covenant, number, page, text (first lines).

    A heading either names its covenant ("ARTICLE 4 of the draft covenant on economic, social
    and cultural rights", "ARTICLE 3 of both draft covenants") or not ("ARTICLE 9"). Plain
    headings come in two runs, the civil and political articles (6-50) and then the economic,
    social and cultural ones (6-25): the covenant changes where the numbering starts again."""
    d = OCR / safe_name("A/2929") / "vote"
    out, plain_cov, last_plain = [], "ICCPR", 0
    for p in sorted(d.glob("page-*.txt")):
        body, _ = strip_furniture(p.read_text(encoding="utf-8"), first_page=p.name == "page-001.txt")
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        for i, ln in enumerate(lines):
            m = DRAFT_HEAD_RE.match(ln)
            # a heading stands alone ("ARTICLE 11", or with its covenant); commentary says "article 11"
            if not m or not re.match(r"^\W*(?:$|of\s|,\s*draft)", m.group("rest")):
                continue
            n = int(m.group("n").translate(str.maketrans("IlOkhU", "110444")))
            around = " ".join(lines[i:i + 3])
            both = bool(re.search(r"both\s+draft\s+covenants", around, re.I))
            named = covenant_of(around) if re.match(r"\W*(?:of\s|,)", m.group("rest")) else None
            if both:
                covs = ["ICCPR", "ICESCR"]
            elif named:
                covs = [named]
            else:
                if n < last_plain - 5:
                    plain_cov = "ICESCR"
                last_plain = n
                covs = [plain_cov]
            rest = lines[i + 1:]
            # skip the heading's continuation ("of the draft covenant on ... rights"), then the
            # title ("Liberty and security of person"): one short line, capitalised, no full stop
            while rest and re.match(r"^(?:of\s|rights\b|cultural|political|and\s|civil\b)", rest[0], re.I):
                rest = rest[1:]
            if rest and len(rest[0]) < 70 and not re.match(r"^\d", rest[0]) and not rest[0].rstrip().endswith("."):
                rest = rest[1:]
            # the article ends where the commentary starts: its paragraphs are numbered on from the
            # chapter ("326 Article 12 contains ...", OCR "le, There was ..."); the article's own run 1., 2., 3.
            end = next((k for k, x in enumerate(rest) if re.match(r"^(?:\d{2,3}|[a-z]{1,2}[,.])[.,]?\s+[A-Z]", x)), len(rest))
            text = " ".join(rest[:end])[:900]
            for c in covs:
                out.append({"instrument": c, "draft_article": n, "page": int(p.stem.split("-")[1]), "text": text})
    # one entry per (covenant, article): the first reprint
    seen, uniq = set(), []
    for x in out:
        k = (x["instrument"], x["draft_article"])
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    return uniq


# Words every article of a covenant shares ("The States Parties to the present Covenant
# recognize the right of everyone to ..."): left out of the comparison, so that the margin
# between the best and the second-best final article reflects the substance.
BOILERPLATE = set("the states parties to present covenant recognize recognizes undertake undertakes right rights "
                  "of everyone to and in a an be shall this that which for with by or any all no one".split())


def content(text: str) -> str:
    return " ".join(w for w in re.findall(r"[a-z]+", text.lower()) if w not in BOILERPLATE)


def main() -> int:
    finals = final_texts()
    for k, v in finals.items():
        print(f"final {k}: {len(v)} articles", file=sys.stderr)
    if len(finals.get("ICCPR", {})) < 40 or len(finals.get("ICESCR", {})) < 25:
        print("  final texts incomplete; stopping", file=sys.stderr)
        return 1
    FINAL_OUT.write_text(json.dumps({"source": "A/RES/2200(XXI), annex (the UN printed text; OCR checked against the page images)",
                                     "instruments": {k: {str(n): t for n, t in v.items()} for k, v in finals.items()}},
                                    ensure_ascii=False, indent=1), encoding="utf-8")
    rows = []
    # A/2929 states it outright for article 1: "Part I, Article 1, of both draft covenants"
    for p in sorted((OCR / safe_name("A/2929") / "vote").glob("page-*.txt")):
        if re.search(r"Part\s+I,?\s+Article\s+1,?\s+of\s+both\s+draft\s+covenants", p.read_text(encoding="utf-8")):
            for inst in ("ICCPR", "ICESCR"):
                rows.append({"instrument": inst, "stage": "e2573", "stage_symbol": "E/2573 (as reprinted in A/2929)",
                             "draft_article": 1, "final_article": 1, "source_pinpoint": f"A/2929 p. {int(p.stem[5:])}",
                             "note": "stated in A/2929: Part I, Article 1, of both draft covenants (self-determination)",
                             "_score": 100})
            break
    drafts = [d for d in a2929_drafts() if d["draft_article"] != 1 or not rows]
    for d in drafts:
        fin = finals[d["instrument"]]
        # substance words first; a tie (a short draft, "social security", sits whole inside several
        # final articles) is settled by the texts compared as a whole
        scores = sorted(((fuzz.token_set_ratio(content(d["text"][:500]), content(t[:500])),
                          fuzz.ratio(d["text"][:300].lower(), t[:300].lower()), n) for n, t in fin.items()), reverse=True)
        (best, whole, n), (runner, runner_whole, _) = scores[0], scores[1]
        ok = best >= 55 and (best - runner >= 5 or (best == runner and whole - runner_whole >= 10))
        rows.append({"instrument": d["instrument"], "stage": "e2573", "stage_symbol": "E/2573 (as reprinted in A/2929)",
                     "draft_article": d["draft_article"], "final_article": n if ok else "",
                     "source_pinpoint": f"A/2929 p. {d['page']}", "_score": best,
                     "note": f"text similarity {best:.0f} (margin {best - runner:.0f})" + ("" if ok else "; no clear match")})
    # several drafts on one final article: articles were merged (E/2573 arts 11 and 12 became
    # art. 11), but a weak match can also land there; keep a second only if it is close too
    for inst in ("ICCPR", "ICESCR"):
        by_final: dict[int, list[dict]] = {}
        for r in rows:
            if r["instrument"] == inst and r["final_article"]:
                by_final.setdefault(r["final_article"], []).append(r)
        for fin, rs in by_final.items():
            rs.sort(key=lambda r: -r["_score"])
            for k, r in enumerate(rs):
                if k >= 2 or (k == 1 and r["_score"] < 70):
                    r["note"] += f"; set aside: draft article {rs[0]['draft_article']} is closer to final article {fin}"
                    r["final_article"] = ""
    for r in rows:
        r.pop("_score", None)
    rows.sort(key=lambda r: (r["instrument"], r["draft_article"]))
    fin_of = {(r["instrument"], r["draft_article"]): r["final_article"] for r in rows}
    DRAFT_TEXTS.write_text(json.dumps([
        {"instrument": d["instrument"], "stage": "e2573", "stage_symbol": "A/2929", "draft_article": d["draft_article"],
         "page": d["page"], "final_article": fin_of.get((d["instrument"], d["draft_article"])) or None, "text": d["text"]}
        for d in drafts], ensure_ascii=False, indent=1), encoding="utf-8")
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for inst in ("ICCPR", "ICESCR"):
        rs = [r for r in rows if r["instrument"] == inst]
        print(f"  {inst}: {len(rs)} draft articles, {sum(1 for r in rs if r['final_article'])} matched: " +
              " ".join(f"{r['draft_article']}->{r['final_article'] or '?'}" for r in rs), file=sys.stderr)
    print(f"-> {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
