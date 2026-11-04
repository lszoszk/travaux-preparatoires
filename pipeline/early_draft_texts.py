#!/usr/bin/env python3
"""The 1947 draft texts for the article histories, cut from the UN documents' OCR by hand-set anchors.

For the texts whose articles the automatic run of headings cannot find (E/CN.4/21 annex F, whose
headings the OCR lost) or which build_concordance.py does not read (the Geneva working groups'
E/CN.4/57 and E/CN.4/56, the Geneva draft Covenant in E/600 annex B), each article's text is fixed
by two anchors read by hand from the cleaned OCR page text: the words it starts with and the words
it ends with (data/concordance/draft_text_anchors.json). The text between them is the OCR's, as
for every other stage; the final article comes from the hand concordances.

Usage:
  python3 pipeline/early_draft_texts.py                      # write data/segments/_draft_texts_early.json
  python3 pipeline/early_draft_texts.py --show E/600 31      # a page's cleaned text, as anchors must match it
  python3 pipeline/early_draft_texts.py --check < anchors    # the texts a list of anchors gives (JSON on stdin)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from articles import load_concordance  # noqa: E402
from build_concordance import pages_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ANCHORS = ROOT / "data" / "concordance" / "draft_text_anchors.json"
OUT = ROOT / "data" / "segments" / "_draft_texts_early.json"  # OCR text: gitignored with the segments
# stage -> (UN symbol, instrument)
STAGES = {"drafting_committee_1": ("E/CN.4/21", "UDHR"), "e_cn4_57": ("E/CN.4/57", "UDHR"),
          "e_cn4_56": ("E/CN.4/56", "ICCPR"), "e600": ("E/600", "ICCPR"),
          # June 1947: the United Kingdom's draft bill (E/CN.4/21, annex B) and the Drafting Committee's articles for a
          # convention taken from it (annex G), each article's final article with the anchor
          "uk_draft_1947": ("E/CN.4/21", "ICCPR"), "e_cn4_21_g": ("E/CN.4/21", "ICCPR"),
          # articles whose headings the automatic run lost in the other stages' texts
          "secretariat_outline": ("E/CN.4/AC.1/3", "UDHR"), "cassin_draft": ("E/CN.4/AC.1/W.2/Rev.2", "UDHR"),
          "geneva_draft": ("E/600", "UDHR"),
          "drafting_committee_2": ("E/CN.4/95", "UDHR"), "chr_3": ("E/800", "UDHR"),
          # the Third Committee's text of 7 December 1948 (A/777), numbered before the plenary deleted its article 3
          "a777": ("A/777", "UDHR"),
          # the Commission's draft Covenant(s), 1948-53, each as its session's report prints it: E/800 annex B and
          # E/1371 (numbered as the concordance's chr5 and chr6); E/1992, E/2256 and E/2447, whose articles carry
          # their instrument and final article with the anchor (None: per anchor)
          "chr5": ("E/800", "ICCPR"), "chr6": ("E/CN.4/350", "ICCPR"),
          # the text the sixth session (1950) left, in its report (E/1681, annex I): one covenant, civil and political
          "e1681": ("E/1681", "ICCPR"),
          "e1992": ("E/CN.4/640", None), "e2256": ("E/CN.4/669", None), "e2447": ("E/CN.4/689", None),
          # the Third Committee's texts as adopted, in its reports' annexes: articles 15-18 (1960), 19-25 (1961)
          "a4625": ("A/4625", "ICCPR"), "a5000": ("A/5000", "ICCPR")}


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


_PAGES: dict[str, dict[int, str]] = {}


def page(symbol: str, n: int) -> str:
    """A page's text with the running headers and page furniture removed, whitespace collapsed."""
    if symbol not in _PAGES:
        by = {}
        for pg, ln in pages_text(symbol):
            by.setdefault(pg, []).append(ln)
        _PAGES[symbol] = {pg: norm(" ".join(lns)) for pg, lns in by.items()}
    return _PAGES[symbol].get(n, "")


def cut(symbol: str, a: dict) -> str:
    """The text from the start anchor to the end of the end anchor, across pages."""
    first, last = page(symbol, a["page_start"]), page(symbol, a["page_end"])
    i = first.find(norm(a["start"]))
    if i < 0:
        raise ValueError(f"start not found on p. {a['page_start']}: {a['start']!r}")
    if a["page_end"] == a["page_start"]:
        j = first.find(norm(a["end"]), i)
        if j < 0:
            raise ValueError(f"end not found after the start on p. {a['page_end']}: {a['end']!r}")
        return first[i:j + len(norm(a["end"]))]
    j = last.find(norm(a["end"]))
    if j < 0:
        raise ValueError(f"end not found on p. {a['page_end']}: {a['end']!r}")
    # across a page break: the catchword at the foot of a page ("/Article 13") and the running head at the top of
    # the next ("page 6", "E/600 Page 36") are not the text
    foot = lambda t: re.sub(r"\s+/\S+(?:\s+\S+){0,2}\s*$", "", t)
    head = lambda t: re.sub(r"^\W*(?:\S{0,3}/\S+\s+)?page\W{0,3}\w{1,3}\b\W*", "", t, flags=re.I)
    middle = [head(foot(page(symbol, n))) for n in range(a["page_start"] + 1, a["page_end"])]
    return norm(" ".join([foot(first[i:]), *middle, head(last[:j + len(norm(a["end"]))])]))


def finals(stage: str, draft: str, conc: dict, cov: dict, inst: str) -> list[int]:
    """The final article(s) a draft article's text belongs in the history of."""
    first = re.match(r"\d+", draft).group(0)  # "3 to 6", "26 and 27", "2 (second alternative)"
    if inst == "UDHR":
        hit = conc.get((stage, draft)) or conc.get((stage, first))
        return [hit[0]] if hit else []
    fin = cov.get((stage, inst, first))
    return [fin] if fin else []


def build(anchors: list[dict]) -> list[dict]:
    sys.path.insert(0, str(ROOT / "api"))
    from build_db import load_covenant_concordance
    conc, cov = load_concordance(), load_covenant_concordance()
    out = []
    for a in anchors:
        symbol, inst = STAGES[a["stage"]]
        inst = a.get("instrument") or inst
        text = cut(symbol, a)
        # an anchor may carry its final article (the texts without a concordance of their own)
        fins = ([a["final"]] if a.get("final") else [] if "final" in a else finals(a["stage"], str(a["draft_article"]), conc, cov, inst))
        fins += [f for f in a.get("also_final", [])]
        for fin in dict.fromkeys(fins):
            out.append({"stage": a["stage"], "stage_symbol": symbol, "draft_article": str(a["draft_article"]),
                        "final_article": fin, "page": a["page_start"], "text": text[:4000], "instrument": inst})
    return out


def main() -> int:
    if len(sys.argv) >= 4 and sys.argv[1] == "--show":
        print(page(sys.argv[2], int(sys.argv[3])))
        return 0
    if len(sys.argv) >= 2 and sys.argv[1] == "--check":
        for a in json.load(sys.stdin):
            symbol = STAGES[a["stage"]][0]
            try:
                print(f"[{a['stage']} {a['draft_article']}] {cut(symbol, a)}\n")
            except ValueError as exc:
                print(f"[{a['stage']} {a['draft_article']}] ERROR {exc}\n")
        return 0
    anchors = json.loads(ANCHORS.read_text())["anchors"]
    rows = build(anchors)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} draft texts from {len(anchors)} anchors -> {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
