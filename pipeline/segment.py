#!/usr/bin/env python3
"""Split OCR'd summary records into segments: speeches, chair interventions, votes, headings.

Summary records (1946-54 mimeographed) follow a fixed pattern:
  masthead with symbol, date and the attendance list (page 1)
  "Article 16"                                  <- heading: the draft article under debate
  Mr. PAVLOV (Union of Soviet Socialist Republics) said that ...   <- speech
  He preferred the Drafting Committee's text.   <- same speaker, next paragraph
  The CHAIRMAN put to the vote ...              <- chair
  The proposal was rejected by 6 votes to 5, with 4 abstentions.   <- vote

A speech runs from a speaker opening to the next speaker, chair, vote or heading.
Each segment keeps the page it starts and ends on, for pinpoint citations.
Speakers and countries are kept as printed (raw OCR); resolving them against the
meeting's attendance list is entities.py's job.

Usage: python3 pipeline/segment.py E/CN.4/SR.60 [--engine layer] [--out data/segments]
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import safe_name  # noqa: E402
from normalize import DOC_NOTE_MARK, drop_french_runs, english_only, meeting_number, strip_furniture  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OCR = ROOT / "data" / "ocr"

# Titles as typed, plus the OCR confusions seen in the 1948 scans ("Ml'.", "MI.", "Hr.").
# with the OCR's usual misreadings of "Mr." ("My.", "Me,", "Mx,", "Kr.", "Mises" for "Miss"): the
# pattern that follows ("SURNAME (Country) said") keeps them from matching prose
# (and the audit's "Mir.", "Mya", "i'r.", and "The Marquis DE VALDEIGLESIAS (Spain)": segmentation audits, October 2026; "Mo,", round 97)
TITLE = (r"(?:M[rlI1iyexapo][s']?|Mir|Mya|i'r|Mi[gs]s|MIss|Mies|M(?=[:;])|Kr|Lr|Hr|Mrs|Miss|Mises|Mme|Mlle|Dr|Col|Colonel|Gen|General|Sir|Lord|Lady|Begum|Father|Prof|Professor|Judge|Major|Maj|Captain|Capt|Commander|Lieutenant|Ato|Tengku|Dato|Datuk|Raja|Shri|Haji|Madame|"
         r"Count|Countess|Baron|Prince|Princess|Sheikh|Sheik|Emir|Rev|Reverend|Ambassador|Senator|Dame|Rabbi|U|Sardar|Chief|(?:The\s+)?Marquis)")
# (a hyphen the OCR reads as a tilde: "Mr. MASSOUD~ANSARI (Iran)")
NAME = r"[A-Za-zÀ-ž](?:[A-Za-zÀ-ž'`\-~]|’(?=[A-Za-zÀ-ž]))+(?:\s+(?:de|da|del|la|le|van|von|y|[A-Za-zÀ-ž](?:[A-Za-zÀ-ž'`\-~]|’(?=[A-Za-zÀ-ž]))+)){0,3}?"  # ("D’SOUZA"; not "FOMIN’")
# capitals with diacritics, which the vision reader keeps ("Mr. JEVREMOVIĆ (Yugoslavia)", "Mr. SØRENSEN": 28 Oct 2026)
UC = "A-ZÀ-ÖØ-Þ" + "".join(c for c in map(chr, range(0x100, 0x180)) if c.isupper())
# From 1950 the records number their paragraphs, and OCR mangles the numbers: "8, Mr,",
# "- 33, Mr.", "56. _ Mr.", "bd, _ Mr." (61.), "uy Mr." The token before the title is
# allowed; it is kept as the paragraph number (the pinpoint) only when it is all digits.
# OCR debris around a paragraph number: ". Mr. DUKES", "23. | —«- Mr. ORIBE"
# a number without its full stop ("5h Mr. WHITLAM") only if it starts with a digit
# (the debris before a paragraph number is a few letters, but not a word that joins a sentence: "in reply to Mr. SAPOZHNIKOV
# (USSR)" wraps to a line that starts "to Mr. ...", A/C.3/SR.1076. "he", "it", "is", "be", "so" stay debris: the OCR's "13" is
# often "he Mr. MENDEZ (Philippines)")
PARA_NO = (r"(?:[-_–—~|'\"`.,:;+•«»“”‘’°*]+\s*)?(?:(?!(?:to|by|of|in|on|at|and|for|the)\s)[a-z'\"`~|]{1,3}\s+)?(?:(?P<n>\d\w{0,3}[°º]?(?=[-.,;]{0,3}\s)|\w{1,3}(?=\s*[.,;]))\s*[.,;]{0,3}\s*)?"
           r"(?:[-_–—~|•«»>.:/°'\"‘’“”][-_–—~|•«»>.:/°'\"‘’“”\s]*)?")  # one run of debris; no nested repeat (backtracking)
SPEAKER_RE = re.compile(
    rf"^\s*{PARA_NO}(?P<title>{TITLE})(?:[.,'`:;\-‘’»«•·]+\s*(?=[A-Z])|[.,'`:;\-‘’»«•·]*\s+)(?:[a-z|~'`]\s+)?['‘’\"]?(?:(?:[A-Z][.,]{{1,2}}\s*){{1,3}})?(?P<name>{NAME})[.:;'’`•·]*\s*"  # "Mr. CASSIN: (France)", "M:. AMADO", "Mr, A. A, MOHAMMED"
    rf"[({{\[](?P<country>[^(){{}}\[\]\n]{{2,100}})[)}}\]](?:\s*\((?P<role>[^()\n]{{2,40}})\))?"  # "(Director-General of the Food and ...)", "(Madagascar}"
)
# a title after the name: "AZMI Bey (Egypt)", "ZAFRULLAH KHAN Pasha": the surname in capitals
POSTTITLE_RE = re.compile(rf"^\s*{PARA_NO}(?P<name>[{UC}][{UC}'\-]{{1,}}(?:\s+[{UC}][{UC}'\-]+)?)\s+(?P<title>Bey|BEY|Bay|Pasha|PASHA|Pacha)[.,]?\s*"
                          rf"\((?P<country>[^()\n]{{2,100}})\)(?:\s*\((?P<role>[^()\n]{{2,40}})\))?")
# "The CHAIRMAN", including OCR variants such as "CHAIRMAH", "CHAIEMAN", and the printed
# records' small capitals ("The Carman", "The CHaIrman"). Not the
# possessive: "The Chairman's ruling was accepted by 6 votes" is a vote. The Rapporteur as the OCR misreads him ("The RAPPORITUR
# cesd the full text", "The RAPPORTHOR noted") only with the turn's words after the role, not a masthead's "The RAPPORIEUR" (round 96).
# A sign for a letter in the typed records: "Tho CHAIRM‘N, as representative of", "The CPAJRM{N. speaking as" (round 97).
CHAIR_RE = re.compile(r"^\s*(?:[-_–—~|'\"`“”‘’•«»°,;+]+\s*)?(?:[a-z'\"`~|]{1,3}\s+)?(?:(?P<n>\w{1,3})\s*[.,]{1,3}\s*)?"
                      r"(?:[-_–—~|>.:'\"‘’“”•«»°]+\s*)*(?:[Pp]a[gs]e\s*\d{1,3}\s+)?T(?:he|ho|ae|hu)\.?\s+(?P<role>CHA[IL1][RE][MVN]A[NH]|CHA[A-Z1l][A-Za-z1l]?[A-Z]?MA[NH]|[CG][A-Z]?A[A-Z1l][RE]MA[NH]|CHA[A-Z1l][RE]M[I1l]N|C[HP][A/][IJ1l][RE]M[A‘'{/]N|Chairman|(?i:c[hn]?a[il1]?r?ma[nh])|PRES[IL1]DENT|President|Pres[il1][a-z]{1,2}ent|"
                      r"SECRETARY(?!-?\s?GENERAL(?!\s*[:(]))|Secretary(?!-?\s?[Gg]eneral(?!\s*[:(]))|RAPPORTEUR|RAPPOR[A-Z1l]{2,4}R(?=[\s,]+[a-z(])|Rapporteur)\b(?!['’]s)")  # (not "The Secretary-General's report": round 95)
# a chair turn opened by a phrase, in a record that numbers its paragraphs ("31. In accordance with the request of the Japanese
# representative, the CHAIRMAN put ..."; "6. In answer to a question from Mr. AZNAR (Spain), the CHAIRMAN stated"): the number
# is required, and the chair must do something right after the phrase (a mention of "the Chairman's suggestion" is not a turn)
CHAIR_PHRASE_RE = re.compile(rf"^\s*{PARA_NO}(?:[A-Z](?:[^.;()\n]|\b(?:Mr|Mrs|Dr|Sir)\.){{2,100}}?(?:\([^()\n]{{2,60}}\))?[^.;()\n]{{0,30}},\s+)"
                             r"(?:the|The)\s+(?P<role>CHAIRMAN|CHAIR-?\s?MAN|PRESIDENT)\s+(?:then\s+|also\s+)?"
                             r"(?:said|suggested|pointed|proposed|noted|announced|recalled|observed|stated|thought|asked|replied|invited|declared|"
                             r"explained|informed|drew|reminded|put|felt|considered|ruled|understood|took|indicated|clarified|appealed|called|withdrew|read|agreed|accepted)\b")
# "Article 16", "Article 16 (continued)", "ARTICLE 16": a heading line, not prose.
# (and a heading for several: "Articles 5, 6 and 7", "Articles 17 and 18": the first number, as build_concordance does)
# (the OCR's "Artigle 18 | So | Be" and "Articlo 9": the word with a letter misread, and a few letters of margin after it)
# (round 89: "Examination of Article 9", the OCR's "Bxu.aation of Article 10"; "Article 1A" for 14)
# (a speck read as dots or colons before the heading: ".:.Article 25 :." heading the second page of A/C.3/266, 46 such lines in all)
ARTICLE_HEAD_RE = re.compile(r"^\s*(?:[_|•.:;]{1,4}\s*)?(?:(?:Examination|Discussion|Consideration|[A-Z][\w.]{1,6}ation)\s+of\s+(?:the\s+)?)?"
                             r"(?:Arti[cg]l[eo]s?|Artic1es?|ARTICLES?|Art\.)\s+(?P<art>[\dIl](?:[\dIl]|A(?![a-z]))?[a-z]?)(?:\s*(?:,|and|&)\s*[\dIl]{1,2}[a-z]?)*"
                             r"(?:\s*,\s*paragraph\s+[\dIl]{1,2})?"  # ("Article 2, paragraph 2.", E/CN.4/SR.74; "• Article 8", E/CN.4/SR.142)
                             r"\s*(?:\((?:discussion\s+)?(?:continued|cont\.?)\))?"
                             # (the documents before the Commission, underlined with it: "Article 15 (E/CN.4/365, E/CN.4/353/Add.10)")
                             r"(?:\s*\((?:[Dd]ocuments?\s+)?[AEB8]\s?/[^()\n]{2,90}(?:\)|$)(?:\s*\((?:discussion\s+)?(?:continued|cont\.?)\))?)?"
                             # (and the explanations of vote that follow it: "Article 5 (continued) : explanation of vote : : ;", round 87)
                             r"(?:\s*[:;,.\-–—]\s*explanations?\s+of\s+votes?)?"
                             r"\s*[.:;}\])|»«,\s]*(?:\s*\|\s*[A-Za-z]{0,2})*\s*$")
# the Commission's second reading (1950, E/CN.4/SR.200): "Article 13 (former article 16) (E/CN.4/L.10, page 27)", the OCR
# "Article 1k (former articl:: 17)": the article of the first reading's text (E/1371) is the number that counts
SECOND_READING_HEAD_RE = re.compile(r"^\s*Art\w{3,6}\s+[\dIlkh]{1,2}\s*\(\s*f\w{3,6}\s+art\w{3,6}\W{0,3}\s*(?P<art>[\dIl]{1,2})\s*\)"
                                    r"(?:\s*\([^)]*\)?)?\W*$", re.I)
# Votes: "adopted by 10 votes to 2, with 3 abstentions", "rejected by 6 votes to 5", "adopted unanimously"
N = r"[\dOolI^h]{1,2}"
VOTE_RE = re.compile(rf"\b(?:was|were)[\s.]+(?P<outcome>adopted|rejected|accepted|approved|carried|defeated|upheld|overruled)\b"
                     rf"(?:\s+by\s+(?P<yes>{N})\s+votes?\s+to\s+(?P<no>{N})(?:,?\s+with\s+(?P<abst>{N})\s+abstentions?)?"
                     rf"|\s+unanimously)?", re.I)
MEETING_ROSE_RE = re.compile(r"^\s*The meeting rose at", re.I)
# A result printed in italics on its own line closes the speech before it. Found by the segmentation audit (October 2026): the
# result was left inside the speech or the chair's turn when it began "Point 2 ...", "Part (b) ...", "The words ..." or ended
# "were retained", or when its wording ran onto a second line.
# (round 86: the typed records' label before it, "DECISION: The amendment was rejected", "Recision:", and up to three marks: "- . The")
RESULT_OPENER_RE = re.compile(r"^\s*(?:[^\w\s]+\s*){0,3}(?:(?:DECISION|Decision|Recision|Dacision)\s*[:;,.]\s*(?:[^\w\s]+\s*)?)?(?:The|Articles?|Paragraphs?|Parag[a-z]{2,4}|Points?|Parts?|Sub-?paragraphs?|Sub-?amendments?|Amendments?|Words|Motion|Draft|Documents?|"
                              r"Sections?|Text|Proposals?|That|It|This|Those|Both|All|These)\b")  # ("Both suggestions were adopted.", round 95)
# (also as "DEOISTON:", and alone on its line above the result: "Decision;" / "This text was adonted by three votes"; round 87)
# (a label, capitalised and followed by a colon: not the word in a sentence, "decision, which was a violation of ...")
DECISION_LABEL_RE = re.compile(r"^\s*(?:[^\w\s]+\s*){0,3}(?:DECISION\s*[:;,.]|[IlB1]ECISION\s*[:;]|(?:Decision|Recision|Dacision|D(?i:[eo][co0]is[it1][o0]n))\s*[,.]?\s*[:;])\s*(?:\S|$)")  # ("Decision,;")
# the underlined decision on a line of its own ("It was so agreed.", "It was so decided."): the Commission's or the Committee's,
# not the speaker's before it (the segmentation audit, October 2026)
DECISION_RE = re.compile(r"^\W{0,3}(?:It|That|This)\s+was\s+(?:(?:[sz]o|50)\s+)?(?:agreed|decided)\W{0,6}\s*(?:\d/)?\s*$")  # ("It was zo decided.", "It was so agreed, 2/")
# headings printed between the turns: "Paragraphs 22 to 26" (the adoption of a draft report, paragraph by paragraph) and a line
# in capitals ("MIGRATION", "PROPOSAL TO HOLD A SPECIAL SESSION OF THE ECONOMIC AND SOCIAL COUNCIL."): their own segment,
# marked "agenda" so that api/build_db.py does not read them as the draft article under debate
PARA_HEAD_RE = re.compile(r"^\s*\W{0,2}(?:(?:Paragraphs?|Sub-?paragraphs?|Sections?|Chapter)\s+[\dIl]{1,3}[a-z]?(?:\s*\([a-z0-9]+\))*"
                          r"(?:\s*(?:to|and|-|–)\s*[\dIl]{1,3}[a-z]?)*"
                          # ("First Paragraph", "Fourth paragraph": E/CN.4/SR.12, A/C.3/SR.911; with a colon it heads a list of amendments)
                          r"|(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Last)\s+[Pp]ar[a-z]{3,6}ph)\s*\.?\s*$")  # ("Second Pararrraph", E/CN.4/SR.12)
# the verbatim plenary records (A/PV, E/PV) print the stage directions in brackets and the decision as its own line, between the
# President's and the speakers' turns: "(A vote was taken by a show of hands ...)", "(The meeting was adjourned at 4.45 p.m.)",
# "Decision: Paragraph 4 (f) of the resolution of the General Committee was adopted."
STAGE_RE = re.compile(r"^\W{0,2}\((?:A vote was taken|The meeting (?:was\s+)?(?:adjourned|rose|resumed|suspended|called)|[^()]{0,50}took the Chair)"
                      r"|^\W{0,2}Decision\s*[:;]", re.I)
SENT_END_RE = re.compile(r"[.,;:!?)\"”’•·]\s*$")  # (the comma, and "•": the OCR's period, "It was so decided,", "paragraph 5•")
CAPS_STOP = {"ASSEMBLY", "COUNCIL", "GENERAL", "NATIONS", "UNITED", "NEW YORK", "GENEVA", "PRESENT", "ENGLISH", "FRENCH", "ORIGINAL",
             "ECONOMIC", "SOCIAL", "COMMISSION", "COMMITTEE", "SUMMARY", "RECORD", "CONTENTS", "ANNEX", "ARTICLE"}


def caps_line(ln: str) -> bool:
    """A line printed in capitals that can be a heading: not a name, a list of countries or running head."""
    t = ln.strip()
    letters = re.sub(r"[^A-Za-z]", "", t)
    if len(letters) < 5 or len(t) > 130 or t.count(",") >= 2 or t.upper().strip(" .,;:") in CAPS_STOP:
        return False
    if sum(c.isupper() for c in letters) / len(letters) < 0.9 or re.search(r"CHAIRMAN|PRESIDENT|\bMr\b|\bMrs\b|\bMiss\b", t):
        return False
    # not a running head the OCR garbled ("E/CN.VSR.31*"), nor a speaker's line whose title it garbled ("157. Me. SANTA CRIT."),
    # nor an article heading (those have their own path: the 1948 headings with a footnote digit, "ARTICLE 101"), nor debris
    if re.match(r"^\W{0,3}[A-Z£]{1,3}\s?[/|]", t) or re.match(r"^\W*(?:\d{1,3}\s*[.,]\s*)?\W*(?:[A-Za-z]{1,3}[.,]|[|^•/][A-Za-z]{1,3}\.?)\s*[A-Z]{3,}", t) \
            or re.match(r"^\W*ART[I1l]CLES?\b", t):
        return False
    words = re.findall(r"[A-Za-z0-9]+", t)
    if any(re.search(r"[A-Za-z]", w) and re.search(r"\d", w) for w in words) \
            or sum(len(w) >= 3 and w.isalpha() for w in words) < 0.6 * sum(w.isalpha() for w in words):
        return False
    return bool(re.search(r"[A-Z]{3}", t)) and not re.match(r"^[A-Z]{1,3}[/. ]?\d", t) and (len(t.split()) >= 2 or len(letters) >= 6)


# the printed records' agenda item between the turns ("AGENDA ITEM 35" / "Draft Convention on Freedom of Information (A/AC.42/7
# and Corr.1, ...)"), and the headings the typed records underline between the turns, in ordinary letters ("Draft resolution B
# (continued)", "Paragraph 3 of the Philippine amendment in document E/CN.4/253", "III. Item 5 on the Agenda: Relations with the
# Trusteeship Council", "Programme of work of the Committee"; the plenary's "116. Draft universal declaration of human rights:
# report of the Third Committee (A/777)"). Found by the segmentation audits (rounds 68 and 72): left at the end of the turn before.
AGENDA_ITEM_RE = re.compile(r"^\W{0,3}AGENDA\s+ITEMS?\s+\d")
SUBHEAD_START_RE = re.compile(r"^[^\w\"“”'‘’]{0,2}(?:(?:[IVX]{1,4}|\d{1,3})\s*\.\s+|[({](?:[a-z]|[ivxl1]{2,4}|\d{1,2})\)\s+)?(?:Draft|Articles?|(?:Additional|New|Proposed)\s+(?:additional\s+)?articles?|Paragraphs?|Sub-?paragraphs?|Items?|Agenda|Programme|"
                              r"Organi[sz]ation|Report|Election|Consideration|Continuation|Question|Proposals?|Amendments?|Award|Communications?|"
                              r"Adoption|Discussion|Chapter|Parts?|Sections?|Preamble|Measures|Recommendations?|Annex|Statement|Resolution|"
                              r"Procedure|Order|Date|Arrangements|Admission|Status)\b")
FINITE_VERB_RE = re.compile(r"\b(?:was|were|is|are|be|been|had|has|have|would|should|could|will|shall|may|might|said|stated|thought|felt|"
                            r"asked|did|does|agreed|proposed|considered|noted|wished|recalled|suggested|pointed|explained|referred|"
                            r"believed|hoped|took|put|called|declared|decided|requested|supported|opposed|moved|"
                            # (a result, also as the OCR reads "was": "Paragraph 2 of the USSR amendment wes rejected"), and verbs of a
                            # sentence that only opens like a heading ("Article 7 served its purpose perfectly as it stood")
                            r"wes|adopted|rejected|retained|deleted|approved|carried|accepted|withdrawn|served|stood|seemed|appeared|"
                            r"contained|provided|meant|dealt|covered|went|came|made|gave|read|reads|means|contains|provides|deals|covers)\b", re.I)


HEADING_PARTICIPLES = {"continued", "concluded", "submitted", "revised", "amended", "proposed", "united", "related", "concerned",
                       "entitled", "based", "recommended", "presented", "prepared", "transmitted", "annexed", "received", "resumed",
                       "deferred", "postponed", "designed", "established", "adopted", "selected", "associated", "specialized"}


def prose_left(t: str) -> bool:
    """What a sentence has and a heading has not, outside the brackets: a semicolon, or a verb in -ed ("Paragraphs 1 and 2 of the
    article categorically prohibited slavery, the slave-trade and servitude; paragraph")."""
    rest = re.sub(r"\([^()]*\)?", " ", t)
    return ";" in rest or any(w.lower() not in HEADING_PARTICIPLES for w in re.findall(r"\b([A-Za-z]{3,}ed)\b", rest)[0:] if w[0].islower())


# the agenda's sub-items of 1951-53 name their sponsor: "(1) Additional article proposed by the Chilean delegation (E/CN.4/L.247)"
# ("(7) Proposed additional article to Part IV submitted by the Philippine delegation")
SPONSOR_RE = re.compile(r"\b(?:proposed|submitted)\s+by\s+the\s+(?:[A-Z][\w-]*\s+){1,4}delegations?\b|^\W{0,2}(?:\(\w{1,4}\)\s+)?Proposed(?=\s+(?:additional\s+|new\s+)?articles?\b)")


def subhead_line(ln: str) -> bool:
    """A heading in ordinary letters: short, opened by a heading's word, with no verb that would make it a sentence."""
    t = ln.strip()
    return 2 <= len(t.split()) <= 24 and not prose_left(t) and len(t) <= 160 and bool(SUBHEAD_START_RE.match(t)) \
        and not FINITE_VERB_RE.search(SPONSOR_RE.sub(" ", t)) \
        and not re.search(r"[.;:!?]\s+[a-z]", t) and not re.search(r"\.\s*$", re.sub(r"\((?:continued|concluded)\)\.?\s*$", "", t)) \
        and not re.match(r"^\W{0,2}\d{1,3}\s*\.\s+(?:Articles?|Paragraphs?)\b", t)


# a heading in ordinary letters that names one article sets it, as an article heading does ("5. Discussion of Article 8, Paragraph
# 3, Sub-Paragraph (a)", "Article 2 Paragraph (a) (Document E/CN.4/AC.1/26)", "Discussion of the First Sentence of Article 13")
SUBHEAD_ARTICLE_RE = re.compile(r"^\W{0,2}(?:[IVX\d]{1,4}\s*\.\s+|\((?:[a-z]|[ivxl1]{2,4}|\d{1,2})\)\s+)?(?:(?:Discussion|Consideration|Examination|Adoption)\s+of\s+)?(?:the\s+)?"
                                r"(?:(?:First|Second|Third)\s+Sentence\s+of\s+)?Article\s+(?P<art>\d{1,2})\b(?!\s*(?:to|and|-|–|,\s*\d)\s*\d)", re.I)


def subhead_cont(ln: str) -> bool:
    """A line that carries a heading on (its title, its documents, its session): short, no verb, not a turn (nor the chair's
    turn the OCR garbled past reading: "Ah Phe OTATRWAN Invited the representative of Lebanon")."""
    t = ln.strip()
    # (nor a speaker's opening whose verb is on the next line: "Sir Mohammed ZAFRULLAH KHAN (Pakistan)" / "recalling ...")
    if re.search(r"\b(?:Mr|Mrs|Miss|Sir|Dr|Begum|Mme)\b\.?,?\s+[A-Z][\w'\-]+(?:\s+[A-Za-z][\w'\-]+){0,3}\s*[({\[][A-Z][^()]{2,60}[)}\]]", t):
        return False
    return 0 < len(t.split()) <= 16 and not FINITE_VERB_RE.search(t) and not opens_turn(t) and not prose_left(t) \
        and not re.search(REPORT_VERBS + r"|\b(?:invited|resumed|opened|announced|welcomed|thanked)\b", t) \
        and not re.search(r"(?:^|\s)(?:The|Phe|Tho|Tne|Ths)\s+[A-Z][A-Za-z]{4,}", t)


def opens_turn(ln: str, numbered: bool = True) -> bool:
    """A line that opens a turn or a heading, or (numbered) a numbered paragraph. After a heading a turn must follow: a numbered
    paragraph can be the rest of the speech a running head the OCR garbled cut ("Draft Human Rights" / "2, Her delegation ...")."""
    return classify(ln)[0] in ("speech", "chair", "heading", "closing") or numbered and bool(re.match(r"^\s*\W{0,2}\d{1,3}\s*[.,]\s+\S", ln))


def agenda_heading_lines(body: list[tuple[int, str]], idx: int, prev: str) -> int:
    """How many lines from body[idx] are a heading between two turns, or 0. The line before must end a sentence."""
    ln = body[idx][1].strip()
    if not SENT_END_RE.search(prev.rstrip()):
        return 0
    if PARA_HEAD_RE.match(ln):
        return 1
    if AGENDA_ITEM_RE.match(ln) or subhead_line(ln):
        n = 1
        # an agenda item runs on to the next turn (its title and documents); a sub-heading takes at most a line or two more like it
        while idx + n < len(body) and n < 8 and not opens_turn(body[idx + n][1]) and \
                (AGENDA_ITEM_RE.match(ln) or (n < 6 and subhead_cont(body[idx + n][1])) or caps_line(body[idx + n][1])):
            n += 1
        nxt = body[idx + n][1].strip() if idx + n < len(body) else ""
        if opens_turn(nxt, numbered=False) or RESULT_OPENER_RE.match(nxt) and RESULT_RE.search(nxt) or STAGE_RE.match(nxt) or DECISION_RE.match(nxt):
            return n
        return 0
    if not caps_line(ln):
        return 0
    n = 1
    while idx + n < len(body) and n < 4 and (caps_line(body[idx + n][1]) or re.match(r"^\(.{2,80}\)\.?$", body[idx + n][1].strip())):
        n += 1
    nxt = body[idx + n][1] if idx + n < len(body) else ""
    # a heading is followed by a turn, a result or another heading: an all-capitals line inside a speech is not
    if classify(nxt)[0] or RESULT_OPENER_RE.match(nxt) and RESULT_RE.search(nxt):
        return n
    return 0
# (the typed records' OCR: "wes rejected", "vas accepted", "wag. adopted", "reJectod"; round 86)
WAS = r"(?:was|were|wes|vas|wag|wae|ves)"
RESULT_VERB = (r"(?:adopted|rejected|accepted|approved|carried|defeated|retained|deleted|maintained|withdrawn|upheld|overruled"  # ("The Chairman's ruling was upheld by 12 votes to 5", round 97)
               r"|a[dn]o[pn]?t[eco][dc]|r[eo][jJst][eoc]?ct[eoa][dc])")  # (round 87: "adonted", "adoptec", "resected", "rotected")
RESULT_RE = re.compile(rf"\b{WAS}[\s.]+(?:not\s+)?(?:unanimously\s+)?{RESULT_VERB}(?![A-Za-z])")  # ("adopted_as amended", round 94)  # ("was unanimously adopted", round 89)
# the body's own decision with its count: "The Commission refused to receive the Polish amendment by 8 votes to 3" (round 85)
BODY_RESULT_RE = re.compile(r"^\W{0,3}The\s+(?:Commission|Committee|Sub-?Commission|Working\s+(?:Group|Party)|Drafting\s+Committee)\s+"
                            r"(?:then\s+)?(?:adopted|rejected|refused|decided|agreed|approved|accepted)\b[^\n]{0,160}?\bby\s+\S+\s+votes?\b")
# (the count can come after a few words, "were retained in paragraph 1 by 55 votes to 10", or as "17 votes being cast in favour")
RESULT_FIGURES_RE = re.compile(rf"\b{WAS}[\s.]+(?:not\s+)?{RESULT_VERB}"
                               r"(?:[^.\n]{0,60}?\s+by\s+\S+\s+votes?\b|\s+unanimously|,\s*\S+\s+votes?\s+being\s+cast)")
# "Mr. X (Country), Vice-Chairman, took the Chair.": a note, not a speech (the chair's name is read from it: pipeline/chairs.py)
CHAIR_NOTE_RE = re.compile(r"^\W{0,3}(?:,?\s*(?:Vice-?\s*Chairman|Vice-?\s*President|Rapporteur|Chairman|President))?,?\s*"
                           r"(?:took|resumed|occupied)\s+the\s+[Cc]hair\b")
# an election, "Miss Imru (Ethiopia) was elected Vice-Chairman by acclamation": 'was' is a turn's verb, but the line is the
# body's decision, not a speech (round 109's audit on page images)
ELECTED_RE = re.compile(r"^\s*[.,]?\s*(?:was|were|had\s+been)\s+(?:unanimously\s+)?(?:re-?\s?)?elected\b")
# The body can open with the meeting itself rather than a speaker (1947 layout:
# "1. Opening Remarks" / "The meeting was called to order by ...").
OPENING_RE = re.compile(r"^\s*(?:\d{1,2}\s*\.\s+[A-Z][A-Za-z ,'\-]{3,70}$|The meeting (?:was called to order|was opened|opened))")
# Body starts after the masthead/attendance list.
BODY_START_RE = re.compile(r"\b(said|stated|opened the meeting|called|proposed|invited|pointed out|recalled|"
                           r"submitted|explained|thought|put to the vote|decided|asked|suggested|supported|wished|"
                           r"welcomed|noted|observed|considered|believed|felt|expressed|emphasized|agreed|opposed|"
                           r"paid|wondered|drew|remarked|introduced|reminded|moved|requested|hoped|regretted|announced)\b")

# A turn the OCR ran into the line before ("... other functions. . Mz. DEHOUSSE (Belgium) stated ...") or whose title it
# garbled ("Mc, MAYHEW (United Kingdom) thought", "bir. NISOT (Belgium) asked", "Mee Mr. RAMADAN (Egypt) thought"), and a
# turn opened by a phrase ("In reply to Mr. RAMADAN (Egypt), Mr. CASSIN (France) thought", "At the CHAIRMAN's request
# Mr. HUMPHREY (Secretariat) explained"): a surname in capitals, a delegation in brackets (letters only) and a reporting
# verb right after. Found by the segmentation audit on page images (eval/segment_audit_sample.py, October 2026): a
# turn in six was inside the speech before it.
REPORT_VERBS = (r"(?:said|stated|thought|considered|asked|agreed|replied|recalled|explained|thanked|proposed|moved|pointed|"
                r"supported|observed|suggested|felt|noted|wished|believed|declared|emphasi[sz]ed|stressed|urged|requested|"
                r"expressed|welcomed|opposed|announced|associated|withdrew|introduced|referred|remarked|maintained|regretted|"
                r"shared|wondered|objected|accepted|endorsed|insisted|questioned|added|drew|hoped|feared|reminded|submitted|reserved|"
                r"presented|congratulated|paid|deplored|doubted|preferred|favou?red|argued|contended|claimed|indicated|read|"
                r"could|would|did|was|had)\b")
TURN_PREFIX = (r"(?:(?:In reply to|In answer to|Replying to|Answering|In response to)\s[^()\n]{3,70}?(?:\([^()\n]{2,60}\))?,\s+|"
               r"At the (?:CHAIRMAN|Chairman)['’]?s request,?\s+|"
               r"(?:Speaking )?[Aa]t the (?:request|invitation) of [^()\n]{3,60}?(?:\([^()\n]{2,60}\))?,\s+|"
               r"(?:On|At) the (?:suggestion|proposal|motion) of [^()\n]{3,60}?(?:\([^()\n]{2,60}\))?,\s+)")
# words that continue a sentence, not a debris token or a title: "and Mr. JEVREMOVIC (Yugoslavia) said" ends a joint
# statement whose start is on the line before
NOT_TITLE = r"(?i:and|or|by|of|to|the|in|as|for|with|from|if|when|since|while|because|although|though|that)\s"
# others speaking with the first: "Mr. NISOT (Belgium) and Mr. CASSIN (France) agreed"
JOINT = r"(?:,?\s+(?:and\s+)?(?:[A-Za-z]{1,4}[.,]{0,2}\s+){1,2}[" + UC + r"][" + UC + r"'\-]{2,}(?:\s+[" + UC + r"][" + UC + r"'\-]+){0,2}\s*\([A-Z][A-Za-z .,'\-]{2,70}\)){0,6}"
TURN_CORE = (r"(?:(?!" + NOT_TITLE + r")[A-Za-z]{1,4}[.,:;]{0,2}\s+){0,2}[" + UC + r"][" + UC + r"'\-]{2,}(?:\s+[" + UC + r"][" + UC + r"'\-]+){0,2}"
             r"\s*\([A-Z][A-Za-z .,'\-]{2,70}\)(?:\s*\([^()\n]{2,40}\))?" + JOINT + r"\s+" + REPORT_VERBS)
MIDTURN_RE = re.compile(rf"^\s*{PARA_NO}(?:[.,]\s*)?(?:[Pp]a[gs]e\s*\d{{1,3}}\s+)?(?:{TURN_PREFIX})?(?!{NOT_TITLE})(?:[A-Za-z]{{1,4}}[.,:;]{{0,2}}\s+)?(?!{NOT_TITLE})(?P<title>[A-Za-z]{{1,4}})[.,:;]{{0,2}}\s+"
                        rf"(?P<name>[{UC}][{UC}'\-]{{2,}}(?:\s+[{UC}][{UC}'\-]+){{0,2}})\s*\((?P<country>[A-Z][A-Za-z .,'\-]{{2,70}})\)"
                        rf"(?:\s*\((?P<role>[^()\n]{{2,40}})\))?(?={JOINT}\s+(?:[a-z]{{3,}}ly\s+)?{REPORT_VERBS})")
# (a title is needed: a surname alone at the start of a line is the rest of a line that ended with the title or with a
# joint statement, "In reply to Mr. PAZWAK (Afghanistan), Mrs. / ROOSEVELT (United States of America) said")
# where such a turn starts inside a line: after the end of a sentence, a little debris and a paragraph number
# (inside a line, also: a title of more than four letters, "Major DUKES (United Kingdom) recalled", "64, Ato Haddis
# ALEMAYEHOU (Ethiopia) wondered"; a full stop after the name or the delegation, "JEVREMOVIC. (Yugoslavia). supported"; an
# adverb before the verb, "Mr. JUVIGNY (France) formally proposed"; more debris, "2300- » Mrs. MEHTA (India)": the misses of
# the audit on random pages of round 80)
SPLIT_CORE = (r"(?:(?!" + NOT_TITLE + r")(?:[A-Za-z]{1,4}|[A-Z][a-z]{2,9})[.,:;]{0,2}\s+){0,2}[" + UC + r"][" + UC + r"'\-]{2,}(?:\s+[" + UC + r"][" + UC + r"'\-]+){0,2}"
              r"[.,•·]?\s*\([A-Z][A-Za-z .,'\-]{2,70}\)[.,]?(?:\s*\([^()\n]{2,40}\))?" + JOINT + r"\s+[‘'`\"]?(?:[a-z]{3,}ly\s+)?" + REPORT_VERBS)
# (a title after the name inside a line: '... a punishable offence." AZMI Bay (Egypt) was unable to accede', round 93)
POSTTITLE_CORE = (r"[" + UC + r"][" + UC + r"'\-]{2,}(?:\s+[" + UC + r"][" + UC + r"'\-]+)?\s+(?:Bey|BEY|Bay|Pasha|PASHA)[.,]?\s*\([A-Z][A-Za-z .,'\-]{2,70}\)[.,]?\s+"
                  r"(?:[a-z]{3,}ly\s+)?(?:was\s+unable|" + REPORT_VERBS[3:])
# (the printed records' small capitals, read as "Mr: Morozov (Union of Soviet Socialist Republics) wished": a strict title, a surname
# in upper and lower case, the delegation and a reporting verb; round 87)
PRINTED_CORE = (r"(?:Mr|Mrs|Miss|Mme|Dr|Sir|Professor|Prof)[.,:;]{0,2}\s+(?:[A-Z][a-z]+\s+)?[A-Z][a-z]{2,}(?:[- ][A-Z][a-z]{2,}){0,2}"
                r"\s*\([A-Z][A-Za-z .,'\-]{2,70}\)[.,]?\s+(?!(?:had|was|were)\s+(?:been\s+)?(?:elected|appointed|nominated|re-elected)\b)"
                r"(?:[a-z]{3,}ly\s+)?" + REPORT_VERBS)
# (and the typed records' turns that give no delegation, "... was included. Prof. CASSIN remarked that ...": a strict title, a
# surname in capitals, a reporting verb right after; round 85)
NOCOUNTRY_CORE = (r"(?:Mr|Mrs|Miss|Mme|Prof|Professor|Dr|Sir|Colonel|Col|General|Major|Begum)[.,]?\s+(?:[A-Z][a-z]+\s+)?[" + UC + r"][" + UC + r"'\-]{3,}(?:\s+[" + UC + r"][" + UC + r"'\-]{2,})?"
                  r",?\s+(?:[a-z]{3,}ly\s+)?(?!(?:could|would|did|was|had)\b)" + REPORT_VERBS)
TURN_SPLIT_RE = re.compile(rf"(?<=[.;:!?\"”’])\s+(?=(?:[^A-Za-z\s]{{1,6}}\s*){{0,3}}(?:[Pp]a[gs]e\s*\d{{1,3}}\s+)?(?:\d{{1,3}}\s*[.,]\s*[.,]?\s*)?(?:{TURN_PREFIX})?(?:{SPLIT_CORE}|{NOCOUNTRY_CORE}|{PRINTED_CORE}|{POSTTITLE_CORE}))")
NOCOUNTRY_RE = re.compile(rf"^\s*{PARA_NO}(?P<title>Mr|Mrs|Miss|Mme|Prof|Professor|Dr|Sir|Colonel|Col|General|Major|Begum)[.,]?\s+(?:[A-Z][a-z]+\s+)?"
                          rf"(?P<name>[{UC}][{UC}'\-]{{3,}}(?:\s+[{UC}][{UC}'\-]{{2,}})?),?(?=\s+(?:[a-z]{{3,}}ly\s+)?(?!(?:could|would|did|was|had)\b){REPORT_VERBS})")


# the chair's turn inside a line: with its paragraph number in the printed records ("... article 8. 33. The CHAIRMAN
# said"), or the verbatim plenary's "The PRESIDENT:" (the audit's cases: A/C.3/SR.1446, A/PV.7)
CHAIR_SPLIT_RE = re.compile(r"(?<=[.;:!?\"”’])\s+(?=(?:"
                            # (a numbered paragraph opened by a phrase, the chair after it: "38. After a procedural discussion in which
                            # Mr. X (Sierra Leone) took part, the CHAIRMAN suggested", round 90)
                            r"\d{1,3}\s*[.,]\s*(?:After|In\s+reply|In\s+answer|Replying|At\s+the\s+request)\b(?:[^.;]|(?<=Mr)\.|(?<=Dr)\.|(?<=Mme)\.|(?<=Mrs)\.|(?<=Sir)\.){0,250}?,\s+the\s+(?:CHAIRMAN|Chairman)\s+"
                            r"(?:said|suggested|pointed|proposed|noted|announced|recalled|observed|stated|asked|replied|ruled|put|invited)\b|"
                            r"\d{1,3}\s*[.,]\s*The\s+(?:CHAIRMAN|Chairman|PRESIDENT|President)\s+"
                            r"(?:said|suggested|pointed|proposed|noted|announced|recalled|observed|stated|thought|asked|replied|"
                            r"invited|declared|explained|informed|drew|reminded|put|felt|considered|ruled|understood|took)\b"
                            r"|The\s+PRESIDENT\s*:"
                            # the typed records' chair, with no paragraph number but in capitals ("... without comment. Tho
                            # CHAIRMAN said that"), and the plenary's "The PRESIDENT (Translation from the French):"
                            r"|T[a-z]{1,2}\s+CHAIRMAN\s+(?:then\s+)?(?:said|suggested|pointed|proposed|noted|announced|recalled|observed|stated|asked|"
                            r"replied|invited|declared|explained|informed|drew|reminded|put|ruled|objected|agreed|urged|thanked)\b"
                            r"|T[a-z]{1,2}\s+P[A-Za-z]{5,8}\s*\(Translation[^()\n]{0,40}\)\s*:"
                            r"|(?:Mr|Mrs|Sir|Dr)[.,]?\s+[A-Z][\w'’\-]+(?:\s+[A-Z][\w'’\-]+){0,3}\s*\([A-Z][^()\n]{2,50}\)\s*\(Translation[^()\n]{0,40}\)\s*:))")


# the chair speaking right after a decision, in a record that numbers no paragraphs ("... It was so agreed. The CHAIRMAN suggested ...")
CHAIR_AFTER_DECISION_RE = re.compile(r"\b(?:agreed|adopted|rejected|decided|approved|carried|abstentions?)\.\s+(?=The\s+(?:CHAIRMAN|Chairman)\s+"
                                     r"(?:said|suggested|proposed|asked|invited|pointed|noted|announced|recalled|observed|stated|put|drew|reminded|"
                                     r"read|declared|explained|informed|ruled|thought|felt|considered|took|then)\b)")


# Notes and decisions the printed records set apart (underlined or in italics), which the OCR can run into the line of the turn
# before; found by the segmentation audit on page images (round 68, October 2026: the largest class of its errors). A roll-call
# block ("A vote was taken by roll-call. ... In favour: ... Against: ...", "At the request of the representative of Haiti, a vote
# was taken by roll-call"), the meeting suspended or resumed, a member taking the chair, and a decision by a count of votes.
ROLL_CALL_RE = re.compile(r"(?:At\.?\s+the\s+request\s+of\s+[^.\n]{3,100}?,?\s+a|A|The)\s+votes?\s*(?:was\s+)?(?:then\s+)?taken\s+(?:by\s+)?roll[- ]?call")
MEETING_NOTE_RE = re.compile(r"The\s+meeting\s+(?:was\s+suspended|was\s+adjourned|was\s+resumed|rose|resumed)\b")
TOOK_CHAIR_RE = re.compile(r"(?:Mr|Mrs|Miss|Mme|Sir)[.,]?\s+[A-Z][\w'’\-]+(?:\s+[A-Z][\w'’\-]+){0,3}(?:\s*[({\[][^(){}\[\]\n]{2,50}[)}\]])?,?\s*"
                           r"(?:(?:Vice-?\s*)?(?:Chairman|President),?\s*)?(?:took|resumed|occupied)\s+the\s+[Cc]hair\b")
DECIDED_BY_RE = re.compile(r"(?:It|The\s+(?:Committee|Commission|Sub-Commission|Working\s+(?:Group|Party)|Drafting\s+Committee|Council))\s+"
                           r"(?:was\s+)?(?:agreed|decided),?\s+by\s+(?:a\s+vote\s+of\s+)?\S+\s+(?:votes?\s+)?to\s+\S+")
# the body's own procedural decision at the head of a line ("At the request of Dr. CHANG (China), the Commission decided to take" /
# "a vote by paragraphs.", E/CN.4/SR.12): the record's narrative (a speaker's account of it would say "had decided")
BODY_DECIDED_RE = re.compile(r"(?:At\s+the\s+request\s+of\s+[^\n]{3,80}?,\s+the|The)\s+(?:Committee|Commission|Sub-Commission|Working\s+(?:Group|Party)"
                             r"|Drafting\s+Committee|Council)\s+(?:then\s+)?(?:decided|agreed)\s+(?:to|that)\b")
NOTE_RES = (ROLL_CALL_RE, MEETING_NOTE_RE, TOOK_CHAIR_RE, DECIDED_BY_RE, re.compile(r"AGENDA\s+ITEMS?\s+\d"))
# a result with its count inside the chair's line ("... put the words to the vote separately. The words "within its territory
# and" were retained in paragraph 1 by 55 votes to 10"): cut only in the chair's turn, where it is the committee's decision
MIDLINE_RESULT_RE = re.compile(r"(?<=[.;,])\s+(?=(?:The|Articles?|Paragraphs?|Sub-?paragraphs?|Amendments?|Words|Draft|Points?|Parts?|Sections?|Proposals?)\b"
                               rf"[^.\n]{{0,220}}?\b{WAS}[\s.]+(?:not\s+)?{RESULT_VERB}\b"
                               r"(?:[^.\n]{0,60}?\s+by\s+\S+\s+votes?|\s+unanimously|,\s*\S+\s+votes?\s+being\s+cast))")


def one_sentence_result(text: str) -> bool:
    """A result with its count that opens the text and runs to its verb in one sentence (no sentence ends before the verb:
    "This Article should be broadened ... Consequently, he would abstain ... the article was accepted by a vote of seven" is
    a speech and a result, not a result)."""
    m = RESULT_FIGURES_RE.search(text)
    return bool(m) and not re.search(r"[.;:!?]\s", text[:m.start()])


def split_notes(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """A line that runs a note or a decision (NOTE_RES) on after the end of a sentence is cut before it; a roll-call block is cut
    wherever it starts, as no speaker words a sentence so."""
    out = []
    for page, ln in lines:
        cuts = []
        for rx in NOTE_RES:
            for m in rx.finditer(ln):
                before = ln[:m.start()]
                if m.start() > 0 and (rx is ROLL_CALL_RE and re.search(r"\s$", before) or re.search(r"[.;:!?\"”’,)]\W{0,30}$", before)):
                    cuts.append(m.start())
        cuts = sorted(set(cuts))
        out.extend((page, ln[a:b]) for a, b in zip([0] + cuts, cuts + [len(ln)]) if ln[a:b].strip())
    return out


def split_turns(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """A line holding the end of one turn and the start of the next is cut in two (TURN_SPLIT_RE, CHAIR_SPLIT_RE)."""
    out = []
    for page, ln in lines:
        cuts = [0]
        found = sorted(list(TURN_SPLIT_RE.finditer(ln)) + list(CHAIR_SPLIT_RE.finditer(ln)) + list(CHAIR_AFTER_DECISION_RE.finditer(ln)),
                       key=lambda m: m.start())
        for m in found:
            # not after a title ("the proposal of Mr. | CASSIN (France) was"), nor again inside the turn just cut
            # nor after a paragraph number alone ("40. | Mr. YANCY (Liberia)": the turn already starts the line)
            if not re.search(r"(?:^|\s)\W{0,2}[A-Z][A-Za-z]{0,3}[.,:;]$", ln[:m.start()]) and (cuts[-1] == 0 or m.end() - cuts[-1] > 14) \
                    and re.search(r"[A-Za-z]{3,}", ln[cuts[-1]:m.start()]):
                cuts.append(m.end())
        out.extend((page, ln[a:b]) for a, b in zip(cuts, cuts[1:] + [len(ln)]) if ln[a:b].strip())
    return out


_ORD = ["", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
        "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth",
        "eighteenth", "nineteenth"]
_CARD = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
         "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def ordinal_words(n: int) -> str:
    """127 -> 'hundred and twenty-seventh', as the 1948 Official Records head their meetings."""
    if n >= 100:
        h, rest = divmod(n, 100)
        head = ("" if h == 1 else _CARD[h] + " ") + "hundred"
        return head + "th" if rest == 0 else f"{head} and {ordinal_words(rest)}"
    if n < 20:
        return _ORD[n]
    t, u = divmod(n, 10)
    return _TENS[t][:-1] + "ieth" if u == 0 else f"{_TENS[t]}-{_ORD[u]}"


def meeting_heading_at(lines: list[tuple[int, str]], i: int, n: int) -> bool:
    """Is lines[i] the heading of meeting n?

    Printed volumes set the English and French headings side by side, so the line may read
    "HUNDRED AND SEVENTY-EIGHTH CENT SOIXANTE-DIX-HUITIEME", with "MEETING ... SEANCE" on
    the next line. Later records use numerals ("1020th MEETING"). The ordinal is compared
    word by word from the start of the line; its last word must match closely, because
    "seventy-eighth" and "seventy-ninth" differ only there.
    """
    from rapidfuzz import fuzz
    line = lines[i][1].strip()
    nxt = lines[i + 1][1].strip() if i + 1 < len(lines) else ""
    # Headings are set in capitals; body text ("at its sixty-first meeting") is not.
    if not (re.search(r"\bMEETING\b", line) or re.match(r"^\W*(?:PLENARY\s+)?MEETING\b", nxt)):
        return False
    if re.match(rf"^\W*{n}\s*(?:st|nd|rd|th)\b", line, re.I):
        return True
    first = re.split(r"[\s\-]+", line.strip())[0]
    if not first.isupper():
        return False
    toks = [t for t in re.split(r"[\s\-]+", line.lower()) if t]
    want = re.split(r"[\s\-]+", ordinal_words(n))
    if len(toks) < len(want):
        return False
    return all(fuzz.ratio(a, b) >= (90 if j == len(want) - 1 else 80) for j, (a, b) in enumerate(zip(toks, want)))


def ocr_digits(s: str | None) -> int | None:
    """Vote counts as OCR'd: '^' and 'h' are 4, 'O'/'o' is 0, 'l'/'I' is 1."""
    if s is None:
        return None
    s = s.translate(str.maketrans({"^": "4", "h": "4", "O": "0", "o": "0", "l": "1", "I": "1"}))
    return int(s) if s.isdigit() else None


DATE_LINE_RE = re.compile(r"^\W*(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+19\d\d)\W*$")


def drop_running_dates(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """The plenary's running head that is only the meeting's date ("9 December 1948"): a date that stands alone in a line on
    three pages or more is the running head, taken out where it stands alone and where the OCR put it inside a sentence
    ("the declaration of human 9 December 1948 rights"); a date alone once is text ("the period from 17 January 1946 to" /
    "15 July 1946.")."""
    counts: dict[str, set] = {}
    for page, ln in lines:
        m = DATE_LINE_RE.match(ln)
        if m:
            counts.setdefault(m.group(1), set()).add(page)
    heads = [d for d, pages in counts.items() if len(pages) >= 3]
    if not heads:
        return lines
    out = []
    for page, ln in lines:
        m = DATE_LINE_RE.match(ln)
        if m and m.group(1) in heads:
            continue
        for d in heads:
            ln = re.sub(rf"(?<=[a-z,])\s+{d}\s+(?=[a-z])", " ", ln)
        out.append((page, ln))
    return out


def drop_catchwords(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """The catchword the OCR garbled past the slash that marks it ("6 ° The CHAIRMAN" for "/8. The CHAIRMAN", "Jac, Me.
    LEROY-BEAULIEU has t/" for "/12. Mr. LEROY-BEAULIEU"): a short last line of a page whose letters open the next page's first
    line. Found by the segmentation audits on page images (rounds 68 and 73)."""
    from rapidfuzz import fuzz

    def opens(a: str, b: str) -> bool:
        # the catchword's letters, less the debris the OCR puts before them (a few letters at most: a longer head is text, "the
        # words "criminal law", /60. With regard"): a tail of the line that matches the next page's head
        return len(a) >= 8 and any(fuzz.ratio(a[cut:], b[:len(a) - cut]) >= 85 for cut in range(0, min(len(a) - 7, 7)))

    def fuz_head(a: str, b: str) -> float:
        return fuzz.ratio(a, b[:len(a)])

    out = list(lines)
    k = len(out) - 2
    while k >= 0:
        (p0, last), (p1, first) = out[k], out[k + 1]
        if p1 == p0 + 1:
            a = re.sub(r"[^a-z]", "", last.lower())
            b = re.sub(r"[^a-z]", "", first.lower())
            if len(last.strip()) <= 45 and not re.search(r"[.!?]\W{0,2}$", last.strip()) and opens(a, b):
                del out[k]
            else:
                # (run into the last sentence of the page: "would withdraw it. /The CRATRMAN")
                m = re.search(r"(?<=[.;:!?,])\s+/\s?\S.{0,40}$", last)
                # (the slash is the mark: a looser match, "/The CRATRMAN" for "The CHAIRMAN drew")
                c = re.sub(r"[^a-z]", "", m.group(0).lower()) if m else ""
                if m and len(c) >= 6 and fuz_head(c, b) >= 70:
                    out[k] = (p0, last[:m.start()])
        k -= 1
    return out


# the reports whose sections and annexes were read by hand, by anchors in their text (data/concordance/report_sections.csv,
# report_annex_sections.csv)
HAND_READ_REPORTS = {r["symbol"] for f in ("report_sections.csv", "report_annex_sections.csv")
                     for r in csv.DictReader((ROOT / "data" / "concordance" / f).open())
                     if (ROOT / "data" / "concordance" / f).exists()}


def load_lines(symbol: str, engine: str, notes: list[tuple[int, str]] | None = None) -> list[tuple[int, str]]:
    """(page, line) pairs for all OCR'd pages, page furniture removed, line-end hyphens joined."""
    d = OCR / safe_name(symbol) / engine
    sel_path = OCR / safe_name(symbol) / "selection.json"
    selection = json.loads(sel_path.read_text()) if sel_path.exists() else {}
    out: list[tuple[int, str]] = []
    for path in sorted(d.glob("page-*.txt")):
        page = int(path.stem.split("-")[1])
        page_notes: list[str] = []
        # (a report whose sections were read by hand keeps its footnotes in the text: the rows' anchors name them, round 83)
        hand_read = not re.search(r"/(?:SR|PV)\.\d", symbol) and symbol in HAND_READ_REPORTS
        body, _ = strip_furniture(path.read_text(encoding="utf-8"), first_page=page == 1, record=bool(re.search(r"/(?:SR|PV)\.\d", symbol)),
                                  notes=None if hand_read else page_notes, number=meeting_number(symbol), printed=bool(re.match(r"A/|E/(?:SR|PV)\.", symbol)))
        if selection.get(path.name, {}).get("two_column"):
            body, _ = english_only(body)  # printed Official Records: drop the French column
            page_notes = [english_only(x)[0].strip() for x in page_notes]  # (and the French footnotes)
        else:
            body, _ = drop_french_runs(body)  # (a French column the gutter test missed, a French page or half-sheet)
        if notes is not None:
            # (a footnote of the French column, "1 Voir E/CN.4/21", is too short for english_only to tell)
            # (a document's note of sources can be symbols only, "29/ E/CN.4/528.", and is kept)
            record = bool(re.search(r"/(?:SR|PV)\.\d", symbol))
            notes.extend((page, x) for x in page_notes if (re.search(r"[A-Za-z]{3}", x) or not record and re.search(r"[A-Za-z]{2}|\d{2}", x))
                         and not re.match(r"^\W*\d{0,2}\s*\W?\s*Voir\b", x))
        # (a document's footnote, marked where it stood: a line of its own for segment_document; other readers drop it)
        out.extend((page, ln.rstrip()) for ln in body.splitlines() if ln.strip() and (notes is not None or not ln.startswith(DOC_NOTE_MARK)))
    if re.search(r"/(?:SR|PV)\.\d", symbol):
        out = drop_catchwords(out)
        out = drop_running_dates(out)
    # join words hyphenated across lines: "mis-under-" + "standings"
    joined: list[tuple[int, str]] = []
    for i, (page, ln) in enumerate(out):
        # (a page number between the halves of the word: "para-" / "_ 187" / "graph")
        if joined and re.search(r"[a-z]-$", joined[-1][1]) and re.match(r"^[\W_]*\d{1,4}[\W_]*$", ln) \
                and i + 1 < len(out) and re.match(r"^[a-z]", out[i + 1][1].strip()):
            continue
        if joined and re.search(r"[a-z]-$", joined[-1][1]) and re.match(r"^[a-z]", ln.strip()):
            p0, prev = joined[-1]
            first, _, rest = ln.strip().partition(" ")
            joined[-1] = (p0, prev[:-1] + first)
            if rest:
                joined.append((page, rest))
            continue
        joined.append((page, ln))
    # a speaker's delegation wrapped in a narrow column: "Mr. CASSIN (United" / "Kingdom) said"
    # Only a short open parenthesis right after the name, closed early on the next line:
    # anything looser glues the next speech onto this one.
    merged: list[tuple[int, str]] = []
    for page, ln in joined:
        prev = merged[-1][1] if merged else ""
        m = re.search(r"^\s*\S{0,4}\s*(?:Mr|Mrs|Miss|Dr|Sir|Begum)\b[.,]?\s+[^()]{2,40}\(([^()]{0,45})$", prev)
        # the same in a numbered paragraph that opens with a phrase ("28. In reply to a question from Mr. NUTTING" / "(Canada),
        # Mr. SCHWELB (...) recalled"; "66. At the request of Mrs. ROOSEVELT (United" / "States of America), Mr. BAROODY ...")
        m = m or re.search(r"^\s*\W{0,3}\d{1,3}\s*[.,].{0,100}?\b(?:Mr|Mrs|Miss|Dr|Sir|Begum)\b[.,]?\s+[^()]{2,40}\(([^()]{0,45})$", prev)
        if m and re.match(r"^[^()]{0,60}\)", ln.strip()):
            merged[-1] = (merged[-1][0], prev + " " + ln.strip())
            continue
        if re.match(r"^\(", ln.strip()) and re.search(r"^\s*\W{0,3}\d{1,3}\s*[.,].{0,100}?\b(?:Mr|Mrs|Miss|Dr|Sir|Begum)\b[.,]?\s+[A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){0,2}$", prev):
            merged[-1] = (merged[-1][0], prev + " " + ln.strip())
            continue
        # a turn that starts after the end of a sentence and breaks before its delegation ("... the Secretariat Draft. Mr. WILSON" /
        # "(United Kingdom) opposed the idea") or before its verb ("... the French paper. Professor KORETSKY (Union of Soviet
        # Socialist Republics)" / "explained that"): the opening goes to the line it belongs with (segmentation audits, October 2026)
        # (the end of a sentence, not a paragraph number's full stop: "1. Mr. PAVLOV (Union of Soviet" / "Socialist Republics) noted")
        w = re.search(r"(?<=[A-Za-z)\]\"”’][.;:!?\"”’])\s+((?:Mr|Mrs|Miss|Dr|Sir|Professor|Prof|General)[.,]?\s+[" + UC + r"][" + UC + r"'\-]{2,}(?:\s+[" + UC + r"][" + UC + r"'\-]+){0,2}"
                      r"(?:\s*\([A-Z][^()]{2,60}\))?)\s*$", prev)
        if w and (w.group(1).endswith(")") and re.match(r"^\s*" + REPORT_VERBS, ln)
                  or not w.group(1).endswith(")") and re.match(r"^\s*\([A-Z][^()]{2,60}\)\s*,?\s*" + REPORT_VERBS, ln)):
            merged[-1] = (merged[-1][0], prev[:w.start()])
            merged.append((page, w.group(1) + " " + ln.strip()))
            continue
        merged.append((page, ln))
    return merged


# Delegations as the French column of the printed records names them: a speech that
# opens with one of these is the French version of an English speech on the same page.
# Only names that differ from the English (Uruguay, Philippines, Canada... tell nothing).
FRENCH_DELEGATION_RE = re.compile(
    r"^\s*(?:Etats-Unis|États-Unis|Royaume-Uni|Union des R|R[ée]publique|Chine|Gr[èe]ce|Belgique|Pays-Bas|Liban|"
    r"[ÉE]gypte|Inde\b|Pologne|Su[èe]de|Turquie|Arabie|Nouvelle-Z|Danemark|Norv[èe]ge|Mexique|Br[ée]sil|Chili\b|"
    r"Australie|Syrie|Irak|Tch[ée]coslovaquie|Yougoslavie|Argentine|Colombie|Equateur|Équateur|P[ée]rou|"
    r"Ethiopie|Éthiopie|Islande)", re.I)


def cut_to_meeting(symbol: str, lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Printed records bundle meetings: keep from this meeting's heading to the next one's.
    Records without such headings (mimeographed ones) are returned unchanged."""
    m = re.search(r"/(?:SR|PV)\.(\d+)$", symbol)
    if not m:
        return lines
    n = int(m.group(1))
    start = next((i for i in range(len(lines)) if meeting_heading_at(lines, i, n)), None)
    if start is None:
        return lines
    end = next((i for i in range(start + 1, len(lines)) if meeting_heading_at(lines, i, n + 1)), len(lines))
    return lines[start:end]


# The printed Third Committee records from 1956 head each debate in capitals, over one or two
# lines: "ARTICLE 15 OF THE DRAFT COVENANT ON ECONOMIC, / SOCIAL AND CULTURAL RIGHTS (E/2573, annex I A)",
# "ARTICLES 13 AND 14 OF THE DRAFT COVENANT ON CIVIL AND POLITICAL RIGHTS". Capitals only: prose
# says "article 15 of the draft Covenant".
# (the word ARTICLE in capitals keeps prose out; the rest may be read in small capitals: "ARTICLE 13 oF THE DRAFT CovENANT")
COVENANT_HEAD_RE = re.compile(r"^\W{0,3}ART[I1l]CLES?\s+(?P<art>[\dIl]{1,2})\b[\s\d,ANDTO.\-–]*?\s*(?i:[O0]F)\s+(?i:THE)\s+"
                              r"(?:(?i:DRAFT)\s+)?(?i:COVENANTS?)\b")


HEAD_TAIL_RE = re.compile(r"^\W{0,2}\((?:continued|concluded|cont\.)\)\W*$", re.I)


def join_covenant_headings(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """A capitals heading that runs onto the next line is taken as one line; so is an article heading whose bracket of documents
    or "(continued)" runs onto the next ("Article 9 of the draft Covenant on Economic, Social and Cultural Rights (E/2573," /
    "annex I A) (continued)"; "Article 9 (E/CN.4/400, ..." / "E/CN.4/406) (continued)"), as the segmentation audit found
    (round 73)."""
    out: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        page, ln = lines[i]
        if (COVENANT_HEAD_RE.match(ln) or ARTICLE_HEAD_RE.match(ln) or re.match(r"^\W{0,2}Art\w{3,5}\s+[\dIl]{1,2}\b.{0,80}\(", ln)) \
                and i + 1 < len(lines):
            joined, n = ln.rstrip(), 1
            while i + n < len(lines) and n <= 3:
                nxt = lines[i + n][1].strip()
                letters = [c for c in re.sub(r"\((?:continued|concluded|cont\.)\)", "", nxt) if c.isalpha()]
                caps = bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.8
                open_bracket = joined.count("(") > joined.count(")")
                unfinished = COVENANT_HEAD_RE.match(ln) and re.search(r"(?:,|\b(?:ON|AND|OF|on|and|of))\s*$", joined)
                if COVENANT_HEAD_RE.match(ln) and caps and not joined.endswith(")") or HEAD_TAIL_RE.match(nxt) \
                        or unfinished and len(nxt) < 120 and not classify(nxt)[0] and not FINITE_VERB_RE.search(nxt) \
                        or open_bracket and len(nxt) < 120 and not classify(nxt)[0] and not FINITE_VERB_RE.search(nxt):
                    joined += " " + nxt
                    n += 1
                    continue
                break
            out.append((page, joined))
            i += n
            continue
        out.append((page, ln))
        i += 1
    return out


def classify(line: str) -> tuple[str, dict]:
    """What kind of paragraph a line would open, if it opens one."""
    m = SECOND_READING_HEAD_RE.match(line)
    if m:
        return "heading", {"article": m.group("art").replace("l", "1").replace("I", "1")}
    if ARTICLE_HEAD_RE.match(line):
        return "heading", {"article": ARTICLE_HEAD_RE.match(line).group("art").replace("l", "1").replace("I", "1").replace("A", "4")}
    m = COVENANT_HEAD_RE.match(line)
    if m:
        return "heading", {"article": m.group("art").replace("l", "1").replace("I", "1")}
    m = SPEAKER_RE.match(line) or POSTTITLE_RE.match(line) or MIDTURN_RE.match(line)
    nocountry = None if m else NOCOUNTRY_RE.match(line)
    if nocountry:
        n = nocountry.group("n")
        return "speech", {"title": nocountry.group("title"), "name": nocountry.group("name"), "country": None, "role": None,
                          "n": n if n and n.isdigit() and len(n) <= 3 else None, "after": line[nocountry.end():], "nocountry": True}
    if m:
        info = {k: (v.strip() if v else None) for k, v in m.groupdict().items()}
        info["n"] = info["n"] if info["n"] and info["n"].isdigit() and len(info["n"]) <= 3 else None  # ("2300-": OCR debris)
        info["after"] = line[m.end():]
        return "speech", info
    m = CHAIR_RE.match(line) or (CHAIR_PHRASE_RE.match(line) if re.match(r"^\s*\W{0,3}\d{1,3}\s*[.,]", line) else None)
    # (not another body's chairman, "The Chairman of the Inter-American Commission of Women", nor a text that names the office,
    # "The Chairman of the Commission may consult experts", E/CN.4/SR.12)
    if m and re.match(r"\s+of\s+the\b", line[m.end():]):
        m = None
    if m:
        role = m.group("role").upper()
        role = "Chairman" if role.startswith("CHA") or re.fullmatch(r"[CG][A-Z]?A[A-Z1l][RE]MA[NH]|C[HP][A/][IJ1l][RE]M[A‘'{/]N", role) else "President" if role.startswith("PRES") \
            else "Rapporteur" if role.startswith("RAPP") else role.title()  # ("The RAPPORITUR cesd the full text", E/CN.4/SR.12)
        n = m.group("n")
        return "chair", {"role": role, "n": n if n and n.isdigit() else None, "after": line[m.end():]}
    if MEETING_ROSE_RE.match(line):
        return "closing", {}
    return "", {}


# a turn opened by a phrase, numbered or not, whose subject comes a line or three later: "After a further exchange of views, in
# which Mr. INGLES (Philippines), ... took part, the CHAIRMAN proposed", "In reply to Mr. HOARE (United Kingdom), the CHAIRMAN
# said", "On behalf of the Committee, the CHAIRMAN" / "thanked", "6. After an exchange of views, in which ... took part, Mr.
# SHALIZI (Afghanistan), supported by ..., proposed" (segmentation audits, October 2026)
TURN_LEAD_RE = re.compile(r"^\s*\W{0,3}(?:\w{1,3}\s*[.,;]\s*)?(?:After\s+(?:a\s+(?:further\s+|brief\s+|short\s+)?|an\s+|some\s+|further\s+)?(?:exchange\s+of\s+views|discussion)|"
                          r"In\s+reply\s+to|In\s+answer\s+to|Replying\s+to|On\s+behalf\s+of|In\s+accordance\s+with|At\s+the\s+request\s+of|"
                          # ("gh, On that understanding, Mr. HOARE (United Kingdom) withdrew the clause", "gh," the OCR's "94."; round 98)
                          r"On\s+that\s+understanding)\b")
LEAD_CHAIR_RE = re.compile(r"(?:,\s*[.,]?\s+|(?<=discussion)\s+|(?<=views)\s+)the\s+(?P<role>CHAIRMAN|Chairman|PRESIDENT|President|CHA[A-Z1l]{3,5}[NH])\s+(?:then\s+|also\s+)?(?:said|suggested|pointed|proposed|noted|"
                           r"announced|recalled|observed|stated|thought|asked|replied|invited|declared|explained|informed|drew|reminded|put|felt|"
                           r"considered|ruled|understood|took|indicated|clarified|appealed|called|withdrew|read|agreed|accepted|thanked|expressed)\b")
LEAD_SPEAKER_RE = re.compile(r"\btook\s+part,\s+(?=(?:Mr|Mrs|Miss|Dr|Sir)\b)")
# the speaker after the phrase's comma: "49. In reply to a question by Mr. PAZHWAK (Afghanistan),-Mr." / "URQUIA (El Salvador) said",
# "88. In reply to a question from the CHAIRMAN," / "Mr. LOPEZ VILLAMIL (Honduras), speaking for" (round 86)
LEAD_REPLY_RE = re.compile(r"(?:,|\))\s*[-–]?\s*(?=(?:Mr|Mrs|Miss|Mme|Dr|Sir|Prof|Professor)\b)")
# (after such a phrase the verb need not be one of saying: "Mrs. ROSSEL (Sweden) reaffirmed", "(Honduras), speaking for")
LEAD_NAME_RE = re.compile(r"(?P<title>Mr|Mrs|Miss|Mme|Dr|Sir|Prof|Professor)[.,:;]{0,2}\s+(?P<name>[" + UC + r"][" + UC + r"'\-]{2,}(?:\s+[" + UC + r"][" + UC + r"'\-]+){0,2})\s*"
                          r"\((?P<country>[A-Z][A-Za-z .,'\-]{2,70})\)(?:\s*\((?P<role>[^()\n]{2,40})\))?,?\s+(?!(?:and|or|the|of|to|in|on|with)\b)[a-z]")


def lead_turn(ln: str, ahead: str) -> tuple[str, dict]:
    """A turn opened by a phrase (TURN_LEAD_RE), read on into the next lines: the chair's or a speaker's, or none."""
    if not TURN_LEAD_RE.match(ln):
        return "", {}
    joined = re.sub(r"CHAIR-\s+MAN", "CHAIRMAN", " ".join([ln.strip(), ahead.strip()]))[:600]
    n = re.match(r"^\s*\W{0,3}(\d{1,3})\s*[.,;]", ln)
    m = LEAD_CHAIR_RE.search(joined)
    # (no sentence ends before the subject: the titles' full stops aside; a number's too, and the next paragraph's number,
    # "... seized of the USSR text. 6, Mr. CHANG (China)", "... as an amendment to article 3. Mr. HOARE", round 98)
    if m and not re.search(r"[a-z]{3}\.\s+(?:[A-Z]|\d{1,3}(?:\s*[.,]\s|\s*$))|(?<=[a-z]\s)\d{1,3}\.\s+[A-Z]", re.sub(r"\b(?:Mr|Mrs|Dr|St|No)\.", "", joined[:m.start()])):
        role = "Chairman" if m.group("role").upper().startswith("CHA") else "President"
        return "chair", {"role": role, "n": n.group(1) if n else None, "after": ""}
    s = LEAD_SPEAKER_RE.search(joined)
    if s and not re.search(r"[a-z]{3}\.\s+(?:[A-Z]|\d{1,3}(?:\s*[.,]\s|\s*$))|(?<=[a-z]\s)\d{1,3}\.\s+[A-Z]", re.sub(r"\b(?:Mr|Mrs|Dr|St|No)\.", "", joined[:s.start()])):
        m2 = MIDTURN_RE.match(joined[s.end():])
        if m2:
            info = {k: (v.strip() if v else None) for k, v in m2.groupdict().items()}
            info["n"], info["after"] = (n.group(1) if n else None), ""
            return "speech", info
    r = LEAD_REPLY_RE.search(joined[:300])
    if r and not re.search(r"[a-z]{3}\.\s+(?:[A-Z]|\d{1,3}(?:\s*[.,]\s|\s*$))|(?<=[a-z]\s)\d{1,3}\.\s+[A-Z]|[.;:]\s*$", re.sub(r"\b(?:Mr|Mrs|Dr|St|No)\.", "", joined[:r.start()])):
        m2 = MIDTURN_RE.match(joined[r.end():]) or LEAD_NAME_RE.match(joined[r.end():])
        if m2:
            info = {k: (v.strip() if v else None) for k, v in m2.groupdict().items()}
            info["n"], info["after"] = (n.group(1) if n else None), ""
            return "speech", info
    return "", {}


# a token of OCR debris before a speaker's turn, after a sentence that ended or a page's head: "Bie Mr. MALIK (Lebanon),
# Rapporteur, read article 3.", "viet) Mr, SCHWELB (Secretariat) pointed out", "Te Mr, SCHACHTER (Secretariat) sugested"; never a
# word that joins the line to the sentence before ("and Mr. WILSON (United Kingdom) said", "by Mr. ENCINAS (Peru), proposed",
# "As Mr. ENTEZAM (Iran) was also dissatisfied"; round 98)
DEBRIS_TURN_RE = re.compile(r"^\W{0,3}(?P<deb>[A-Za-z]{1,4}[).,;:]?)\s+(?=(?:Mr|Mrs|Miss|Mme|Dr|Sir|Prof|Professor)[.,]?\s)")
JOINING_WORDS = {"and", "by", "that", "from", "of", "to", "as", "when", "while", "hile", "the", "she", "he", "how", "in", "with",
                 "for", "but", "if", "so", "or", "nor", "then", "after", "since", "where", "whom", "also", "ment", "puis", "le", "la",
                 "de", "et", "et.", "on", "at", "who", "was", "had", "his", "her", "its", "this", "all", "both", "said", "than"}
PREV_ENDS_RE = re.compile(r"(?:[.,;:!?)\"”’•·][\W_]{0,6}|^\W*Page\s+\S{1,4}\W*)$")


def debris_turn(ln: str, prev: str) -> tuple[str, dict]:
    """A speaker's turn behind a token of OCR debris (DEBRIS_TURN_RE), or none."""
    m = DEBRIS_TURN_RE.match(ln)
    if not m or m.group("deb").lower().rstrip(").,;:") in JOINING_WORDS or not PREV_ENDS_RE.search(prev.rstrip()):
        return "", {}
    kind, info = classify(ln[m.end():])
    return (kind, info) if kind == "speech" and info.get("country") else ("", {})


def classify_ahead(ln: str, nxt: str, more: str = "") -> tuple[str, dict]:
    """classify(), reading on into the next line when a numbered paragraph's opening ends at a closed bracket and the verb that
    makes it a turn is on the next line ("28. In reply to a question from Mr. NUTTING (Canada), Mr. SCHWELB (Secretary of the
    Committee)" / "recalled that")."""
    kind, info = classify(ln)
    if not kind:
        k2, i2 = lead_turn(ln, nxt + " " + more)
        if k2:
            return k2, i2
    # (and a speaker's line that ends with the delegation, its verb on the next line: "* MI. BERNSTEIN (Co-ordinating Board of
    # Jewish Organizations)" / "appreciated the opportunity", round 87)
    if not kind and nxt and re.search(r"\)\s*$", ln.rstrip()) and re.match(r"^\s*[a-z]", nxt):
        kind2, info2 = classify(ln.rstrip() + " " + nxt.strip())
        if kind2 == "speech" and info2.get("country"):
            info2["after"] = ""
            return kind2, info2
    # (also a turn opened by a phrase, with no number: "In reply to a question by the CHAIRMAN, Mr. JUVIGNY (France)" / "formally
    # proposed", round 80)
    if not kind and nxt and re.match(r"^\s*\W{0,3}(?:\d{1,3}\s*[.,]|(?:In\s+(?:reply|answer)\s+to|Replying\s+to|At\s+the\s+(?:request|invitation)\s+of)\b)", ln) \
            and re.search(r"\)\s*$", ln.rstrip()):
        kind2, info2 = classify(ln.rstrip() + " " + nxt.strip())
        if kind2 == "speech":
            info2["after"] = ""  # (the opening is the line; the verb belongs to the text that follows)
            return kind2, info2
    return kind, info


def segment(symbol: str, engine: str) -> list[dict]:
    """Meeting records (…/SR.n, …/PV.n) are split into speeches; other documents
    (reports, drafts, amendments, government comments) into paragraphs."""
    if re.search(r"/(?:SR|PV)\.\d", symbol):
        return segment_record(symbol, engine)
    return segment_document(symbol, engine)


MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
# the year may follow on the next masthead line ("7 October" … "1948")
DATE_RE = re.compile(rf"\b(\d{{1,2}}|[kh^]|\d[kh^])\s+({MONTHS})\s*,?[^\d]{{0,40}}?(19[4-6][\d^kh])", re.I)


WEEKDAY_RE = re.compile(r"\b(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day\b\W{0,4}(?:the\s+)?$", re.I)
# digits the typewriter faces and the OCR confuse in a day of the month
DAY_CONFUSIONS = {"1": "74", "7": "1", "3": "8", "8": "3605", "5": "6", "6": "580", "0": "86", "4": "1", "9": "0"}


def masthead_date(text: str) -> str | None:
    """The meeting's date in a masthead ("Friday, 4 June 1948", OCR "k June 19^8"), ISO.

    Typed records print the date of issue first ("E/CN.4/SR.219 4 June 1951") and the
    meeting's after its weekday ("held ... on Monday, 30 April 1951"): a date after a weekday
    wins, and the weekday settles a misread day ("Monday, 36 April" is 30 April, a Monday).
    Otherwise the first date."""
    import datetime as _dt

    def parse(day: str, month: str, year: str):
        try:
            return _dt.datetime.strptime(f"{int(day)} {month.title()} {year}", "%d %B %Y").date()
        except ValueError:
            return None

    first, dated = None, []
    for m in DATE_RE.finditer(text):
        day = m.group(1).translate(str.maketrans({"k": "4", "h": "4", "^": "4"}))
        year = m.group(3).translate(str.maketrans({"k": "4", "h": "4", "^": "4"}))
        d = parse(day, m.group(2), year)
        first = first or d
        wd = WEEKDAY_RE.search(text[max(0, m.start() - 20):m.start()])
        if wd:
            dated.append((d, wd.group(1).lower(), day, m.group(2), year))
    for d, wd, day, month, year in dated:
        if d and d.strftime("%A").lower().startswith(wd):
            return d.isoformat()
    for d, wd, day, month, year in dated:
        # one digit of the day misread: the reading that falls on the printed weekday, if only one does
        alts = {parse(day[:i] + c + day[i + 1:], month, year) for i, ch in enumerate(day) for c in DAY_CONFUSIONS.get(ch, "")}
        fits = [a for a in alts if a and a.strftime("%A").lower().startswith(wd)]
        if len(fits) == 1:
            return fits[0].isoformat()
    for d, *_ in dated:
        if d:
            return d.isoformat()
    # the weekday garbled too ("held at the Palais des Nations, Geneva, on Hondas, 16 april 1951", E/CN.4/SR.203): the
    # date after "held ... on" is the meeting's, not the date of issue printed first
    for m in DATE_RE.finditer(text):
        if re.search(r"\bheld\b[^.]{0,90}\bon\s+(?:[^\s,]{3,12}\s*,\s*)?$", text[max(0, m.start() - 110):m.start()], re.I):
            day = m.group(1).translate(str.maketrans({"k": "4", "h": "4", "^": "4"}))
            d = parse(day, m.group(2), m.group(3).translate(str.maketrans({"k": "4", "h": "4", "^": "4"})))
            if d:
                return d.isoformat()
    return first.isoformat() if first else None


def finalize(symbol: str, engine: str, segments: list[dict]) -> list[dict]:
    """Votes, ids and provenance for a segmented document."""
    for s in segments:
        s.pop("result", None)
        s.pop("decided", None)
        s.pop("_starts", None)
        m = VOTE_RE.search(s["text"]) if s["kind"] in ("procedural", "chair", "paragraph") else None
        if m and m.group("outcome"):
            s["kind"] = "vote" if s["kind"] == "procedural" else s["kind"]
            yes, no = ocr_digits(m.group("yes")), ocr_digits(m.group("no"))
            if m.group("outcome").lower() in ("rejected", "defeated"):
                yes, no = no, yes  # "rejected by 28 votes to 17": 28 against
            s["vote"] = {"outcome": m.group("outcome").lower(), "yes": yes,
                         "no": no, "abstentions": ocr_digits(m.group("abst")),
                         "unanimous": m.group("yes") is None and "unanimous" in m.group(0).lower()}
    out = []
    for s in segments:
        out.append(s)
        # after "The meeting rose at 12.40 p.m." the page holds the printer's lines and debris ("rn ES A eg eererrene ...", "77301-
        # November 1958-2,075"), or the page's footnotes, which are set apart
        m = re.match(r"\s*The meeting rose at [^.\n]{1,25}?[ap]\.\s?m\.", s["text"]) if s["kind"] == "closing" else None
        if m:
            rest = s["text"][m.end():]
            s["text"] = m.group(0).strip()
            note = re.search(r"(?:^|\s)(?:\d|[*+®])\s*/\s*\S|(?:^|\s)\(\d\)\s*\S", rest) or \
                re.search(r"\b(?:See|Subs\s?equently|Official\s+Records|Resumed|Circulated|Document|Ibid|United\s+Nations\s+publication)\b", rest, re.I)
            if note:
                out.append({"kind": "footnote", "page_start": s["page_end"], "page_end": s["page_end"],
                            "text": " ".join(rest[note.start():].split())})
    segments = out
    for i, s in enumerate(segments, 1):
        s["id"] = f"{safe_name(symbol).lower()}-{i:04d}"
        s["symbol"] = symbol
        s["seq"] = i
        s["engine"] = engine
    return segments


# Documents: who submits them, and how they are divided.
AUTHOR_RE = re.compile(
    r"^\s*(?:\d{1,2}\s*[.,+»]\s*)?(?:(?:TELEGRAM|COMMUNICATION|LETTER|NOTE|MEMORANDUM)\s+(?:RECEIVED\s+)?"
    r"(?:FR|EB|FB|FE|ER|PR)O[MN]\s+(?:THE\s+)?"
    r"(?:GOVERNMENT\s+OF\s+)?(?P<a1>[A-Z][A-Z .'\-]{2,50}?)\s*$"
    r"|(?P<a2>[A-Z][A-Z .'\-]{2,50}?)\s*:\s*(?:(?:revised\s+)?(?:amendments?|proposals?|draft|comments?|observations?|"
    r"sub-amendments?|suggestions?|text)\b))", re.I)
SUBMITTED_RE = re.compile(r"\b(?:submitted|proposed|presented)\s+by\s+the\s+(?:delegations?|representatives?|Governments?)\s+of\s+"
                          r"(?:the\s+)?([A-Z][A-Za-z .'\-]{2,50}?)(?=[.,;:)\n]|\s+(?:and|to|on|at)\b)")
PARA_START_RE = re.compile(r"^\s*(?P<n>\d{1,3})\s*[.,»]\s+\S")
PARA_START_FUZZY_RE = re.compile(r"^\s*[iIl|'`\[]?\s?(?P<n>[\dIlOoSkh^]{1,3})\s*[.,»]\s+[A-Z(\"“]")
OCR_PARA_DIGITS = str.maketrans({"I": "1", "l": "1", "O": "0", "o": "0", "S": "5", "k": "4", "h": "4", "^": "4"})
CONTENTS_RE = re.compile(r"(?:\.\s*){5,}\s*[\dIl]{1,3}\s*$")  # table of contents: dotted leader, page number
ORG_WORDS = re.compile(r"\b(?:ORGANI[SZ]ATION|FEDERATION|CONGRESS|COUNCIL|UNION|ASSOCIATION|COMMITTEE|LEAGUE|"
                       r"OFFICE|SECRETARIAT|SECRETARY-GENERAL|COMMISSION|AGENCY|CONFERENCE|ALLIANCE|BOARD)\b", re.I)
_STATE_NAMES: list[str] | None = None


def author_or_none(candidate: str | None) -> str | None:
    """A submitting state or organisation, or None ("Annex A: Draft …" is not an author)."""
    global _STATE_NAMES
    if not candidate:
        return None
    if _STATE_NAMES is None:
        import csv as _csv
        _STATE_NAMES = []
        with (ROOT / "data" / "gazetteer" / "states.csv").open() as f:
            for row in _csv.DictReader(f):
                _STATE_NAMES += [row["canonical"].lower(), *[v.lower() for v in row["variants"].split("|") if v]]
    from rapidfuzz import fuzz, process
    c = " ".join(candidate.split())
    hit = process.extractOne(c.lower(), _STATE_NAMES, scorer=fuzz.ratio)
    if (hit and hit[1] >= 80) or ORG_WORDS.search(c):
        return c.title()
    return None
SECTION_RE = re.compile(r"^[A-Z][A-Z0-9 ,.'():;\-]{12,110}$")


DOC_SYMBOL_LINE_RE = re.compile(r"^\W{0,3}[A-Z£]\W{0,2}/\s?[A-Z]{1,3}[\s.,]{0,2}\d?\s?/\s?[\w./ ]{1,24}$")


def segment_document(symbol: str, engine: str) -> list[dict]:
    """Paragraphs of a non-meeting document, each with the article and the author in force.

    The masthead runs to the title block (the last capitals lines before the first
    paragraph or article heading). Paragraphs start at printed numbers ("1.", OCR "2»") or,
    in unnumbered texts, after a short line that ends a sentence.
    """
    notes: list[tuple[int, str]] = []  # the footnotes taken out of the pages (normalize._drop_doc_footnotes, round 83)
    lines = load_lines(symbol, engine, notes)
    if not lines:
        return []
    widths = sorted(len(ln) for _, ln in lines)
    short = widths[len(widths) // 2] * 0.72
    start = 0
    for i, (page, ln) in enumerate(lines):
        if page > 2:
            break
        if i >= 3 and (PARA_START_RE.match(ln) or ARTICLE_HEAD_RE.match(ln)
                       or (AUTHOR_RE.match(ln) and author_or_none(AUTHOR_RE.match(ln).group("a1") or AUTHOR_RE.match(ln).group("a2")))
                       or (len(ln) > 55 and not ln.isupper())):
            start = i
            break
    segments: list[dict] = []
    last_n = None  # the last printed paragraph number read
    if start:
        text = "\n".join(l for _, l in lines[:start])
        segments.append({"kind": "masthead", "page_start": 1, "page_end": lines[start - 1][0], "text": text,
                         "meeting_date": masthead_date(text)})
        m = SUBMITTED_RE.search(" ".join(text.split())) or next(
            (AUTHOR_RE.match(l) for _, l in lines[:start] if AUTHOR_RE.match(l)), None)
    else:
        m = None
    author = None
    if m:
        author = author_or_none(m.group(1) if m.re is SUBMITTED_RE else (m.group("a1") or m.group("a2")))
    article: str | None = None
    current: dict | None = None

    def close() -> None:
        nonlocal current
        if current:
            current["text"] = " ".join(current["text"].split())
            if current["text"]:
                segments.append(current)
        current = None

    prev_line = ""
    head_open = 0  # lines a title ("Brazil: amendments to articles 19 and 26 of the draft") may still take
    # the sessions' reports list their documents on pages of two columns, symbols and titles, which the OCR reads one after the
    # other ("E/CN.4/593" ... / "Yugoslavia : amendment to the Lebanese" / "proposal on equality of rights" / "Ditto"): there
    # each title is one paragraph, the symbols another, and a title names no author of what follows (round 83)
    list_pages = {p for p, n in Counter(page for page, ln in lines[start:] if DOC_SYMBOL_LINE_RE.match(ln)
                                        and not re.search(r"[a-z]{3}", re.sub(r"\b(?:Rev|Add|Corr|only|French|English)\b", "", ln))).items() if n >= 8}
    for page, ln in lines[start:]:
        if CONTENTS_RE.search(ln):
            continue
        if ln.startswith(DOC_NOTE_MARK):
            close()
            segments.append({"kind": "footnote", "page_start": page, "page_end": page, "text": ln[len(DOC_NOTE_MARK):].strip(),
                             "article_heading": None, "author_raw": None})
            prev_line = ""
            continue
        if page in list_pages:
            sym = bool(DOC_SYMBOL_LINE_RE.match(ln)) or bool(re.match(r"^\W*\((?:French|English|Spanish|Russian)\s+only\)\W*$", ln))
            entry = bool(re.match(r"^\W{0,2}(?:[A-Z][\w.,'()\- ]{1,60}?\s?:(?:\s+\S|\s*$)|Ditto\b|Compilation\b|Existing\b|Note\s+by\b|Report\b|Memorandum\b)", ln)) \
                or bool(re.fullmatch(r"\W*Ditto\W*", prev_line.strip())) and not sym  # ("Ditto" is a whole title)
            if current is None or "doc_list_symbols" not in current or sym != current["doc_list_symbols"] or (entry and not sym):
                close()
                current = {"kind": "paragraph", "page_start": page, "page_end": page, "text": ln, "n": None,
                           "article_heading": article, "author_raw": None, "doc_list_symbols": sym, "_lines": [ln]}
            else:
                current["text"] += "\n" + ln
                current["page_end"] = page
                current["_lines"].append(ln)
            prev_line = ln
            continue
        if current is not None and current.get("doc_list_symbols") is not None:
            close()
        # a title that runs on: "... of the draft" / "Covenant on Civil and Political Rights 1/", "... amendment to article IV" /
        # "submitted by Czechoslovakia (A/C.3/L.1220, para. 2)" (the audit of round 81)
        if head_open and segments and segments[-1]["kind"] == "heading" and len(ln.strip()) < 90 and not PARA_START_RE.match(ln) \
                and not ARTICLE_HEAD_RE.match(ln) and not re.match(r"^\W{0,2}(?:[IVX]{1,4}|\d{1,2}|[a-z])\s*[.)]\s", ln) \
                and not re.search(r"[.:;)]\W{0,2}$|\d\s*/\s*$", segments[-1]["text"]) \
                and (re.match(r"^\W{0,3}[a-z]", ln) or re.search(r"\b(?:the|of|to|and|on|in|by|for|draft|with)\W{0,2}$", segments[-1]["text"], re.I)):
            segments[-1].setdefault("head_first", segments[-1]["text"])  # (api/build_db.py reads the first line, as before)
            segments[-1]["text"] += " " + ln.strip()
            segments[-1]["page_end"] = page
            head_open -= 1
            prev_line = ln
            continue
        head_open = 0
        a = AUTHOR_RE.match(ln)
        if a and author_or_none(a.group("a1") or a.group("a2")):  # "CUBA: Amendments to …"
            close()
            author = author_or_none(a.group("a1") or a.group("a2"))
            segments.append({"kind": "heading", "page_start": page, "page_end": page, "text": ln.strip(),
                             "article_heading": article, "author_raw": author})
            prev_line = ln
            head_open = 2
            continue
        h = ARTICLE_HEAD_RE.match(ln)
        if h:
            close()
            article = h.group("art").replace("l", "1").replace("I", "1")
            segments.append({"kind": "heading", "page_start": page, "page_end": page, "text": ln.strip(),
                             "article_heading": article, "author_raw": author})
            prev_line = ln
            continue
        if SECTION_RE.match(ln.strip()) and len(ln.split()) >= 3:
            close()
            segments.append({"kind": "heading", "page_start": page, "page_end": page, "text": ln.strip(),
                             "article_heading": article, "author_raw": author})
            prev_line = ln
            continue
        pm = PARA_START_RE.match(ln)
        n_para = pm.group("n") if pm else None
        if not pm and last_n is not None:
            # "12h." for 124, "l41." for 141: an OCR-damaged number counts only as the very next paragraph
            fm = PARA_START_FUZZY_RE.match(ln)
            if fm and fm.group("n").translate(OCR_PARA_DIGITS).isdigit() and int(fm.group("n").translate(OCR_PARA_DIGITS)) == last_n + 1:
                pm, n_para = fm, str(last_n + 1)
        if n_para and n_para.isdigit():
            last_n = int(n_para)
        new_para = bool(pm) or current is None or (
            len(prev_line.strip()) < short and re.search(r"[.:;\"”]\s*$", prev_line) and re.match(r"^\s*[A-Z(\"“]", ln))
        if new_para:
            close()
            sub = SUBMITTED_RE.search(ln)
            if sub and author_or_none(sub.group(1)):
                author = author_or_none(sub.group(1))
            current = {"kind": "paragraph", "page_start": page, "page_end": page, "text": ln,
                       "n": n_para, "article_heading": article, "author_raw": author}
        else:
            current["text"] += "\n" + ln
            current["page_end"] = page
        prev_line = ln
    close()
    # a list's symbols and titles in the same number, one after the other on the page: each title takes its symbol, in order
    # ("E/CN.4/607 — Yugoslavia : amendment to the Chilean proposal on the right to education"); else they stay apart
    i = 0
    while i < len(segments):
        x = segments[i]
        if x.get("doc_list_symbols"):
            syms = [l.strip() for l in x.get("_lines", []) if l.strip()]
            for j in range(len(syms) - 1, 0, -1):  # ("(French only)" goes with the symbol above it)
                if not DOC_SYMBOL_LINE_RE.match(syms[j]):
                    syms[j - 1] += " " + syms.pop(j)
            k = i + 1
            while k < len(segments) and segments[k].get("doc_list_symbols") is False and segments[k]["page_start"] == x["page_start"]:
                k += 1
            if k - i - 1 == len(syms) and syms:
                for sym_, y in zip(syms, segments[i + 1:k]):
                    y["text"] = f"{sym_} — {' '.join(y['text'].split())}"
                del segments[i]
                continue
        i += 1
    for x in segments:
        x.pop("doc_list_symbols", None)
        x.pop("_lines", None)
    # each footnote after the last segment that starts on its page, as in the meeting records
    for page, text in sorted(notes, key=lambda x: x[0], reverse=True):
        at = max((i for i, x in enumerate(segments) if x["page_start"] <= page), default=len(segments) - 1) + 1
        segments.insert(at, {"kind": "footnote", "page_start": page, "page_end": page, "text": " ".join(text.split()),
                             "article_heading": None, "author_raw": None})
    return finalize(symbol, engine, segments)


def one_digit_off(read: str, num: str) -> bool:
    """The OCR's reading of a paragraph number against the number the sequence wants: one digit more ("355" for 55, "730" for
    73), one less ("7" for 67), or one misread ("34" for 54, "19" for 79)."""
    if len(read) == len(num) + 1:
        return any(read[:k] + read[k + 1:] == num for k in range(len(read)))
    if len(num) == len(read) + 1:
        return any(num[:k] + num[k + 1:] == read for k in range(len(num)))
    return len(read) == len(num) and sum(a != b for a, b in zip(read, num)) == 1


def mend_numbers(segments: list[dict]) -> None:
    """A paragraph number that breaks its record's sequence, read again from its neighbours: "355. Mr. PAVLOV" between 54 and 60
    is 55, when one number of the gap is a digit off the reading and only one is (round 99: 161 numbers out of their sequence,
    the ¶ that citations give). The text keeps the number as printed."""
    numbered = [s for s in segments if str(s.get("n") or "").isdigit()]
    for p, s, q in zip(numbered, numbered[1:], numbered[2:]):
        pn, n, qn = int(p.get("n_end") or p["n"]), int(s["n"]), int(q["n"])
        # (not a number its neighbour also has: "18." after another "18." is a split speech or a wrong neighbour)
        if not pn < qn <= pn + 6 or pn <= n <= qn:
            continue
        fits = [c for c in range(pn + 1, qn) if one_digit_off(str(n), str(c))]
        if len(fits) != 1:
            continue
        last = fits[0]
        for k in s.get("_starts", []):
            if last < k <= last + 3:
                last = k
        if last >= qn:  # (the speech's own paragraphs would run into the next one's number: the sequence is wrong elsewhere)
            continue
        s["n_read"], s["n"] = s["n"], str(fits[0])
        if last > fits[0]:
            s["n_end"] = str(last)
        else:
            s.pop("n_end", None)


def para_end(text: str, n) -> str | None:
    """The last printed paragraph of a speech that runs over several ("7. Mr. HOFFMEISTER ...",
    "8. The citizens ...", ... "15. Mr. Hoffmeister concluded ..."): the run of numbers at line
    starts that goes on from the speech's own number."""
    if not n or not str(n).isdigit():
        return None
    last = int(n)
    for m in re.finditer(r"(?m)^\s*(\d{1,3})\s*[.,]\s+\S", text):
        k = int(m.group(1))
        if last < k <= last + 3:  # OCR can drop a number; a jump further is a list or a date
            last = k
    return str(last) if last > int(n) else None


# who presided, closing the masthead's attendance: "Chairman: Mr. Humberto DIAZ CASANUEVA" / "(Chile).", "In the absence of the
# Chairman, Mr. Dehousse (Belgium), Vice-Chairman, presided.", "President : Mr. H. V. Evatt (Australia)."
PRESIDING_RE = re.compile(r"^\W{0,3}(?:(?:Acting\s+|Vice-?\s*)?(?:Chairman|President|Pr[ée]sident)\s*:\s|In\W{0,3}the\s+absence\s+of\s+the\s+(?:Chairman|President))")
AGENDA_BLOCK_RE = re.compile(r"AGENDA\s+ITEM|\[\s*Item\s+\d|\((?:continued|concluded)\)|\bitem\s+\d{1,2}\s+of\s+the\s+agenda\b|^\W{0,3}\d{1,3}\s*\.\s+[A-Z][a-z]", re.I | re.M)


def masthead_agenda(lines: list[tuple[int, str]]) -> int | None:
    """Where the agenda item printed above the first turn starts in the masthead's lines: after the line that names who
    presided (the printed records), or the typed records' first heading in capitals after the list of the Secretariat; a
    block of at most 25 lines that reads as an agenda item (an item number, "(continued)", "AGENDA ITEM")."""
    if len(lines) < 3:
        return None
    def valid(a):
        if a is None or a >= len(lines) or len(lines) - a > 25:
            return False
        block = "\n".join(l for _, l in lines[a:])
        if re.search(r"\b(?:Present|Members|Observers?|Rapporteur)\s*:", block) or \
                len(re.findall(r"\b(?:Mr|Mrs|Miss|Dr|Prof)[.,]?\s+[A-Z][^()\n]{2,40}\([A-Z]", block)) >= 2:
            return False  # (an attendance list, not an agenda item)
        # an item number, "(continued)", a heading in capitals, or a short heading of its own ("Organization of work")
        return bool(AGENDA_BLOCK_RE.search(block) or caps_line(lines[a][1][:130])
                    or len(lines) - a <= 3 and re.match(r"^\W{0,3}[A-Z][a-z]", lines[a][1]) and not re.search(r"\(", block))
    pres = [i for i, (_, ln) in enumerate(lines) if PRESIDING_RE.match(ln)]
    if pres:
        i = pres[-1]
        # (the name and delegation can run onto the next line: "Chairman: Mr. Humberto DIAZ CASANUEVA" / "(Chile).";
        # "In the absence of the Chairman, Mr. Dehousse (Belgium)," / "Vice-Chairman, presided.")
        ends = [j for j in range(i, min(i + 3, len(lines))) if re.search(r"(?:presided|took\s+the\s+[Cc]hair)\W{0,4}$", lines[j][1].strip())] or \
               [j for j in range(i, min(i + 3, len(lines))) if re.search(r"\)\W{0,4}$", lines[j][1].strip())]
        if ends:
            a = ends[0] + 1
            # ("Chairman: Mr. Ramadan (Egypt);" / "later, Mr. Charles MALIK (Lebanon)."): who presided later is the attendance's
            while a < len(lines) and re.match(r"^\W{0,3}[Ll]ater\b", lines[a][1]):
                a += 1
            if valid(a):
                return a
    sec = [i for i, (_, ln) in enumerate(lines) if re.search(r"\bSecretar(?:y|ies)\b|Representative\s+of\s+the\s+Secretary", ln)]
    if sec:
        a = next((j for j in range(sec[-1] + 1, len(lines)) if caps_line(lines[j][1][:130]) or
                  re.match(r"^\W{0,6}(?:\d{1,2}\s*\.?\s*)?[A-Z][A-Z ,'\-]{20,}", lines[j][1])), None)
        if valid(a):
            return a
    return None


def segment_record(symbol: str, engine: str) -> list[dict]:
    notes: list[tuple[int, str]] = []  # the footnotes at the foot of the pages, taken out of the lines (normalize.strip_furniture)
    lines = split_notes(split_turns(join_covenant_headings(cut_to_meeting(symbol, load_lines(symbol, engine, notes)))))
    if not lines:
        return []
    # The masthead (title, attendance list, observers, secretariat) can run onto page 2.
    # It ends at the first article heading or the first speaker/chair line that goes on
    # to say something ("said", "opened the meeting"); attendance lines never do.
    start = 0
    for i, (page, ln) in enumerate(lines):
        kind, info = classify_ahead(ln, lines[i + 1][1] if i + 1 < len(lines) else "")
        if page > 8:
            break
        # an attendance line ("Mr. Roland Lebeau (Belgium) Mr. T. Kaminsky (...)") names
        # people; a speech opening goes on to a speaking verb right after the parenthesis
        after = (info.get("after", "") + " " + (lines[i + 1][1] if i + 1 < len(lines) else ""))[:80]
        # printed records from 1950 number their paragraphs: "1. Mr. ALTMAN (Poland) wished ..." is the body
        numbered = kind in ("speech", "chair") and str(info.get("n") or "").isdigit()
        # "The CHAIRMAN iavited ...": attendance lists write "Chairman: Mr. X", never "The CHAIRMAN"
        # (the verbatim plenary: "Mr. Pérez Cisneros (Cuba) (Translation from the French): ...", no verb; round 93)
        verbatim = "/PV." in symbol and kind == "speech" and re.search(r"\(\s*Transl\w*\s+from|^\s*:", after)
        if page <= 3 and (kind == "heading" or OPENING_RE.match(ln) or kind == "chair" or (kind == "speech" and (numbered or BODY_START_RE.search(after) or verbatim))):
            start = i
            break
        # the Commission's records of 1951-53 print a long contents page and an attendance table that run past page 3: from
        # there on only a turn that says something starts the body ("The CHAIRMAN invited ...", not "Chairman: Mr. AZMI (Egypt)")
        if page > 3 and (kind == "chair" or (kind == "speech" and (numbered or BODY_START_RE.search(info.get("after", "")[:80])))):
            start = i
            break
    segments: list[dict] = []
    if start:
        a = masthead_agenda(lines[:start])
        mtext = "\n".join(l for _, l in lines[:a or start])
        segments.append({"kind": "masthead", "page_start": 1, "page_end": lines[(a or start) - 1][0],
                         "text": mtext, "meeting_date": masthead_date(mtext)})
        if a:
            # the agenda item above the first turn, set apart from the masthead (the audit on random pages of round 80: 13 of
            # 81 errors were these headings, which the readers found in no segment); api/build_db.py reads it with the masthead
            segments.append({"kind": "heading", "page_start": lines[a][0], "page_end": lines[start - 1][0],
                             "text": " ".join(" ".join(l for _, l in lines[a:start]).split()), "agenda": True, "masthead_agenda": True})

    current: dict | None = None
    article: str | None = None

    def close() -> None:
        nonlocal current
        if current:
            current.pop("lead", None)
            end = para_end(current["text"], current.get("n"))
            if end:
                current["n_end"] = end
            current["_starts"] = [int(m.group(1)) for m in re.finditer(r"(?m)^\s*(\d{1,3})\s*[.,]\s+\S", current["text"])]
            current["text"] = " ".join(current["text"].split())
            segments.append(current)
        current = None

    def cut_chair_result(page: int, ln: str, nxt: str, append: bool = False) -> bool:
        """The chair's line running on into the result it announced (its verb can be on the next line): the chair's words stay
        in the turn, the result opens a segment of its own."""
        nonlocal current
        m = MIDLINE_RESULT_RE.search(ln + " " + nxt)
        if not m or m.start() >= len(ln.rstrip()):
            return False
        if append:
            current["text"] += "\n" + ln[:m.start()]
            current["page_end"] = page
        else:
            current["text"] = ln[:m.start()]
        close()
        current = {"kind": "procedural", "page_start": page, "page_end": page, "text": ln[m.end():], "article_heading": article}
        return True

    body = lines[start:]
    skip = 0
    for idx, (page, ln) in enumerate(body):
        if skip:
            skip -= 1
            continue
        kind, info = classify_ahead(ln, body[idx + 1][1] if idx + 1 < len(body) else "", " ".join(l for _, l in body[idx + 2:idx + 7]))
        if not kind and current is not None:
            kind, info = debris_turn(ln, current["text"].rstrip().rsplit("\n", 1)[-1])
        # (a turn with no delegation opens a line only after a sentence that ended: "... supported the proposal of" / "Mr. CASSIN
        # said ..." is not one; round 85)
        if kind == "speech" and info.get("nocountry") and current is not None and not re.search(r"[.!?:;\"”’)]\W{0,3}$", current["text"].rstrip()):
            kind, info = "", {}
        if not kind and current is not None:
            # (after a result the heading of the next paragraph needs no full stop before it: "... subject to those amendments" /
            # "Paragraphs 106 to 113", round 89)
            n = agenda_heading_lines(body, idx, "." if current.get("result") and PARA_HEAD_RE.match(ln)
                                     else current["text"].rstrip().rsplit("\n", 1)[-1])
            if n:
                close()
                text = " ".join(l.strip() for _, l in body[idx:idx + n])
                m = SUBHEAD_ARTICLE_RE.match(text) if not AGENDA_ITEM_RE.match(text) else None
                # (the preamble, after the articles: no article in force, "Preamble to the draft covenant", E/CN.4/SR.308)
                if re.match(r"^\W{0,2}(?:[IVX\d]{1,4}\s*\.\s+)?(?:(?:Discussion|Consideration)\s+of\s+)?(?:the\s+)?Preamble\b", text, re.I):
                    article = None
                if m:
                    article = m.group("art")
                    segments.append({"kind": "heading", "article_heading": article, "page_start": page, "page_end": body[idx + n - 1][0], "text": text})
                else:
                    segments.append({"kind": "heading", "article_heading": article, "page_start": page, "page_end": body[idx + n - 1][0],
                                     "text": text, "agenda": True})
                skip = n - 1
                continue
        # (in a meeting record a heading behind a bar is the other column's, "| ARTICLE 28" from the meeting before; round 90)
        # (the verbatim plenary, round 93: the President's turn however the OCR spells the role, "THe she (Translation from the" /
        # "French): We can now consider ...")
        if not kind and "/PV." in symbol and re.match(r"^\W{0,3}T[Hh][eo]?\s+\S{2,10}\s*\.?\s*\((?:Translation|translated)\s+from\b", ln):
            kind, info = "chair", {"role": "President", "n": None, "after": ""}
        # (and an item of the agenda after a decision: "Decision: The agenda was adopted." / "102. Distribution of Agenda Items
        # among" / "the Committees (document A/163).")
        if not kind and "/PV." in symbol and current is not None and re.match(r"^\s*\d{2,3}\.\s+[A-Z][a-z]", ln) \
                and (current.get("result") or SENT_END_RE.search(current["text"].rstrip())):
            # (the item's title runs over up to six lines and ends on its document or on "(postponement of the discussion)")
            k2 = next((k for k in range(idx, min(idx + 6, len(body)))
                       if re.search(r"\((?:documents?\s+[AE]\s?/[^()]*|postponement\s+of\s+the\s+discussion)\)\W*$", body[k][1])), None)
            if k2 is not None:
                close()
                segments.append({"kind": "heading", "article_heading": article, "page_start": page, "page_end": body[k2][0],
                                 "text": " ".join(l.strip() for _, l in body[idx:k2 + 1]), "agenda": True})
                skip = k2 - idx
                continue
        # (after a result, the next item's heading in the typed records: "First new article", "Document E/CN.4/L.366/Add.3"; round 94)
        if not kind and current is not None and current.get("result") and re.match(
                r"^\W{0,2}(?:(?:First|Second|Third|Fourth|Fifth|Sixth)\s+(?:new\s+)?article|New\s+article|Additional\s+article"
                r"|Documents?\s+[AEB£]\s?/\S+(?:\s+and\s+\S+)?)\W{0,3}$", ln.strip()):
            close()
            segments.append({"kind": "heading", "article_heading": article, "page_start": page, "page_end": page, "text": ln.strip(), "agenda": True})
            continue
        if kind == "heading" and ln.lstrip().startswith("|") and info.get("article") == article:
            kind, info = "", {}  # (but "| Article 38" after article 37 is the next article's heading: E/CN.4/SR.240)
        if kind == "heading":
            close()
            article = info["article"]
            # (with its paragraph, "Article 3, paragraph 2": the drafts that split an article, E/CN.4/95 art. 3, para. 2 is final
            # art. 7, E/CN.4/SR.52; the Covenant's keep the whole article, api/build_db.py whole_article)
            par = re.search(r",\s*paragraph\s+(\d)\b", ln)
            if par:
                article = f"{article}.{par.group(1)}"
            segments.append({"kind": "heading", "article_heading": article, "page_start": page,
                             "page_end": page, "text": ln.strip()})
            continue
        # an unnumbered "Mr. X (Country)" after a line that stops on a joining word, or on a delegation and a comma (a list of
        # speakers), is the rest of that sentence ("Mr. PHILLIPS (United Kingdom), replying to" / "Mr. P. C. CHANG (China), said that
        # ..."; "... in which Mr. YAPOU (Israel), Mr. CALDERON PUIG (Mexico)," / "Mr. BAROODY (Saudi Arabia), Mr. MEZINCESCU ..."; "49. After a further exchange of views in which" / "Mr. KASLIWAL (India), ... took part", round 99)
        if kind == "speech" and not info.get("n") and current is not None and (current["kind"] != "procedural" or current.get("result")) \
                and re.search(r"\b(?:to|by|from|of|and|with|than|which|whom)\s*$|\)\s*,\s*$", current["text"].rstrip().rsplit("\n", 1)[-1]):
            kind, info = "", {}
        # (the note can run onto the next line: "Mr. Ghorbal (United Arab Republic), Vice-Chairman," / "took the Chair.")
        # (a turn opened by a phrase names its speaker a line or more later: that line does not open the turn again, "6. After an
        # exchange of views, in which ... took" / "part, Mr. BAROODY (Saudi Arabia) proposed")
        if kind == "speech" and current is not None and current.get("lead") and current.get("speaker_raw") \
                and (info.get("name") or "").upper() == current["speaker_raw"].upper() and len(current["text"]) < 900:
            current["text"] += "\n" + ln
            current["page_end"] = page
            continue
        if kind == "speech" and CHAIR_NOTE_RE.match((info.get("after") or "") + " " + (body[idx + 1][1] if idx + 1 < len(body) else "")):
            close()
            current = {"kind": "procedural", "page_start": page, "page_end": page, "text": ln, "article_heading": article}
            continue
        if kind == "speech" and ELECTED_RE.match(info.get("after") or ""):
            close()
            current = {"kind": "procedural", "page_start": page, "page_end": page, "text": ln, "article_heading": article}
            continue
        if kind in ("speech", "chair", "closing"):
            close()
            current = {"kind": kind, "page_start": page, "page_end": page, "text": ln,
                       "article_heading": article, "n": info.get("n")}
            if kind == "speech":
                current.update({"title": info["title"], "speaker_raw": info["name"],
                                "country_raw": info["country"], "role_raw": info["role"]})
                if TURN_LEAD_RE.match(ln):
                    current["lead"] = True
            elif kind == "chair":
                current["role_raw"] = info["role"]
                cut_chair_result(page, ln, body[idx + 1][1] if idx + 1 < len(body) else "")
            continue
        if current is None:
            current = {"kind": "procedural", "page_start": page, "page_end": page, "text": ln,
                       "article_heading": article}
            # (a result right after its heading: "Paragraph 6" / "Paragraph 6 was accepted without objection." / "Paragraph 7")
            if RESULT_OPENER_RE.match(ln) and RESULT_RE.search(ln):
                current["result"] = True
            continue
        # a note set apart from the turns: the meeting suspended, a member taking the chair (each its own segment), a roll-call
        # or a decision by a count of votes (closing the turn before it)
        if MEETING_NOTE_RE.match(ln.strip()) or TOOK_CHAIR_RE.match(ln.strip()) or \
                (ROLL_CALL_RE.match(ln.strip()) or DECIDED_BY_RE.match(ln.strip())) and current["kind"] != "procedural" or \
                BODY_DECIDED_RE.match(ln.strip()) and current["kind"] in ("speech", "chair") and SENT_END_RE.search(current["text"].rstrip()):
            close()
            current = {"kind": "procedural", "page_start": page, "page_end": page, "text": ln, "article_heading": article}
            if BODY_DECIDED_RE.match(ln.strip()):
                current["decided"] = True
            continue
        # the chair's line that runs on into the result it announced: the result is the committee's, a segment of its own
        if current["kind"] == "chair" and cut_chair_result(page, ln, body[idx + 1][1] if idx + 1 < len(body) else "", append=True):
            continue
        # a vote sentence starting its own line closes the running speech (also one whose wording runs onto the next line,
        # when the speech before it has ended its sentence)
        nxt = body[idx + 1][1] if idx + 1 < len(body) else ""
        # (a result whose verb is two lines on: "The Polish oral amendment to substitute ... for" / "the phrase beginning ..." / "... was rejected")
        nxt2 = nxt + " " + (body[idx + 2][1] if idx + 2 < len(body) else "")
        result = RESULT_OPENER_RE.match(ln) and (
            (RESULT_RE.search(ln) and (VOTE_RE.search(ln) or RESULT_FIGURES_RE.search(ln + " " + nxt)))
            or (len(ln) < 130 and one_sentence_result(ln + " " + nxt2)
                and current["text"].rstrip().endswith((".", ";", ":", ","))))  # (a speech's too since round 86: the OCR's period)
        result = result or DECISION_RE.match(ln.strip()) or "/PV." in symbol and STAGE_RE.match(ln.strip())
        # (the typed records' label of the decision, "DECISION: This proposal was rejected by 5 votes to 3"; round 86)
        result = result or DECISION_LABEL_RE.match(ln)
        # (the count alone: "There were 6 votes in favour, 6 against and 4 abstentions;", "There were four votes in favour to four
        # votes against the proposal ... and it was declared rejected", E/CN.4/AC.1/SR.27; round 97)
        result = result or re.match(r"^\W{0,3}There\s+were\s+\S+\s+votes?\s+(?:in\s+favou?r|for)\b", ln)
        # (round 85: the body's decision with its count, and a decision without one that is a whole short line after a sentence that
        # ended: "Document E/CN.4/L.366/Add.7 was adopted, subject to those amendments.")
        result = result or BODY_RESULT_RE.match(ln + " " + nxt) or (
            len(ln.strip()) < 110 and RESULT_OPENER_RE.match(ln) and RESULT_RE.search(ln) and re.search(r"[.]\W{0,2}$", ln.strip())
            and not re.search(r"\bhad\s+been\b|\b(?:he|she|they|it)\s+(?:said|thought)\b", ln) and current["text"].rstrip().endswith((".", ";", ":")))
        # (a result after a result is the next vote: "Article 13 was adopted ..." / "Article 14 was adopted ...", round 89)
        # (and a labelled decision after the body's own note: "... the Commission decided to take a vote by paragraphs." /
        # "IECISION: The United Kingdom representative's amendment ... was rejected.", E/CN.4/SR.12; round 97)
        if result and (current["kind"] != "procedural" or current.get("result") and RESULT_RE.search(current["text"])
                       or DECISION_LABEL_RE.match(ln) and current.get("decided") and SENT_END_RE.search(current["text"].rstrip())):
            close()
            # ("result": a decision that stops on "submitted by" goes on with the name, "Mr. Amado (Panama) by 2 votes to 1")
            current = {"kind": "procedural", "page_start": page, "page_end": page, "text": ln,
                       "article_heading": article, "result": True}
            continue
        current["text"] += "\n" + ln
        current["page_end"] = page
    close()
    # bilingual printed records only: drop speeches whose delegation is written in French
    sel_path = OCR / safe_name(symbol) / "selection.json"
    sel = json.loads(sel_path.read_text()) if sel_path.exists() else {}
    bilingual = bool(sel) and sum(bool(v.get("two_column")) for v in sel.values()) / len(sel) >= 0.3
    segments = [x for x in segments if not (bilingual and x["kind"] == "speech" and x.get("country_raw")
                                            and FRENCH_DELEGATION_RE.match(x["country_raw"])
                                            and not re.search(r"\b(?:said|stated|thought|felt|pointed)\b", x["text"][:160]))]

    # a footnote is neither the speaker's words nor lost: its own segment after the last one that starts on its page (it carries the
    # documents the Secretariat cites there, "Subsequently circulated as document A/C.3/L.980")
    for page, text in sorted(notes, key=lambda x: x[0], reverse=True):
        at = max((i for i, x in enumerate(segments) if x["page_start"] <= page), default=len(segments) - 1) + 1
        segments.insert(at, {"kind": "footnote", "page_start": page, "page_end": page, "text": " ".join(text.split()), "article_heading": None})
    mend_numbers(segments)
    return finalize(symbol, engine, segments)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--engine", default="layer")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "segments")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for symbol in args.symbols:
        segs = segment(symbol, args.engine)
        path = args.out / f"{safe_name(symbol)}.{args.engine}.json"
        path.write_text(json.dumps(segs, ensure_ascii=False, indent=1), encoding="utf-8")
        kinds: dict[str, int] = {}
        for s in segs:
            kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
        print(f"  {symbol} [{args.engine}]: {len(segs)} segments {kinds}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
