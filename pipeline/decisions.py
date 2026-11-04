"""Decisions in the records: what was put to the vote, the outcome, the figures, the roll-call.

  "The Lebanese amendment (A/C.3/260) was adopted by 17 votes to 13, with 7 abstentions."
  "The amendment was rejected by four votes to one."   "Article 18 was adopted unanimously."
  "A vote was taken by roll-call as follows: In favour: Argentina, ... Against: ... Abstaining: ..."

The subject is the clause before the verb ("This amendment" takes in the sentence before it,
which names the amendment). Proposers are read from the subject ("the Cuban amendment",
"submitted by the representatives of Uruguay and Belgium"), and so are the documents it cites.
Roll-call lists are matched against the gazetteer of states; the OCR of two-column printed
records can interleave them, so a list whose length disagrees with the figures is flagged.
"""
from __future__ import annotations

import csv
import unicodedata
import re
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]

_UNITS = ["none", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
          "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60}
WORD_NUM = rf"(?:(?:{'|'.join(_TENS)})(?:[\s-](?:{'|'.join(_UNITS[1:10])}))?|{'|'.join(sorted(_UNITS, key=len, reverse=True))}|nil|throe)"
# OCR digits ("l7", "ik" for 14), but not the "o" of "one"
NUM = rf"(?:(?:[\dOolI]{{1,3}}|[1Iil][hk]|J[\dO])(?![A-Za-z])|{WORD_NUM})"  # ("J0" for 10, round 90)
# the figures: "11 votes to 2, with one abstention", "twelve votes for, none against, and four abstentions",
# "three votes in favour to none against with one abstention", "7 votes to, with 7 abstentions" (a figure lost),
# "a vote of four to none" ("votes" left out), "45 vote. to 6", "61.votes to none", "with no abstentions"
FIGURES = (rf"(?P<yes>{NUM})(?:(?:\s+|\.\s*)votes?\.?(?:\s+(?:for|in\s+favou?r))?(?:\s+[a-zA-Z|1](?=\s+to\b))?|(?=\s+to\s+{NUM}(?![\w-])))"
           rf"(?:\s*(?:to|,(?=\s*{NUM}\s+(?:votes?\s+)?against))[\s._]*(?:[a-zA-Z|]\s+(?={NUM}\b))?(?:(?P<no>{NUM}|\)(?=\s*,?\s*with\b)|[hk](?=[\s.,;]|$))(?:\s+(?:votes?\s+)?against)?)?)?"
           rf"(?:\s+\d(?=[\s,.;]+(?:with|and)\b))?"  # (the figure printed twice: "to 3 3, with 1 abstention")
           rf"(?:[\s,.;]+(?:[a-zA-Z|]\s+(?=with))?(?:and\s+|[‘'`]?[wvW]ith[\s-]+)(?P<abst>{NUM}|[hk]|no)\s+[a-z]{{0,3}}[s5]t[ea]nt[il1]ons?)?")
# (the OCR's misreadings of the words around the figures: "wes adopted", "hy 12 votes", "31 votesto 20",
# "‘with 2 abstentlons"; the figures and "votes" must still be there)
DECISION_RE = re.compile(
    rf"\b(?:was|were|wes|ws|vere|vas|wae|wis|wno|wag|way,?)\s+(?:[^\w\s]{{1,2}}\s*|\d\s+)?(?:thus\s+|therefore\s+|then\s+|also\s+)?"
    rf"(?P<outcome>adopted|rejected|accepted|approved|carried|defeated|deleted|retained|maintained|upheld|overruled|not\s+adopted|"
    rf"a[uo]opted|adoptcd|adopte[cd]|ado[nm]ted|rejecte\S|re[jJ]ccted|r[eo][st]ected)\b"  # ("adoptec", "resected", "rotected": round 87)
    rf"(?!\s+(?:out|on(?![\s.]*a\s+roll)|over|forward|into|through)\b)"
    rf"(?:\s+unanimously(?P<un>)|\s+without\s+(?:objection|opposition|a\s+(?:formal\s+)?vote|comment|discussion|dissent)(?P<wo>)"
    rf"|[\s,]*(?:as\s+amended,?\s*|as\s+a\s+whole,?\s*|in\s+(?:its|their)\s+entirety,?\s*|on\s+a\s+roll[-\s.]?ca[l1][l1](?:\s+vote)?\s*,?\s*)?"
    rf"(?:[\dIl|!]\s+(?=(?:by|hy)\b))?"  # (a stray mark before "by": "approved 1 by 11 votes")
    rf"(?:\s?\.\s?(?=(?-i:by)\b))?(?:by|hy|ty|bv|oy|>y|b;|b(?=\s+{NUM}\s+votes?\b))\s*[,.'‘\"]?\s*(?:a\s+vote\s+of\s+)?{FIGURES})?", re.I)  # ("adopted .by", "b; 8 votes": round 90)
# outcomes counted only with their figures: "The word was deleted" alone is a text's history, not a decision
FIGURES_ONLY = {"deleted", "retained", "maintained", "upheld", "overruled", "not adopted"}
# "It was decided, by 7 votes to 6, to retain ...", "The Commission decided by 9 votes to 3 that ..."
DECIDED_RE = re.compile(
    rf"\b(?:[Ii]t\s+(?:was|vas|wes|wae)|[Tt]he\s+(?:Commission|Committee|Working\s+(?:Party|Group)|Sub-?Committee|Drafting\s+Committee)"
    rf"(?:\s+(?:thus|therefore|then|accordingly|also))?)\s+(?:decided|agreed)\s*[,”\"]*\s*(?:by|hy|ty)\s+(?:a\s+vote\s+of\s+)?{FIGURES}"
    rf"\s*,?\s*(?P<rest>[^.;]{{0,300}})")
# the body as the subject: "The Commission rejected the Polish proposal by 7 votes to 3", "It adopted the report by 11
# votes to none", "the Commission adopted, by 11 votes to 3, the following article: ..."
ACTIVE_RE = re.compile(
    rf"\b(?:[Tt]he\s+(?:Third\s+)?(?:Commission|Committee|Working\s+(?:Party|Group)|Sub-?Commission|Sub-?Committee|Drafting\s+Committee|"
    rf"General\s+Assembly|Council)|It)\s+(?:thus\s+|then\s+|also\s+|therefore\s+|accordingly\s+|finally\s+|unanimously\s+)?"
    rf"(?P<outcome>adopted|rejected|approved|accepted|retained|deleted)\b(?P<obj>[^.;:]{{0,250}}?)\s*,?\s*(?:by|hy|ty)\s*[,.'‘\"]?\s*"
    rf"(?:a\s+vote\s+of\s+)?{FIGURES}\s*,?\s*(?P<after>[^.;]{{0,300}})")
# the figures first: "By 38 votes to 2, with 7 abstentions, the words were retained", "By 19 votes to 12, the Committee
# decided to meet on that date"
FRONT_RE = re.compile(rf"(?:^|(?<=[.;:])\s+|\n)\s*By\s+{FIGURES}\s*,\s*(?P<rest>[^.;]{{5,300}})")
FRONT_OUTCOME_RE = re.compile(r"\b(adopted|rejected|approved|accepted|retained|deleted|maintained|decided|agreed)\b")
# a resolution or text followed by its result in brackets: "(Adopted by 8 votes to 1)", "(Adopted by 10 votes to 0 on 6 December 1947)"
BRACKET_RE = re.compile(rf"\(\s*(?P<outcome>Adopted|Rejected|Approved)\s+(?:by|hy)\s+{FIGURES}[^)]{{0,40}}\)")
# "It was so decided": a decision without a vote on what the chair (or a delegate) had just proposed
SO_DECIDED_RE = re.compile(r"\b[Ii]t\s+was\s+so\s+(?:decided|agreed)\b")
# the chair's words before a decision taken without a vote: "Is there any objection? Decision: Paragraphs 4 (b) and (c)
# ... were adopted", "I take it that we can consider paragraph 4 (e) ... as approved", "under rule 128 ... the text as a
# whole need not be put to the vote and ... was rejected"
NO_VOTE_RE = re.compile(r"\bIs\s+there\s+any\s+objection|\bIf\s+there\s+(?:is|are|were|was)\s+no\s+objections?|\bthere\s+being\s+no\s+objection|"
                        r"\bin\s+the\s+absence\s+of\s+(?:any\s+)?objection|\bno\s+objection\s+(?:was|being)\s+raised|"
                        r"\b(?:take|takes|took)\s+it\s+that\b[^.]{0,200}?\b(?:approv|adopt|accept|agree|decid)|"
                        r"\bneed\s+not\s+be\s+put\s+to\s+(?:the\s+|a\s+)?vote", re.I)
# "There were 6 votes in favour, 6 against and 4 abstentions"
TALLY_RE = re.compile(rf"(?P<yes>{NUM})\s+votes?\s+in\s+favou?r(?:\s+of\s+[^,;.]{{1,60}})?\s*[,;]?\s*(?:and\s+)?(?P<no>{NUM})\s+(?:votes?\s+)?against"
                      rf"(?:[\s,;]*(?:and|with)?\s*(?P<abst>{NUM})\s+abstentions?)?", re.I)
BY_SPONSOR_RE = r"\s+by\s+(?:all\s+)?(?:the|its|their|his|her)\s+(?:[\w-]+\s+){0,3}?(?:co-)?(?:sponsors?|authors?|representatives?|delegations?)\b"
PROCEDURAL_MOTION_RE = re.compile(r"\bmotion\s+(?:for|to)\s+(?:the\s+)?(?:adjourn\w*|closure|clos\w+|suspen\w+)|"
                                  r"\bconsideration\s+of\s+[^;]{0,160}?\b(?:should\s+be\s+|be\s+)?(?:suspended|postponed|deferred|adjourned)\b|"
                                  r"\b(?:adjournment|closure|suspension)\s+of\s+the\s+(?:meeting|debate|discussion)|"
                                  r"\bChairman'?s\s+ruling\b|\bchallenge\s+to\s+the\s+(?:Chairman|ruling)", re.I)
# "if they were adopted", "unless it was accepted": not a decision
CONDITIONAL_RE = re.compile(r"\b(?:if|unless|whether|when|once|until|before)\b\W+(?:\S+\W+){0,6}$", re.I)


def _own_sentence(subj: str) -> str:
    """The vote's own sentence: what a speaker "observed" earlier in the subject is not the vote's reporter (a result that
    runs on after junk OCR, E/CN.4/SR.322)."""
    return re.split(r"[.!?][\"”]?\s+", subj[-400:])[-1]


def conditional(full: str, start: int) -> bool:
    """The clause before a vote makes it conditional ("if it was adopted"); within its own sentence only (not the
    words "if he so desires" put to the vote in the sentence before)."""
    window = re.split(r"[.!?;]\s+|\n\s*\n", full[max(0, start - 60):start])[-1]
    return bool(CONDITIONAL_RE.search(window))
# a speaker recounting or anticipating a vote ("he recalled that article 3 was adopted")
REPORTED_RE = re.compile(r"\b(?:said|recalled|pointed out|noted|thought|felt|believed|considered|stated|explained|hoped|feared|"
                         r"regretted|observed|remarked|reminded|emphasized|stressed)\b", re.I)
# "A vote was taken by roll-call on the first part of the seven-Power amendment (A/C.3/L.929 and Add.1)": what the list is on
ANNOUNCE_RE = re.compile(r"vote\s+was\s+taken\s+by\s+roll[-\s]?ca[l1][l1]\s*(?:on|of)\s+(?P<what>[^.]{3,250}?)(?=\.\s|:|$)", re.I)
ROLL_RE = re.compile(r"in\s+favou?r\s*:\s*(?P<yes>.*?)\s*Against\s*:\s*(?P<no>.*?)\s*Abstain(?:ing|ed)?\s*:\s*(?P<abst>.*?)"
                     r"(?=\.\s+[A-Z(]|\.\s*$|$|[;.]?\s*Absent\s*:)", re.I | re.S)
SYMBOL_RE = re.compile(r"\b((?:A|E) ?/ ?(?:(?![AE] ?/)[A-Z][A-Z0-9]*(?:\. ?[A-Z0-9]+)* ?/ ?)*(?:(?:[A-Z]+|[lI1](?=\. ?\d{2}))\. ?)?[1-9]\d*(?![\dA-Za-z])(?: ?/ ?(?:Rev|Add|Corr)\. ?\d+)*)")


def repair_symbols(text: str) -> str:
    """OCR punctuation inside a document symbol: "A/C,3/L,929 and Add,1", "A/C.3/L»923/Rev.2", "E/CN.V117", "#/CN.4/434"."""
    text = re.sub(r"(?<![\w/])#(?=/CN\.4/)", "E", text)
    text = re.sub(r"\bE/CN\.[V^](?=\d)", "E/CN.4/", text)
    text = re.sub(r"\b(A/C)[,](?=\d\b)", r"\1.", text)
    text = re.sub(r"\bA/[ecC][.,]\s?3(?=/)", "A/C.3", text)  # "A/e. 3/344", "A/c, 3/344"
    text = re.sub(r"(/L)[,»](?=\d)", r"\1.", text)
    return re.sub(r"\b(Add|Rev|Corr)[,](?=\d)", r"\1.", text)


def symbols_in(text: str) -> list[str]:
    """The documents a passage cites, closed up where the OCR spaced them ("A/C.3/ 247"); not a bare series ("A/C.3")."""
    out = {re.sub(r"\s+", "", s).rstrip(".") for s in SYMBOL_RE.findall(repair_symbols(text))}
    return sorted(s for s in out if not re.fullmatch(r"[AE]/C(?:N)?\.\d", s))

# Adjectives the records use for delegations' proposals ("the Cuban amendment")
ADJECTIVES = {
    "Afghan": "Afghanistan", "Argentine": "Argentina", "Australian": "Australia", "Belgian": "Belgium",
    "Bolivian": "Bolivia", "Brazilian": "Brazil", "Burmese": "Burma", "Byelorussian": "Byelorussian Soviet Socialist Republic",
    "Canadian": "Canada", "Chilean": "Chile", "Chinese": "China", "Colombian": "Colombia", "Costa Rican": "Costa Rica",
    "Cuban": "Cuba", "Czechoslovak": "Czechoslovakia", "Danish": "Denmark", "Dominican": "Dominican Republic",
    "Ecuadorean": "Ecuador", "Ecuadorian": "Ecuador", "Egyptian": "Egypt", "Salvadorean": "El Salvador",
    "Ethiopian": "Ethiopia", "French": "France", "Greek": "Greece", "Guatemalan": "Guatemala", "Haitian": "Haiti",
    "Honduran": "Honduras", "Icelandic": "Iceland", "Indian": "India", "Iranian": "Iran", "Iraqi": "Iraq",
    "Lebanese": "Lebanon", "Liberian": "Liberia", "Mexican": "Mexico", "Netherlands": "Netherlands",
    "New Zealand": "New Zealand", "Nicaraguan": "Nicaragua", "Norwegian": "Norway", "Pakistani": "Pakistan",
    "Panamanian": "Panama", "Paraguayan": "Paraguay", "Peruvian": "Peru", "Philippine": "Philippines",
    "Polish": "Poland", "Saudi Arabian": "Saudi Arabia", "Swedish": "Sweden", "Syrian": "Syria", "Siamese": "Thailand",
    "Turkish": "Turkey", "Ukrainian": "Ukrainian Soviet Socialist Republic", "South African": "Union of South Africa",
    "Soviet": "Union of Soviet Socialist Republics", "USSR": "Union of Soviet Socialist Republics",
    "United Kingdom": "United Kingdom", "United States": "United States of America", "Uruguayan": "Uruguay",
    "Venezuelan": "Venezuela", "Yemeni": "Yemen", "Yugoslav": "Yugoslavia",
    # members admitted 1949-66
    "Israeli": "Israel", "Indonesian": "Indonesia", "Albanian": "Albania", "Austrian": "Austria", "Bulgarian": "Bulgaria",
    "Cambodian": "Cambodia", "Ceylonese": "Ceylon", "Finnish": "Finland", "Hungarian": "Hungary", "Irish": "Ireland",
    "Italian": "Italy", "Jordanian": "Jordan", "Laotian": "Laos", "Libyan": "Libya", "Nepalese": "Nepal",
    "Portuguese": "Portugal", "Romanian": "Romania", "Spanish": "Spain", "Sudanese": "Sudan", "Moroccan": "Morocco",
    "Tunisian": "Tunisia", "Japanese": "Japan", "Ghanaian": "Ghana", "Malayan": "Federation of Malaya", "Guinean": "Guinea",
    "Cameroonian": "Cameroon", "Chadian": "Chad", "Cypriot": "Cyprus", "Dahomeyan": "Dahomey", "Gabonese": "Gabon",
    "Ivorian": "Ivory Coast", "Malagasy": "Madagascar", "Malian": "Mali", "Nigerian": "Nigeria", "Senegalese": "Senegal",
    "Somali": "Somalia", "Togolese": "Togo", "Mauritanian": "Mauritania", "Mongolian": "Mongolia",
    "Sierra Leonean": "Sierra Leone", "Tanganyikan": "Tanganyika", "Algerian": "Algeria", "Jamaican": "Jamaica",
    "Rwandese": "Rwanda", "Ugandan": "Uganda", "Kenyan": "Kenya", "Kuwaiti": "Kuwait", "Malaysian": "Malaysia",
    "Maltese": "Malta", "Zambian": "Zambia", "Tanzanian": "United Republic of Tanzania", "Gambian": "Gambia",
    "Guyanese": "Guyana", "Malawian": "Malawi", "Burundian": "Burundi", "Trinidadian": "Trinidad and Tobago",
    "Barbadian": "Barbados", "Upper Voltan": "Upper Volta",
}


def load_states() -> dict[str, str]:
    """Every name and variant in the gazetteer -> canonical name."""
    out = {}
    with (ROOT / "data" / "gazetteer" / "states.csv").open() as f:
        for r in csv.DictReader(f):
            out[r["canonical"]] = r["canonical"]
            for v in filter(None, (r.get("variants") or "").split("|")):
                out[v] = r["canonical"]
    return out


STATES = load_states()
_NAME_RE = re.compile(r"\b(" + "|".join(re.escape(n) for n in sorted({*STATES, *ADJECTIVES}, key=len, reverse=True)) + r")\b")


def number(raw: str | None) -> int | None:
    if raw is None:
        return None
    r = raw.lower().replace("-", " ").strip()
    if r in ("none", "nil", "no"):
        return 0
    if r in ("h", "k"):
        return 4  # the OCR's 4 (E/CN.4/SR.40: "with h abstentions"; E/CN.4/SR.331: "by ik votes")
    if re.fullmatch(r"[1il][hk]", r):
        return 14
    if r == "throe":
        return 3
    if r == ")":
        return 1  # ("rejected by 2 votes to ) with 4 abstentions": the OCR's 1)
    r = re.sub(r"^j(?=[\do])", "1", r)  # ("J0": 10)
    if r in _UNITS:
        return _UNITS.index(r)
    parts = r.split()
    if parts and parts[0] in _TENS:
        return _TENS[parts[0]] + (_UNITS.index(parts[1]) if len(parts) > 1 and parts[1] in _UNITS else 0)
    digits = r.translate(str.maketrans("oli", "011"))
    return int(digits) if digits.isdigit() else None


def ocr_adjective(word: str) -> list[str]:
    """A delegation's adjective the OCR misread, just before "amendment" or "proposal" ("The Teyptian proposal", "the Beleian
    amendment"): the nearest adjective, at a similarity of 85 or more, for a word of six letters or more."""
    w = re.sub(r"[^A-Za-z]", "", word)
    if len(w) < 6 or w in ADJECTIVES or w.lower() in {a.lower() for a in _LANGUAGES}:
        return []
    best = max((a for a in ADJECTIVES if " " not in a), key=lambda a: fuzz.ratio(w.lower(), a.lower()))
    return [ADJECTIVES[best]] if fuzz.ratio(w.lower(), best.lower()) >= 85 else []


def delegations_named(text: str) -> list[str]:
    """States a phrase names, by name or adjective, in order of mention (accents the OCR added dropped: "Nétherlands")."""
    out = []
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode() if not text.isascii() else text
    for m in _NAME_RE.finditer(text):
        name = STATES.get(m.group(1)) or ADJECTIVES.get(m.group(1))
        if name and name not in out:
            out.append(name)
    return out


def state_list(raw: str) -> list[str]:
    """A roll-call list ("Argentina, Australia, Brazl!, ...") as canonical state names."""
    out = []
    raw = re.sub(r"\s+", " ", raw)
    # "United Kingdom of Great Britain and Northern Ireland", "Trinidad and Tobago": not two items (OCR spellings too)
    raw = re.sub(r"(Br\w{3,6}n)\s+and\s+(Nor\w{3,5}\s+Ir\w{3,6})", r"\1 & \2", raw)
    raw = re.sub(r"(Trinidad)\s+and\s+(Tobago)", r"\1 & \2", raw)
    for item in re.split(r"\s*[,;]\s*|\s+and\s+", raw):
        item = item.replace(" & ", " and ")
        item = re.sub(r"[^\w\s'()-]", "", item).strip(" .|_-")
        item = re.sub(r"\s+Voted$", "", item)  # the plenary's "Uruguay. Voted against: ..."
        if not item or len(item) > 60:
            continue
        name = STATES.get(item)
        if not name:
            best = max(STATES, key=lambda n: fuzz.ratio(item.lower(), n.lower()))
            name = STATES[best] if fuzz.ratio(item.lower(), best.lower()) >= 85 else None
        if name and name not in out:
            out.append(name)
    return out


# "It", "That amendment", "The proposal", "The second part of the amendment": the clause names what was voted on only
# by reference
ANAPHOR_RE = re.compile(r"^\W*(?:(?:the\s+)?(?:\w+\s+)?(?:points?|parts?|paragraphs?|sub-paragraphs?|sentences?|clauses?|sections?)"
                        r"(?:\s+[\w()]+)?\s+of\s+)?"
                        r"(?:it|this|that|these|those|they|(?:the|this|that|these|those)\s+(?:\w+\s+)?"
                        r"(?:amendments?|amen\w{3,5}|proposals?|motions?|texts?|paragraphs?|words?|phrases?|sentences?|articles?|drafts?|"
                        r"remainder|parts?|resolutions?|suggestions?|clauses?))\b(?!\s+\d)", re.I)
PART_RE = re.compile(r"^(?:and\s+)?(?:then\s+)?(?:the\s+)?(?:\w+\s+)?(?:parts?|words?|phrases?|remainder|sentences?|clauses?)\b", re.I)
ORDINAL_RE = re.compile(r"\b(?:first|second|third|fourth|fifth|sixth|last|remaining|other|next)\b", re.I)
# where a clause starts: a sentence's end, the plenary records' "Decision:" (OCR "IECISION:"), a blank line, and a comma
# or semicolon before "The" (the OCR's reading of a full stop: "with 11 abstentions, The second paragraph was adopted")
# (and "the CHAIRMAN" after a full stop, the OCR having lost its capital: ". . the CHAIRMAN put to the vote ...", round 89)
BOUND_RE = re.compile(r"(?:[.!?]\s+(?=[A-Z\"“(]|the\s+(?:CHAIRMAN|PRESIDENT|Chairman|President)\b)|(?:Decision|[A-Z]?ECISION)\s*:\s*|\n\s*\n|(?<=[a-z)'’”])\s*[,;]\s+(?=The\s+\w))")
# a sentence that puts something to the vote: "The CHAIRMAN put to the vote the Lebanese amendment (A/C.3/L.86)",
# "called for a vote by division on paragraph 1 of the United Kingdom amendment", "a vote was taken by roll-call on ..."
PUT_RE = re.compile(r"(?<!be )(?<!been )\bput\b.{0,250}?\bto\s+(?:the\s+|a\s+)?vote\b|(?<!be )(?<!been )\bsubmit\w*\s+to\s+(?:the\s+|a\s+)?vote\b|"
                    r"\b(?:vote|voted|voting)\s+(?:separately\s+|first\s+|next\s+)?(?:up)?on\b|\bvote\s+was\s+taken\b.{0,40}?\bon\b|"
                    r"\bvote\s+by\s+(?:roll[-\s]?call|show\s+of\s+hands|division)\s+on\b|"
                    r"\b(?:called|asked)\s+for\s+a\s+(?:separate\s+)?vote\b|\bproceed(?:ed)?\s+to\s+(?:the\s+|a\s+)?vote\s+on\b", re.I | re.S)
ROLL_LIST_RE = re.compile(r"\b(?:in\s+favou?r|against|abstain(?:ing|ed)?)\s*:", re.I)


def is_anaphor(subj: str) -> bool:
    """A clause that names what was voted on only by reference: not "The Afghan motion", "The USSR resolution", a
    symbol, quoted words or a number ("The amendment to paragraph 2 of article 29")."""
    s = subj.strip()
    m = ANAPHOR_RE.match(s)
    if not m or delegations_named(s) or symbols_in(s):
        return False
    rest = s[m.end():]
    # "The words "and unions"": the words are quoted, but whose they were the sentence before says
    if re.match(r"\s*[“\"‘']", rest) and re.search(r"\b(?:words?|phrases?|sentences?)$", s[:m.end()], re.I):
        return len(rest.split()) <= 12
    return len(rest.split()) <= 3 and not re.search(r"[\d\"“”]|\b[A-Z]", rest)


NAMED_PROPOSAL_RE = re.compile(r"^\W*(?:\w{1,2}\s+)?(?:the|this|that)\s+(?:[\w-]+\s+){1,4}(?:joint\s+)?(?:amendments?|sub-amendments?|proposals?|motion|"
                               r"(?:draft\s+)?resolution|text|suggestion)\W*$", re.I)


def _result(sentence: str):
    """A decision recorded in a sentence (with or without figures, or "It was so decided"), or None."""
    return DECISION_RE.search(sentence) or SO_DECIDED_RE.search(sentence)


def antecedent(head: str, bounds: list[int], names: set | None = None) -> str | None:
    """The sentence an anaphoric clause refers to: the last one before it that puts something to the vote, past the
    roll-call lists, the remarks of the speakers and the results of the parts voted on before it ("The first paragraph
    was rejected ..."); not past the result of another vote, a proposal made in between ("Mr. X proposed to add ..."),
    nor further back than ten sentences. For a clause that names its proposer ("The Lebanese proposal"), `names` are
    its delegations: the sentence must name one of them, and the proposal's own sentence will do."""
    pos = [0] + bounds
    for k in range(len(pos) - 2, max(-1, len(pos) - 12), -1):
        if pos[-1] - pos[k] > 3000:
            break
        s = head[pos[k]:pos[k + 1]].strip()
        if ROLL_LIST_RE.search(s):
            continue
        # a request for a roll-call that does not say on what ("PAZHWAK (Afghanistan) asked for a vote by roll-call")
        if re.search(r"roll[-\s.]?ca[l1][l1]", s, re.I) and not re.search(r"roll[-\s.]?ca[l1][l1]\s+(?:vote\s+)?on\b|vote\s+was\s+taken\b.{0,40}?\bon\b", s, re.I):
            continue
        v = _result(s)
        if v is not None:
            if is_anaphor(s[:v.start()]):
                continue
            return None
        if PUT_RE.search(s):
            return s if not names or names & set(delegations_named(s)) else None
        if re.search(r"\b(?:propos\w*|amend\w*|suggest\w*|moved|motion)\b", s, re.I):
            return s if names and names & set(delegations_named(s)) else None
    return None


def subject_before(text: str, start: int, vote: bool = True) -> str:
    """The clause a decision is about: back to the sentence start; when the clause is only "It" or "This amendment",
    with the sentence that put it to the vote (else the sentence before, or the clause of the part voted on before).
    `vote` False ("It was so decided"): the sentence before only."""
    head = text[:start]
    bounds = [m.end() for m in BOUND_RE.finditer(head)]
    cut = bounds[-1] if bounds else 0
    # the result of the vote before, run on by the OCR ("... with 17 abstentions, Point 2 of the Argentine amendments");
    # in a vote by parts ("The United Kingdom amendment was voted on in parts: the words ... were adopted by 5 votes to
    # 3; the word "solely" ..."), the part with the sentence's start, which names what the parts are of
    counted = [r for r in DECISION_RE.finditer(head, cut) if r.group("yes") or r.group("un") is not None or r.group("wo") is not None]
    if counted:
        rest = re.sub(r"^[\W_]*(?:[A-Za-z][\W_]+(?=[A-Z]))?", "", head[counted[-1].end():])
        if rest.strip() and PART_RE.match(rest) and not re.search(r"\bas\s+(?:amended|a\s+whole)\b", rest, re.I):
            lead = re.sub(r"\s+", " ", head[cut:counted[0].start()]).strip()
            return clip(lead + " … " + re.sub(r"\s+", " ", rest).strip(), 400)
        if rest.strip():
            cut = len(head) - len(rest)
            bounds.append(cut)
    subj = head[cut:].strip()
    ante = None
    if bounds and is_anaphor(subj):
        ante = antecedent(head, bounds) if vote else None
        prev = bounds[-2] if len(bounds) >= 2 else 0
        before = head[prev:cut].strip()
        res = DECISION_RE.search(before)
        # (a result without figures is the same item, announced: "she would take it that the fourth amendment ... was
        # adopted. The proposal was adopted without objection")
        if res is not None and not (res.group("yes") or res.group("un") is not None
                                    or re.search(r"\b\d+\s+(?:votes?\s+)?(?:in\s+favou?r|against)", before[res.end():])):
            res = None
        if ante:
            subj = ante + " " + subj
        elif res is not None:
            # another vote: only a sequence of parts takes what the one before was on ("The first part of the Lebanese
            # amendment was adopted by 9 votes to 2. The second part ..."), not "The paragraph, as amended,"
            if ORDINAL_RE.search(subj):
                subj = before[:res.start()].strip() + " … " + subj
        elif not ROLL_LIST_RE.search(before):
            subj = (before + " " + subj).strip()
    elif bounds and vote and NAMED_PROPOSAL_RE.match(subj) and delegations_named(subj) and not symbols_in(subj):
        # "The Lebanese proposal": the sentence that put it to the vote says what it was ("... the proposal of the
        # Lebanese delegation to adopt the text of article 4 of the Declaration as article 8 of the covenant")
        ante = antecedent(head, bounds, set(delegations_named(subj)))
        if ante:
            subj = ante + " " + subj
    # (the sentence that put it to the vote is kept whole, to be clipped in the middle; else the last 400 characters)
    return re.sub(r"\s+", " ", subj)[-1500 if ante else -400:]


def clip(subject: str, size: int = 400) -> str:
    """A long clause shortened in the middle: its start (what was put to the vote) and its end (the decision's own words)."""
    if len(subject) <= size:
        return subject
    return subject[:size - 110].rsplit(" ", 1)[0] + " … " + subject[-100:].split(" ", 1)[-1]


_WHO = r"(?:the\s+)?(?:delegations?|representatives?|governments?)?\s*(?:of\s+)?"
PROPOSER_BEFORE_RE = re.compile(
    r"(?:amendments?|proposals?|draft\s+resolution|text)\s+(?:jointly\s+)?(?:submitted|proposed|presented|put\s+forward|sponsored|"
    r"introduced)\s+(?:jointly\s+)?by\s+" + _WHO + r"(?P<who>[^.;()]{3,140}?)\s*[,(]?\s*$", re.I)
PROPOSER_AFTER_RE = re.compile(r"^\s*\)?\s*,?\s*(?:(?:which\s+(?:had\s+been|was)\s+)?(?:submitted|proposed|presented|sponsored|introduced)"
                               r"\s+(?:jointly\s+)?by\s+" + _WHO + r"(?P<who>[^.;()]{3,120}))", re.I)
# (names joined by a hyphen: "the India-United Kingdom text", "the joint United Kingdom-Indian amendment")
ADJ_BEFORE_RE = re.compile(r"(?P<who>(?:[A-Z][\w.]*(?:-[A-Z][\w.]*)*\s+){1,4}?)(?:joint\s+)?(?:amendments?|proposals?|draft\s+resolution|text)\s*[,(]?\s*$")


def proposers_of(text: str, start: int, end: int) -> list[str]:
    """Who proposed the document cited at text[start:end]: "the Cuban amendment (A/C.3/...)",
    "the amendment submitted by the delegations of Uruguay and Belgium (A/C.3/...)",
    "A/C.3/260, submitted by Lebanon"."""
    before = text[max(0, start - 160):start]
    before = re.sub(r"\(\s*(?:document|doc\.)\s*$", "(", before, flags=re.I)  # "text (document E/CN.4/99)"
    for rx in (PROPOSER_BEFORE_RE, ADJ_BEFORE_RE):
        m = rx.search(before)
        if m and delegations_named(m.group("who")):
            return delegations_named(m.group("who"))
    m = PROPOSER_AFTER_RE.match(text[end:end + 160])
    return delegations_named(m.group("who")) if m else []


# (and "amendment" as the typed records' OCR spells it: "emeniment", "anendment", "amenduent"; round 86)
AMEND_OCR = r"(?!amendments?\b)[ae][mn][ae]n[dil1]?[a-z]{0,2}[mnu][ea]nts?"
_PROPOSAL_RE = re.compile(rf"\b(?:joint\s+)?(?:(?:sub-?)?amendments?|{AMEND_OCR}|proposals?|(?:draft\s+)?resolution|motion|suggestion|text)\b", re.I)
# the words before the text an amendment is to: "the Egyptian amendment to the ", "the deletion of the words ... from the "
# (not "proposed in the": "the third paragraph proposed in the USSR amendment")
TARGET_RE = re.compile(r"\b(?:amendments?|sub-amendments?|additions?|deletions?|insertions?|substitut\w*|replac\w*)\b"
                       r"(?:(?!\b(?:proposed|contained|set\s+forth|submitted|put\s+forward)\b)[^.;])*?\b(?:to|in|from)\s+(?:the\s+)?$|"
                       # "the Afghan amendment to the text proposed in point 2 of the Indian amendment"
                       r"\b(?:amendments?|sub-amendments?)\b[^.;]{0,40}?\bto\s+the\s+(?:text|paragraph|wording)\s+(?:proposed|submitted|contained)\s+"
                       r"(?:in|by)\b[^.;]*$|"
                       # the object of another's proposal: "the United Kingdom proposal to add the Belgian amendment"
                       r"\bpropos\w*\s+to\s+(?:add|insert|include|incorporate|retain|combine|use|take)\s+(?:the\s+)?$|"
                       r"\b(?:with\s+the\s+exception\s+of|except(?:\s+for)?|without)\s+(?:the\s+)?$", re.I)
# "the French text": the French version, not a French proposal
_LANGUAGES = {"French", "English", "Spanish", "Russian", "Chinese", "Arabic"}
# who moved a procedural motion: "Mr. PAZHWAK (Afghanistan) further proposed that the meeting should be adjourned"
MOVER_RE = re.compile(r"\b[A-Z][A-Z'\-.]+(?:\s+[A-Z][A-Z'\-.]+)*\s+\((?P<who>[^)]{3,60})\)\s+(?:further\s+|then\s+|also\s+|formally\s+)?"
                      r"(?:proposed|moved)\s+(?:that|the)\b")


def proposers_in(subject: str, noun: str | None = None) -> list[str]:
    """Delegations a decision's subject names as authors: "the Cuban amendment", "the Belgian
    and Uruguayan proposal", "the amendment submitted by the delegations of X and Y", "the
    proposal of X". Not every state the clause mentions ("Iceland, having been drawn by lot"), nor the authors of the
    text an amendment is to ("the Egyptian amendment to the United States text"). `noun`: only proposals so called
    ("amendment" for "The amendment")."""
    out: list[str] = []
    # "the motion of Lebanon, seconded by Chile", "supported by the representatives of India and Israel": not authors
    # "amended at the suggestion of the representatives of China and France": nor are those who only suggested changes
    subject = re.sub(r",?\s*\b(?:(?:seconded|supported|endorsed)\s+by|(?:amended\s+)?at\s+the\s+(?:suggestion|request)\s+of)\s+[^,;()]{3,120}",
                     "", subject, flags=re.I)
    # a motion to adjourn or close: its mover (a proposal it names is only the object: "to allow for consultations on
    # the Philippine suggestion")
    if PROCEDURAL_MOTION_RE.search(re.split(r"(?<=[.;])\s+", subject)[-1]) or re.search(r"\badjourn", subject, re.I):
        mover = list(MOVER_RE.finditer(subject))
        return delegations_named(mover[-1].group("who")) if mover else []
    for m in _PROPOSAL_RE.finditer(subject):
        word = re.sub(r"s$", "", m.group(0).lower()).split()[-1]
        word = "amendment" if re.fullmatch(AMEND_OCR, word + "s") or re.fullmatch(AMEND_OCR, word) else word
        if noun and word != noun:  # ("sub-amendment" is not "amendment")
            continue
        pre = subject[max(0, m.start() - 60):m.start()]
        pre = re.sub(r"\b(?:oral|written|revised|new|further)\s+$", "", pre)  # "the Polish oral amendment"
        mb = re.search(r"((?:[A-Z][\w.]*(?:-[A-Z][\w.]*)*\s+(?:and\s+)?){1,5})$", pre)
        if mb and re.search(r"(?<!vote )(?<!voting )\b(?:on|about|concerning|regarding|with)\s+the\s+$", pre[:mb.start()]):
            continue  # "consultations on the Philippine suggestion": not the item put to the vote ("a vote on the" is)
        if m.group(0).lower() == "text" and mb and mb.group(1).split()[-1] in _LANGUAGES:
            continue  # "the French text": the language version
        start0 = m.start() - (len(mb.group(1)) if mb else 0)
        # (a symbol's full stops do not end the sentence: "the USSR amendment (E/CN.4/L.121) to the United Kingdom ...")
        if TARGET_RE.search(re.sub(r"\([^()]{0,60}\)", "()", subject[max(0, start0 - 200):start0])):
            continue  # the text amended: "the Egyptian amendment to the United States text", "deletion ... from the X text"
        names = delegations_named(mb.group(1)) if mb else []
        if mb and not names:
            names = ocr_adjective(mb.group(1).split()[-1])
        if not names:
            ma = re.match(r"\s*(?:\([^)]*\)\s*,?\s*)?(?:jointly\s+)?(?:submitted|proposed|presented|put\s+forward|sponsored|"
                          r"introduced|of)\s+(?:jointly\s+)?(?:by\s+)?" + _WHO + r"(?P<who>[^.;()]{3,120})",
                          subject[m.end():m.end() + 160], re.I)
            names = delegations_named(ma.group("who")) if ma else []
        out += [n for n in names if n not in out]
    if not out:
        # "the sentence which the Haitian representative proposed", "proposed by the French representative", "the United
        # Kingdom representative's amendment"
        for m in REP_PROPOSER_RE.finditer(subject):
            out += [n for n in delegations_named(m.group("a") or m.group("b")) if n not in out]
    return out


REP_PROPOSER_RE = re.compile(
    r"\b(?:proposed|submitted|presented|sponsored|introduced|moved|suggested)\s+(?:jointly\s+)?by\s+(?:the\s+)?"
    r"(?P<a>[-\w]+(?:\s+[A-Z][\w-]*){0,3})\s+(?:representatives?|delegations?|delegates?|Governments?)\b|"
    r"\b[Tt]he\s+(?P<b>[A-Z][\w-]*(?:\s+[A-Z][\w-]*){0,3})\s+(?:representative|delegation|delegate|Government)(?:['’]s|s['’])?\s+"
    r"(?:had\s+)?(?:proposed|submitted|suggested|moved|amendments?|proposals?|motion|suggestion)\b")


BASE_TEXT_RE = re.compile(r"\bas\s+(?:a\s+whole|(?:orally\s+|thus\s+)?amended)\b|\b(?:original|basic)\s+text\b|\bin\s+(?:its|their)\s+entirety\b", re.I)


def proposers_for(subject: str) -> list[str]:
    """The proposers of what a decision's clause names: a clause that names them ("The Guatemalan proposal") alone, not
    the others its sentence before names; an anaphoric one ("The amendments") from the proposals so called in the
    sentence that put it to the vote ("the Saudi Arabian amendments ... and the Peruvian draft resolution")."""
    parts = re.split(r"(?<=[.;][\"”’'])\s+|(?<=[.;])\s+", subject)
    last = parts[-1]
    # a base text ("draft resolution A/C.3/L.194 as a whole, as amended", "paragraph 1 of the original text"): no
    # proposers unless the clause names them ("The Lebanese amendment as a whole"); round 78's blind check
    proposal = re.match(r"^\W*(?:[\w()-]+\W+){0,6}?(?:(?:sub-?)?amendments?|proposals?|motions?|suggestions?)\b", last, re.I)
    if BASE_TEXT_RE.search(last) and not delegations_named(last) and not proposal:
        return []  # ("The proposal, as amended," is still the proposal)
    if len(parts) > 1:
        own = proposers_in(last)
        if own:
            return own  # the clause names its proposers ("The amendment proposed by the representative of Yugoslavia")
        n = re.search(r"\b(amendment|proposal|motion|resolution|suggestion)s?\b", last, re.I)
        if n and is_anaphor(last):
            got = proposers_in(" ".join(parts[:-1]), noun=n.group(1).lower())
            if got:
                return got
    return proposers_in(subject)


def roll_misfit(d: dict, roll: dict) -> float:
    """How far a decision's figures are from a roll-call's list lengths (no figures: neutral)."""
    if d.get("yes") is None:
        return 50.0
    # a list with more names than a figure is another vote's: the OCR loses names, it does not add them (round 79: 9 of
    # 12 lists with two or more names too many belonged to the vote before or after, on the page images)
    if sum(max(0, len(roll[k]) - (d.get(k) or 0)) for k in ("yes", "no", "abstentions")) > 1:
        return 99.0
    return sum(abs(len(roll[k]) - (d.get(k) or 0)) for k in ("yes", "no", "abstentions"))


def _decision(start: int, subj: str, outcome: str, yes, no, abst) -> dict:
    return {"start": start, "subject": subj, "outcome": outcome, "yes": yes, "no": no, "abstentions": abst,
            "unanimous": False, "without_vote": False, "proposers": proposers_for(subj),
            "refs": symbols_in(subj),
            "article": article_of(subj), "roll_call": None,
            "procedural": bool(PROCEDURAL_MOTION_RE.search(own_clause(subj)))}


def article_of(subject: str) -> str | None:
    """The draft article a clause names last; not the one a new article is to follow ("to insert a new article after
    article 30": a vote on no existing article, round 78)."""
    if re.search(r"\bnew\s+article\b[^.;]{0,40}?\b(?:after|before|following)\s+article\s+\d", subject, re.I):
        return None
    return (re.findall(r"\barticles?\s+(\d{1,2})\b", subject, re.I) or [None])[-1]


def own_clause(subject: str) -> str:
    """A decision's own sentence, with the sentence that put it to the vote when it names it only by reference
    ("The CHAIRMAN put the motion for the adjournment of the meeting to the vote. The motion") or by its proposer
    ("... proposed that the consideration of article 26 bis ... should be suspended. The New Zealand proposal")."""
    parts = re.split(r"(?<=[.;])\s+", subject)
    named = NAMED_PROPOSAL_RE.match(parts[-1]) and delegations_named(parts[-1])
    return " ".join(parts[-2:]) if len(parts) > 1 and (is_anaphor(parts[-1]) or named) else parts[-1]


def decisions(text: str, speech: bool = False, context: str = "") -> list[dict]:
    """Every decision in a passage, in order. In a speech, only a decision with figures that
    the speaker isn't recounting (summary records sometimes run the result on into the speech).
    `context` (the end of the passage before) supplies the subject of "The amendment was ..."."""
    pre = context[-3000:] + "\n\n" if context else ""
    full = pre + text
    out = []
    for m in DECISION_RE.finditer(full, len(pre)):
        if conditional(full, m.start()):
            continue
        subj = subject_before(full, m.start())
        yes, no, abst = number(m.group("yes")), number(m.group("no")), number(m.group("abst"))
        # (a rejection however the OCR spells it, "rejecte|", "reJccted", "resected": its majority voted against; round 87)
        raw = m.group("outcome").lower()
        against = raw in ("rejected", "defeated") or raw.startswith("rej") or bool(re.fullmatch(r"r[eo][st]ected", raw))
        tail = full[m.end():m.end() + 160]
        t = TALLY_RE.match(tail.lstrip(" ,;:(")) if yes is None else None
        if t is None and yes is None:
            t = TALLY_RE.search(subj)
        if t:
            yes, no, abst = number(t.group("yes")), number(t.group("no")), number(t.group("abst"))
        elif yes is not None and no is None and abst is not None and not re.search(r"\bto\b", full[m.start("yes"):m.start("abst")]) \
                and re.match(r"adopt|approv|accept|carried|a[uo]opt|ado[nm]t", m.group("outcome"), re.I):
            no = 0  # "adopted by 25 votes with 10 abstentions" (no "to"): none against
        elif against and m.group("no") is not None \
                and not re.search(r"\b(?:for|in\s+favou?r)\b", m.group(0), re.I):  # "one vote in favour to seven against"
            # "rejected by 28 votes to 17": the majority comes first, and it voted against
            yes, no = no, yes
        elif against and yes is not None and no is None \
                and not re.search(r"\b(?:for|in\s+favou?r)\b", m.group(0), re.I):
            # "rejected by 20 votes to ó (6), with 11 abstentions": the one figure read is the majority's, against
            yes, no = None, yes
        if speech and (yes is None and m.group("un") is None or REPORTED_RE.search(_own_sentence(subj))):
            continue
        outcome = re.sub(r"\s+", " ", m.group("outcome").lower())
        outcome = ("adopted" if re.fullmatch(r"a[uo]opted|adoptcd|adoptec|ado[nm]ted", outcome)
                   else "rejected" if outcome.startswith("rej") or re.fullmatch(r"r[eo][st]ected", outcome) else outcome)
        if outcome in FIGURES_ONLY and yes is None:
            continue
        if outcome == "not adopted":
            outcome = "rejected"
        # "This suggestion was adopted by the sponsors of the eleven-Power proposal": a sponsor's revision, not a vote
        if yes is None and m.group("un") is None and m.group("wo") is None and re.match(BY_SPONSOR_RE, tail):
            continue
        # no figures after "Is there any objection?", "I take it that ... approved", "need not be put to the vote": no vote
        without = m.group("wo") is not None
        if yes is None and m.group("un") is None and not without:
            window = full[max(0, m.start() - 500):m.start()]
            prior = [r.end() for r in DECISION_RE.finditer(window)]
            without = bool(NO_VOTE_RE.search(window[prior[-1] if prior else 0:]))
        out.append({
            "start": m.start() - len(pre), "subject": subj, "outcome": outcome,
            "yes": yes, "no": no, "abstentions": abst,
            "unanimous": m.group("un") is not None, "without_vote": without,
            "proposers": proposers_for(subj),
            "refs": symbols_in(subj),
            "article": article_of(subj),
            "roll_call": None,
            # the motion to adjourn or close, a ruling challenged: the vote is on procedure, not on an article
            "procedural": bool(PROCEDURAL_MOTION_RE.search(own_clause(subj))),
        })
    for m in DECIDED_RE.finditer(full, len(pre)):
        if conditional(full, m.start()) or speech and REPORTED_RE.search(_own_sentence(subject_before(full, m.start()))):
            continue
        rest = m.group("rest").strip()
        # (not the next sentence the OCR ran on with a comma: "..., Tae CHAIRMAN put the Egyptian amendment")
        rest = re.split(r"[,;]\s+(?=(?:T\w{1,2}\s+)?(?:CHAIRMAN|PRESIDENT)\b|Mrs?\.?\s+[A-Z]{2,})", rest)[0]
        subj = rest if re.match(r"(?:to|that|not)\b", rest) else subject_before(full, m.start())
        out.append(_decision(m.start() - len(pre), re.sub(r"\s+", " ", subj)[:400], "decided",
                             number(m.group("yes")), number(m.group("no")), number(m.group("abst"))))
    def reported(start: int) -> bool:
        return bool(conditional(full, start) or speech and REPORTED_RE.search(_own_sentence(subject_before(full, start))))

    def figures(m) -> tuple:
        yes, no, abst = number(m.group("yes")), number(m.group("no")), number(m.group("abst"))
        against = m.group("outcome").lower() == "rejected" and not re.search(r"\b(?:for|in\s+favou?r)\b", m.group(0), re.I)
        if against and no is None and yes is not None:  # (the minority's figure lost: the one read is the majority's, against)
            return (None, yes, abst)
        return (no, yes, abst) if against and no is not None else (yes, no, abst)

    def anaphoric(subj: str, start: int) -> str:
        # "It adopted it", "the words were retained": the sentence before names what was voted on
        if is_anaphor(subj):
            s0 = ([0] + [x.end() for x in BOUND_RE.finditer(full[:start])])[-1]
            return subject_before(full[:s0] + subj[:1].upper() + subj[1:] + " ", s0 + len(subj) + 1)
        return subj

    for m in ACTIVE_RE.finditer(full, len(pre)):
        if reported(m.start()):
            continue
        obj = m.group("obj").strip(" ,")
        subj = obj if len(obj.split()) >= 2 or re.search(r"\d", obj) else (obj + " " + m.group("after")).strip(" ,")
        subj = anaphoric(re.sub(r"\s+", " ", subj), m.start())
        yes, no, abst = figures(m)
        out.append(_decision(m.start() - len(pre), subj[:400], m.group("outcome").lower(), yes, no, abst))
    for m in FRONT_RE.finditer(full, len(pre)):
        if reported(m.start()):
            continue
        rest = re.sub(r"\s+", " ", m.group("rest"))
        o = FRONT_OUTCOME_RE.search(rest)
        if not o:
            continue
        outcome = o.group(1)
        subj = rest[o.end():].strip(" ,") if outcome in ("decided", "agreed") else rest[:o.start()]
        subj = re.sub(r"\s+(?:was|were)\s*$", "", subj.strip())
        subj = anaphoric(subj, m.start()) if outcome not in ("decided", "agreed") else subj
        yes, no, abst = number(m.group("yes")), number(m.group("no")), number(m.group("abst"))
        if outcome == "rejected" and no is not None and not re.search(r"\b(?:for|in\s+favou?r)\b", m.group(0), re.I):
            yes, no = no, yes
        elif outcome == "rejected" and no is None and yes is not None and not re.search(r"\b(?:for|in\s+favou?r)\b", m.group(0), re.I):
            yes, no = None, yes
        d = _decision(m.start() - len(pre), subj[:400], outcome, yes, no, abst)
        d["_span"] = (m.start() - len(pre), m.end() - len(pre))
        out.append(d)
    for m in BRACKET_RE.finditer(full, len(pre)):
        if reported(m.start()):
            continue
        yes, no, abst = figures(m)
        out.append(_decision(m.start() - len(pre), subject_before(full, m.start()), m.group("outcome").lower(), yes, no, abst))
    # a fronted vote's own verb ("... the amendment was adopted") is not a second decision
    spans = [d.pop("_span") for d in out if "_span" in d]
    out = [d for d in out if not (d["yes"] is None and any(a < d["start"] < b for a, b in spans))]
    if not speech:
        for m in SO_DECIDED_RE.finditer(full, len(pre)):
            subj = subject_before(full, m.start(), vote=False)
            # (the decision set apart at the head of its own passage: what the chair proposed ends the passage before; round 88)
            if len(subj.split()) < 4 and pre and not full[len(pre):m.start()].strip(" \n.,;:-|'\"_"):
                subj = subject_before(full[:len(pre) - 2] + "  " + full[len(pre):], m.start(), vote=False)
            if len(subj.split()) < 4:  # "It": the sentence before holds what was decided
                continue
            d = _decision(m.start() - len(pre), subj, "decided", None, None, None)
            d["without_vote"] = True
            out.append(d)
    out.sort(key=lambda d: d["start"])
    for r in ROLL_RE.finditer(full, len(pre)):
        roll = {"yes": state_list(r.group("yes")), "no": state_list(r.group("no")), "abstentions": state_list(r.group("abst"))}
        # the decision the roll-call belongs to: summary records give the result after the list,
        # reports before it ("... was adopted by 57 votes to 26 ... The voting was as follows:");
        # of the nearest decision on each side, the one whose figures fit the list
        rs = r.start() - len(pre)
        after = [d for d in out if d["start"] >= rs and d["roll_call"] is None]
        before = [d for d in out if d["start"] < rs and d["roll_call"] is None]
        cands = ([after[0]] if after else []) + ([before[-1]] if before else [])
        target = min(cands, key=lambda d: (roll_misfit(d, roll), 0 if d in after else 1)) if cands else None
        if target is not None and target.get("yes") is not None and roll_misfit(target, roll) > 10:
            target = None  # its figures belong to another vote: the list stands on its own
        if target is None:
            target = {"start": rs, "subject": subject_before(full, r.start()), "outcome": None, "yes": None,
                      "no": None, "abstentions": None, "unanimous": False, "without_vote": False, "proposers": [],
                      "refs": [], "article": None, "roll_call": None}
            target["proposers"] = proposers_for(target["subject"])
            target["refs"] = symbols_in(target["subject"])
            # the plenary's form of 1946 (A/PV.7): "The result of the voting is as follows: ... Voted against ... 27 Voted
            # in favour ... 12 Abstained ... 10 ... The amendment is not carried."
            after_list = full[r.end():r.end() + 600]
            res = re.search(r"\b(?:is|are)\s+(not\s+)?(?:carried|adopted)\b", after_list)
            if res and re.search(r"result\s+of\s+the\s+vot\w+\s+is\s+as\s+follows", after_list[:res.start()], re.I):
                table = after_list[:res.start()]
                # (each figure is the last number before the next label: dot leaders are read as "2.seeeeseee 27")
                cells = re.split(r"(Voted\s+in\s+favou?r|Voted\s+against|Abstained|Absent|Number\s+of\s+States\s+voting)", table)
                fig = {}
                for label, cell in zip(cells[1::2], cells[2::2]):
                    k = "yes" if "favour" in label else "no" if "against" in label else "abstentions" if label == "Abstained" else None
                    nums = re.findall(r"\b\d{1,2}\b", cell)
                    if k and nums:
                        fig[k] = int(nums[-1])
                target["outcome"] = "rejected" if res.group(1) else "adopted"
                target.update({k: fig.get(k) for k in ("yes", "no", "abstentions")})
                announce = full.rfind("(A vote was taken", 0, r.start())
                if announce > 0 and subject_before(full, announce).strip():
                    target["subject"] = subject_before(full, announce)
                    target["proposers"], target["refs"] = proposers_for(target["subject"]), symbols_in(target["subject"])
            out.append(target)
        # the sentence that announced it ("a vote was taken by roll-call on ..."), for a vote that names nothing itself
        ann = list(ANNOUNCE_RE.finditer(full[max(0, r.start() - 700):r.start()]))
        if ann and not target["refs"]:
            what = ann[-1].group("what")
            target["refs"] = symbols_in(what)
            if not target["proposers"]:
                target["proposers"] = proposers_in(what)
        roll["complete"] = all(target[k] is None or len(roll[k]) == target[k] for k in ("yes", "no", "abstentions"))
        target["roll_call"] = roll
    for d in out:
        # a motion to adjourn or close whose mover spoke before the chair put it ("Mr. Carrera ANDRADE (Ecuador) moved the
        # adjournment of the meeting ... The CHAIRMAN put the motion for the adjournment of the meeting to the vote")
        kind = re.search(r"adjourn|clos|suspen", own_clause(d["subject"]), re.I) if d.get("procedural") and not d["proposers"] else None
        if kind:
            s = d["start"] + len(pre)
            movers = [x for x in MOVER_RE.finditer(full[max(0, s - 2500):s])
                      if re.match(r"[^.]{0,80}?\b" + kind.group(0), full[max(0, s - 2500) + x.end():], re.I)]
            if movers:
                d["proposers"] = delegations_named(movers[-1].group("who"))
        d["subject"] = clip(d["subject"])
    return sorted(out, key=lambda d: d["start"])
