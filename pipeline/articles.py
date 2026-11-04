"""Which final article a segment is about.

Segments carry the article number as the record heads it ("Article 16"), in the numbering
of the text the body had before it. That text (the stage) is read from the record's
agenda: the first stage document its opening pages cite (SR.60: "E/CN.4/95"; A/C.3/SR.127:
"E/800"); failing that, from the session. The stage's draft number is then mapped to the
final article through data/concordance/drafts.csv (built from the UN texts).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFTS = ROOT / "data" / "concordance" / "drafts.csv"
ARTICLES = ROOT / "data" / "concordance" / "articles.csv"
OVERRIDES = ROOT / "data" / "concordance" / "overrides.csv"
# the 1947 texts and the Geneva draft, read by hand: text matching could not tell their articles apart
EARLY = ROOT / "data" / "concordance" / "udhr_drafts_early.csv"
# which of those texts each 1947-48 meeting worked from, read from the records (the same session
# moved from one text to the next, and took up the draft Covenant too)
EARLY_MEETINGS = ROOT / "data" / "concordance" / "udhr_early_meetings.csv"

# Stage documents, as cited in agendas; "final" means the numbering of the adopted text. A/777, the Third Committee's
# text of 7 December 1948, is not: the plenary deleted its article 3 (its substance went into final article 2), so its
# articles 4-31 are final 3-30 (data/concordance/overrides.csv, stage a777)
STAGE_SYMBOLS = [
    ("A/RES/217(III)", "final"),
    ("A/777", "a777"),
    ("E/800", "chr_3"),
    ("E/CN.4/95", "drafting_committee_2"),
    ("E/600", "geneva_draft"),
    ("E/CN.4/21", "drafting_committee_1"),
    ("E/CN.4/AC.1/W.2/Rev.2", "cassin_draft"),
    ("E/CN.4/AC.1/3", "secretariat_outline"),
]
# The text each session worked from, when its records don't cite one.
SESSION_STAGE = {
    "General Assembly plenary / 3rd session (1948)": "a777",
    "General Assembly Third Committee / 3rd session (1948)": "chr_3",
    "Commission on Human Rights / 3rd session (1948)": "drafting_committee_2",
    "CHR Drafting Committee / 2nd session (1948)": "geneva_draft",
    "Commission on Human Rights / 2nd session (1947)": "drafting_committee_1",
    "CHR Drafting Committee / 1st session (1947)": "secretariat_outline",
    # the Geneva working groups (December 1947) worked from the Drafting Committee's text
    "CHR Working Group on the Declaration / 2nd session (1947)": "drafting_committee_1",
    "CHR Working Group on the Convention / 2nd session (1947)": "drafting_committee_1",
    "CHR Working Group on Implementation / 2nd session (1947)": "drafting_committee_1",
}
OCR_SYMBOL_FIXES = [(re.compile(r"E/CN\.[U^hA]/"), "E/CN.4/"), (re.compile(r"E/8OO\b"), "E/800"), (re.compile(r"E/6OO\b"), "E/600")]


def load_concordance() -> dict[tuple[str, str], tuple[int, str]]:
    """(stage, draft number) -> (final article, how). data/concordance/overrides.csv holds the
    correspondences the texts state but the matching cannot find (a draft split in two, a
    heading lost in the OCR); they come first. The stages in udhr_drafts_early.csv are read by
    hand only."""
    out = {}
    early = list(csv.DictReader(EARLY.open())) if EARLY.exists() else []
    hand = {r["stage"] for r in early}
    if DRAFTS.exists():
        with DRAFTS.open() as f:
            for r in csv.DictReader(f):
                if r["final_article"] and r["stage"] not in hand:
                    out[(r["stage"], str(r["draft_article"]))] = (int(r["final_article"]), r["note"])
    for r in early:
        if r["final_article"]:
            out[(r["stage"], r["draft_article"])] = (int(r["final_article"]), f"{r['stage_symbol']} art. {r['draft_article']}, "
                                                     f"{r['source_pinpoint']}: {r['note']} (read by hand)")
    if OVERRIDES.exists():
        with OVERRIDES.open() as f:
            for r in csv.DictReader(f):
                if r["instrument"] == "UDHR":  # draft_article "3.2": paragraph 2 of draft article 3
                    out[(r["stage"], str(r["draft_article"]))] = (int(r["final_article"]), r["note"])
    return out


def early_meetings() -> tuple[set[str], dict[str, str | None]]:
    """(the stages read by hand, symbol -> the text a 1947-48 meeting worked from; None: no Declaration numbering)."""
    stages = {r["stage"] for r in csv.DictReader(EARLY.open())} if EARLY.exists() else set()
    meetings = {r["symbol"]: r["stage"] or None for r in csv.DictReader(EARLY_MEETINGS.open())} if EARLY_MEETINGS.exists() else {}
    return stages, meetings


def article_titles() -> dict[str, str]:
    with ARTICLES.open() as f:
        return {r["article"]: r["short_title"] for r in csv.DictReader(f) if r["instrument"] == "UDHR"}


def stage_of(symbol: str, opening_text: str, session_key: str | None) -> str | None:
    """The stage whose numbering a document uses."""
    own = next((st for sym, st in STAGE_SYMBOLS if sym == symbol), None)
    if own:
        return own
    text = opening_text
    for rx, rep in OCR_SYMBOL_FIXES:
        text = rx.sub(rep, text)
    hits = [(m.start(), st) for sym, st in STAGE_SYMBOLS for m in re.finditer(re.escape(sym) + r"(?![\d/])", text)]
    if hits:
        return min(hits)[1]
    return SESSION_STAGE.get(session_key or "")


def final_article(stage: str | None, draft: str | None, conc: dict) -> tuple[int | None, str | None]:
    """(final article, how it was mapped) for a draft article number in a stage."""
    art, _, par = str(draft or "").partition(".")
    if not stage or not art.isdigit():
        return None, None
    if stage == "final":
        return int(art), "final numbering"
    hit = (conc.get((stage, f"{int(art)}.{par}")) if par else None) or conc.get((stage, str(int(art))))
    return (hit[0], hit[1]) if hit else (None, None)
