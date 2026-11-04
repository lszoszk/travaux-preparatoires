#!/usr/bin/env python3
"""Build the local SQLite database behind the test frontend.

Reads the segmented records (data/segments/<symbol>.<engine>.json), the UN Library
manifest (body, session, meeting date) and the harvest log (UN PDF URL), and writes
data/travaux.sqlite3 with:
  documents     one row per record
  segments      speeches, chair interventions, votes, headings, in record order
  segments_fts  FTS5 index over text, speaker and delegation

Usage: python3 api/build_db.py [--engine vote]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from articles import early_meetings, final_article, load_concordance, stage_of  # noqa: E402
from decisions import BASE_TEXT_RE, SYMBOL_RE as _SYM, decisions as find_decisions, delegations_named, proposers_of, repair_symbols  # noqa: E402
from amendment_sponsors import sponsors_before  # noqa: E402
from entities import SESSION_OVERRIDES  # noqa: E402
from segment import CHAIR_NOTE_RE, MEETING_NOTE_RE, TOOK_CHAIR_RE, masthead_date  # noqa: E402
from sessions import body_from_symbol, fix_year, sessions_for  # noqa: E402
from dates import repair as repair_dates  # noqa: E402
# eval/jev_procedure_check.py's answers, by speech: the organisation of work, not the article (measured on the judged tags)
JEV_PROCEDURE = Path(__file__).resolve().parents[1] / "data" / "cache" / "jev_procedure_v2.json"
PROCEDURE_THRESHOLD = 0.8
# eval/jev_article_choice.py's answers, by speech: which of the meeting's listed articles an untagged speech is about
JEV_CHOICE = Path(__file__).resolve().parents[1] / "data" / "cache" / "jev_article_choice.json"
CHOICE_THRESHOLD = 0.9
# Schabas's index (eval/schabas_candidates.py, data/concordance/schabas_candidates.csv): the speeches its Table of provisions
# lists for an article and Jev confirms. Off until the preregistered acceptance test passes (docs/devlog.md, 21 Oct 2026):
# until then every row is only a possible article.
SCHABAS_TAGS_LIVE = False
SCHABAS_CSV = Path(__file__).resolve().parents[1] / "data" / "concordance" / "schabas_candidates.csv"
SCHABAS_LOG: dict[str, int] = {"applied": 0, "skipped_procedural": 0, "rejected_by_jev": 0}


def load_schabas() -> tuple[dict[str, dict], dict[str, list[str]]]:
    """(the rows that may tag a speech, the possible articles of the rest, by segment id)."""
    tags, possible = {}, {}
    if not SCHABAS_CSV.exists():
        return tags, possible
    for r in csv.DictReader(SCHABAS_CSV.open()):
        if r["verdict"] == "tag" and SCHABAS_TAGS_LIVE:
            tags[r["segment_id"]] = r
        else:
            possible.setdefault(r["segment_id"], []).append(
                f"{r['instrument']} {r['final_article']} (Schabas index p. {r['book_pages'].replace(' ', ', ')})")
    return tags, possible


def possible_text(sid: str, fin, possible: dict[str, str], schabas_possible: dict[str, list[str]]) -> str | None:
    """A untagged segment's possible articles: the readers' (possible_articles.csv) and Schabas's index, joined."""
    if fin:
        return None
    parts = ([possible[sid]] if possible.get(sid) else []) + schabas_possible.get(sid, [])
    return "; ".join(parts) or None
from topics import THRESHOLD as TOPIC_THRESHOLD, CACHE as TOPIC_CACHE, all_topics  # noqa: E402
from jev_articles import THRESHOLD as JEV_THRESHOLD, THRESHOLD_EARLY as JEV_THRESHOLD_EARLY, key as jev_key, load_cache as load_jev_checks  # noqa: E402

DB = ROOT / "data" / "travaux.sqlite3"
SEG = ROOT / "data" / "segments"

SCHEMA = """
CREATE TABLE documents (
  symbol TEXT PRIMARY KEY, body TEXT, session TEXT, meeting_date TEXT,
  doc_type TEXT, pdf_url TEXT, local_pdf TEXT, n_pages INTEGER, stage TEXT, instrument TEXT,
  source_language TEXT, machine_translated INTEGER DEFAULT 0, translation_model TEXT, translation_check TEXT,
  translation_date TEXT
);
CREATE TABLE segments (
  id TEXT PRIMARY KEY, symbol TEXT, seq INTEGER, kind TEXT,
  page_start INTEGER, page_end INTEGER, n TEXT,
  speaker TEXT, delegation TEXT, speaker_method TEXT, speaker_raw TEXT, country_raw TEXT,
  votes TEXT, review TEXT, article_heading TEXT, vote TEXT, text TEXT,
  final_article INTEGER, article_mapping TEXT, draft_article TEXT, article_instrument TEXT, n_end TEXT,
  article_confidence REAL,
  -- an article a reader of the whole record suggested but that did not pass the checks (pipeline/reader_tags.py):
  -- metadata only, used by no filter or count
  possible_article TEXT
);
CREATE INDEX seg_final ON segments(final_article);
CREATE TABLE refs (segment_id TEXT, ref_symbol TEXT, amendment INTEGER, proposers TEXT);
CREATE TABLE decisions (
  id INTEGER PRIMARY KEY, segment_id TEXT, symbol TEXT, seq INTEGER, stage TEXT, draft_article TEXT,
  final_article INTEGER, subject TEXT, outcome TEXT, yes INTEGER, no INTEGER, abstentions INTEGER,
  unanimous INTEGER, without_vote INTEGER, proposers TEXT, refs TEXT, roll_call TEXT, roll_complete INTEGER,
  article_instrument TEXT
);
CREATE INDEX dec_article ON decisions(final_article);
CREATE INDEX refs_symbol ON refs(ref_symbol);
-- a question of general debate (data/concordance/topics.csv, and "general") for a speech no article tag fits: Jev's choice
-- (pipeline/topics.py) at TOPIC_THRESHOLD or more, unless a blind check refused it (data/concordance/topic_rejections.csv)
CREATE TABLE topics (topic TEXT PRIMARY KEY, label TEXT, description TEXT, articles TEXT);
CREATE TABLE segment_topics (id TEXT PRIMARY KEY, topic TEXT, p REAL);
CREATE INDEX seg_topic ON segment_topics(topic);
CREATE TABLE draft_texts (stage TEXT, stage_symbol TEXT, draft_article INTEGER, final_article INTEGER,
  page INTEGER, text TEXT, instrument TEXT);
CREATE INDEX seg_symbol ON segments(symbol, seq);
CREATE VIRTUAL TABLE segments_fts USING fts5(
  text, speaker, delegation, id UNINDEXED, tokenize='porter unicode61'
);
-- the same text unstemmed: a quoted search ("conception") matches the word itself, not "concept"
CREATE VIRTUAL TABLE segments_fts_exact USING fts5(text, id UNINDEXED, tokenize='unicode61 remove_diacritics 2');
"""


# UN symbols cited in a segment ("E/CN.4/95", "A/C.3/L.874/Rev.2"), with the OCR's usual
# misreading of "CN.4" corrected; bare committee names ("A/C.3") are not documents
# (the OCR also spaces them out: "A/C.3/ 247", "A/C.3 /232", "A /C.3/289 /Rev.1", "A/C. 3/L.656"; fix_symbol closes them up)
REF_RE = re.compile(r"\b((?:A|E) ?/ ?(?:C[NIl1],\s?4 ?/ ?|(?![AE] ?/)[A-Z][A-Z0-9]*(?:\. ?[A-Z0-9]+)* ?/ ?)*(?:(?:[A-Z]+|[lI1](?=\. ?\d{2}))\. ?)?[1-9]\d*(?![\dA-Za-z])(?: ?/ ?(?:Rev|Add|Corr)\. ?\d+)*)")


def fix_symbol(raw: str) -> str:
    """OCR damage in the Commission's series: "E/CN.U/95", "E/CI.4/202", "E/CN,4/L.110", "E/ON.4/L.140", "E/AN.4/L.140";
    and the L-series read with an I: "A/C.3/I.1177"."""
    raw = re.sub(r"\s+", "", raw)
    raw = re.sub(r"^A/C\.3\d/L\.", "A/C.3/L.", raw)  # "A/C.38/L.875": no committee A/C.38
    raw = re.sub(r"^A/C\.L/(?=\d{3,4}\b)", "A/C.3/L.", raw)  # "A/C.L/1373": the 3 read as an L
    raw = re.sub(r"^E/(?:C[NIl1]|[OA]N)[.,]?\s?[4U^hA]/", "E/CN.4/", raw.rstrip("."))  # (also "E/CN4/")
    return re.sub(r"^(A/C\.3|E/CN\.4)/[Il1]\.(?=\d)", r"\1/L.", raw)  # "A/C.3/I.1177", "A/C.3/1.656" are the L-series


# a speaker's own proposal: "introduced his delegation's amendment (A/C.3/L.644)", "the amendment he had submitted"
OWN_PROPOSAL_RE = re.compile(r"\b(?:(?:his|her|its|the)\s+(?:own\s+)?delegation'?s|his|her|its\s+own)\s+(?:joint\s+)?(?:revised\s+)?"
                             r"(?:amendments?|proposals?|sub-amendments?|draft\s+resolution|text)\s*[,(]?\s*$"
                             r"|\b(?:he|she)\s+had\s+(?:just\s+)?(?:submitted|proposed|introduced|tabled)\s*[,(]?\s*$", re.I)


def cited(text: str, own: str, delegation: str | None = None) -> dict[str, tuple[bool, list[str]]]:
    """Documents a passage cites -> (cited as an amendment or proposal, its proposers). The proposers are those the
    words around the symbol name (decisions.proposers_of), else those a list names strictly ("submitted by Chile,
    China and Egypt (E/CN.4/L.333)": pipeline/amendment_sponsors.py), else, in a speech, the speaker's delegation
    when the speaker calls it his own ("his delegation's amendment (...)")."""
    out: dict[str, tuple[bool, list[str]]] = {}
    text = repair_symbols(text)
    prev_end, prev_amend = 0, False
    for m in REF_RE.finditer(text):
        sym = fix_symbol(m.group(1))
        if sym == own or re.fullmatch(r"A/C\.\d|E/CN\.\d", sym):
            continue
        # (this sentence's words before the symbol, up to 260 characters: "amendments submitted ... by the representatives of
        # India (E/CN.4/563/Rev.1), of Yugoslavia (...)")
        window = max(text[max(0, m.start() - 120):m.start()], re.split(r"[.;]\s+(?=[A-Z])", text[max(0, m.start() - 260):m.start()])[-1],
                     key=len) + text[m.start():m.end() + 60]
        amend = "/L." in sym or bool(re.search(r"ame[nu]\w{0,3}ments?|amend\w*|proposal|proposed|submitted|presented|draft resolution", window, re.I))
        # a document that recapitulates the amendments is not one: "were recapitulated in document A/C.3/294/Rev.1"
        if re.search(r"recapitulat\w*\s+in\s+(?:the\s+)?(?:documents?\s+)?$", text[max(0, m.start() - 45):m.start()], re.I):
            amend = False
        # a list of amendments, ", of Yugoslavia (E/CN.4/573), of Egypt (E/CN.4/626) and of the United Kingdom (E/CN.4/628)"
        in_list = bool(prev_end) and re.fullmatch(r"\s*(?:,|and)?\s*(?:of\s+)?(?:the\s+)?[A-Z][\w -]{2,40}?\s*\(?", text[prev_end:m.start()]) is not None
        if in_list and prev_amend:
            amend = True
        who = proposers_of(text, m.start(), m.end())
        if not who:
            opened = text.rfind("(", max(0, m.start() - 3), m.start() + 1)
            who = sponsors_before(text, opened if opened >= 0 else m.start(), prev_end if in_list else 0) or []
        close = text.find(")", m.end(), m.end() + 4)
        prev_end, prev_amend = (close + 1 if close >= 0 else m.end()), amend
        mine = OWN_PROPOSAL_RE.search(text[max(0, m.start() - 80):m.start()]) if not who and delegation else None
        if mine:
            # a bare "his amendment" is another's when the sentence names another delegation's representative first:
            # "He hoped that the Netherlands representative would not press his amendment" (A/C.3/SR.730)
            sentence = re.split(r"[.;]\s+", text[max(0, m.start() - 300):m.start()])[-1]
            other = [d for d in delegations_named(" ".join(re.findall(r"(?:\b[A-Z][\w-]+(?:\s+[A-Z][\w-]+)?\s+(?:representative|delegate|delegation)\b|"
                                                                       r"\brepresentative\s+of\s+(?:the\s+)?[A-Z][\w-]+(?:\s+[A-Z][\w-]+)*)", sentence)))
                     if d != delegation]
            if not (re.match(r"(?:his|her)\s+(?!own\b|delegation)", mine.group(0), re.I) and other):
                who = [delegation]
        old = out.get(sym, (False, []))
        out[sym] = (old[0] or amend, old[1] or who)
    return out


# Sessions whose "article N" is the Declaration's numbering of their stage: checked by
# eval/article_topic_check.py (speeches match their article's text as often as under a
# heading). Before May 1948 the same meetings also took up the draft Covenant, with its own
# numbering, and moved from one text to the next within a session: by session the tags fit only
# a third of the time. Those records are tagged only where data/concordance/udhr_early_meetings.csv
# names the text the meeting worked from (EARLY_MEETINGS), through a concordance read by hand.
VERIFIED_STAGES = {"chr_3", "drafting_committee_2", "a777", "final"}
EARLY_STAGES, EARLY_MEETINGS = early_meetings()


def load_covenant_concordance() -> dict[tuple[str, str, str], int]:
    """(stage, ICCPR|ICESCR, draft number) -> final article: E/2573's numbering, matched by text
    (pipeline/build_covenant_concordance.py), and the Commission's earlier ones, read by hand
    from the drafts' texts (covenant_drafts_chr.csv)."""
    import csv
    out = {}
    for name in ("covenant_drafts.csv", "covenant_drafts_chr.csv", "covenant_drafts_tc.csv"):
        path = ROOT / "data" / "concordance" / name
        if path.exists():
            with path.open() as f:
                for r in csv.DictReader(f):
                    if r["final_article"].isdigit() and r["draft_article"]:
                        out[(r["stage"], r["instrument"], r["draft_article"])] = int(r["final_article"])
                    if r.get("meetings"):
                        # the meetings that discussed the article, where the session's report lists them
                        # (two drafts can have become one final article: their meetings together)
                        key = (r["stage"], "meetings", r["instrument"], r["final_article"])
                        out[key] = out.get(key, set()) | {int(m) for m in r["meetings"].split()}
    return out


# the Commission's drafts before E/2573, by the session that debated them: the fifth (1949)
# worked through the Drafting Committee's draft (E/800), the sixth (1950) through its own (E/1371),
# the eighth (1952) through the seventh's (E/1992), whose part III held the economic, social and
# cultural rights; the ninth (1953) through the measures of implementation of E/2256 (E/1992's numbering);
# the tenth (1954) through the ninth's (E/2447) measures of implementation of those rights
DRAFTING_DECISION_RE = re.compile(r"\b(?:words?|text|wording|paragraph|sub-paragraph|sentence|phrase|amendments?|delet\w*|insert\w*|"
                                  r"replac\w*|substitut\w*|retain\w*|combin\w*|merg\w*|add\w*|drafting|formula|translation)\b", re.I)
# (but the work on a text is not its text: a time-limit for amendments, the order of the votes, the list of speakers; round 88)
ORDERS_WORK_RE = re.compile(r"\btime[\s~=\-]*limit|\bdeadline|\blist\s+of\s+speakers|\b(?:be\s+)?put\s+to\s+the\s+vote\s+first|"
                            r"\bvote\s+(?:first|should\s+(?:not\s+)?be\s+taken|be\s+postponed)|\bfirst\s+vote\s+on\b|\badjourn|\bsuspend|\bpostpon|\bdefer|"
                            r"\b(?:submission|submit\w*)\s+(?:of\s+)?(?:written\s+)?(?:amendments|proposals|draft)|\bin\s+writing\b|"
                            r"\b(?:amendments?|proposals?)\b[^.;]{0,50}\bshould\s+be\s+submitted\s+(?:by|not\s+later\s+than)\b|"
                            r"\bhear\s+(?:a\s+statement\s+by\s+)?the\s+representatives?|\bauthori[sz]e\b|\bcirculated\b|\bno\s+vote\s+should\s+be\s+taken|\bclos(?:ed|ure)\b|"
                            r"\b(?:proceed\s+immediately|start|begin|go\s+on)\s+(?:b[y\w]\s+|to\s+)?(?:the\s+)?(?:consider\w*|discuss\w*|examin\w*)\b|"
                            r"\bdecided\b[^.;]{0,55}\bto\s+consider\s+(?:the\s+additions\s+to\s+)?article\s+\d|"
                            r"\bnot\s+to\s+wait\s+until\s+it\s+had\s+completed|\bre-?open\s+the\s+discussion\b|"
                            r"\breconsider\w*\s+(?:the|its|that|those|these)(?:\s+previous)?\s+decision|\bshould\s+be\s+reconsidered\b|"
                            r"\bset\s+aside\s+for\s+meetings\s+of\b|\bmeet\s+in\s+the\s+Economic\s+and\s+Social\s+Council\s+Chamber\b|"
                            r"\brise\s+the\s+following\s+afternoon\b|\bexpressed\s+her\s+sympathy\b|"
                            r"\bfollow\s+the\s+order\s+indicated\b|\bvoted\s+on\s+(?:last|point\s+by\s+point)\b|"
                            r"\bbefore\s+a\s+vote\s+was\s+taken\b|\bnext\s+meeting\b|"
                            r"\b(?:working\s+(?:group|party))\s+should\s+be\s+composed\s+of\b|\bSub-Committee\b[^.;]{0,30}\bshould\s+meet\s+on\b", re.I)
# a procedural line that is about no article (round 115: 4 of 10 procedural tags right; round 119): an attendance list, a
# decision on the order of work, a member taking the chair, the meeting suspended or risen, a bare "It was so decided" after a
# turn that does not speak of the text
ATTENDANCE_RE = re.compile(r"\b(?:Chairm[ae]n|Chadrman|President|Present|PRESENT)\s*[:;].{0,400}\b(?:Members|Representatives?|Rapporteur)\s*[:;]"
                           r"|^\W*(?:PRESENT|Present)\s*:|^\W*(?:Mrs?[.,]?\s+[A-Z]+\s+[^:\n]{3,40}\s+)?Members\s*:\s*(?:Mr|Mrs|Miss)\b"
                           r"|^\W*Mr\.\s+(?:EVANS|WEISS?)\s+International\s+(?:Labour|Refugee)\s+Organi[sz]ation\b"
                           r"|^\W*United\s+Nations\s+Nations\s+Unies\b", re.S)
SO_DECIDED_RE = re.compile(r"^\W*(?:It\s+was\s+so\s+(?:decided|agreed)|It\s+was\s+agreed|It\s+was\s+decided|"
                           r"The\s+(?:Committee|Commission|Sub-Commission|Working\s+Group)\s+(?:so\s+)?(?:decided|agreed))\b", re.I)


def procedural_off_article(text: str, before: str) -> bool:
    t = text.strip()
    if len(t) <= 3 or ATTENDANCE_RE.search(t[:600]) or ORDERS_WORK_RE.search(t):
        return True
    if len(t) < 200 and (TOOK_CHAIR_RE.match(t) or CHAIR_NOTE_RE.search(t[:200]) or MEETING_NOTE_RE.match(t)):
        return True
    t_core = re.split(r"\s+(?:AGENDA\s+ITEM|DRAFT\s+INTERNATIONAL\s+COVENANT)", t)[0].strip()
    return len(t_core) < 80 and bool(SO_DECIDED_RE.match(t_core)) and not (DRAFTING_DECISION_RE.search(before[-600:]) and not ORDERS_WORK_RE.search(before[-600:]))


ITEM_TITLE_RE = re.compile(r"covenant\W+(?:\w+\W+){0,4}?and[\W_]+measures[\W_]+(?:\w+[\W_]+)?of[\W_]+implementation", re.I)
CONTENTS_HEAD_RE = re.compile(r"\bCONT[EA]NTS|\bCOMMENTS\s*[:;]")
CONTENTS_FIRST_ARTICLE_RE = re.compile(r"\bArt[a-z1]{3,6}\s+\W{0,2}(\d{1,2})\b", re.I)  # ("Article", "Articles", "Axvticle “10")
CONTENTS_FIRST_ITEM_RE = re.compile(r"[({]\s*(?:1|i|l|a)\s*\)\s*(?!Art)\w")  # a first item that is no article
NEW_ARTICLE_ITEM_RE = re.compile(r"[({]\s*(?:[a-z]|[ivxl1]{1,4}|\d{1,2})\s*\)\s+(?:Proposed\s+|Additional\s+|New\s+)+articles?\b(?![^()]*\bArticle\s+\d)", re.I)
CONTINUED_AGENDA_RE = re.compile(r"\bArt[il1]c[l1]es?\s+(\d{1,2})\s*[\"'“”]?\s*\((?:discussion\s+)?cont[il1]nued\)", re.I)
CHR_STAGES = {5: "chr5", 6: "chr6", 7: "chr7", 8: "chr8", 9: "chr9", 10: "chr10"}
STAGE_SYMBOL = {"chr5": "E/800", "chr6": "E/1371", "chr7": "E/1992", "chr8": "E/1992", "chr9": "E/2256", "chr10": "E/2447",
                # the Geneva draft Covenant, which the Drafting Committee took up first in May 1948 (records of the UDHR
                # corpus, staged by data/concordance/udhr_early_meetings.csv)
                "e600": "E/600",
                # the Geneva working group's draft Convention, debated with the Declaration in the plenary (December 1947)
                "e_cn4_56": "E/CN.4/56",
                # the Third Committee 1955-63 and 1966: E/2573's numbering, with the meetings its reports
                # (A/3077 ... A/5000, A/5365, A/5655, A/6546) list for each article
                **{f"tc{y}": "E/2573" for y in range(1955, 1964)}, "tc1966": "E/2573 (A/6342)"}
# the Third Committee's sessions whose reports give each article's meetings (covenant_drafts_tc.csv)
TC_SESSIONS = {**{n: f"tc{1945 + n}" for n in range(10, 17)}, 17: "tc1962", 18: "tc1963", 21: "tc1966"}
TC_STAGES = set(TC_SESSIONS.values())
# a Geneva plenary meeting (E/CN.4/SR.34-42) took up both working groups' texts, often a Declaration article with
# the corresponding Convention article: each passage is numbered by the text the record names for it
TWO_TEXT_STAGES = {"geneva_plenary": ("e_cn4_57", "e_cn4_56")}
# the run-in headings of those records: "Declaration Article 10 Paragraph 3 and Convention Article 6",
# "Declaration Article 18 and Resolution 2 of the Convention Report", "Convention Article 11"
# which text an article mention in those records belongs to: "Article 9 of Declaration", "Articles 21 and 22 of the
# Declaration", "paragraph 3 of Article 10 of the Declaration" (after it), "Convention Article 11" (before it)
MENTION_OF_RE = re.compile(r"^\W{0,3}(?:(?:,|and|or|to)\s*\d{1,2}\s*)*(?:\([^)]{0,20}\)\s*)?,?\s*of\s+(?:the\s+)?(?:draft\s+)?"
                           r"(Declaration|Convention|Covenant)", re.I)
MENTION_AFTER_RE = re.compile(r"\b(Declaration|Convention)\W{0,3}$", re.I)


# the nearest cue before a mention in the same clause: "the Declaration (E/CN.4/57) - Article 1"
MENTION_CUE_RE = re.compile(r"(Declaration|E/CN\.?\s?4/57|Convention|Covenant|E/CN\.?\s?4/56)", re.I)


def mention_text(text: str, end: int) -> str | None:
    """"declaration" or "covenant" for the article mention ending at end, if the record says which."""
    m = MENTION_OF_RE.match(text[end:end + 60])
    if not m:
        start = [x.start() for x in re.finditer(r"\barticles?\W{0,3}\d", text[:end], re.I)]
        m = MENTION_AFTER_RE.search(text[max(0, start[-1] - 20):start[-1]]) if start else None
        if not m and start:
            cues = list(MENTION_CUE_RE.finditer(text[max(0, start[-1] - 45):start[-1]]))
            m = cues[-1] if cues else None
    if not m:
        return None
    return "declaration" if re.match(r"declaration|e/cn\.?\s?4/57", m.group(1), re.I) else "covenant"


# a heading run into the end of a passage (any kind, speeches too): a short verbless tail that opens with it,
# "... adopted by sixteen votes. 4. Article 4 of the Convention.", "2. Declaration on Human Rights (Document
# E/CN.4/57) - Article 1.", "Declaration Article 18 and Resolution 2 of the Convention Report"
TAIL_START_RE = re.compile(r"^(?:\d{1,2}\.\s*|page\s+\w+\s+|\W+)*(?:(?:examination|discussion|consideration)\s+of\s+)?"
                           r"(?:(?:the\s+)?(?:draft\s+)?(?:Declaration|Convention|Covenant)\b|Articles?\W{0,3}\d|"
                           r"(?:draft\s+)?(?:Resolution|Recommendation)s?\b)", re.I)
TAIL_VERB_RE = re.compile(r"\b(?:said|was|were|is|are|had|has|have|would|should|could|shall|proposed|pointed|put|stated|thought|"
                          r"considered|felt|asked|agreed|explained|suggested|moved|declared|opened|read|called|adopted|"
                          r"rejected|supported|accepted|referred|applied|dealt|contained|covered)\b", re.I)
RESOLUTION_RE = re.compile(r"\b(?:draft\s+)?(?:resolution|recommendation)s?\b", re.I)


def tail_heading(text: str) -> tuple[int, str] | None:
    """(start, heading) of a heading run into the end of a passage, if there is one."""
    t = text.rstrip(" .;:-|*")
    cut = max((m.end() for m in re.finditer(r"[.;:!?]\s+", t)), default=0)
    tail = t[cut:]
    # after an agenda item's number ("page 9 2. ...") the heading may be damaged by the OCR at its start
    item = re.search(r"\b\d{1,2}\.\s+$", t[:cut]) and re.search(r"\bof\s+the\s+(?:draft\s+)?(?:Declaration|Convention)\b", tail, re.I)
    if not tail or len(tail.split()) > 25 or TAIL_VERB_RE.search(tail) or not (TAIL_START_RE.match(tail) or item):
        return None
    if not re.search(r"\barticles?\W{0,3}\d", tail, re.I) and not RESOLUTION_RE.search(tail):
        return None
    return cut, tail


# The Third Committee's printed records of 1948 (A/C.3/SR.88-179) run an article's heading into the passage before
# it ("... by the end of the month. ARTICLE 201") and print a footnote marker after its number, which the OCR reads
# as a last digit ("ARTICLE 71" is article 7) or as a sign ("ARTICLE 16}"). A heading in capitals (or small capitals
# read in mixed case, "ArticLe 18", or misread, "Articte 3"), not the prose "Article 28, as amended, was adopted".
RUNIN_1948_RE = re.compile(r"(?:(?<=[.;:!?,)”’\"\\|_])|^)\s*[_\\|“\"‘']*\s*(?P<w>[A-Za-z]{7})\s+(?P<n>\d{1,3})(?P<mark>\s*[}*!¹²³])?(?![\d,])"
                           r"(?P<cont>\s*\(\s*(?:continued|suite)\s*\))?(?P<rest>.{0,12})", re.S)


def runin_headings_1948(text: str) -> list[tuple[int, str, bool, bool]]:
    """(start, number as printed, footnote sign seen, "(continued)") of each article heading in a passage."""
    out = []
    for m in RUNIN_1948_RE.finditer(text):
        w = m.group("w")
        if w.lower() not in ("article", "articte", "axticte") or (w.lower() == "article" and sum(c.isupper() for c in w) < 2
                                                                 and not m.group("cont")):
            continue
        # a heading ends its passage, or carries a footnote's digit, "(continued)" or its subject ("ARTICLE 21: REPORT OF ...")
        if len(m.group("n")) == 3 or m.group("cont") or re.fullmatch(r"\W*", text[m.end("n") + len(m.group("mark") or ""):]) \
                or re.match(r"\s*:\s*REPORT\b", m.group("rest"), re.I):
            out.append((m.start("w"), m.group("n"), bool(m.group("mark")), bool(m.group("cont"))))
    return out


def unglue_1948(raw: str, marked: bool, continued: bool, prev: int | None) -> int | None:
    """The article a 1948 heading gives, its footnote's digit taken off. The Committee took E/800's 28 articles in
    order: a two-digit number that does not follow the last heading (prev) and whose first digit does is article
    and footnote ("ARTICLE 21" after article 1 is article 2; "ARTICLE 25" after article 24 is article 25)."""
    n = int(raw)
    if len(raw) == 3:
        return int(raw[:2]) if int(raw[:2]) <= 28 else None
    if len(raw) == 1 or marked or continued:
        return n if n <= 28 else None
    p = prev or 0
    if n <= 28 and 0 <= n - p <= 2:
        return n
    if 0 <= int(raw[0]) - p <= 2 or n > 28:
        return int(raw[0])
    return n


# The reports of the Commission (1949-54) and the Third Committee (1955-66) on the draft covenants: each section of
# their numbered paragraphs, read by hand, with the final article it is about (data/concordance/report_sections.csv).
# The reports' own headings are often lost to the OCR or run on into the next section, and their numbering is that of
# the text the session worked from. A report's annexes (the texts, the governments' comments) are not tagged.
REPORT_SECTIONS = ROOT / "data" / "concordance" / "report_sections.csv"
ANNEX_RE = re.compile(r"^\W*ANNEX(?:ES)?\b")


def load_report_sections() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    if REPORT_SECTIONS.exists():
        for r in csv.DictReader(REPORT_SECTIONS.open()):
            out.setdefault(r["symbol"], []).append({**r, "para_first": int(r["para_first"]), "para_last": int(r["para_last"]),
                                                     "final": int(r["final_article"]) if r["final_article"].isdigit() else None})
    return out


# The drafts and amendments of the Third Committee and the Commission (A/C.3/L.n, E/CN.4/L.n): the article each concerns,
# from its text and the debates that cite it, decided by two independent readers (pipeline/l_series_articles.py;
# data/concordance/l_series_articles.csv). Its Rev, Add and Corr versions go with the base document.
L_ARTICLES = ROOT / "data" / "concordance" / "l_series_articles.csv"
L_BASE_RE = re.compile(r"(?:/(?:Rev|Add|Corr)\.\d+)+$", re.I)


def load_l_articles() -> dict[str, dict]:
    if not L_ARTICLES.exists():
        return {}
    return {r["base"].upper(): r for r in csv.DictReader(L_ARTICLES.open()) if r["final_article"].isdigit()}


# a symbol the OCR misread in one passage only ("E/CN.4/L.145" for L.143 at E/CN.4/SR.319, where L.145 is a real document
# cited correctly elsewhere): (segment, symbol read) -> symbol, read from the scan
REF_FIXES = {(r["segment_id"], r["ocr_symbol"]): r["correct_symbol"]
             for r in csv.DictReader((ROOT / "data" / "concordance" / "ref_fixes.csv").open())}
# the proposers of a decision, read by hand where the words mislead the parser (an oral sub-amendment accepted by
# the sponsors of the text): segment, words of the subject -> proposers
DECISION_PROPOSERS = [r for r in csv.DictReader((ROOT / "data" / "concordance" / "decision_proposers_checked.csv").open())]
REPORT_ANNEXES = ROOT / "data" / "concordance" / "report_annex_sections.csv"
BARE_PART_RE = re.compile(r"^\W*PART\s+[IVXLlT1]{1,4}(?:\s+[IVXl1T]{1,2})?(?:\s+\d{1,3})?\W*$", re.I)
ANNEX_LOG: list[tuple[str, int, str]] = []  # annex anchors not found


def load_report_annexes() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    if REPORT_ANNEXES.exists():
        for r in csv.DictReader(REPORT_ANNEXES.open()):
            out.setdefault(r["symbol"], []).append({**r, "page": int(r["page"]),
                                                     "final": int(r["final_article"]) if r["final_article"].isdigit() else None})
    return out


def _flat(text: str) -> str:
    return " ".join(text.split())


# a running head that opens an annex row's anchor ("Page 20 'Art 21 Every one ...", read before the segmenter dropped
# running heads from the text): the anchor is matched without it
ANCHOR_PAGE_RE = re.compile(r"\b(?:[PpFf]a[gsc]e|[Pp]ara)\s*[\dOoIlh^|]{1,3}\b[\s|;]*")  # and one inside it ("Text adopted. page 7 ARTICLE 8")
ANCHOR_HEAD_RE = re.compile(r"^[\W_]*(?:[A-Za-z0-9]{1,3}\s?/[\w.,'/ \-^•]{2,22}[:,.;]?\s*)?(?:English\s+|French\s+)?(?:[PpFf]a[gsc]e|[Pp]ara)\s*[\dOoIlh^|]{1,3}[\s.:;|°,\-]*(?=\S)")


def anchor_starts(segs: list[dict], annex: list[dict]) -> tuple[dict[int, dict], list[dict]]:
    """{segment index: annex row} for the segments that open the annexes' sections, and the rows whose anchor was not found.
    The anchors are looked for in order, each within the segment's first words (a re-segmentation can join a heading to the
    section's first line), as they were copied from the OCR. Only when that misses one (the anchors were copied from the
    OCR, and a cleaner reading of the page, the vision reader's, differs in case, stops and misread letters: "Article 8 ."
    where it reads "Article 8") is the report anchored again with a close match at the segment's start, and an anchor not
    found does not hold up the next two."""
    from rapidfuzz import fuzz

    def exact(x, row) -> bool:
        # (in a footnote set apart, anywhere: the anchor can be a note's second line, "365, E/CN.4/415 and Corr.1, ...")
        at = _flat(x["text"]).find(_flat(ANCHOR_PAGE_RE.sub("", ANCHOR_HEAD_RE.sub("", row["anchor"])))[:40])
        return abs(x["page_start"] - row["page"]) <= 1 and (0 <= at <= 40 or x["kind"] == "footnote" and at >= 0)

    def close(x, row) -> bool:
        if exact(x, row):
            return True
        key = lambda t: " ".join(re.sub(r"\W+", " ", t.lower()).split())
        a = key(_flat(ANCHOR_PAGE_RE.sub("", ANCHOR_HEAD_RE.sub("", row["anchor"])))[:40])
        t = key(x["text"])
        return abs(x["page_start"] - row["page"]) <= 1 and len(a) >= 8 and (
            t.startswith(a) or len(a) >= 12 and fuzz.partial_ratio(a, t[:len(a) + 40]) >= 88)

    starts, k = {}, 0
    for i, x in enumerate(segs):
        if k < len(annex) and exact(x, annex[k]):
            starts[i], k = annex[k], k + 1
    if k == len(annex):
        return starts, []
    starts, k, missed = {}, 0, []
    for i, x in enumerate(segs):
        hit = next((j for j in range(k, min(k + 3, len(annex))) if close(x, annex[j])), None)
        if hit is not None:
            missed += annex[k:hit]
            starts[i], k = annex[hit], hit + 1
    return starts, missed + annex[k:]


def report_tags(symbol: str, segs: list[dict], rows: list[dict], annex: list[dict] | None = None) -> None:
    """Each segment of a report's body gets its section's article (or none): the paragraph in force is the last
    printed number that follows on (quotations and sub-items have none, and their own "1.", "2." do not follow on).
    A heading ends a section: an article's heading ("ARTICLE 9") opens the next section when that is the article's
    (its first paragraph's number may be misread: "52." for 32.); any other heading ("B. The applicability of ...")
    leaves what follows untagged until the next paragraph number."""
    cur, body, closed = 0, True, False
    starts, missed = anchor_starts(segs, annex or [])
    ANNEX_LOG.extend((symbol, r["page"], r["anchor"]) for r in missed)
    arow = None

    for i, x in enumerate(segs):
        if cur and ANNEX_RE.match(x["text"]):
            body = False
        # the annexes (data/concordance/report_annex_sections.csv): a section starts at the segment its anchor names
        if i in starts:
            body, arow = False, starts[i]
        # a footnote set apart from the text where it stood (pipeline/segment.py, round 83) can be an anchor, but is in no section
        if x["kind"] == "footnote":
            x["_fixed"], x["_art"] = (None, None, None), None
            continue
        if arow:
            x["_fixed"] = ((arow["final"], f"{symbol}, annex (p. {arow['page']}): {arow['note']} (the report's annexes, read by hand)",
                            arow["instrument"]) if arow["final"] else (None, None, None))
            x["_art"] = (arow["draft_article"] or None) if arow["final"] else None
            if not re.search(r"/(?:SR|PV)\.", symbol):  # (a meeting record's rows keep each speech's speaker)
                x["delegation"] = arow["author"] or None  # the author of the amendment or comment, not a heading misread
            continue
        # (a number the segmenter left on a line of its own, "5.", is the next paragraph's; the first number read can
        # come late when the OCR garbled the first paragraphs')
        bare = re.fullmatch(r"\s*(\d{1,3})\.\s*", x["text"])
        n = str(x.get("n") or (bare.group(1) if bare else ""))
        heading = x["kind"] == "heading" or (len(x["text"]) < 250 and not n and re.match(r"\s*(?:[A-H]|[IVX]{1,4})\.\s+[A-Z]", x["text"]))
        if body and n.isdigit() and cur < int(n) <= cur + (15 if not cur else 5):
            cur, closed = int(n), False
        elif body and cur and heading:
            art = re.match(r"\W*ART[I1l]CLE\s+(\d{1,2})\b", x["text"], re.I)
            nxt = next((r for r in rows if r["para_first"] > cur), None)
            if art and nxt and re.match(rf"{art.group(1)}\b", nxt["draft_article"]):
                cur, closed = nxt["para_first"], False
            else:
                closed = True
        row = next((r for r in rows if r["para_first"] <= cur <= r["para_last"]), None) if body and cur and not closed else None
        if row and row["final"]:
            x["_fixed"] = (row["final"], f"{symbol}, paras. {row['para_first']}-{row['para_last']}: {row['note']} "
                                         f"(the report's sections, read by hand)", row["instrument"])
            x["_art"] = row["draft_article"] or None
        else:
            x["_fixed"] = (None, None, None)
    # a bare part heading ("PART III") opens a part, whatever section the paragraph before it was in (round 66)
    for x in segs:
        if len(x["text"]) <= 20 and BARE_PART_RE.match(x["text"]):
            x["_fixed"], x["_art"] = (None, None, None), None


def headings_1948(records: dict[int, list[dict]]) -> dict[str, dict[int, tuple[int, int | None]]]:
    """For each 1948 printed record (by meeting number), its segments' article headings: {symbol: {seq: (start,
    article)}}, the footnote digits taken off in the order of the meetings (a heading follows the one before it)."""
    out, prev = {}, None
    for n in sorted(records):
        for s in records[n]:
            if s["kind"] == "heading" and s.get("article_heading"):
                raw = s["article_heading"].translate(OCR_DIGITS)
                if not raw.isdigit():
                    continue
                heads = [(0, raw, bool(re.search(r"\d\s*[}*!¹²³]", s["text"])), bool(re.search(r"\((?:continued|cont|suite)", s["text"], re.I)))]
            else:
                heads = runin_headings_1948(s["text"])
            for start, raw, marked, cont in heads:
                art = unglue_1948(raw, marked, cont, prev)
                if art:
                    out.setdefault(s["symbol"], {})[s["seq"]] = (start, art)
                    prev = art
    return out


PAIR_GAP_RE = re.compile(r"\W*(?:(?:and|,)\s*\d{1,2}\s*)*(?:\W*paragraph\s+\d\W*)?(?:of\s+(?:the\s+)?(?:draft\s+)?(?:Declaration|Convention)\b)?"
                         r"\W*and\W+(?:the\s+)?(?:draft\s+)?(?:Declaration|Convention)?\W*", re.I)


def paired(text: str, named: list[tuple[str, int]]) -> tuple[str, int, str | None] | None:
    """The Declaration mention of the last Declaration/Convention pair named together ("Article 8 of the
    Declaration and Articles 8 and 9 of the Convention"), with its end offset; None if there is none."""
    whose = [(n, e, mention_text(text, e)) for n, e in named]

    def joined(a, b) -> bool:  # "Article 9 of Declaration and Article 12 of the Convention": nothing else between
        start = [m.start() for m in re.finditer(r"\barticles?\W{0,3}\d", text[:b[1]], re.I)][-1]
        return bool(PAIR_GAP_RE.fullmatch(text[a[1]:start]))
    pairs = [(a, b) for a, b in zip(whose, whose[1:]) if {a[2], b[2]} == {"declaration", "covenant"} and joined(a, b)]
    if not pairs:
        return None
    a, b = pairs[-1]
    return a if a[2] == "declaration" else b


def pair_convention(text: str, named: list[tuple[str, int]]) -> list[str]:
    """The Convention articles of that pair: "Articles 8 and 9 of the Convention" is 8 and 9."""
    whose = [(n, e, mention_text(text, e)) for n, e in named]
    d = paired(text, named)
    first = next(((n, e) for n, e, w in whose if w == "covenant" and abs(e - d[1]) < 90), None) if d else None
    if not first:
        return []
    more = re.match(r"(?:\s*(?:,|and)\s*\d{1,2})*", text[first[1]:]).group(0)
    return [first[0].split(".")[0]] + re.findall(r"\d{1,2}", more)


def heading_context(heading: str, instrument: str) -> tuple[str | None, str | None, str | None]:
    """(instrument, article, the pair's Convention article) a run-in heading opens: a pair by its
    Declaration article; a resolution or recommendation: none."""
    heading = re.sub(r"(?<=\d)[*^](?=\d)", "", heading)  # "Article 1*4" is 14
    heading = re.sub(r"\b(articles?)(?=\d)", r"\1 ", heading, flags=re.I)  # "Article2 of Convention"
    # a damaged pair heading ("2. ick s to 6 of the Draft Declaration ... and Article 19 of the Draft Convention"):
    # the number before "of the Draft Declaration" stands for the Declaration's article
    heading = re.sub(r"(?<!\barticle )(?<!\barticles )\b(\d{1,2})(\s+of\s+the\s+(?:draft\s+)?Declaration)", r"Article \1\2", heading, flags=re.I)
    named = article_mentions(heading, instrument, "both")
    if not named:
        return ("other", None, []) if RESOLUTION_RE.search(heading) else (None, None, [])
    d = paired(heading, named)
    if d:
        return "declaration", d[0], pair_convention(heading, named)
    n, e = named[0]
    return mention_text(heading, e), n, []


RUNIN_RE = re.compile(r"\b(Declaration|Convention)\s+Articles?\W{0,3}(\d{1,2})\b(?:\W{0,3}Par\w*\W{0,3}(\d)\b)?", re.I)
# the seventh (1951) drafted the economic, social and cultural articles from texts numbered as the Secretariat
# and the delegations numbered them: only whole meetings are tagged, from the report's meeting lists
MEETING_ONLY = {"chr7"}


def covenant_stage(body: str | None, date: str | None, session: str | None = None) -> str | None:
    """The numbering a Covenant record uses: the Third Committee worked through the
    Commission's 1954 drafts (E/2573) from its ninth session (autumn 1954) to 1966 (the sessions
    whose reports list each article's meetings: TC_SESSIONS); the Commission's sessions of 1949-54
    through the drafts of CHR_STAGES."""
    m = re.match(r"(\d+)", session or "")
    if body == "Commission on Human Rights" and m:
        return CHR_STAGES.get(int(m.group(1)))
    # the Third Committee's sessions of 1962, 1963 and 1966 (the general provisions, the measures of implementation,
    # the final clauses), still in E/2573's numbering: their reports list each article's meetings
    if body == "General Assembly Third Committee" and m and int(m.group(1)) in TC_SESSIONS:
        return TC_SESSIONS[int(m.group(1))]
    if body and body.startswith("General Assembly") and date and date >= "1954-09-01":
        return "e2573"
    # no date read: the session (from the meetings around it) tells; the ninth opened in September 1954
    if body and body.startswith("General Assembly") and not date and m and int(m.group(1)) >= 9:
        return "e2573"
    return None


BOTH = "ICCPR+ICESCR"


def covenant_article(stage: str | None, instr: str | None, draft: str | None, conc: dict,
                     meeting: int | None = None) -> tuple[int | None, str | None, str | None]:
    """(final article, how, instrument tag) for a draft article under discussion. Parts I and
    II (articles 1-5) were debated for both covenants at once ("article 1 of the draft
    covenants"): tagged for both where both drafts map to the same final number."""
    if stage and stage != "e2573":
        # "paragraph 1 of article 33" is article 33's: the Commission's drafts (1949-54, under their reports' meeting
        # lists) and the Third Committee's of 1962-66
        draft = whole_article(draft)
    if not stage or not draft or not str(draft).isdigit():
        return None, None, None
    n = str(int(draft))
    if stage != "e2573":
        # the Commission's single draft covenant (1949-52), numbered through: a number is one covenant's
        # article; the measures of implementation and the Declaration had their own numbers (not in 1966,
        # when the Third Committee took up the implementation articles of E/2573)
        if instr in ("declaration", "other") or instr == "implementation" and stage not in TC_STAGES:
            return None, None, None
        found = []
        for inst in ("ICCPR", "ICESCR"):
            fin = conc.get((stage, inst, n))
            if not fin or instr in ("iccpr", "icescr") and instr != inst.lower():
                continue
            # not at a meeting the report says discussed the article: a stale or passing number
            if meeting and meeting not in conc.get((stage, "meetings", inst, str(fin)), {meeting}):
                continue
            found.append((fin, inst))
        # the same number in both covenants at this meeting: the general provisions the Third Committee adopted in
        # identical terms for both (1962: articles 3 and 5) are the two at once; other numbers cannot be told apart
        if stage in TC_STAGES and len(found) == 2 and conc.get((stage, BOTH, n)) and instr not in ("iccpr", "icescr"):
            return found[0][0], f"{STAGE_SYMBOL[stage]} draft article {n} of both draft covenants", BOTH
        if len(found) != 1:
            return None, None, None
        fin, inst = found[0]
        return fin, f"{STAGE_SYMBOL[stage]} draft article {n} (concordance read from the UN text)", inst
    if instr in ("iccpr", "icescr"):
        fin = conc.get(("e2573", instr.upper(), n))
        return (fin, f"E/2573 draft article {n} of the {instr.upper()} draft (concordance from A/2929)", instr.upper()) \
            if fin else (None, None, None)
    both = [conc.get(("e2573", i, n)) for i in ("ICCPR", "ICESCR")]
    if instr == "both" and int(n) <= 5 and both[0] and both[0] == both[1]:
        return both[0], f"E/2573 draft article {n} of both draft covenants (concordance from A/2929)", BOTH
    return None, None, None


def two_text_article(stage: str, instr: str | None, draft: str | None, conc: dict,
                     cov_conc: dict) -> tuple[int | None, str | None, str | None]:
    """A passage of a meeting on both texts: numbered by the Declaration's or the Convention's text,
    as the record names it; a passage the record does not place gets no article."""
    decl, conv = TWO_TEXT_STAGES[stage]
    if instr == "declaration":
        fin, how = final_article(decl, draft, conc)
        return (fin, how, "UDHR") if fin else (None, None, None)
    if instr == "covenant":
        return covenant_article(conv, "covenant", whole_article(draft), cov_conc)
    return None, None, None


# 1966: draft article 26 of the ICESCR held both who may become a party and the number of ratifications for entry into
# force; the Committee made the second a separate article (26 bis, final 27). A speech that opens on the number of
# ratifications (not on participation) and dwells on it more is about article 27
ENTRY_FORCE_RE = re.compile(r"entry\s+into\s+force|(?:enter|come|came)\s+into\s+force|number\s+of\s+(?:ratifications|instruments|States|"
                            r"accessions|acceptances)|(?:twenty|thirty|thirty-five|forty|fifty|35|20|50)\s+(?:ratifications|instruments|States|"
                            r"accessions)|L\.\s?1367|26\s+bis|figure\s+of\s+(?:twenty|thirty|fifty)", re.I)
PARTICIPATION_RE = re.compile(r"\ball\s+States\b|participation|Vienna\s+formula|specialized\s+agenc|Member\s+States|universal|eligib|"
                              r"L\.\s?1359|L\.\s?1352|which\s+States|become\s+part(?:y|ies)|paragraph\s+1\b|Ukrainian|"
                              r"United\s+Kingdom\s+(?:amendment|proposal|text|formula)|signature", re.I)


def stage_1966_entry(s: dict, fin: int | None, art_instr: str | None) -> bool:
    if s.get("_stage") != "tc1966" or s["kind"] != "speech" or fin != 26 or art_instr != "ICESCR":
        return False
    t, opening = s["text"], s["text"][:450]
    e, p = len(ENTRY_FORCE_RE.findall(t)), len(PARTICIPATION_RE.findall(t))
    return e >= p and bool(ENTRY_FORCE_RE.search(opening) and not PARTICIPATION_RE.search(opening) or e >= 2 and not p)


def whole_article(draft: str | None) -> str | None:
    """"8.3" (paragraph 3 of article 8) is article 8, for the 1947-48 Covenant texts, whose paragraphs all stayed in one article."""
    return str(draft).split(".")[0] if draft else draft


def tags_udhr(stage: str | None, instr: str | None) -> bool:
    # a heading naming the Declaration is not enough in the earlier sessions: the plausibility
    # check found those tags right about a third of the time (their numbering is not settled)
    return (stage in VERIFIED_STAGES or stage in EARLY_STAGES) and instr in (None, "declaration")


OCR_DIGITS = str.maketrans("IlOkh^$", "1104445")


# "article 5" of something else: the Charter, the rules of procedure, a constitution, the other instrument,
# another delegation's declaration (1947: "Article 8 of the Declaration submitted by Panama")
# the second reading's headings: "Article 13 (former article 16) (E/CN.4/L.10, page 27)": its number, the first reading's
SECOND_READING_NUMBERS_RE = re.compile(r"^\W*Art\w{3,6}\s+(?P<new>[\dIlkh]{1,2})\s*\(\s*f\w{3,6}\s+art\w{3,6}\W{0,3}\s*(?P<old>[\dIlkh]{1,2})\s*\)", re.I)


def second_reading_agrees(new: str, old: str, cov_conc: dict) -> bool:
    """A "former article" heading is read only when its numbers agree: the second reading's article (E/1681's numbering, from
    the hand-cut texts) and the first reading's (E/1371's) go to the same final article. The OCR misreads digits
    ("Article 6 (fomany article 2)": article 9, E/CN.4/SR.199)."""
    global E1681_FINALS
    if E1681_FINALS is None:
        anchors = json.loads((ROOT / "data" / "concordance" / "draft_text_anchors.json").read_text())["anchors"]
        E1681_FINALS = {}
        for a in anchors:
            if a["stage"] == "e1681" and a.get("final"):
                E1681_FINALS.setdefault(str(a["draft_article"]), set()).add((a.get("instrument", "ICCPR"), int(a["final"])))
        for a in anchors:  # (also_final: an article that split)
            if a["stage"] == "e1681":
                for f in a.get("also_final", []):
                    E1681_FINALS.setdefault(str(a["draft_article"]), set()).add((a.get("instrument", "ICCPR"), int(f)))
    n, o = new.translate(OCR_DIGITS).lstrip("0"), old.translate(OCR_DIGITS).lstrip("0")
    old_final = {(i, cov_conc.get(("chr6", i, o))) for i in ("ICCPR", "ICESCR")} - {(i, None) for i in ("ICCPR", "ICESCR")}
    return bool(E1681_FINALS.get(n, set()) & old_final)


E1681_FINALS: dict | None = None
OTHER_TEXT_RE = re.compile(r"^(?:\s*(?:,|and|or|to)\s*\d{1,2})*\s*(?:\([^)]{0,20}\)\s*)?,?\s*(?:and\s+\d{1,2}\s+)?(?:paragraph\s+\d{1,2}\s*,?\s*)?of\s+(?:the\s+)?"
                           r"(?:United\s+Nations\s+)?(?:Charter|rules?|Constitution|Statute|(?:[\w-]+\s+){1,3}Constitution|"
                           r"Convention|{other})", re.I)
# the 1947-48 records also cite the other delegations' declarations: "Article 8 of the Declaration submitted
# by Panama", "Article 15 of the draft submitted by the Delegation of Panama", "(Article 7 of its Declaration)"
OTHER_DECLARATION = (r"(?:[\w.-]+\s+){0,2}Declarations?\s+(?:submitted|proposed|presented|prepared)\s+by|"
                     r"(?:draft|text|proposals?)\s+(?:submitted|proposed|presented|prepared)\s+by\s+(?:the\s+)?(?:delegations?|representatives?|governments?)\b|"
                     r"its\s+(?:own\s+)?(?:draft|declaration|text|proposals?)\b|Panam\w*\s+(?:draft|text|declaration|proposal)")
# ... or "in" one: "given at the end of Article 10 in its draft Declaration"
IN_OTHER_DECLARATION_RE = re.compile(r"\s*,?\s*in\s+(?:its|their)\s+(?:own\s+)?(?:draft\s+)?(?:declaration|text|proposals?|draft)\b", re.I)
# "article 13" named as where something else belongs, not as the article taken up: "it was covered by
# Article 13", "had been included in the amended text of Article 29", "corresponded with Article 7"
# "the amendment it had submitted to article 26", "amendments to paragraph 2 of article 7": the article amended
AMENDMENT_TO_RE = re.compile(r"\bamendments?\b[^.;]{0,60}\bto\s+(?:the\s+)?(?:draft\s+)?(?:paragraph\s+\d\s+of\s+)?articles?\s+\d{1,2}\s*$", re.I)
REFERENCE_RE = re.compile(r"\b(?:covered|dealt\s+with|provided\s+for|included|contained|embodied|set\s+forth|laid\s+down|mentioned|referred\s+to|"
                          r"formulated|stated|expressed|proclaimed|enunciated|defined)\s+"
                          r"(?:by|in|under)\s+(?:the\s+)?(?:[\w-]+\s+){0,5}$|\bcorrespond\w*\s+(?:with|to)\s+(?:the\s+)?$|"
                          # "a decision could be postponed until the final wording of Article 4 had been agreed upon"
                          r"\buntil\s+(?:the\s+)?(?:[\w-]+\s+){0,3}$|"
                          # "they were unnecessary in view of the provisions of article 2" (the chair on article 14, E/CN.4/SR.61; round 97)
                          r"\bin\s+(?:view|the\s+light)\s+of\s+(?:the\s+)?(?:provisions?\s+of\s+)?(?:the\s+)?$|"
                          r"\b(?:had\s+been|was)\s+done\s+in\s+(?:the\s+)?(?:[\w-]+\s+){0,4}$|"
                          # "the article ... contained in document E/CN.4/82/Add.8 as article 28": that document's number
                          r"(?:\bdocument\s+\S+(?:\s\S+)?|\b[AE]/[\w./]+)\)?\s+as\s+$", re.I)


ASIDE_RE = re.compile(r"(?:\b(?:when|until|once|before|after)\s+(?:it\s+|they\s+|the\s+(?:Committee|Commission)\s+)?(?:\w+\s+){0,2}"
                      r"(?:consider\w*|discuss\w*|examin\w*|reach\w*|c[ao]me\s+to|comes\s+to|take[sn]?\s+up|took\s+up|turn\w*\s+to|"
                      r"deal\w*\s+with)|\blater\b[^.;]{0,40}|\bin\s+connexion\s+with)(?:\W+(?:\w+\W+){0,4}?)?(?:the\s+)?(?:draft\s+)?$", re.I)


def article_mentions(text: str, instrument: str, text_of: str | None = None) -> list[tuple[str, int]]:
    """Article numbers a passage names as the one under discussion: (number, end offset), in
    order. Not "Articles 1 and 55 of the Charter", "rule 11", "article 5 of the Covenant" (in a
    UDHR record) or "article 2 of the Universal Declaration" (in a Covenant record). text_of: the
    instrument whose articles the record takes up, where not its corpus's (the draft Covenant in 1948)."""
    other = r"(?:draft\s+)?Covenants?|" + OTHER_DECLARATION if (text_of or instrument) == "UDHR" else r"(?:Universal\s+)?Declaration"
    pattern = OTHER_TEXT_RE.pattern.replace("{other}", other)
    if text_of == "both":  # the draft Declaration and the draft Convention are both under discussion
        pattern = OTHER_TEXT_RE.pattern.replace("Convention|{other}", OTHER_DECLARATION)
    rx = re.compile(pattern, re.I)
    out = []
    for m in re.finditer(r"\barticles?\s+(\d{1,2})\b", text, re.I):
        # "article 25 bis": a new article, not article 25
        if re.match(r"\s*(?:bis|ter|quater)\b", text[m.end():m.end() + 10], re.I):
            continue
        # the 1948 printed records' footnotes give the A/777 number of the article under debate
        # ("¹ Article 16 of the draft universal declaration of human rights (A/777)"): not ours
        if re.search(r"\(A\s*/\s*777\)", text[m.end():m.end() + 90]):
            continue
        # (Covenant records) the chair looking ahead or aside: "would have full latitude to go into the question again
        # when considering article 15", "could be raised in connexion with article 20": not the article under discussion
        if instrument == "Covenants" and ASIDE_RE.search(re.split(r"[.;:]\s", text[max(0, m.start() - 70):m.start()])[-1]):
            continue
        # ... or where something else belongs: "whether the atrocities contemplated under article 7 were covered by
        # article 5" (E/CN.4/SR.182)
        if instrument == "Covenants" and re.search(r"\b(?:covered|dealt\s+with|provided\s+for|done)\s+(?:by|in|under)\s+(?:the\s+)?(?:draft\s+)?"
                                                   r"(?:articles?\s+\d{1,2}\s+and\s+)?$",
                                                   text[max(0, m.start() - 40):m.start()], re.I):
            continue
        # (another treaty: "as had been done in articles 12 and 14 of the draft Covenant ... and article 2 of the draft Convention on
        # Freedom of Information", the chair on article 19, A/C.3/SR.1077; round 99)
        if instrument == "Covenants" and re.match(r"\s+of\s+the\s+(?:draft\s+)?Convention\b", text[m.end():m.end() + 40], re.I):
            continue
        if instrument == "UDHR" and (REFERENCE_RE.search(text[max(0, m.start() - 60):m.start()])
                                     or IN_OTHER_DECLARATION_RE.match(text[m.end():m.end() + 40])):
            continue
        # (both texts under discussion) "substitute the language of Article 13 of the Convention": a source of words
        if text_of == "both" and re.search(r"\b(?:(?:language|wording|terms)\s+(?:used\s+in\s+|of\s+)|(?:after|before|following|between)\s+)(?:the\s+)?$",
                                           text[max(0, m.start() - 40):m.start()], re.I):
            continue  # ... or a place: "they would appear in the Convention after Article 3"
        if not rx.match(text[m.end():m.end() + 80]):
            # the paragraph, when named: the split drafts (E/CN.4/95 art. 3, para. 2 is final art. 7)
            par = re.search(r"paragra\w*\s+(\d)\s+of\s+(?:the\s+)?$", text[max(0, m.start() - 30):m.start()], re.I) \
                or re.match(r",?\s*paragra\w*\s+(\d)\b", text[m.end():m.end() + 20], re.I)
            out.append((f"{m.group(1)}.{par.group(1)}" if par else m.group(1), m.end()))
    return out


# the 1947-48 records' run-in headings: "Examination of Article 9", "Discussion of article 5"
EXAMINATION_RE = re.compile(r"\b(?:examination|discussion)\s+of\s+(?:the\s+)?(?:draft\s+)?articles?\s+\d{1,2}\s*$", re.I)
TAKES_UP_RE = re.compile(r"\b(?:consider(?:ation\s+of)?|turn(?:ed)?\s+to|take\s+up|took\s+up|proceed(?:ed)?\s+to|pass(?:ed)?\s+to|"
                         r"continue\s+(?:its\s+)?(?:consideration|discussion|examination)\s+of|opened\s+the\s+(?:general\s+)?debate\s+on)"
                         r"\W+(?:\w+\W+){0,6}(?:draft\s+)?articles?\s+\d{1,2}\s*$", re.I)
# the debate leaves the articles: "The Commission then turned to the preamble", "... Preamble"
LEAVES_ARTICLES_RE = re.compile(r"\bpreamble\b|\b(?:turned|passed|proceeded|moved\s+on)\s+to\s+(?:the\s+)?(?:consideration\s+of\s+)?"
                                r"(?:item|question|report|agenda|next\s+item)", re.I)
# the chair takes up a proposed article placed among the numbered ones: "the Uruguayan proposal of a
# new article to be inserted between articles 61 and 62" is about neither
NEW_ARTICLE_RE = re.compile(r"\b(?:new|additional)\s+article\b[^.]{0,60}?\b(?:between|after|before|following)\s+(?:draft\s+)?articles?\s+\d", re.I)
# the chair takes up other business in a meeting: a new article, a draft resolution, another agenda item
OTHER_BUSINESS_RE = re.compile(r"\b(?:new|additional)\s+articles?\b|\bdraft\s+resolutions?\b|\bitem\s+\d+\s+of\s+the\s+agenda\b", re.I)
NEW_ARTICLE_WORDS_RE = re.compile(r"\b(?:new|additional)\s+articles?\b", re.I)


def other_business(text: str) -> bool:
    """The chair takes up something else than the covenant's articles (not the agenda on the first page,
    nor "item 3 of the agenda" when that item is the covenant)."""
    if "CONTENTS" in text[:400]:
        return False
    return any(not (m.group(0).lower().startswith("item") and re.search(r"cov[eo]n[ae]nt", text[max(0, m.start() - 150):m.end() + 150], re.I))
               for m in OTHER_BUSINESS_RE.finditer(text))


BIS_TAKEN_RE = re.compile(r"\b(?:consider\w*|take\s+up|took\s+up|attention\s+to|turn\w*\s+to|proposed)\W+(?:\w+\W+){0,4}"
                          r"articles?\s+\d{1,2}\s*(?:bis|ter|quater)\b", re.I)
# a "procedural" passage that is a speech whose opening the OCR broke ("Mr. HO.ARE (United Kingdom)
# introduced his delegation's amendments to article 60"): not the chair's, so it sets no article
# (also after a heading's tail the OCR ran into it: "A/C.3/L.625) (continued) 1. Mr. MASSOUD-ANSARI (Iran) said")
SPEECH_LIKE_RE = re.compile(r"^\W{0,3}(?:Mr|Mrs|Miss|Sir|Lady|Begum)\b|^.{0,60}?\(continued\)\W{0,3}\d{1,3}[.,]\s+(?:Mr|Mrs|Miss|Sir|Lady|Begum)\b")
# the chair closes an article and opens something else: "consideration of article 32 had been completed.
# Preamble", "the debate on article 31 was closed ... a new article proposed by the French representative"
ENDS_ARTICLE_RE = re.compile(r"\b(?:completed|closed|concluded|adopted)\b.{0,150}?(?:\bpreamble\b|\b(?:new|additional)\s+articles?\b)"
                             r"|\bpreamble\s+to\s+the\s+draft\s+(?:covenant|declaration)\W*$", re.I | re.S)
# "Article 5, as amended, was adopted in its entirety", "The whole of article 8 as amended was adopted"
# ("adopted" as the OCR reads it: "Article 29 as a whole was adoster", "adopiced")
ADOPTED = r"\bado\w{2,3}(?:ed|er|cd)\b"
# (the number run into the next word by the OCR, "Article 4as amended was adopted": round 86)
ADOPTED_WHOLE_RE = re.compile(rf"\barticle\s+\d{{1,2}}(?!\d).{{0,60}}{ADOPTED}|\bwhole\s+of\s+article\s+\d{{1,2}}(?!\d).{{0,40}}{ADOPTED}", re.I | re.S)


def adopts_article(text: str) -> bool:
    """A sentence that adopts an article (ADOPTED_WHOLE_RE), not one that adopts an amendment to it ("The third amendment to
    article 28 in documents A/C.3/L.1373 ... was adopted": the result the segmenter now sets apart from the chair's turn)."""
    # (nor a part of it: "Paragraph 1 of the joint France-United States text of article 16 was put to the vote, Paragraph 1 was
    # adopted", the clauses the OCR's comma runs together; round 86)
    return any(ADOPTED_WHOLE_RE.search(t) and not re.search(r"\b(?:sub-?)?amendments?\b", t, re.I)
               and not re.match(r"\W*(?:Paragraph|Sub-?paragraph|Sentence|Part|Point|Section)s?\b", t, re.I)
               for t in re.split(r"(?<=[.;])\s+|,\s+(?=[A-Z])", text))
# a printed agenda-item heading (capitals), often run into the passage before it:
# "AGENDA ITEM 35 Draft Convention on Freedom of Information", which has its own "ARTICLE 2"
AGENDA_ITEM_RE = re.compile(r"AGENDA\s+ITEMS?\s+\d+\W{0,3}([^()]{0,120})")
# speeches about the conduct of the meeting, not the article under discussion
PROCEDURAL_RE = re.compile(r"\bpoint\s+of\s+order\b|\brules?\s+of\s+procedure\b|\brule\s+\d{1,3}\b|\bChairman'?s\s+ruling\b|"
                           r"\border\s+(?:of|in\s+which)\s+(?:the\s+)?(?:discussion|debate|articles|work|speakers|voting)\b|"
                           r"\badjourn|\bclosure\s+of\s+the\s+(?:debate|list)|\blist\s+of\s+speakers\b|"
                           r"\bexplain\w*\s+(?:their|his|her)\s+votes?\s+(?:before|after)\b|\breproduced\s+and\s+circulated\b|"
                           r"\breconsider\w*\s+(?:the|its|that|those|these)\s+decision|\bvote\s+(?:first|be\s+taken)\b|\busual\s+procedure\b|"
                           r"\bpriority\b[^.]{0,40}\b(?:vote|voting|motion|proposal|amendment|draft\s+resolution)s?\b|"
                           r"\b(?:vote|voting|motion|proposal|amendment)s?\b[^.]{0,40}\bpriority\b|\bprocedural\s+(?:question|point|motion|proposal)|"
                           # when and how to vote, not on what: "asked that the vote should be taken at the afternoon meeting"
                           r"\bvote\s+(?:should|would|could|might|must)\s+be\s+(?:taken|postponed|deferred)\s+(?:at\s+the\s+"
                           r"(?:next|following|afternoon|morning)|until\b|after\s+the\b|later\b)|"
                           r"\bwhether\s+(?:his|her|its|the|an)\s+(?:\w+\s+)?amendment\s+could\s+be\s+voted\b|\bvoting\s+had\s+begun\b|"
                           r"\bbegun\s+to\s+vote\b|\b(?:regular|normal|usual|proper)\s+procedure\b|"
                           r"\bfor\s+dealing\s+with\s+the\s+(?:amendments|proposals|texts)\b|\bprocedure\s+adopted\s+for\b|"
                           r"\bprocedure\s+to\s+be\s+(?:followed|adopted)\s+in\s+(?:the\s+)?(?:discussion|debate|voting|vote|consideration)\b|"
                           # the plan of work: "decided ... that the Commission should devote two weeks to", "a sub-committee"
                           r"\bdevote\s+\w+\s+(?:weeks?|days?|meetings?)\b|\b(?:programme|plan)\s+of\s+(?:its\s+|the\s+|their\s+)?work\b|"
                           r"\borganization\s+of\s+(?:its|the|their)\s+work\b|"
                           r"\bproposal\s+for\s+a\s+sub-?committee\b|\b(?:set\s+up|establish|appoint)\w*\s+a\s+(?:sub-?committee|working\s+(?:group|party))\b|"
                           r"\bestablishment\s+of\s+(?:a|the)\s+(?:sub-?committee|working\s+(?:group|party))\b",
                           re.I)


DRAFTING_WORD_RE = re.compile(r"\b(?:articles?|paragraphs?|amendments?|sub-amendments?|texts?|wording|provisions?|clauses?|"
                              r"covenants?|drafts?|sentences?|words?|phrase|formula|proposals?)\b", re.I)
# in a short intervention, these mark the conduct of business too (a long speech can mention them in passing)
SHORT_PROCEDURAL_RE = re.compile(r"\bcirculated\b|"
                                 r"\bthe\s+Committee'?s\s+report\b|\breport\s+(?:of|to)\s+the\s+(?:Committee|General\s+Assembly)\b|"
                                 r"\bnext\s+meeting\b|\bsuspend(?:ed)?\s+the\s+meeting\b", re.I)
# ... and in one of middling length, these (the summary records, the time-limit for amendments)
MEDIUM_PROCEDURAL_RE = re.compile(r"\bsummary\s+records?\b|\btime\W?limit(?!\w*,?\s+within\s+which\s+(?:States|a\s+State))", re.I)


def instrument_named(text: str) -> str | None:
    """"iccpr" or "icescr" when a passage names one of the two Covenants; otherwise "covenant",
    "declaration" or "implementation" when it names exactly one of them."""
    t = text.lower()
    c = bool(re.search(r"civil\W+and\W+political", t))
    e = bool(re.search(r"economic\W+social\W+and\W+cultural", t))  # OCR: "SociAL AND .CULTURAL"
    if c != e and re.search(r"\bcov[eo]n[ae]\w*", t):
        return "iccpr" if c else "icescr"
    # "article 1 of the draft covenants", "both draft covenants": the two at once
    if re.search(r"\b(?:both|two)\s+(?:draft\s+)?cov[eo]n[ae]nts\b|\bcov[eo]n[ae]nts\b", t) and not re.search(r"\bdeclaration\b", t):
        return "both"
    found = {k for k, rx in (("covenant", r"\bcov[eo]n[ae]\w*|\bconvention\b"), ("declaration", r"\bdeclaration\b"),
                             ("implementation", r"\bimplementation\b")) if re.search(rx, t)}
    return found.pop() if len(found) == 1 else None


DATE_LOG: list[tuple[str, str | None, str | None]] = []  # (symbol, date read, date kept) for repaired dates
UNIFY_LOG: list[tuple[str, str, str, int]] = []  # (delegation, spelling replaced, spelling kept, speeches)


def unify_speakers(con: sqlite3.Connection) -> int:
    """One spelling per delegate across sessions. Speakers are resolved session by session, so
    the same person can carry an OCR variant in one session ("NISCT", "WHITIAM"). Within a
    delegation, a name close to a commoner one is merged into it when the two are very close
    (similarity >= 85), or close (>= 80) and either rare or read the same way somewhere
    in the raw text; a rare spelling also joins a common one that another engine read in its
    place. The spelling kept is the one the engines' readings support most."""
    import unicodedata
    from collections import Counter, defaultdict
    from rapidfuzz import fuzz

    def norm_ascii(s: str) -> str:
        return re.sub(r"[^A-Z]", "", unicodedata.normalize("NFKD", s.upper()).encode("ascii", "ignore").decode())

    rows = con.execute("SELECT delegation, speaker, upper(coalesce(speaker_raw, '')), votes, symbol FROM segments "
                       "WHERE kind='speech' AND speaker IS NOT NULL AND delegation IS NOT NULL").fetchall()
    count, raws, own_raws, support = Counter(), defaultdict(set), defaultdict(set), Counter()
    # in the General Assembly's printed records: speeches, and names read as names ("MEANY",
    # "Warr"; typed records are left out: there the engines can agree on garbage)
    count_printed, caps_printed = Counter(), Counter()
    for d, sp, raw, votes, symbol in rows:
        count[(d, sp)] += 1
        # what every engine read for this opening ("LUNDE (Norway) [vision]")
        read = [m.group(1).strip() for v in json.loads(votes or "[]") for m in [re.match(r"(.+?)\s*\(", v)] if m]
        readings = [r.upper() for r in read] or [raw]
        raws[(d, sp)] |= set(readings) | {raw}
        if raw:
            own_raws[(d, sp)].add(norm_ascii(raw))
        for r in readings:  # one vote per engine
            support[(d, r)] += 1
        if symbol.startswith("A/"):
            count_printed[(d, sp)] += 1
            for r in read:
                caps_printed[(d, r.upper())] += r.isupper() or r.istitle()
    by = defaultdict(list)
    for (d, sp), n in count.items():
        by[d].append(sp)
    merged = 0
    for d, names in by.items():
        names.sort(key=lambda sp: (-count[(d, sp)], sp))
        groups: list[list[str]] = []
        for sp in names:
            for g in groups:
                head = g[0]
                r = fuzz.ratio(sp.upper(), head.upper())
                rare = count[(d, sp)] <= 15 and count[(d, head)] > count[(d, sp)]
                # a name the engines read as printed (two readings a speech, all in the General Assembly's
                # printed records) is not a garbled form of another: "SINGH (India)" in 1956 is not
                # SINHA (1966); unless one name holds the other ("MENESES", "MENESES PALLARES") or an
                # engine read the other in its place ("Liraver" where the others read LITAUER)
                a, b = set(re.split(r"[\s-]+", sp.upper())), set(re.split(r"[\s-]+", head.upper()))
                printed = not (a <= b or b <= a) and head.upper() not in raws[(d, sp)] and sp.upper() not in raws[(d, head)] \
                    and count_printed[(d, sp)] == count[(d, sp)] and caps_printed[(d, sp.upper())] >= 2 * count[(d, sp)]
                same_own_raw = (count[(d, sp)] <= 2 and count[(d, head)] >= 3 and not printed
                                and bool(own_raws[(d, sp)]) and own_raws[(d, sp)] == {norm_ascii(head)})
                if same_own_raw or (len(sp) >= 4 and (r >= 85 or not printed and (
                        (r >= 80 and (min(count[(d, sp)], count[(d, head)]) < 5 or raws[(d, sp)] & raws[(d, head)]))
                        # a rare garbled spelling that another engine read as the common one, when
                        # the two are alike (an engine can also pick up a colleague's opening:
                        # BEVIN read as DAVIES is two people)
                        or (rare and head.upper() in raws[(d, sp)] and r >= 65)
                        # or that shares its opening letters ("DEMCURNXO" for DEMCHENKO)
                        or (rare and count[(d, head)] >= max(10, 5 * count[(d, sp)])
                            and (r >= 60 and sp[:4].upper() == head[:4].upper()
                                 or r >= 75 and sp[:2].upper() == head[:2].upper()))))):
                    g.append(sp)
                    break
            else:
                groups.append([sp])
        for g in groups:
            # the spelling the engines read most often, over all the group's speeches: one of the
            # names given, or a reading close to them ("HAMPI" given, "HAMDI" read 6 times to 3)
            readings = {r for sp in g for r in raws[(d, sp)]
                        if r and r.isupper() and re.fullmatch(r"[A-ZÀ-Ý' -]{3,40}", r) and fuzz.ratio(r, g[0].upper()) >= 75}
            cands = list(g) + sorted(readings - {sp.upper() for sp in g})
            best = max(cands, key=lambda sp: (support[(d, sp.upper())], count[(d, sp)], sp in g))
            # keep a name's particle: "de QUIJANO", not "QUIJANO" (openings often drop it)
            best = next((sp for sp in g if re.match(r"^(?:de|da|del|di|van|von|le|la)\s", sp, re.I)
                         and sp.upper().endswith(" " + best.upper())), best)
            if best not in g:
                g = g + [best]
            if len(g) < 2:
                continue
            for sp in g:
                if sp != best:
                    UNIFY_LOG.append((d, sp, best, count[(d, sp)]))
                    con.execute("UPDATE segments SET speaker = ? WHERE delegation = ? AND speaker = ?", (best, d, sp))
                    con.execute("UPDATE segments_fts SET speaker = ? WHERE delegation = ? AND speaker = ?", (best, d, sp))
                    merged += 1
    return merged


def load_actors() -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Exact names (lower case) -> canonical, and (normalised variant, canonical) pairs for
    fuzzy matching: the states of the gazetteer and the organisations that spoke."""
    import csv
    exact, fuzzy = {}, []
    for name in ("states.csv", "organizations.csv"):
        with (ROOT / "data" / "gazetteer" / name).open() as f:
            for r in csv.DictReader(f):
                for v in [r["canonical"], *filter(None, (r.get("variants") or "").split("|"))]:
                    exact[v.lower()] = r["canonical"]
                    fuzzy.append((_letters(v), r["canonical"]))
    return exact, fuzzy


def _letters(s: str) -> str:
    return " ".join(re.findall(r"[a-z]+", s.lower()))


ACTORS = None


def normalize_delegation(d: str | None) -> str | None:
    """One name per state or organisation: OCR variants ("Internetional Lebour Organization",
    "TlorId Federation of Trade Unions"), abbreviations in brackets ("(ILO"), trailing debris
    ("Lebanon •• , J~OVIC ...") and offices of the Secretariat. Strings that name nothing
    ("continued", "artlole 1") are dropped."""
    global ACTORS
    if not d:
        return d
    from rapidfuzz import fuzz, process
    if ACTORS is None:
        ACTORS = load_actors()
    exact, fuzzy = ACTORS
    clean = re.sub(r"\s*\([^)]*\)?\s*[.,]*$", "", d).strip(" .,'")  # "International Labour Organisation (ILO"
    if clean.lower() in exact:
        return exact[clean.lower()]
    if d.lower() in exact:
        return exact[d.lower()]
    key = _letters(clean)
    if len(key) < 5:
        return None
    hit = process.extractOne(key, [k for k, _ in fuzzy], scorer=fuzz.ratio)
    if hit and hit[1] >= 85:
        return fuzzy[hit[2]][1]
    # a known name followed by OCR debris
    starts = [c for k, c in fuzzy if len(k) >= 5 and key.startswith(k)]
    if starts:
        return max(starts, key=len)
    hit = process.extractOne(key, [k for k, _ in fuzzy], scorer=fuzz.token_set_ratio)
    if hit and hit[1] >= 90 and len(key) >= 8:
        return fuzzy[hit[2]][1]
    # a long name whose opening the OCR read right and whose end it garbled ("World Union for Pl'bg:resBive .Tvdatsm")
    near = [(fuzz.ratio(key, k), c) for k, c in fuzzy if len(k) >= 20 and key[:14] == k[:14]] \
        if re.search(r"[:;^~\d]|[a-z][A-Z]", d) else []  # only a name the OCR visibly garbled
    if near and max(near)[0] >= 70:
        return max(near)[1]
    return d if re.search(r"[A-Z][a-z]+.*\b(?:Organi[sz]ation|Federation|Union|Council|Congress|League|Committee|"
                          r"Association|Alliance|Society)\b", d) else None


def fix_case(name: str | None) -> str | None:
    """One spelling per name: "AZKouL", "Cassin" -> "AZKOUL", "CASSIN" (summary records print
    surnames in capitals, printed records in title case, OCR mixes both); particles ("de
    QUIJANO", "van ROIJEN") stay lower case."""
    if not name:
        return name
    out = []
    for w in name.split():
        letters = [c for c in w if c.isalpha()]
        up = sum(c.isupper() for c in letters)
        out.append(w.upper() if len(letters) >= 2 and (w[0].isupper() or up / len(letters) >= 0.5) else w)
    return " ".join(out)


# "Tho CHAIRMAN, speaking as the representative of France, stressed ...": a delegate's speech in the chair's turn
CHAIR_AS_DELEGATE_RE = re.compile(r"\W{0,3}(?:\d{1,3}\s*[.,]\s*)?T\w{1,2}\s+(?:CHAIRMAN|Chairman|PRESIDENT|President)\s*,?\s*(?:then\s+)?speaking\s+as\s+"
                                  r"(?:the\s+)?(?:representative|delegate)\b|\W{0,3}T\w{1,2}\s+CHAIRMAN\s+stated\s+that,?\s+as\s+[Rr]epresentative\s+of")


def merge_roll_calls(ds: list[dict]) -> list[dict]:
    """A roll-call can stand in a passage of its own, its result in the passage before (reports)
    or after (summary records): join it to the neighbouring decision whose figures fit it."""
    from decisions import roll_misfit
    out = list(ds)
    for i, d in enumerate(list(out)):
        if not (d["roll_call"] and d["outcome"] is None):
            continue
        k = out.index(d)
        near = [x for x in (out[k - 1] if k > 0 else None, out[k + 1] if k + 1 < len(out) else None)
                if x and x["outcome"] and not x["roll_call"] and abs(x["seq"] - d["seq"]) <= 3]
        if not near:
            continue
        x = min(near, key=lambda x: (roll_misfit(x, d["roll_call"]), 0 if x["seq"] >= d["seq"] else 1))
        if x.get("yes") is not None and roll_misfit(x, d["roll_call"]) > 10:
            continue
        x["roll_call"] = d["roll_call"]
        if len(x["subject"].split()) <= 4:
            x["subject"] = d["subject"] + " … " + x["subject"]
        x["proposers"] = x["proposers"] or d["proposers"]
        x["refs"] = x["refs"] or d["refs"]
        out.remove(d)
    for d in out:
        r = d["roll_call"]
        if r:
            r["complete"] = all(d[k] is None or len(r[k]) == d[k] for k in ("yes", "no", "abstentions"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="vote")
    args = ap.parse_args()

    guide = {d["symbol"]: d for d in json.loads((ROOT / "data/manifest/udhr.json").read_text())["documents"]}
    others, covenant_docs, alternates = {}, set(), {}
    # covenants_alt.json: documents fetched under another symbol (the Commission's reports under their E/CN.4
    # symbols, "= E/1992") or by hand (the Third Committee's reports 1955-61): Covenant documents too
    # lseries.json: the drafts and amendments of 1950-66 (A/C.3/L.n, E/CN.4/L.n) that the records cite: Covenant documents
    for name in ("udhr_supplement.json", "covenants.json", "covenants_alt.json", "lseries.json", "uva_extra.json"):
        path = ROOT / "data" / "manifest" / name
        if path.exists():
            for d in json.loads(path.read_text())["documents"]:
                others.setdefault(d["symbol"], d)
                if name.startswith("covenants") or name in ("lseries.json", "uva_extra.json"):
                    covenant_docs.add(d["symbol"])
                m = re.match(r"=\s*(E/\d+)", d.get("note") or "") if name == "covenants_alt.json" else None
                if m:
                    alternates[d["symbol"]] = m.group(1)
    # documents that exist only in French, machine-translated (pipeline/translations.py): flagged in the documents table
    translations = {}
    for path in sorted((ROOT / "data" / "translations").glob("*.json")):
        t = json.loads(path.read_text())
        translations[t["symbol"]] = t
    harvest = {}
    for path in sorted((ROOT / "data" / "manifest").glob("harvest_*.json")):
        for sym, e in json.loads(path.read_text()).items():
            if e.get("status") == "ok" and (sym not in harvest or e.get("final_url")):
                harvest[sym] = e

    # First pass: meeting dates, and sessions for records the manifests leave without one
    seg_paths = sorted(p for p in SEG.glob(f"*.{args.engine}.json") if not p.name.startswith("_"))
    # a report held under both symbols (E/1992 and E/CN.4/640): the E/ symbol's copy only
    held = {p.name.split(f".{args.engine}.json")[0] for p in seg_paths}
    seg_paths = [p for p in seg_paths if not (p.name.split(f".{args.engine}.json")[0].replace("_", "/") in alternates
                                              and alternates[p.name.split(f".{args.engine}.json")[0].replace("_", "/")].replace("/", "_") in held)]
    meta, printed_1948 = {}, {}
    for path in seg_paths:
        segs = json.loads(path.read_text())
        if not segs:
            continue
        symbol = segs[0]["symbol"]
        g, o = guide.get(symbol) or {}, others.get(symbol) or {}
        m = (g.get("mentions") or [{}])[0]
        body, session = m.get("body") or o.get("body"), m.get("session") or o.get("session")
        if symbol in SESSION_OVERRIDES:
            body, _, session = SESSION_OVERRIDES[symbol].partition(" / ")
        body = body or body_from_symbol(symbol)
        masthead = next((x for x in segs if x["kind"] == "masthead"), {})
        date = g.get("meeting_date") or masthead.get("meeting_date") or (
            masthead_date(" ".join(x["text"] for x in segs[:3])[:2500]) if not masthead and re.search(r"/(?:SR|PV)\.", symbol) else None)
        meta[symbol] = [body, session, date]
        if symbol in guide and re.fullmatch(r"A/C\.3/SR\.\d+", symbol) and 88 <= int(symbol.rsplit(".", 1)[1]) <= 179:
            printed_1948[int(symbol.rsplit(".", 1)[1])] = segs
    # a date that breaks the order of its series' meetings is read again from the scans (pipeline/dates.py)
    for sym, (b, sess, d) in meta.items():
        meta[sym][2] = fix_year(d, sess)
    for _ in range(2):  # a date filled in can put a neighbour out of order: a second pass
        for sym, d in repair_dates({sym: d for sym, (b, sess, d) in meta.items()}).items():
            DATE_LOG.append((sym, meta[sym][2], d))
            meta[sym][2] = d
    # dates read by hand where the scans mislead (a document dated by its last page, a resolution by its meeting)
    for r in csv.DictReader((ROOT / "data" / "concordance" / "date_overrides.csv").open()):
        if r["symbol"] in meta:
            meta[r["symbol"]][2] = r["date"]
    # dates two readers agreed on, read from the first page of a document the OCR left undated (data/concordance/dates_read.csv)
    dates_read = ROOT / "data" / "concordance" / "dates_read.csv"
    for r in (csv.DictReader(dates_read.open()) if dates_read.exists() else []):
        if r["symbol"] in meta and not meta[r["symbol"]][2]:
            meta[r["symbol"]][2] = r["date"]
    inferred = sessions_for({sym: (b, d) for sym, (b, sess, d) in meta.items() if not sess})
    for sym, sess in inferred.items():
        meta[sym][1] = sess

    heads_1948 = headings_1948(printed_1948)
    report_sections, report_annexes = load_report_sections(), load_report_annexes()
    l_articles = load_l_articles()
    accepted_csv = ROOT / "data" / "tagger" / "accepted.csv"
    tagger_accepted = {r["segment_id"]: (r["instrument"], int(r["final_article"]), float(r["score"]), r["checked"])
                       for r in csv.DictReader(accepted_csv.open())} if accepted_csv.exists() else {}
    # pipeline/reader_tags.py: two readers of the whole record agree, Jev confirms; and the articles that did not pass
    reader_csv, possible_csv = ROOT / "data" / "concordance" / "reader_tags.csv", ROOT / "data" / "concordance" / "possible_articles.csv"
    reader_tags = {r["segment_id"]: r for r in csv.DictReader(reader_csv.open())} if reader_csv.exists() else {}
    # a targeted re-read moved these speeches from the article their debate was filed under to the one they are about
    # (data/concordance/speech_retags.csv; applied last, and only to the tag it names as the previous one)
    retag_csv = ROOT / "data" / "concordance" / "speech_retags.csv"
    speech_retags = {r["segment_id"]: r for r in csv.DictReader(retag_csv.open())} if retag_csv.exists() else {}
    # tags a blind check of the judges found wrong (data/concordance/tag_rejections.csv: the speech and the article it must not
    # carry); applied last, so that no rule gives it back
    rej_csv = ROOT / "data" / "concordance" / "tag_rejections.csv"
    tag_rejections = {(r["segment_id"], r["instrument"], int(r["final_article"])) for r in csv.DictReader(rej_csv.open())} if rej_csv.exists() else set()
    possible = {r["segment_id"]: r["articles"] for r in csv.DictReader(possible_csv.open())} if possible_csv.exists() else {}
    schabas_tags, schabas_possible = load_schabas()
    # the questions of general debate (pipeline/topics.py), and the ones a blind check refused
    topic_list = all_topics()
    jev_topics = json.loads(TOPIC_CACHE.read_text()) if TOPIC_CACHE.exists() else {}
    trej_csv = ROOT / "data" / "concordance" / "topic_rejections.csv"
    topic_rejections = {(r["segment_id"], r["topic"]) for r in csv.DictReader(trej_csv.open())} if trej_csv.exists() else set()
    # Jev's picks under the threshold that two blind judges found right (eval/topic_band.py, 29 Oct 2026)
    tacc_csv = ROOT / "data" / "concordance" / "topic_accepted.csv"
    topic_accepted = {(r["segment_id"], r["topic"]) for r in csv.DictReader(tacc_csv.open())} if tacc_csv.exists() else set()
    sponsors_csv = ROOT / "data" / "concordance" / "amendment_sponsors.csv"
    sponsors = {r["symbol"]: [w for w in r["sponsors"].split("|") if w]  # (none: a compilation, A/C.3/L.460)
                for r in csv.DictReader(sponsors_csv.open())} if sponsors_csv.exists() else {}
    conc = load_concordance()
    cov_conc = load_covenant_concordance()
    jev_checked = load_jev_checks()
    jev_procedure = json.loads(JEV_PROCEDURE.read_text()) if JEV_PROCEDURE.exists() else {}
    jev_choice = json.loads(JEV_CHOICE.read_text()) if JEV_CHOICE.exists() else {}
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO topics VALUES (?,?,?,?)", [(t["topic"], t["label"], t["description"], t["articles"]) for t in topic_list])
    n_docs = n_segs = 0
    for path in seg_paths:
        segs = json.loads(path.read_text())
        if not segs:
            continue
        # the agenda item set apart from the masthead (pipeline/segment.py, round 81) is read with the masthead for the meeting's
        # instrument and article, as before it was set apart; it is stored as the heading it is
        for x in segs:
            if x.get("masthead_agenda"):
                x["kind"], x["_real_kind"] = "masthead", "heading"
        symbol = segs[0]["symbol"]
        g, o = guide.get(symbol) or {}, others.get(symbol) or {}
        body, session, date = meta[symbol]
        date = fix_year(date, session)
        h = harvest.get(symbol, {})
        opening = " ".join(x["text"] for x in segs[:4])[:3000]
        # the Covenants' records (1949-66) are not tagged with UDHR articles, even when they cite
        # E/800 (whose annex held the 1948 draft Covenant)
        instrument = "Covenants" if symbol in covenant_docs and symbol not in guide else "UDHR"
        stage = stage_of(symbol, opening, f"{body} / {session}" if body and session else None) if instrument == "UDHR" else None
        # a 1947-48 record: the text its meeting worked from, as read from the records; one not listed, or
        # listed with none (the draft Covenant, two texts at once), gets no article of the Declaration
        tag_stage = stage
        if stage in EARLY_STAGES or symbol in EARLY_MEETINGS:
            tag_stage = EARLY_MEETINGS.get(symbol)
            stage = tag_stage or stage
        text_of = "Covenants" if tag_stage in STAGE_SYMBOL else instrument  # a 1948 meeting on the draft Covenant
        if tag_stage in TWO_TEXT_STAGES:
            text_of = "both"
        cstage = covenant_stage(body, date, session) if instrument == "Covenants" and not symbol.startswith("A/RES/") else None
        meeting_no = int(symbol.rsplit(".", 1)[1]) if re.fullmatch(r"(?:E/CN\.4|A/C\.3)/SR\.\d+", symbol) else None
        tr = translations.get(symbol)
        if tr and not date and re.fullmatch(r"\d{4}-\d\d-\d\d", tr.get("date") or ""):
            date = tr["date"]  # a translated page's own date line, where the segmenter read none
        con.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            symbol, body, session, date, g.get("doc_type") or o.get("doc_type") or "document",
            h.get("final_url") or h.get("official_url"), Path(h.get("file", "")).name or None, h.get("pages"), stage,
            instrument, tr["source_language"] if tr else None, 1 if tr else 0, tr["translation_model"] if tr else None,
            tr["check"]["summary"] if tr else None, tr["translation_date"] if tr else None))
        n_docs += 1
        # Article in force: a heading sets it; so does the chair, a procedural line or a vote
        # naming one article ("The CHAIRMAN invited the Committee to consider article 17").
        # Speakers' mentions don't: delegates cite other articles all the time.
        # The instrument under discussion matters as much: in 1947-48 the same meetings took up
        # the draft Declaration and the draft Covenant, each with its own article numbers. A
        # heading ("DRAFT INTERNATIONAL COVENANT", "B. OBSERVATIONS ON THE DRAFT DECLARATION") or
        # the chair ("article 5 of the draft Covenant") says which; covenant articles get no UDHR tag.
        ctx, instr = None, None
        prev_procedural = False
        after_adoption = False  # an article just adopted as a whole: explanations of vote follow
        if instrument == "Covenants":
            # the agenda on the first page: "Draft International Covenants on Human Rights", or one covenant by name
            masthead = "\n".join(x["text"] for x in segs if x["kind"] == "masthead")
            found = instrument_named(masthead)
            instr = found if found in ("iccpr", "icescr", "both") else None
            # (not the agenda item's own title, "Draft international covenant on human rights and measures of
            # implementation", which every meeting of 1949-50 on the covenant carries: SR.90, SR.139)
            if cstage in ("chr5", "chr6") and re.search(r"\bimplementation\b", ITEM_TITLE_RE.sub(" ", masthead), re.I):
                # the measures of implementation had their own article numbers (E/1371, annex III);
                # a meeting that also took them up cannot be told apart part by part
                cstage = None
            # the agenda's "Article 5 (discussion continued)": the Commission's typed records of 1949-50 often print no
            # heading for the article a meeting takes up where the last one left off. (From 1951 the reports' meeting
            # lists place such speeches; there the agenda's article is often done with early in the meeting: SR.324)
            cont = CONTINUED_AGENDA_RE.search(masthead)
            # the Commission's records of 1951-53 list the meeting's items under CONTENTS: "(1) Article 40 and the Working Party's
            # redraft ... 4-14, (2) article 34 14-15". The first article is the one the meeting opens with, and a debate started
            # under it has no heading of its own (the old segmenter, which read the contents as the first passage of the
            # meeting, gave it that article too). It counts only where the session report's meeting list puts that article at
            # this meeting.
            head_ = CONTENTS_HEAD_RE.search(masthead)
            first_item = CONTENTS_FIRST_ARTICLE_RE.search(masthead[head_.end():head_.end() + 700]) if head_ and not cont else None
            # (only when it is the first item: "(1) Additional article proposed by the Chilean delegation ... 4 - 10 (11) Article 58"
            # opens on the Chilean article, E/CN.4/SR.389; 28 Oct 2026)
            if first_item and CONTENTS_FIRST_ITEM_RE.search(masthead[head_.end():head_.end() + first_item.start()]):
                first_item = None
            if first_item and meeting_no and cstage in STAGE_SYMBOL:
                d_ = first_item.group(1).translate(OCR_DIGITS)
                on_ = {(k[2], k[3]) for k, v in cov_conc.items() if len(k) == 4 and k[:2] == (cstage, "meetings") and meeting_no in v}
                if any(str(cov_conc.get((cstage, i_, d_))) == str(f_) for i_, f_ in on_):
                    ctx = d_
            if cont and cstage in ("chr5", "chr6"):
                ctx = cont.group(1).translate(OCR_DIGITS)
            elif cont and cstage in STAGE_SYMBOL and meeting_no:
                # (the 1952 debate on article 14, E/CN.4/SR.322: its first speeches carry no heading)
                d_ = cont.group(1).translate(OCR_DIGITS)
                on_ = {(k[2], k[3]) for k, v in cov_conc.items() if len(k) == 4 and k[:2] == (cstage, "meetings") and meeting_no in v}
                if len(on_) == 1:
                    inst_, fin_ = next(iter(on_))
                    if str(cov_conc.get((cstage, inst_, d_))) == str(fin_):
                        ctx = d_
        agenda_instr, doc_stage = instr, cstage
        # a Declaration article and its Convention article(s) under discussion together (two-text records)
        pair_decl, pair_convs, switch_to = None, [], None
        h48 = heads_1948.get(symbol, {})
        # a run of results set apart one by one (round 89): the votes on the amendments come before the one that adopts the
        # article and names it ("The first United Kingdom amendment was adopted ..." ... "Article 63, as amended, was adopted");
        # those that name no article take the article the run's adoption names
        run_art: dict[int, str] = {}
        _RESULT_WORD_RE = re.compile(r"\b(?:adopted|rejected|accepted|approved|retained|deleted)\b", re.I)
        ahead = None
        for x in reversed(segs):
            if x["kind"] in ("vote", "procedural"):
                named_ = re.search(r"\barticle\s+(\d{1,2})(?!\d)", x["text"], re.I)
                if re.search(r"\barticles\b|\bpreamble\b|\brecitals?\b", x["text"], re.I):
                    ahead = None  # (several articles, or the preamble: no one article to pass on, nor to take)
                elif named_ and _RESULT_WORD_RE.search(x["text"]):
                    ahead = named_.group(1)  # ("Paragraph 1 of article 8 was adopted as amended")
                elif named_:
                    ahead = None
                elif ahead:
                    run_art[id(x)] = ahead
            else:
                ahead = None
        # "10. The Chairman of the Working Party had stated ...": not the chair speaking, but a delegate (or the record)
        # reporting what another body's chairman said; it goes on from the speech before, if there is one
        for k, x in enumerate(segs):
            if x["kind"] == "chair" and re.match(r"\W*(?:\d{1,3}\s*[.,]\s*)?The\s+Chairman\s+of\s+the\s+(?!Committee\b|Commission\b(?!\s+on))",
                                                 x["text"]):
                prev = segs[k - 1] if k and segs[k - 1]["kind"] == "speech" else None
                x["kind"] = "speech" if prev else "procedural"
                if prev:
                    x["speaker"], x["delegation"] = prev.get("speaker"), prev.get("delegation")
            elif x["kind"] == "speech":
                # "General debate (continued)" read as "General DEBATE (continued)" (title "General"): a heading
                if re.match(r"^(?:\d+\.\s*)?General\s+(?:debate|discussion|statements|clause)\b", x["text"], re.I) \
                        and "Present:" not in x["text"]:
                    x["kind"] = "heading"
                    x["speaker"] = x["delegation"] = x["speaker_method"] = None
                # an attendance table or corrections notice on the first pages cut at a delegate's title, or a note on taking the Chair
                elif (x["seq"] <= 7 and x["id"] not in ("e_cn.4_ac.1_sr.39-0002", "e_cn.4_sr.86-0002", "e_cn.4_sr.94-0002")
                      and re.search(r"\bMembers\s*:|^\W*Mr\.\s+(?:EVANS|WEISS?)\s+International\s+(?:Labour|Refugee)\s+Organi[sz]ation\s*\("
                                    r"|\bAny\s+corrections\s+of\s+this\s+record\b"
                                    r"|Mr\.\s+ROOSEVELT\s+\(United\s+States\s+of\s+America\)\s+later\s*:", x["text"])) \
                        or x["id"] in ("e_cn.4_sr.202-0026", "e_cn.4_sr.210-0012"):
                    x["kind"] = "procedural"
                    x["speaker"] = x["delegation"] = x["speaker_method"] = None
                # a line inside a speech that opened with "General Assembly (...)" or "General ROMULO (...)" and was split by the title "General"
                elif x["text"].startswith("General ") and (not x.get("speaker") or x.get("speaker") == "Assembly"):
                    prev = next((segs[j] for j in range(k - 1, -1, -1) if segs[j]["kind"] == "speech" and segs[j].get("speaker")), None)
                    if prev:
                        x["speaker"], x["delegation"], x["speaker_method"] = prev.get("speaker"), prev.get("delegation"), prev.get("speaker_method")
        if text_of == "both":
            # the agenda in the masthead: the pair or article taken up first, else the one report named
            masthead = "\n".join(x["text"] for x in segs if x["kind"] == "masthead")
            named = article_mentions(masthead, instrument, "both")
            if named:
                d = paired(masthead, named)
                instr, ctx = ("declaration", d[0]) if d else (mention_text(masthead, named[-1][1]), named[-1][0])
                pair_convs = pair_convention(masthead, named) if d else []
                pair_decl = ctx if d else None
            else:
                groups = set(re.findall(r"Working\s+Group\s+on\s+(?:an\s+International\s+|the\s+)?(Declaration|Convention)", masthead, re.I))
                instr = {"declaration": "declaration", "convention": "covenant"}[groups.pop().lower()] if len(groups) == 1 else instr
        first_reading_stage, in_second = None, False
        for s in segs:
            if cstage in STAGE_SYMBOL and re.search(r"(?i:second\s+reading)" if s["kind"] == "masthead" else r"SECOND\s+READING", s["text"]):
                # the second reading (1950) went through a renumbered text, the measures of implementation
                # with it: no tags from there ("the second reading" in a speech is only a mention)
                first_reading_stage, cstage = cstage, None
            # ... except under a heading that gives the first reading's number, "Article 13 (former article 16)": that
            # article's meetings are in the session's list (E/CN.4/SR.200)
            sr_head = SECOND_READING_NUMBERS_RE.match(s["text"]) if first_reading_stage == "chr6" and s["kind"] == "heading" else None
            if sr_head and second_reading_agrees(sr_head.group("new"), sr_head.group("old"), cov_conc):
                cstage, in_second = "chr6", True
            s["_stage"] = cstage
            # (document segmenters copy the running article onto every heading: test the text)
            if s["kind"] == "heading" and not s.get("agenda") and not re.match(r"^\W*art", s["text"], re.I) and text_of != "both":
                # (a title that runs on to a second line is read by its first, as before the segmenter joined them: round 82)
                found = instrument_named(s.get("head_first") or s["text"])
                if found is None and instrument == "Covenants":
                    # a chapter heading in a Covenant document: "CIVIL AND POLITICAL RIGHTS"
                    c = bool(re.search(r"civil\W+and\W+political", s["text"], re.I))
                    e = bool(re.search(r"economic\W+social\W+and\W+cultural", s["text"], re.I))
                    found = "iccpr" if c and not e else "icescr" if e and not c else None
                # in a Covenant document a generic heading ("MEASURES OF IMPLEMENTATION") does not
                # undo the covenant a chapter named: the implementation articles are the ICCPR's
                if instrument == "Covenants" and found in ("covenant", "implementation", "both") and instr in ("iccpr", "icescr"):
                    found = None
                if found:
                    instr, ctx = found, None
                    # "Article 14 of the draft Covenant on Civil and Political Rights (continued)"
                    m = re.search(r"\barticles?\s+(\d{1,2})\b", s.get("head_first") or s["text"], re.I)
                    # (1948: "DISCUSSION OF ARTICLE 11 OF THE COVENANT", in a meeting on the draft Covenant)
                    if m and (found in ("iccpr", "icescr") or found == "covenant" and text_of == "Covenants" and instrument == "UDHR"):
                        ctx = m.group(1)
                        s["_art"], s["_art_src"], s["_instr"] = ctx, "heading", instr
                        continue
            # a heading between the turns that turns to the preamble ("Preamble to the draft covenant", E/CN.4/SR.308): no article
            if s["kind"] == "heading" and s.get("agenda") and re.match(r"^\W{0,2}(?:[IVX\d]{1,4}\s*\.\s+)?(?:(?:Discussion|Consideration)\s+of\s+)?"
                                                                      r"(?:the\s+)?Preamble\b", s["text"], re.I):
                ctx = None
            # an item of the agenda that is a new article ("(3) New article proposed by the United States delegation", "(7) Proposed
            # additional article to Part IV"): no article in force (28 Oct 2026)
            if s["kind"] == "heading" and s.get("agenda") and NEW_ARTICLE_ITEM_RE.search(s["text"][-200:]):
                ctx = None
            # only a heading line sets the article (segmenters also copy the running heading onto
            # every passage after it, which must not shadow the chair's later announcements)
            if s["kind"] == "heading" and s.get("article_heading") and not s.get("agenda") and text_of != "both":
                ctx = s["article_heading"].translate(OCR_DIGITS)  # "2k" is 24
                if s["seq"] in h48:  # (1948) its footnote's digit taken off
                    ctx = str(h48[s["seq"]][1])
                # "ARTICLE 15 OF THE DRAFT COVENANT ON ECONOMIC, SOCIAL AND CULTURAL RIGHTS": the heading names its covenant
                found = instrument_named(s["text"])
                if found in ("iccpr", "icescr", "both"):
                    instr = found
                s["_art"], s["_art_src"], s["_instr"] = ctx, "heading", instr
                continue
            opener = None
            runin = h48.get(s["seq"]) if s["kind"] != "heading" else None
            s["_prev_ctx"] = ctx
            if text_of == "both":
                # a run-in heading opens the next subject: what comes before it closes the current one
                runs = list(RUNIN_RE.finditer(s["text"]))
                while len(runs) > 1 and re.fullmatch(r"\W*and\W*", s["text"][runs[-2].end():runs[-1].start()], re.I):
                    runs = runs[:-2] + [runs[-2]]  # "Declaration Article 13 and Convention Article 10": one heading
                heads = [(runs[-1].start(), s["text"][runs[-1].start():runs[-1].end() + 90])] if runs else []
                tail = tail_heading(s["text"])
                opener = max(heads + ([tail] if tail else []), default=None)
            if in_second and s["kind"] in ("chair", "procedural", "vote"):
                pass  # (the chair's article numbers are the second reading's, not the first's)
            elif s["kind"] in ("chair", "procedural", "vote") and cstage == "e2573" and instr not in ("iccpr", "icescr"):
                # 1954-66: the printed records head each article's debate ("Article 1 (continued)"); while
                # both covenants were before the Committee, the chair's mentions of an article were as
                # often about whether to take it up. Once the agenda names one covenant (the 1966 debate
                # on "articles on measures of implementation"), the chair's "draft article 17" counts.
                pass
            elif s["kind"] in ("chair", "vote") or s["kind"] == "procedural" and not SPEECH_LIKE_RE.match(s["text"]) \
                    or s["kind"] == "heading" and text_of == "both":
                text = s["text"][:opener[0]] if opener else s["text"][:runin[0]] if runin else s["text"]
                named = article_mentions(text, instrument, text_of)
                # the chair speaking as a delegate: the article the speech opens on ("stressed the fundamental importance of
                # article 3"), not the last one a long speech names (E/CN.4/SR.310, round 80)
                if named and CHAIR_AS_DELEGATE_RE.match(s["text"]):
                    named = named[:1]
                if named:
                    # the article the chair takes up ("invited the Committee to consider article 25"), else
                    # the last one named: a later aside ("unlike article 24") must not replace it
                    taken = [(n, e) for n, e in named if TAKES_UP_RE.search(text[max(0, e - 90):e])
                             or instrument == "UDHR" and EXAMINATION_RE.search(text[max(0, e - 90):e])]
                    # (else the article an amendment is submitted to: "withdraw the amendment it had submitted to article 26
                    # ... in accordance with those used in article 23", E/CN.4/SR.197)
                    if not taken:
                        taken = [(n, e) for n, e in named if AMENDMENT_TO_RE.search(text[max(0, e - 130):e])][:1]
                    ctx, end = taken[0] if taken else named[-1]
                    # 1966: the chair on "the final clauses" as a whole, their numbers only cited ("articles 26 and 26 bis,
                    # which corresponded to articles 51 and 51 bis"): no one article is under discussion
                    if cstage in TC_STAGES and not taken and re.search(r"\bfinal\s+clauses\b", text, re.I):
                        ctx = None
                    if ENDS_ARTICLE_RE.search(text[named[-1][1]:]) or NEW_ARTICLE_RE.search(text):
                        ctx = None
                    # (the instrument of that article, not one a later clause names: "article 20 relating to petitions until articles
                    # on implementation had been drafted" is the Declaration's, E/CN.4/SR.61; 25 Oct 2026)
                    found = instrument_named(re.split(r"\b(?:until|pending|unless|before|after|once)\b", text[end:end + 90], 1)[0])
                    if text_of == "both":
                        # each mention's own text; a Declaration article taken up with its Convention article
                        # (a pair) is numbered by the Declaration's
                        d = paired(text, named)
                        if d and not taken:
                            ctx, end, found = d
                            pair_decl, pair_convs = d[0], pair_convention(text, named)
                        else:
                            found = mention_text(text, end)
                            decided = bool(re.search(r"\b(?:adopted|rejected|carried)\b", text[end:]))
                            if found is None and not taken and not decided and not re.search(r"\bto\s+the\s+vote\b", text):
                                ctx = s["_prev_ctx"]  # a bare passing mention ("transpose Article 38") moves nothing
                            # the pair's Declaration article decided as a whole: the debate turns to its Convention article
                            elif found in ("declaration", None) and pair_convs and pair_decl and ctx == str(pair_decl).split(".")[0] and decided:
                                switch_to = ("covenant", pair_convs[0])
                    if found:
                        instr = found
                elif BIS_TAKEN_RE.search(s["text"]):
                    ctx = None  # "drew attention to the proposed article 50 bis": a new article, not article 50
                elif instrument_named(s["text"][:300]) and re.search(r"\b(?:turned|proceeded|passed|consider|discussion|examination)\b",
                                                                     s["text"][:300], re.I):
                    instr, ctx = instrument_named(s["text"][:300]), None
                elif LEAVES_ARTICLES_RE.search(s["text"]):
                    ctx = None  # on to the preamble or another item: no article in force
            art = ctx
            if id(s) in run_art:
                art = run_art[id(s)]
            if cstage in STAGE_SYMBOL:
                # the Commission's typed records (1949-50) lose headings to the OCR: after an article is
                # adopted as a whole, only explanations of vote are about it; the next speech that is not
                # one has moved on (to an article whose heading was lost). The Third Committee's printed
                # records (1962-66) keep their headings: such a speech gets no article, the explanations
                # of vote after it still do
                if s["kind"] != "speech":
                    # (a result whose verb the OCR misspelled is set apart as procedural: "Article 2 as a whole ... wes adopted", round 89)
                    after_adoption = s["kind"] in ("vote", "procedural") and adopts_article(s["text"])
                elif after_adoption and not re.search(r"\b(?:voted|vote|voting|abstain\w*|abstention)\b", s["text"][:400], re.I):
                    if cstage in TC_STAGES:
                        art = None
                    else:
                        ctx, art, after_adoption = None, None, False
            s["_art"], s["_art_src"], s["_instr"] = art, "context" if art else None, instr
            if text_of == "both" and pair_decl and s["kind"] == "speech":
                members = {("declaration", str(pair_decl).split(".")[0])} | {("covenant", c) for c in pair_convs}
                if (instr, str(ctx or "").split(".")[0]) in members:
                    # a speech that names one half of the pair by number, and not the other, is about that half
                    own = s["text"][:opener[0]] if opener else s["text"]
                    said = {(mention_text(own, e), n.split(".")[0]) for n, e in article_mentions(own, instrument, "both")}
                    # a number the speech gives without its text counts for every half it could be
                    said |= {m for w, n in said if w is None for m in members if m[1] == n}
                    halves = [m for m in said if m in members]
                    if len({w for w, _ in halves}) == 1:
                        w, n = halves[0]
                        s["_art"], s["_instr"] = (pair_decl if w == "declaration" else n), w
            if runin:
                # (1948) a heading run into the passage: its article from the next passage on (or this one, when it opens with it)
                ctx = str(runin[1])
                if runin[0] < 5:
                    s["_art"], s["_art_src"] = ctx, "context"
            if switch_to and not opener:
                (instr, ctx), switch_to = switch_to, None
            if opener:
                # from the next passage on (or this one, when it is the heading itself)
                w, n, convs = heading_context(opener[1], instrument)
                switch_to = None
                if convs:
                    pair_decl, pair_convs = n, convs
                if w or n:
                    instr, ctx = w or instr, n
                    if opener[0] < 5:
                        s["_art"], s["_art_src"], s["_instr"] = ctx, "context" if ctx else None, instr
                    # "Declaration Article 15 and Convention article 14. The CHAIRMAN put to the vote Article 15 of the
                    # Declaration; it was adopted": on to the Convention article
                    if convs and n and re.search(rf"\bArticle\s+{re.escape(n)}\s+of\s+the\s+Declaration\b[^.]{{0,80}}?\b(?:adopted|rejected|carried)\b",
                                                     s["text"][opener[0]:], re.I):
                        instr, ctx = "covenant", convs[0]
            if text_of == "both" and pair_decl:
                members = {("declaration", str(pair_decl).split(".")[0])} | {("covenant", c) for c in pair_convs}
                if (instr, str(ctx or "").split(".")[0]) not in members:
                    pair_decl, pair_convs = None, []  # the debate has left the pair
            if s["kind"] == "speech":
                # procedural speeches get no article; nor does plenary general debate. (A speech's own
                # mention of an article is not used: "the part referring to article 9", "article 19 of
                # the new Indian Constitution" were more often asides than its subject.)
                plain = re.sub(r"[\"“”]", "", s["text"][:400]).replace("’", "'")
                # (the framing "on a point of order" says the form, not the subject: a delegate offering to withdraw the
                # second part of an amendment, A/C.3/SR.1077)
                framed = re.search(r"\bon\s+a\s+point\s+of\s+order\b", plain, re.I)
                # only where the point is about the words of an amendment (its withdrawal, a separate vote on a phrase); a point
                # on the order of voting or on whether a text is a new amendment stays procedural (A/C.3/SR.148, 714, 881)
                substance = framed and re.search(r"\bwithdraw\w*\s+(?:the\s+|a\s+)?(?:second|first|part)\b|\bseparate\s+vote\s+on\s+(?:the\s+)?(?:phrase|words?)\b",
                                                 s["text"][:600], re.I | re.S)
                if substance:
                    plain = re.sub(r"\b(?:speaking\s+)?on\s+a\s+point\s+of\s+order\b,?", "", plain, flags=re.I)
                words = len(s["text"].split())
                # a brief "Mr. X also supported the remarks of Y" follows the point it supports
                echo = words < 40 and re.search(r"\b(?:supported|agreed\s+with|associated\s+\w+self\s+with|endorsed)\b", plain)
                # Covenant debates (1955-66) run over many meetings under one heading, with interjections on
                # other business: a speech that uses no drafting word at all keeps the article only on a clearer yes from
                # Jev's check (below), and Jev's choice among the meeting's articles does not apply to it (28 Oct 2026: the
                # skip it had also dropped the Commission's substantive speeches, E/CN.4/SR.389's on the annual report)
                s["_no_drafting_word"] = instrument == "Covenants" and not DRAFTING_WORD_RE.search(s["text"])
                # an attendance list cut as a speech ("Mr. MALIK (Lebanon) Mr. WHITLAM Mr. SANTA CRUZ Mr. TU ...")
                roster = len(re.findall(r"\b(?:Mr|Mrs|Miss|Sir)\b\.?,?\s+[A-Z][A-Z-]{2,}", s["text"])) >= 6 \
                    and len(re.findall(r"\b[a-z]{4,}\b", s["text"])) < 0.2 * words
                if (not substance and (PROCEDURAL_RE.search(plain) or (words < 80 and SHORT_PROCEDURAL_RE.search(plain))
                                       or (words < 110 and MEDIUM_PROCEDURAL_RE.search(plain)) or (echo and prev_procedural))) \
                        or roster:
                    s["_art"], s["_art_src"], s["_skip"] = None, None, True
                    prev_procedural = True
                else:
                    prev_procedural = s["_no_drafting_word"]
                    if s["_art_src"] == "context" and symbol.startswith("A/PV."):
                        s["_art"], s["_art_src"] = None, None
            items = AGENDA_ITEM_RE.findall(s["text"]) if instrument == "Covenants" and s["kind"] != "masthead" else []
            if items:
                # what follows belongs to that item: the covenants (as the masthead named them) or another draft
                instr = agenda_instr if re.search(r"\bcov[eo]n[ae]nts?\b", items[-1], re.I) else "other"
                ctx = None
        # an article number the session's numbering does not know, or not at a meeting its report lists for it,
        # is another text's ("article 16" of the Declaration in the 1953 debate on marriage and the family)
        numbered = doc_stage not in MEETING_ONLY and any(
            x.get("_art") and covenant_article(x.get("_stage"), x.get("_instr") if x.get("_instr") in ("iccpr", "icescr") else None,
                                               whole_article(x["_art"]), cov_conc, meeting_no)[0]
            for x in segs)
        on = {(k[2], k[3]) for k, v in cov_conc.items() if len(k) == 4 and k[:2] == (doc_stage, "meetings") and meeting_no in v}
        inst, fin = next(iter(on)) if len(on) == 1 else (None, "")
        draft = next((k[2] for k, v in cov_conc.items() if len(k) == 3 and k[:2] == (doc_stage, inst) and str(v) == fin), None)
        # a meeting the report gives to an article proposed at the session (no number in the text before it):
        # the chair taking up "the new article" is taking up that article
        business = other_business if draft else lambda t: other_business(NEW_ARTICLE_WORDS_RE.sub("", t))
        if doc_stage in STAGE_SYMBOL and meeting_no and not numbered and fin.isdigit() \
                and not any(business(x["text"]) for x in segs if x["kind"] in ("chair", "procedural", "vote")):
            # a Commission record with no heading or chair to go by: the session's report lists the meetings
            # on each article; a meeting it gives to one article alone was about that article
            how = (f"{STAGE_SYMBOL[doc_stage]}" + (f" draft article {draft}" if draft else "") +
                   "; the session's report lists this meeting for the article alone")
            for x in segs:
                if x["kind"] == "speech" and not x.get("_skip"):
                    x["_art"], x["_art_src"], x["_fixed"] = draft, "meeting", (int(fin), how, inst)
        in_reports = symbol in report_sections or symbol in report_annexes
        if in_reports:
            report_tags(symbol, segs, report_sections.get(symbol, []), report_annexes.get(symbol))
        la = l_articles.get(L_BASE_RE.sub("", symbol).upper())
        # (one article for the whole document: not for a compilation of amendments to several articles, E/CN.4/L.93's pages
        # 2-26; page 1 of E/CN.4/L.93 is the Lebanon-US amendment to article 20 = ICESCR 6)
        if la and not in_reports and (len(segs) <= 40 or symbol == "E/CN.4/L.93"):
            for x in segs:
                if symbol == "E/CN.4/L.93" and x["page_start"] > 1:
                    x["_art"], x["_art_src"], x["_fixed"] = None, None, None
                elif x["kind"] != "masthead":
                    x["_fixed"] = (int(la["final_article"]), f"{symbol}: the article the debates that cite it and its own text give ({la['note']})",
                                   la["instrument"])
                    x["_art"] = la["draft_article"] or None
        doc_decisions = []
        prev_text = ""
        # who proposed each document the record cites, as its own words say ("the amendment of Mexico and Saudi Arabia
        # (A/C.3/L.1176)"), for a decision whose clause cites one document and names no proposer ("Point 1 of the
        # amendment (A/C.3/L.1176)"); and each speaker's delegation, for "Mr. Pavlov's amendment"
        doc_proposers: dict[str, list[str]] = {}
        speakers_of: dict[str, set] = {}
        for s in segs:
            if s["kind"] != "masthead":
                for ref, (amend, who) in cited(s["text"], symbol).items():
                    if amend and who:
                        doc_proposers.setdefault(ref, who)
            if s.get("speaker") and s.get("delegation"):
                speakers_of.setdefault(s["speaker"].split()[-1].upper(), set()).add(normalize_delegation(s["delegation"]))
        for s in segs:
            if s["kind"] != "masthead":
                for d in find_decisions(s["text"], speech=s["kind"] == "speech", context=prev_text):
                    d.update(segment_id=s["id"], seq=s["seq"], _art=s.get("_art"), _instr=s.get("_instr"), _stage=s.get("_stage"),
                             _fixed=s.get("_fixed") if in_reports else None)
                    doc_decisions.append(d)
                # (the passages before: a vote set apart from the chair's turn that put it, with a roll-call between; not a
                # footnote, which stands where the page ends, not where the debate is: round 88)
                if s["kind"] != "footnote":
                    prev_text = (prev_text + "\n\n" + s["text"])[-3000:]
        for d in merge_roll_calls(doc_decisions):
            draft = d["article"] or d["_art"]
            if d["_fixed"]:  # a report's section (data/concordance/report_sections.csv)
                fin_d, _, d_instr = d["_fixed"]
                draft = d["_art"]
            elif text_of == "both":
                fin_d, _, d_instr = two_text_article(tag_stage, d["_instr"], draft, conc, cov_conc)
            elif text_of == "Covenants" and instrument == "UDHR":
                fin_d, _, d_instr = covenant_article(tag_stage, d["_instr"], whole_article(draft), cov_conc)
            elif instrument == "UDHR":
                # the preamble, a resolution, the Declaration as a whole, several articles at once ("Articles 4 to 13"):
                # no one article
                last = re.split(r"(?<=[.;…])\s+", d["subject"])[-1]
                if re.search(r"\b(?:preamble|recitals?|resolution)\b|Universal\s+Declaration\s+of\s+Human\s+Rights\W*$|"
                             r"\barticles\s+\d{1,2}\s+(?:to|and)\s+\d", last, re.I):
                    draft = None
                fin_d, _ = final_article(tag_stage, draft, conc) if tags_udhr(tag_stage, d["_instr"]) else (None, None)
                d_instr = "UDHR" if fin_d else None
            else:
                fin_d, _, d_instr = covenant_article(d["_stage"], d["_instr"], draft, cov_conc, meeting_no)
            # a decision on one amendment whose sponsors the session report lists: the report's sponsors (the records'
            # own wording misleads the parser: "the Colombian-Uruguayan amendment", sub-amendments, the sentence before)
            if d.get("procedural"):
                fin_d, d_instr = None, None
            # a vote on the chair's ruling ("The Chairman's ruling was upheld by 19 votes to 9") decides the procedure, not the
            # article under debate (two blind judges, round 97)
            if d["outcome"] in ("upheld", "overruled"):
                fin_d, d_instr = None, None
            # a decision without a vote ("It was so decided") is the article's only when it settles its text; otherwise
            # it orders the work (when to meet, what to take up next, whom to consult)
            if d["outcome"] == "decided" and d["without_vote"] and (not DRAFTING_DECISION_RE.search(d["subject"])
                                                                    or ORDERS_WORK_RE.search(d["subject"])):
                fin_d, d_instr = None, None
            # (a vote the re-read of the record moved to the article its clause is, data/concordance/speech_retags.csv)
            rt_d = speech_retags.get(d["segment_id"])
            if rt_d and fin_d and rt_d["previous"] == f"{d_instr} {fin_d}":
                fin_d, d_instr = int(rt_d["final_article"]), rt_d["instrument"]
            refs = list(dict.fromkeys(REF_FIXES.get((d["segment_id"], fix_symbol(r)), fix_symbol(r)) for r in d["refs"]))
            for (sid_, ocr), right in REF_FIXES.items():
                if sid_ == d["segment_id"]:
                    d["subject"] = d["subject"].replace(ocr, right)
            listed = set(refs) & sponsors.keys()
            if len(listed) == 1 and len(refs) == 1:
                d["proposers"] = sponsors[listed.pop()]
            elif not d["proposers"] and len(refs) == 1 and refs[0] in doc_proposers and not BASE_TEXT_RE.search(d["subject"].split(" … ")[-1]):
                d["proposers"] = doc_proposers[refs[0]]
            if not d["proposers"]:
                own = re.findall(r"\bMrs?\.?\s+([A-Z][\w-]+)['’]\s?s\s+(?:\w+\s+)?(?:amendments?|proposals?|motion|suggestion|text)\b", d["subject"])
                who = speakers_of.get(own[-1].upper()) if own else None
                if who and len(who) == 1 and None not in who:
                    d["proposers"] = list(who)
            for c in DECISION_PROPOSERS:
                if c["segment_id"] == d["segment_id"] and c["subject_contains"] in d["subject"]:
                    d["proposers"] = [x for x in c["proposers"].split("|") if x]  # (empty: a check found no proposer)
            con.execute("INSERT INTO decisions (segment_id, symbol, seq, stage, draft_article, final_article, subject, outcome, "
                        "yes, no, abstentions, unanimous, without_vote, proposers, refs, roll_call, roll_complete, "
                        "article_instrument) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                            d["segment_id"], symbol, d["seq"], stage, draft, fin_d, d["subject"], d["outcome"], d["yes"],
                            d["no"], d["abstentions"], int(d["unanimous"]), int(d["without_vote"]),
                            json.dumps(d["proposers"]), json.dumps(refs),
                            json.dumps(d["roll_call"]) if d["roll_call"] else None,
                            int(d["roll_call"]["complete"]) if d["roll_call"] else None, d_instr))
        prev_turn, last = {}, ""
        for s in segs:
            prev_turn[id(s)] = last
            if s["kind"] in ("chair", "speech", "procedural"):
                last = s["text"]
        for s in segs:
            if in_reports and instrument == "UDHR":
                # (the Declaration's reports: E/CN.4/21, E/CN.4/113) their sections and annexes, read by hand
                fin, how, art_instr = s.get("_fixed") or (None, None, None)
            elif text_of == "both":
                fin, how, art_instr = two_text_article(tag_stage, s.get("_instr"), s.get("_art"), conc, cov_conc)
            elif text_of == "Covenants" and instrument == "UDHR":
                fin, how, art_instr = covenant_article(tag_stage, s.get("_instr"), whole_article(s.get("_art")), cov_conc)
            elif instrument == "UDHR":
                fin, how = final_article(tag_stage, s.get("_art"), conc) if tags_udhr(tag_stage, s.get("_instr")) else (None, None)
                art_instr = "UDHR" if fin else None
            else:
                fin, how, art_instr = s.get("_fixed") or covenant_article(s.get("_stage"), s.get("_instr"), s.get("_art"), cov_conc, meeting_no)
            if stage_1966_entry(s, fin, art_instr):
                fin, how = 27, (f"{how}; " if how else "") + ("on the number of ratifications for entry into force, the paragraph "
                                                                "of draft article 26 that became article 26 bis (ICESCR 27)")
            # a speech the rules leave untagged, at a meeting whose articles the session's report lists: Jev's choice
            # among them (eval/jev_article_choice.py), at CHOICE_THRESHOLD or more
            choice = jev_choice.get(s["id"]) if s["kind"] == "speech" and not s.get("_skip") and not s.get("_no_drafting_word") else None
            # (1948) a pick among the articles the record's headings and chair give the meeting (no report lists them)
            pick_1948 = None
            if choice and (choice.get("p") or 0) >= CHOICE_THRESHOLD and (choice.get("pick") or "") in choice.get("drafts", {}):
                inst_p, fin_p = choice["pick"].rsplit(" ", 1)
                pick_1948 = (int(fin_p), choice["drafts"][choice["pick"]],
                             f"Jev's choice among the articles the record's headings and chair give this meeting (p = {choice['p']:.2f})",
                             inst_p)
                if not fin:
                    fin, art_instr, how = pick_1948[0], pick_1948[3], pick_1948[2]
                    s["_art"] = pick_1948[1] or None
            if choice and not fin and (choice.get("p") or 0) >= CHOICE_THRESHOLD and re.fullmatch(r"(ICCPR|ICESCR) \d+", choice.get("pick") or ""):
                c_inst, c_fin = choice["pick"].split()
                if meeting_no in cov_conc.get((s.get("_stage"), "meetings", c_inst, c_fin), ()):
                    fin, art_instr = int(c_fin), c_inst
                    how = (f"{STAGE_SYMBOL.get(s.get('_stage'), '')}: Jev's choice among the articles the session's report lists "
                           f"for this meeting (p = {choice['p']:.2f})")
            if fin and s.get("_art_src") == "context":
                how = f"{how}; article from the chair or agenda" if how else "article from the chair or agenda"
            # Jev's check (pipeline/jev_articles.py): is the speech about its article? Below the threshold
            # the tag is dropped; the probability is kept either way
            conf = jev_checked.get(jev_key(s["id"], art_instr, fin, s.get("_art"))) if fin and s["kind"] == "speech" else None
            # (a speech a hand-read row tags, report_annex_sections.csv, keeps its tag: two readers settled it)
            # (the stricter threshold also for a Covenant speech with no drafting word: the context is its only evidence)
            if conf is not None and conf < (JEV_THRESHOLD_EARLY if symbol in EARLY_MEETINGS or s.get("_no_drafting_word") else JEV_THRESHOLD) \
                    and "(the report's annexes, read by hand)" not in (how or ""):
                art_before = art_instr
                # (the stricter threshold of a speech with no drafting word only withholds the debate's article: below the
                # usual one, as for any speech, Jev's no also keeps the readers' same article off it)
                if not (s.get("_no_drafting_word") and symbol not in EARLY_MEETINGS and conf >= JEV_THRESHOLD):
                    s["_jev_rejected"] = (art_instr, fin)
                fin, how, art_instr = None, f"not tagged: Jev judged the speech not about the article (p = {conf:.2f})", None
                # (1948) not about the article in force, but about another the meeting took up: Jev's choice, checked in turn
                if pick_1948 and (s.get("_art") != pick_1948[1] or art_before != pick_1948[3]):
                    s["_art"] = pick_1948[1] or None
                    conf = jev_checked.get(jev_key(s["id"], pick_1948[3], pick_1948[0], s["_art"]))
                    if conf is None or conf >= JEV_THRESHOLD:
                        fin, art_instr, how = pick_1948[0], pick_1948[3], pick_1948[2]
            # Jev's second question (eval/jev_procedure_check.py): is a short speech, or the chair's turn (round 120), about the
            # organisation of work?
            proc = jev_procedure.get(s["id"]) if fin and s["kind"] in ("speech", "chair") else None
            if proc is not None and proc >= PROCEDURE_THRESHOLD:
                fin, how, art_instr = None, f"not tagged: Jev judged the speech to be about the organisation of work (p = {proc:.2f})", None
            # the offline tagger's proposals (pipeline/article_tagger.py) that a hand check accepted (data/tagger/accepted.csv):
            # they fill a speech the rules and Jev's checks left untagged, and no classifier overrides a hand check
            if not fin and s["kind"] == "speech" and s["id"] in tagger_accepted:
                inst_t, fin_t, score_t, round_t = tagger_accepted[s["id"]]
                fin, art_instr, conf = fin_t, inst_t, None
                how = f"the offline tagger's proposal (score {score_t:.2f}), checked by hand ({round_t})"
            # (a speech the rules, Jev's checks and the tagger leave untagged; not one Jev judged procedural, nor one whose
            # tag Jev dropped when the readers give that same article)
            # (a chair's turn or a vote a resegmentation split off a tagged speech can carry the old tag back: "restored" rows)
            restored = s["id"] in reader_tags and reader_tags[s["id"]]["note"].startswith("restored")
            rt = reader_tags.get(s["id"]) if not fin and (s["kind"] == "speech" or restored) and "organisation of work" not in (how or "") else None
            # (and a speech the debate's context alone filed under another article: the readers read the speech itself; round 80,
            # where a chair's turn split off by the segmenter carried article 10 of the Geneva draft into the debate on asylum)
            if not rt and fin and (s["kind"] == "speech" or restored) and s.get("_art_src") == "context" and s["id"] in reader_tags \
                    and s["id"] not in speech_retags \
                    and (reader_tags[s["id"]]["instrument"], reader_tags[s["id"]]["final_article"]) != (art_instr, str(fin)):
                rt = reader_tags[s["id"]]
            # (a readers' suggestion that two blind judges found right, round 108: a hand check, which Jev's no does not override)
            judged = bool(rt) and rt["note"].startswith("judged")
            if rt and not judged and s.get("_jev_rejected") and s["_jev_rejected"] == (rt["instrument"], int(rt["final_article"])):
                rt = None
            if rt:
                fin, art_instr, conf = int(rt["final_article"]), rt["instrument"], float(rt["jev"]) if rt["jev"] else None
                s["_art"] = rt["draft_article"] or s.get("_art")
                how = ("the tag before a resegmentation, kept: the text is unchanged" if restored and "not judged" in reader_tags[s["id"]]["note"]
                       else "the tag before a resegmentation, judged right on the page image by two blind judges" if restored
                       else f"a reader's suggestion, {rt['note'].split(':')[0]}" if judged
                       else f"two readers of the whole record agree; Jev confirms (p = {conf:.2f})")
            # Schabas's index lists the speech's page for an article, and Jev confirms it on the speech (an untagged speech only;
            # not one the rules found procedural, nor one whose same article Jev already turned down)
            st = schabas_tags.get(s["id"]) if not fin and s["kind"] == "speech" and "organisation of work" not in (how or "") else None
            if st and s.get("_skip"):
                SCHABAS_LOG["skipped_procedural"] += 1
                st = None
            if st and s.get("_jev_rejected") and s["_jev_rejected"] == (st["instrument"], int(st["final_article"])):
                SCHABAS_LOG["rejected_by_jev"] += 1
                st = None
            if st:
                fin, art_instr, conf = int(st["final_article"]), st["instrument"], float(st["jev"])
                s["_art"] = st["draft_article"] or s.get("_art")
                how = (f"Schabas index p. {st['book_pages'].replace(' ', ', ')}: the Table of provisions lists this article on "
                       f"the page; Jev confirms (p = {conf:.2f})")
                SCHABAS_LOG["applied"] += 1
            rr = speech_retags.get(s["id"]) if fin and s["kind"] == "speech" else None
            if rr and rr["previous"] == f"{art_instr} {fin}":
                fin, art_instr, conf = int(rr["final_article"]), rr["instrument"], float(rr["jev"])
                how = (f"re-read: the speech is about this article, not the {rr['previous']} its debate was filed under; "
                       f"two readers sure, Jev confirms (p = {conf:.2f})")
            if fin and s["kind"] == "procedural" and not restored and procedural_off_article(s["text"], prev_turn.get(id(s), "")):
                fin, art_instr, conf = None, None, None
                how = "not tagged: a procedural line (an attendance list, the order of work, the chair, the meeting) is not about an article"
            if fin and (s["id"], art_instr, fin) in tag_rejections:
                fin, art_instr, conf = None, None, None
                how = "not tagged: a blind check found the speech not mainly about the article its context gave it"
            # a speech no article fits: the question of general debate Jev chose for it
            tc = jev_topics.get(s["id"]) if not fin and s["kind"] == "speech" else None
            topic = (tc["pick"], tc["p"]) if tc and tc["pick"] in {t["topic"] for t in topic_list} and (tc["p"] >= TOPIC_THRESHOLD or (s["id"], tc["pick"]) in topic_accepted) \
                and (s["id"], tc["pick"]) not in topic_rejections else None

            # (a speaker's delegation the bilingual columns garbled, "Union des Républiques socia...": the country as printed)
            deleg = normalize_delegation(s.get("delegation"))
            if not deleg and s["kind"] == "speech" and s.get("speaker"):
                deleg = normalize_delegation(s.get("country_raw"))
            if s.get("_real_kind"):
                s["kind"] = s["_real_kind"]
            # (the close of the meeting, "The meeting rose at 5.25 p.m.", is about no article: blind judges, round 99;
            # nor is the masthead itself once it has given the meeting's opening context)
            if s["kind"] == "closing" and fin:
                fin, art_instr, conf, how = None, None, None, "not tagged: the close of the meeting"
            if s["kind"] == "masthead" and fin:
                fin, art_instr, conf, how = None, None, None, None
            con.execute("INSERT INTO segments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                s["id"], symbol, s["seq"], s["kind"], s["page_start"], s["page_end"], s.get("n"),
                fix_case(s.get("speaker")), deleg, s.get("speaker_method"), s.get("speaker_raw"),
                s.get("country_raw"), json.dumps(s.get("votes") or []), s.get("review"),
                s.get("article_heading"), json.dumps(s["vote"]) if s.get("vote") else None, s["text"], fin, how,
                s.get("_art"), art_instr, s.get("n_end"), conf, possible_text(s["id"], fin, possible, schabas_possible)))
            if topic:
                con.execute("INSERT INTO segment_topics VALUES (?,?,?)", (s["id"], *topic))
            if s["kind"] != "masthead":
                for ref, (amend, who) in cited(s["text"], symbol, deleg if s["kind"] == "speech" else None).items():
                    con.execute("INSERT INTO refs VALUES (?,?,?,?)", (s["id"], REF_FIXES.get((s["id"], ref), ref), int(amend), json.dumps(who)))
            if s["kind"] != "masthead":
                con.execute("INSERT INTO segments_fts VALUES (?,?,?,?)",
                            (s["text"], fix_case(s.get("speaker")) or "", deleg or "", s["id"]))
                con.execute("INSERT INTO segments_fts_exact VALUES (?,?)", (s["text"], s["id"]))
            n_segs += 1
    if ANNEX_LOG:
        print(f"report annexes: {len(ANNEX_LOG)} section anchors not found, e.g. {ANNEX_LOG[:3]}", file=sys.stderr)
    print(f"Schabas index ({'live' if SCHABAS_TAGS_LIVE else 'possible only'}): {SCHABAS_LOG}", file=sys.stderr)
    # the speakers kept from the OCR engines' resolution where the vision reader's text replaced the OCR's (the user's decision
    # of 21 Oct 2026; pipeline/speaker_carry.py writes data/gazetteer/speaker_kept.csv), before the hand fixes and name unification
    kept = ROOT / "data" / "gazetteer" / "speaker_kept.csv"
    for r in (csv.DictReader(kept.open(encoding="utf-8")) if kept.exists() else []):
        con.execute("UPDATE segments SET speaker = coalesce(nullif(?, ''), speaker), delegation = coalesce(nullif(?, ''), delegation), "
                    "speaker_method = coalesce(nullif(?, ''), speaker_method) WHERE id = ?",
                    (r["speaker"], r["delegation"], r["speaker_method"], r["segment_id"]))
        con.execute("UPDATE segments_fts SET speaker = coalesce(nullif(?, ''), speaker), delegation = coalesce(nullif(?, ''), delegation) WHERE id = ?",
                    (fix_case(r["speaker"] or None) or "", r["delegation"], r["segment_id"]))
    # surnames the OCR garbled in a record whose roster has no entry for them, read from the page images by the speaker audit
    # (data/gazetteer/speaker_fixes.csv: segment, speaker, delegation if wrong too, note)
    fixes = ROOT / "data" / "gazetteer" / "speaker_fixes.csv"
    for r in (csv.DictReader(fixes.open(encoding="utf-8")) if fixes.exists() else []):
        con.execute("UPDATE segments SET speaker = ?, delegation = coalesce(nullif(?, ''), delegation), speaker_method = 'checked on the page image' "
                    "WHERE id = ?", (r["speaker"], r.get("delegation") or "", r["segment_id"]))
        con.execute("UPDATE segments_fts SET speaker = ?, delegation = coalesce(nullif(?, ''), delegation) WHERE id = ?",
                    (r["speaker"], r.get("delegation") or "", r["segment_id"]))
    merged = unify_speakers(con)
    print(f"{merged} spellings of delegates merged into their commonest form", file=sys.stderr)
    # the chair's turns: who presided, from the mastheads and the record's "took the Chair" (pipeline/chairs.py)
    import chairs
    print(f"{chairs.assign(con, normalize_delegation)} of the chair's turns named", file=sys.stderr)
    # (data/gazetteer/chair_kept.csv: chair's turns round 124's rules left unnamed that had the masthead's chairman before;
    # round 128's blind check found such blanks wrong; applied only where the turn is still unnamed)
    kept = ROOT / "data" / "gazetteer" / "chair_kept.csv"
    for r in (csv.DictReader(kept.open(encoding="utf-8")) if kept.exists() else []):
        con.execute("UPDATE segments SET speaker = ?, speaker_method = 'chair (masthead, kept from before round 124)' "
                    "WHERE id = ? AND kind = 'chair' AND (speaker IS NULL OR speaker = '')", (r["speaker"], r["segment_id"]))
    print(f"meeting dates read again from the scans: {sum(1 for _, old, d in DATE_LOG if old and d)} out of their series' "
          f"order corrected, {sum(1 for _, old, d in DATE_LOG if old and not d)} dropped, "
          f"{sum(1 for _, old, d in DATE_LOG if not old and d)} missing filled in", file=sys.stderr)
    # (the 1947 texts cut by hand-set anchors, pipeline/early_draft_texts.py, carry their final articles already,
    # and replace the automatic cut of the same stage and number where there is one)
    early_path = SEG / "_draft_texts_early.json"
    by_hand = {(d["stage"], str(d["draft_article"])) for d in json.loads(early_path.read_text())} if early_path.exists() else set()
    for name in ("_draft_texts.json", "_covenant_draft_texts.json", "_draft_texts_early.json"):
        dt_path = SEG / name
        if dt_path.exists():
            for d in json.loads(dt_path.read_text()):
                if name != "_draft_texts_early.json" and (d["stage"], str(d["draft_article"])) in by_hand:
                    continue
                fin = d["final_article"]
                if name == "_draft_texts.json" and d["stage"] in EARLY_STAGES:  # the concordance read by hand
                    fin = (conc.get((d["stage"], str(d["draft_article"]))) or (None,))[0]
                elif name == "_draft_texts.json" and (d["stage"], str(d["draft_article"])) in conc:
                    fin = conc[(d["stage"], str(d["draft_article"]))][0]  # overrides.csv corrects the text match
                con.execute("INSERT INTO draft_texts VALUES (?,?,?,?,?,?,?)", (d["stage"], d["stage_symbol"], d["draft_article"],
                            fin, d["page"], d["text"], d.get("instrument", "UDHR")))
    con.commit()
    con.close()
    print(f"{n_docs} records, {n_segs} segments -> {DB.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
