#!/usr/bin/env python3
"""Attendance lists and speaker resolution.

1. roster(): read the attendance list on the first page(s) of a summary record from the
   PDF text layer, using word positions. The list is a table:
       Members:   Mr. HOOD        Australia
                  Mr. STEPANENKO  Byelorussian Soviet Socialist
                                  Republic
   (label column, then title + name, then the delegation; long delegation names wrap).
2. resolve(): give every speech segment a delegation and a speaker from that roster.
   OCR garbles names ("VHSOB", "FOHTAIKA") far more than countries, so the delegation
   is resolved first (gazetteer, then roster), and the speaker is then picked among the
   delegates the roster lists for that delegation.

Each resolution records its method and score, so the weak ones can go to review (or to
Jev, choosing among the roster entries).

Usage: python3 pipeline/entities.py E/CN.4/SR.60 [--engine layer]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

from rapidfuzz import fuzz, process

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sessions import body_from_symbol, sessions_for  # noqa: E402
from common import safe_name  # noqa: E402
from vote import majority, speaker_votes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TRUST_PRINTED = os.environ.get("TRAVAUX_TRUST_PRINTED_NAMES") == "1"  # (off in the pipeline as it stands: see resolve())
_KNOWN = None


def known_names():
    """pipeline/name_guard.py's names known per delegation, from the database as it stands (loaded once)."""
    global _KNOWN
    if _KNOWN is None:
        from name_guard import Guard
        _KNOWN = Guard()
    return _KNOWN


RAW = ROOT / "data" / "raw"
SEG = ROOT / "data" / "segments"
GAZ = ROOT / "data" / "gazetteer" / "states.csv"
DELEGATES = ROOT / "data" / "gazetteer" / "delegates.csv"          # checked by a person
DELEGATES_DRAFT = ROOT / "data" / "gazetteer" / "delegates_draft.csv"  # written by --draft

TITLE_RE = re.compile(r"^(M[rlI1i][s']?|Mrs|Miss|Miser|Mme|Mlle|Dr|Col|Colonel|Gen|General|Sir|Lord|Lady|Begum|Father|Prof|Professor|Judge)[.,;']*$")
# Section labels in the left column. Matched on their first letters only, because OCR
# damages them ("Speciallzed Agenclee", "Non-Govemntal"); 1947 records use "Present:".
SECTIONS = [
    ("vice-chairman", r"^Vice"), ("chairman", r"^Chair"), ("rapporteur", r"^Rapp"),
    ("member", r"^Memb"), ("member", r"^Pres"), ("also present", r"^Also"),
    ("specialized agency", r"^(?:Representatives?\s+of\s+)?Spec"),
    ("observer", r"^Obs"), ("ngo", r"^(?:Consult|Non-?\s?Gov)"), ("secretariat", r"^Secr"),
]
PARTICLES = {"de", "da", "del", "la", "le", "van", "von", "y"}


def load_gazetteer() -> dict[str, str]:
    """name or variant (lower case) -> canonical state name"""
    out = {}
    with GAZ.open() as f:
        for row in csv.DictReader(f):
            out[row["canonical"].lower()] = row["canonical"]
            for v in filter(None, row["variants"].split("|")):
                out[v.lower()] = row["canonical"]
    return out


def rows_of(page) -> list[list[tuple]]:
    """Words grouped into printed rows (y within 4 pt), each row sorted left to right."""
    rows: list[list[tuple]] = []
    for w in sorted(page.get_text("words"), key=lambda w: (w[1], w[0])):
        if rows and abs(rows[-1][0][1] - w[1]) < 4:
            rows[-1].append(w)
        else:
            rows.append([w])
    return [sorted(r, key=lambda w: w[0]) for r in rows]


def affiliation_column(rows: list[list[tuple]]) -> float | None:
    """x where the delegation column starts on this page: the median start of the text
    after the widest gap in entry rows. Found per page, because one row's gap can be
    narrow ("Franklin D. ROOSEVELT United States of America")."""
    starts = []
    for words in rows:
        if len(words) < 3 or not TITLE_RE.match(words[0][4]) and not any(TITLE_RE.match(w[4]) for w in words[:2]):
            continue
        gap, i = max((words[i + 1][0] - words[i][2], i) for i in range(len(words) - 1))
        if gap > 25:
            starts.append(words[i + 1][0])
    if not starts:
        return None
    starts.sort()
    return starts[len(starts) // 2]


def roster(symbol: str, max_pages: int = 3) -> list[dict]:
    """Attendance list entries: {section, title, name, affiliation, page}."""
    import fitz
    path = RAW / f"{safe_name(symbol)}-EN.pdf"
    if not path.exists():  # a machine-translated French-only document: no English scan, no attendance list to read
        return []
    pdf = fitz.open(path)
    entries: list[dict] = []
    section = None
    started = False
    for pno in range(min(max_pages, pdf.page_count)):
        rows = rows_of(pdf[pno])
        col = affiliation_column(rows)
        for row in rows:
            text = " ".join(w[4] for w in row)
            if started and re.search(r"Any corrections of this record", text):
                break  # the rest of the page is the corrections notice
            if started and re.search(r"^CONTINUATION|^(?:Article|ARTICLE)\s+\d", text):
                return entries
            words = list(row)
            # a section label in the left column (x < 160) may share the row with the first entry
            if words[0][0] < 160 and not TITLE_RE.match(words[0][4]):
                label = " ".join(w[4] for w in words if w[0] < 180)
                for key, pat in SECTIONS:
                    if re.match(pat, label, re.I):
                        section, started = key, True
                        break
                words = [w for w in words if w[0] >= 180]
                if not words:
                    continue
            if not started:
                continue
            split = (col - 8) if col else 10_000
            name_words = [w for w in words if w[0] < split]
            aff_words = [w for w in words if w[0] >= split]
            if name_words and (TITLE_RE.match(name_words[0][4])
                               or (name_words[0][4].isalpha() and name_words[0][4].isupper() and len(name_words[0][4]) > 2)):
                title = name_words[0][4] if TITLE_RE.match(name_words[0][4]) else None
                name = " ".join(w[4] for w in name_words[1 if title else 0:])
                aff = " ".join(w[4] for w in aff_words).strip()
                entries.append({"section": section, "title": title, "name": name,
                                "affiliation": aff.strip("()~ "), "page": pno + 1})
            elif entries and aff_words and not name_words and (
                    aff_words[0][0] > (col or 0) + 3
                    or re.search(r"(-|\b(?:of|the|and|for|Soviet|Socialist))$", entries[-1]["affiliation"])):
                # continuation of a wrapped delegation name: printed indented by ~6 pt.
                # An unindented line is the delegation of a row whose name OCR lost, and
                # must not be glued to the previous delegate ("MALIK | Lebanon Australia").
                prev = entries[-1]["affiliation"]
                sep = "" if prev.endswith("-") else " "
                entries[-1]["affiliation"] = (prev.rstrip("-") + sep + " ".join(w[4] for w in aff_words)).strip("()~ ")
    return entries


def surname(name: str) -> str:
    """The surname as printed.

    1948 lists capitalise it: 'Franklin D. ROOSEVELT' -> 'ROOSEVELT', 'de QUIJANO' -> 'de QUIJANO'.
    1947 lists don't: 'Prof. René Cassin' -> 'Cassin', 'Dr. P. C. Chang' -> 'Chang'
    (initials dropped; the last word is taken, so 'H. Santa Cruz' -> 'Cruz', which the
    token-based name match still pairs with 'SANTA CRUZ').
    """
    parts = [p for p in name.split() if not re.fullmatch(r"(?:[A-Z0-9]\.?){1,3},?", p)]
    if not parts:
        return name
    caps = [i for i, p in enumerate(parts) if p.isalpha() and p.isupper() and len(p) > 1]
    if not caps:
        return parts[-1]
    i = caps[0]
    while i > 0 and parts[i - 1].lower() in PARTICLES:
        i -= 1
    return " ".join(parts[i:])


def resolve_delegation(raw: str | None, gaz: dict[str, str], rost: list[dict]) -> tuple[str | None, str, float]:
    """(canonical delegation, method, score) for a parenthesised country/organisation."""
    if not raw:
        return None, "none", 0.0
    raw_c = " ".join(raw.replace("ı", "i").split())  # (the OCR's dotless i: "Malı", round 92)
    # Whole-string similarity: partial scorers (WRatio) let "American Federation of Labor"
    # match "United States of America".
    hits = process.extract(raw_c.lower(), list(gaz), scorer=fuzz.ratio, limit=5)
    hit = hits[0] if hits else None
    if hit and hit[1] >= 85:
        return gaz[hit[0]], "gazetteer", hit[1]
    # a garbled name ("united ~in~dom") that still clearly points at one state
    rivals = [h for h in hits[1:] if gaz[h[0]] != gaz[hit[0]]] if hit else []
    if hit and hit[1] >= 72 and len(raw_c) <= 40 and (not rivals or hit[1] - rivals[0][1] >= 12):
        return gaz[hit[0]], "gazetteer_margin", hit[1]
    affs = [e["affiliation"] for e in rost if e.get("affiliation")]
    if affs:
        hit2 = process.extractOne(raw_c, affs, scorer=fuzz.ratio)
        if hit2 and hit2[1] >= 80:
            # an affiliation that is itself a state (garbled) maps through the gazetteer
            g = process.extractOne(hit2[0].lower(), list(gaz), scorer=fuzz.ratio)
            return (gaz[g[0]] if g and g[1] >= 85 else hit2[0]), "roster", hit2[1]
    return raw_c, "unresolved", hit[1] if hit else 0.0


# A name as the speech openings print it: capitals in the mimeographed records ("WU",
# "de QUIJANO"), often title case in the printed Official Records ("Contoumas", "Santa Cruz").
TEXT_NAME_RE = re.compile(r"^(?:(?:de|da|del|la|le|van|von|y)\s)?[A-ZÀ-Ý][A-Za-zÀ-ÿ'\-]{1,}"
                          r"(?:\s(?:(?:de|da|del|y|DE\sLA|DE|DA|DEL|Y)\s)?[A-ZÀ-Ý][A-Za-zÀ-ÿ'\-]{1,}){0,2}$")  # ("ESTRADA DE LA HOZ", A/C.3/SR.495)
CLEAN_NAME_RE = re.compile(r"^(?:(?:de|da|del|la|le|van|von|y)\s)?[A-Z][A-Za-z'\-]+(?:\s[A-Z][A-Za-z'\-]+)?$")


def meeting_roster(symbol: str, gaz: dict[str, str]) -> list[dict]:
    """Attendance list of one meeting, each entry with its resolved delegation and surname."""
    rost = roster(symbol)
    for e in rost:
        d, _, _ = resolve_delegation(e["affiliation"], gaz, [])
        e["delegation"] = d if d and d in gaz.values() else (e["affiliation"] or None)
        e["surname"] = surname(e["name"])
        # trustworthy entries: a name that reads as a name, and a delegation that is a known
        # state or at least a plausible organisation name
        e["clean"] = bool(CLEAN_NAME_RE.match(e["surname"])) and bool(e["delegation"]) and (
            e["delegation"] in gaz.values() or len(e["delegation"]) >= 6)
        e["state"] = e["delegation"] in gaz.values()
    return rost


def bare(name: str) -> str:
    """Surname without particles, upper case: 'de QUIJANO' -> 'QUIJANO'."""
    return " ".join(w for w in name.split() if w.lower() not in PARTICLES).upper()


def same_delegation(a: str | None, b: str | None) -> bool:
    """States compare exactly (already canonical); organisation names, OCR'd differently
    in each meeting's list, compare fuzzily."""
    if not a or not b:
        return False
    return a == b or fuzz.ratio(a.lower(), b.lower()) >= 80


def session_roster(rosters: list[list[dict]]) -> list[dict]:
    """Clean entries pooled across the meetings of one session, one per delegate.

    Delegations barely change within a session, so a meeting whose own list is garbled
    (E/CN.4/SR.61: "BA.YLOV" for PAVLOV) borrows the delegates from its neighbours.
    """
    pooled: list[dict] = []
    for rost in rosters:
        for e in rost:
            if not e["clean"]:
                continue
            # the same delegate under an OCR variant ("FONTAINA" / "FONTAIHA") is one person
            twin = next((p for p in pooled if same_delegation(p["delegation"], e["delegation"])
                         and fuzz.ratio(bare(p["surname"]), bare(e["surname"])) >= 75), None)
            if twin:
                twin["spellings"][e["surname"]] = twin["spellings"].get(e["surname"], 0) + 1
            else:
                pooled.append({**e, "spellings": {e["surname"]: 1}})
    for p in pooled:  # the most frequent spelling wins
        p["surname"] = max(p["spellings"], key=p["spellings"].get)
        p["seen"] = sum(p["spellings"].values())
    # A spelling seen once is usually a garbled copy of a frequent one ("KLEXDVKIN" of
    # KLEKOVKEN scores 67); two real delegates of one delegation score far lower
    # (STEYAERT / LEBEAU: 29).
    for p in sorted(pooled, key=lambda p: p["seen"]):
        if p["seen"] != 1 or p.get("merged"):
            continue
        host = max((q for q in pooled if q is not p and not q.get("merged") and q["seen"] >= 2
                    and q["delegation"] == p["delegation"]
                    and fuzz.ratio(bare(q["surname"]), bare(p["surname"])) >= 60),
                   key=lambda q: q["seen"], default=None)
        if host:
            for sp, n in p["spellings"].items():
                host["spellings"][sp] = host["spellings"].get(sp, 0) + n
            host["seen"] += p["seen"]
            p["merged"] = True
    return [p for p in pooled if not p.get("merged")]


def joint_pick(votes: list[dict], pooled: list[dict]) -> tuple[dict | None, float, float]:
    """The attendee that best fits all readings of a speech opening, name and country together.

    Scored per reading as 0.6 x name similarity + 0.4 x delegation similarity, averaged.
    Deciding the delegation first can go wrong: four engines read "CHANG (Chine)", and
    "Chine" is as close to Chile as to China; the name settles it.
    Returns (best, its score, margin over the runner-up).
    """
    if not votes or not pooled:
        return None, 0.0, 0.0
    scored = []
    for cand in pooled:
        total = 0.0
        names = [cand["surname"], *cand.get("variants", [])]
        for v in votes:
            name = max(fuzz.ratio(bare(v["name"].strip("-")), bare(n)) for n in names)
            deleg = fuzz.ratio(v["country"].lower(), (cand["delegation"] or "").lower())
            total += 0.6 * name + 0.4 * deleg
        scored.append((total / len(votes), cand))
    scored.sort(key=lambda t: -t[0])
    best, runner = scored[0], (scored[1][0] if len(scored) > 1 else 0.0)
    return best[1], best[0], best[0] - runner


def printed_stranger(symbol: str, votes: list[dict], pick: dict) -> bool:
    """The General Assembly's records are printed and read cleanly: when three engines or more
    agree on a name in capitals that is clearly not the attendee picked ("Mr. SINHA (India)"
    against SAKSENA, "Mr. HOY (Haiti)" against ROY), that is the name printed and the list
    lacks the delegate. (In typed records the engines can agree on garbage: "AZECUL".)"""
    if not symbol.startswith("A/"):
        return False
    names = [bare(v["name"].strip("-")) for v in votes if v["name"].strip("-").isupper() and TEXT_NAME_RE.match(v["name"].strip("-"))]
    top = max(set(names), key=names.count, default=None)
    if top is None or names.count(top) < 3:
        return False
    theirs = set(re.split(r"[\s-]+", top))
    for n in (pick["surname"], *pick.get("variants", [])):
        mine = set(re.split(r"[\s-]+", bare(n)))
        # one name inside the other is the same person: "SEKANINOVA" and "SEKANINOVA-CAKRTOVA"
        if mine <= theirs or theirs <= mine or fuzz.ratio(top, bare(n)) >= 75:
            return False
    return True


def clean_reading(r: str, readings: list[str]) -> bool:
    """A reading that is probably right: a name in capitals, or one another engine confirms."""
    if not TEXT_NAME_RE.match(r):
        return False
    return r.isupper() or sum(1 for o in readings if fuzz.ratio(bare(o), bare(r)) >= 85) >= 2


def compatible(readings: list[str], person: dict) -> bool:
    """Could the readings be this person's name? A clean reading must be close (>= 60:
    "RODRIGUEZ FABREGAT" is not JIMÉNEZ DE ARÉCHAGA, "NOSEK" not HOFFMEISTER); if every
    reading is garbled ("Duuco", "Duttico", "Dico" for DIHIGO), a faint likeness will do."""
    names = [person["surname"], *person.get("variants", [])]
    rs = [r for r in readings if r]
    best = max((fuzz.ratio(bare(r), bare(n)) for r in rs for n in names), default=0)
    if any(clean_reading(r, rs) for r in rs):
        return best >= 60
    return best >= 30


def like_text_name(readings: list[str], person: dict) -> bool:
    """A name read in another speech (no list of those present, as in the printed records) is the one delegate only if a
    reading is at least half like it: "CUANC" is CHANG (60), "Santa Cnuz" is not FERNANDEZ (42), nor "Dayres" BEVIN (round 86)."""
    return max((fuzz.ratio(bare(r), bare(person["surname"])) for r in readings if r), default=0) >= 50


def best_reading(readings: list[str]) -> str | None:
    """The cleanest of several garbled readings of one name: the largest group of similar
    readings, then a reading that looks like a printed name (capitals), then the longest."""
    rs = [r for r in readings if r]
    if not rs:
        return None
    def group(r: str) -> int:
        return sum(1 for o in rs if fuzz.ratio(bare(r), bare(o)) >= 70)
    return max(rs, key=lambda r: (group(r), bool(TEXT_NAME_RE.match(r)) and r.isupper(), len(r)))


def corroborated_stranger(raw: str, votes: int, known: dict | None) -> bool:
    """A clean name that two or more engines agree on and that is clearly not the listed
    delegate ("WU (China)" when only CHANG is listed). The one-delegate fallback must not
    overrule it: the list is incomplete, not the reading wrong."""
    if not TEXT_NAME_RE.match(raw) or votes < 2:
        return False
    return known is None or fuzz.ratio(bare(raw), bare(known["surname"])) < 50


# Speakers who are not delegates: organisations with consultative status, the Secretariat,
# officers of other bodies
ORG_OR_ROLE_RE = re.compile(r"\b(?:Organi[sz]ation|Federation|Congress|Council|Union|Association|League|Alliance|Office|"
                            r"Bureau|Chamber|Institute|Movement|Society|Secretar(?:y|iat)|Rapporteur|Department|Division|"
                            r"Director|Assistant|Representative of the Secretary|Commission on the Status of Women|"
                            r"Labour Organi[sz]ation|UNESCO|ILO|WHO|FAO|AF of L|CIO|WFTU|ICFTU)\b", re.I)
ORG_ALIASES = {"AF of L": "American Federation of Labor", "A.F. of L.": "American Federation of Labor",
               "A F of L": "American Federation of Labor"}


def resolve(symbol: str, engine: str, rost: list[dict], pooled: list[dict], gaz: dict[str, str],
            use_votes: bool = True) -> dict:
    """Delegation and speaker for every speech, against the session's pooled attendance list.

    The pooled list already holds this meeting's clean entries, under the spelling most
    frequent across the session.
    """
    seg_path = SEG / f"{safe_name(symbol)}.{engine}.json"
    segs = json.loads(seg_path.read_text())
    stats = {"speeches": 0, "delegation_resolved": 0, "speaker_resolved": 0}
    for s in segs:
        if s["kind"] != "speech":
            continue
        for stale in ("review", "jev", "speaker", "delegation"):  # from an earlier run
            s.pop(stale, None)
        stats["speeches"] += 1
        # The same opening as read by every engine; the majority decides.
        votes = speaker_votes(symbol, s) if use_votes else []
        s["votes"] = [f"{v['name']} ({v['country']}) [{v['engine']}]" for v in votes]
        per_vote = [resolve_delegation(v["country"], gaz, rost + pooled) for v in votes]
        top, n = majority([r[0] for r in per_vote if r[1] != "unresolved"])
        if top:
            deleg, dmethod, dscore = top, f"vote {n}/{len(votes)}", round(100 * n / len(votes), 1)
        else:
            deleg, dmethod, dscore = resolve_delegation(s.get("country_raw"), gaz, rost + pooled)
        # With the vision reader's text (TRAVAUX_TRUST_PRINTED_NAMES=1, pipeline/preview_mixed.py), and only on a page the vision
        # reader read (the copy marks it, vote/page-NNN.vision): the name its text prints is taken when it is a known person of the
        # delegation, in the database's spelling ("Charles MALIK" is MALIK, "HANSA MEHTA" is MEHTA), or the one delegate of the
        # session close to it (a typist's "SORENSON", "MOROSOV": the user's decision of 20 Oct 2026, the text keeps the page's
        # spelling). Nothing else changes: three rounds of wider rules each lost names elsewhere (results_preview_mixed.md).
        if TRUST_PRINTED and deleg and dmethod not in ("unresolved", "none") and \
                (SEG.parent / "ocr" / safe_name(symbol) / "vote" / f"page-{s['page_start']:03d}.vision").exists():
            printed = (s.get("speaker_raw") or "").strip("-")
            known = (known_names().canonical(printed, deleg) or known_names().session_match(symbol, printed, deleg)) if printed else None
            if known:
                entry = next((e for e in pooled if same_delegation(e["delegation"], deleg) and bare(e["surname"]) == bare(known)), None)
                if entry is None:
                    entry = {"surname": known, "delegation": deleg, "clean": True, "spellings": {known: 0}, "seen": 0, "from_text": True}
                    pooled.append(entry)
                s["delegation"], s["delegation_method"], s["delegation_score"] = deleg, dmethod, round(dscore, 1)
                s["speaker"], s["speaker_method"], s["speaker_score"] = entry["surname"], "printed_known", 100.0
                s["_person"] = id(entry)
                stats["delegation_resolved"] += 1
                stats["speaker_resolved"] += 1
                continue
        # The name is voted among the readings that agree on the delegation: an engine can pair
        # this speech with a neighbour's opening ("KURAL (Turkey)" for "CAÑAS (Costa Rica)").
        agreeing = [v for v, r in zip(votes, per_vote) if top and r[0] == top] or votes
        name, name_votes = majority([v["name"].strip("-") for v in agreeing], key=bare)
        readings = [v["name"].strip("-") for v in agreeing] or [(s.get("speaker_raw") or "").strip("-")]
        s["speaker_voted"] = name
        pick, jscore, margin = joint_pick(votes, [e for e in pooled if sane_option(e)])
        # (and in the General Assembly's printed records, read cleanly, the name must fit too: two engines read "BRANA (Cuba)",
        # and the delegation alone made it CORTINA; round 86. In typed records the engines agree on garbage, "MEM'EA" for MEHTA)
        if pick is not None and jscore >= 70 and margin >= 8 and not printed_stranger(symbol, votes, pick) \
                and (not symbol.startswith("A/") or compatible([v["name"].strip("-") for v in votes], pick)):
            s["delegation"], s["delegation_method"], s["delegation_score"] = pick["delegation"], "vote_joint", round(jscore, 1)
            s["speaker"], s["speaker_method"], s["speaker_score"] = pick["surname"], "vote_joint", round(jscore, 1)
            s["_person"] = id(pick)
            stats["delegation_resolved"] += 1
            stats["speaker_resolved"] += 1
            continue
        same = [e for e in pooled if same_delegation(e["delegation"], deleg)] if dmethod != "unresolved" else []
        pool = same or pooled
        raw = (name or s.get("speaker_raw") or "").strip("-")
        speaker, smethod, sscore = None, "unresolved", 0.0
        if raw:
            # printed records have no attendance list, so the pool can be empty: then only
            # the name as printed (below) is available
            names = [e["surname"].upper() for e in pool]
            hit = process.extractOne(raw.upper(), names, scorer=fuzz.ratio) if names else None
            tok = process.extractOne(raw.upper(), names, scorer=fuzz.token_set_ratio) if same else None
            stranger = len(same) == 1 and printed_stranger(symbol, votes, same[0])
            # (an office printed for the delegation is not a state's delegate: "Mr. DAS (Secretary of the Committee)" is not DAES of
            # Greece; round 99)
            office = dmethod in ("unresolved", "none") and ORG_OR_ROLE_RE.search(s.get("country_raw") or "") \
                and not re.search(r"Rapporteur|Chairman|President", s.get("country_raw") or "")  # (a delegate in an office: "Mr. NISOT (Rapporteur)")
            if hit and office and not ORG_OR_ROLE_RE.search(pool[hit[2]].get("delegation") or ""):
                hit = None
            if hit and hit[1] >= 75:
                speaker, smethod, sscore = pool[hit[2]], "roster_match", hit[1]
            elif tok and tok[1] >= 90:
                # compound surnames: "SANTA CRUZ" in the text, "Cruz" in the list
                speaker, smethod, sscore = pool[tok[2]], "roster_token", tok[1]
            elif len(same) == 1 and not stranger and not corroborated_stranger(raw, name_votes, same[0]) \
                    and compatible(readings, same[0]) and not (same[0].get("from_text") and not like_text_name(readings, same[0])):
                # one delegate known for this delegation, and the garbled name could be theirs
                speaker, smethod, sscore = same[0], "sole_delegate", hit[1] if hit else 0.0
            elif dmethod != "unresolved" and (TEXT_NAME_RE.match(raw) or TEXT_NAME_RE.match(best_reading(readings) or "")) and (
                    not same or stranger or corroborated_stranger(raw, name_votes, same[0] if len(same) == 1 else None)
                    or (len(same) == 1 and not compatible(readings, same[0])) or len(same) > 1
                    or len(same) == 1 and same[0].get("from_text") and not like_text_name(readings, same[0])):
                raw = raw if TEXT_NAME_RE.match(raw) and name_votes >= 2 else (best_reading(readings) or raw)
                # nobody in the list fits ("Col. William R. EoQ8on"; or the list lacks an
                # alternate, "AZKOUL (Lebanon)" when only MALIK is listed), but the text prints
                # a clean name: take it, at lower confidence, and flag it for the list
                if any(p.get("authority") for p in pooled):  # only a checked list can lack someone
                    s["review"] = f"{raw} ({deleg}) is not in the delegate list for this session"
                # the entry itself goes into the pool: speeches point to people by id(), so the
                # object must stay alive (a freed dict's id can be reused by another person)
                # ("from_text": a name read in a speech, not a list of those present: the one-delegate fallback above is for
                # lists only, or "Mr. Santa Cnuz (Chile)" became the FERNANDEZ another speech printed; round 86)
                speaker = {"surname": raw, "delegation": deleg, "clean": True, "spellings": {raw: 0}, "seen": 0, "from_text": True}
                pooled.append(speaker)
                smethod, sscore = "text_name", 0.0
        org = s.get("country_raw") or ""
        if speaker is None and raw and TEXT_NAME_RE.match(raw) and dmethod in ("unresolved", "none") and ORG_OR_ROLE_RE.search(org):
            # not a delegation but an organisation or an office: "Miss SENDER (American Federation
            # of Labor)", "Mr. HESSEL (Secretary of the Committee)". Nobody's attendance list
            # has them, so the name as printed is taken, with the organisation as printed
            deleg, dmethod, dscore = ORG_ALIASES.get(org.strip(), " ".join(org.split()).strip(" .,")), "organization", 0.0
            speaker = {"surname": raw, "delegation": deleg, "clean": True, "spellings": {raw: 0}, "seen": 0, "from_text": True}
            pooled.append(speaker)
            smethod, sscore = "text_org", 0.0
        if speaker and dmethod in ("unresolved", "none") and smethod == "roster_match" and sscore >= 80:
            # "CHABG (CMna)": an unreadable delegation, but an unmistakable delegate; or no
            # delegation printed at all ("Mr. WILSON suggested ..." in the typed records)
            deleg, dmethod, dscore = speaker["delegation"], "from_speaker", sscore
        s["delegation"], s["delegation_method"], s["delegation_score"] = deleg, dmethod, round(dscore, 1)
        s["speaker"] = speaker["surname"] if speaker else None
        s["_person"] = id(speaker) if speaker else None
        s["speaker_method"], s["speaker_score"] = smethod, round(sscore, 1)
        stats["delegation_resolved"] += dmethod not in ("unresolved", "none")
        stats["speaker_resolved"] += speaker is not None
    return segs, {"roster": len(rost), "clean": sum(e["clean"] for e in rost), **stats}


def canonical_spellings(all_segs: list[list[dict]], pooled: list[dict]) -> None:
    """Name each person by the spelling seen most often, in the lists and in the text.

    A single meeting's list can be worse than the speeches ("KOHTA" in the list,
    "MEHTA" twice in the text), so every OCR'd occurrence gets a vote.
    """
    by_id = {id(p): p for p in pooled}
    for segs in all_segs:
        for s in segs:
            p = by_id.get(s.get("_person"))
            said = s.get("speaker_voted") or s.get("speaker_raw")
            if p is not None and said:
                # speech openings print surnames only ("Mr. Santa Cruz (Chile)"): take the
                # name whole; surname() is for attendance lists, which add first names
                raw = said.strip("-")
                if TEXT_NAME_RE.match(raw):
                    p["spellings"][raw] = p["spellings"].get(raw, 0) + 1
    for p in pooled:
        votes: dict[str, int] = {}
        for sp, n in p["spellings"].items():
            key = next((k for k in votes if bare(k) == bare(sp)), sp)
            votes[key] = votes.get(key, 0) + n
        p["surname"] = max(votes, key=lambda k: (votes[k], k.isupper()))
    for segs in all_segs:
        for s in segs:
            p = by_id.get(s.get("_person"))
            if p is not None:
                s["speaker"] = p["surname"]


JEV_INSTRUCTIONS = (
    "The state holds the attendance list of a UN meeting and the opening words of speech {key} from its "
    "summary record. The opening names the speaker as 'Mr. SURNAME (Delegation)', but the text is OCR of a "
    "typewritten copy, so names and delegations are often garbled (for example 'VHSOB (United Kingdom)' "
    "for WILSON, 'CEAUG- (Chim)' for CHANG of China). Which entry of the attendance list is the speaker "
    "of speech {key}?"
)
def sane_option(p: dict) -> bool:
    """An attendee fit to offer Jev: a name-like surname and a delegation without OCR debris."""
    d = p.get("delegation") or ""
    letters = sum(c.isalpha() or c in " '-,.()" for c in d)
    return (bool(CLEAN_NAME_RE.match(p["surname"]) or TEXT_NAME_RE.match(p["surname"]))
            and 2 < len(d) <= 70 and letters / len(d) >= 0.97
            and not re.search(r"\d|/|\bM[rR]s?\.|\bMiss\b", d))


JEV_ACCEPT = 0.9  # 125/125 correct at p >= 0.9 on CHR 3rd session (eval/jev_speakers.py)
WEAK = ("unresolved", "sole_delegate", "text_name")


def jev_fallback(all_segs: list[list[dict]], pooled: list[dict], batch: int = 25) -> dict:
    """Ask Jev about the speeches the rules could not resolve, or resolved weakly.

    Unresolved: Jev's pick is accepted at p >= JEV_ACCEPT (method "jev"), else stored
    as a suggestion for review. Weak rule matches: Jev's pick is only a check; a
    disagreement is flagged for review and nothing is overwritten.
    """
    import jev
    # Jev is only as good as its options: a garbled list row that fuses two attendees
    # ("SENDER (Ar2erican Federation of Labar I /MY. WILSOIi)") drew a confident wrong pick.
    labels = {f"{p['surname']} ({p['delegation']})": p for p in pooled if sane_option(p)}
    options = {lab: "listed attendee" for lab in labels}
    todo = [s for segs in all_segs for s in segs if s["kind"] == "speech" and s["speaker_method"] in WEAK]
    stats = {"asked": len(todo), "accepted": 0, "suggested": 0, "confirmed": 0, "disputed": 0}
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        state = {"attendance_list": list(labels),
                 "speeches": {f"S{j}": s["text"][:160] for j, s in enumerate(chunk)}}
        qs = {f"S{j}": jev.choice(JEV_INSTRUCTIONS.format(key=f"S{j}"), options) for j in range(len(chunk))}
        answers = jev.ask(state, qs, task="speaker")
        for j, s in enumerate(chunk):
            a = answers.get(f"S{j}") or {}
            pick = a.get("choice")
            prob = (a.get("probabilities") or {}).get(pick) or 0.0
            if pick not in labels:
                continue
            person = labels[pick]
            s["jev"] = {"pick": pick, "p": round(prob, 3)}
            if s["speaker_method"] == "unresolved":
                if prob >= JEV_ACCEPT:
                    s["speaker"], s["speaker_method"], s["speaker_score"] = person["surname"], "jev", round(prob * 100, 1)
                    if s["delegation_method"] == "unresolved":
                        s["delegation"], s["delegation_method"] = person["delegation"], "jev"
                    s["_person"] = id(person)
                    stats["accepted"] += 1
                else:
                    s["review"] = f"Jev suggests {pick} (p={prob:.2f})"
                    stats["suggested"] += 1
            elif s["speaker"] and bare(s["speaker"]) == bare(person["surname"]) and s["delegation"] == person["delegation"]:
                stats["confirmed"] += 1
            elif prob >= JEV_ACCEPT:
                s["review"] = f"rules say {s['speaker']} ({s['delegation']}), Jev says {pick} (p={prob:.2f})"
                stats["disputed"] += 1
    return stats


def save(symbol: str, engine: str, segs: list[dict], rost: list[dict]) -> None:
    seg_path = SEG / f"{safe_name(symbol)}.{engine}.json"
    seg_path.write_text(json.dumps(segs, ensure_ascii=False, indent=1), encoding="utf-8")
    (SEG / f"{safe_name(symbol)}.roster.json").write_text(json.dumps(rost, ensure_ascii=False, indent=1),
                                                            encoding="utf-8")


def authority(session: str) -> list[dict]:
    """Checked delegate list for a session (data/gazetteer/delegates.csv), as pool entries.

    Where a session has one, it replaces the pooled attendance lists: its spellings are
    the canonical ones, and its variants column lets garbled readings match.
    """
    if not DELEGATES.exists():
        return []
    out = []
    with DELEGATES.open() as f:
        for row in csv.DictReader(f):
            if row["session"] == session:
                out.append({"surname": row["surname"], "delegation": row["delegation"], "clean": True,
                            "state": row["delegation"] in load_gazetteer().values(),
                            "spellings": {row["surname"]: 1000}, "seen": 1000, "authority": True,
                            "variants": [v for v in row.get("variants", "").split("|") if v]})
    return out


def write_draft(session: str, pooled: list[dict], all_segs: list[list[dict]]) -> int:
    """Append this session's delegates to delegates_draft.csv for a person to check:
    the voted spelling, every spelling seen with its count, and the meetings it came from."""
    by_id = {id(p): p for p in pooled}
    speeches: dict[int, int] = {}
    for segs in all_segs:
        for x in segs:
            if x.get("_person") in by_id:
                speeches[x["_person"]] = speeches.get(x["_person"], 0) + 1
    new = not DELEGATES_DRAFT.exists()
    with DELEGATES_DRAFT.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["session", "delegation", "surname", "spellings_seen", "speeches", "status"])
        for p in sorted(pooled, key=lambda p: (p["delegation"] or "", p["surname"])):
            seen = "|".join(f"{k}:{v}" for k, v in sorted(p["spellings"].items(), key=lambda kv: -kv[1]))
            w.writerow([session, p["delegation"], p["surname"], seen, speeches.get(id(p), 0), "draft"])
    return len(pooled)


# Records outside the UN Library's UDHR guide (the Covenant period) until the Covenant
# manifests carry their own session data.
SESSION_OVERRIDES = {
    "E/CN.4/SR.164": "Commission on Human Rights / 6th session (1950)",
    "E/RES/84(V)": "Economic and Social Council / 5th session (1947)",
    "E/CN.4/80": "Sub-Commission on Freedom of Information and of the Press / 2nd session (1948)",
    "E/CN.4/83": "Commission on Human Rights / 3rd session (1948)",
    "E/CN.4/89": "CHR Drafting Committee / 2nd session (1948)",
}


def masthead_date_of(symbol: str, engine: str = "vote") -> str | None:
    """The meeting date: from the masthead, or when no masthead was split off (1949 layout),
    from the opening text."""
    from segment import masthead_date
    path = ROOT / "data" / "segments" / f"{safe_name(symbol)}.{engine}.json"
    if not path.exists():
        return None
    segs = json.loads(path.read_text())
    m = next((s for s in segs if s["kind"] == "masthead"), None)
    if m and m.get("meeting_date"):
        return m["meeting_date"]
    return masthead_date(" ".join(s["text"] for s in segs[:3])[:2500])


def sessions_of(symbols: list[str]) -> dict[str, list[str]]:
    """Group symbols by body and session, as the UN Library guide files them."""
    guide = {d["symbol"]: d for d in json.loads((ROOT / "data" / "manifest" / "udhr.json").read_text())["documents"]}
    groups: dict[str, list[str]] = {}
    # outside the guide: body from the symbol, session from the meeting date (or the meetings
    # numbered around it), so the record pools its attendance list with the rest of its session
    outside = {sym: (body_from_symbol(sym), masthead_date_of(sym)) for sym in symbols
               if sym not in guide and sym not in SESSION_OVERRIDES}
    inferred = sessions_for(outside)
    for sym in symbols:
        m = (guide.get(sym) or {}).get("mentions") or [{}]
        if sym in SESSION_OVERRIDES:
            key = SESSION_OVERRIDES[sym]
        elif sym in guide:
            key = f"{m[0].get('body')} / {m[0].get('session')}"
        else:
            body, session = outside[sym][0], inferred.get(sym)
            key = f"{body} / {session}" if body and session else f"(not in guide) {sym}"
        groups.setdefault(key, []).append(sym)
    return groups


def run(symbols: list[str], engine: str, jev: bool = False, votes: bool = True, draft: bool = False,
        quiet: bool = False) -> dict:
    """Resolve speakers for meeting records, session by session. Returns totals."""
    gaz = load_gazetteer()
    totals = {"records": 0, "speeches": 0, "speaker_resolved": 0}
    for session, syms in sessions_of(symbols).items():
        rosters = {sym: meeting_roster(sym, gaz) for sym in syms}
        checked = authority(session)
        pooled = checked or session_roster(list(rosters.values()))
        if not quiet:
            print(f"{session}: {len(pooled)} delegates {'from delegates.csv' if checked else 'pooled'}", file=sys.stderr)
        results = {sym: resolve(sym, engine, rosters[sym], pooled, gaz, use_votes=votes) for sym in syms}
        if jev:
            print(f"  Jev: {jev_fallback([segs for segs, _ in results.values()], pooled)}", file=sys.stderr)
            for segs, stats in results.values():
                stats["speaker_resolved"] = sum(1 for x in segs if x["kind"] == "speech" and x.get("speaker"))
        if not checked:
            canonical_spellings([segs for segs, _ in results.values()], pooled)
        if draft and not checked:
            write_draft(session, pooled, [segs for segs, _ in results.values()])
        for segs, _ in results.values():
            for x in segs:
                x.pop("_person", None)
        for sym, (segs, stats) in results.items():
            save(sym, engine, segs, rosters[sym])
            totals["records"] += 1
            totals["speeches"] += stats["speeches"]
            totals["speaker_resolved"] += stats["speaker_resolved"]
            if not quiet:
                print(f"  {sym}: {stats}", file=sys.stderr)
    return totals


# compilations of many governments' comments: one state's name in the header does not make it the author of the
# paragraphs that follow (E/CN.4/365 gave "Iran" to 99 paragraphs and "France" to 85 of other states' comments); their
# paragraphs carry no delegation until each government's section is read by hand
COMPILATIONS = {"E/CN.4/365", "E/CN.4/353/Add.1"}


def resolve_authors(symbol: str, engine: str, gaz: dict[str, str]) -> int:
    """Documents: the submitting state or organisation of each paragraph, as a delegation."""
    if symbol in COMPILATIONS:
        return 0
    seg_path = SEG / f"{safe_name(symbol)}.{engine}.json"
    segs = json.loads(seg_path.read_text())
    n = 0
    for s in segs:
        if s.get("author_raw"):
            deleg, method, _ = resolve_delegation(s["author_raw"], gaz, [])
            s["delegation"] = deleg if method != "unresolved" else s["author_raw"]
            s["delegation_method"] = f"author/{method}"
            n += 1
    seg_path.write_text(json.dumps(segs, ensure_ascii=False, indent=1), encoding="utf-8")
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--engine", default="layer")
    ap.add_argument("--jev", action="store_true", help="ask Jev about unresolved and weakly resolved speeches")
    ap.add_argument("--no-votes", action="store_true", help="use only this engine's reading of speaker lines")
    ap.add_argument("--draft", action="store_true", help="write the pooled delegates to data/gazetteer/delegates_draft.csv")
    args = ap.parse_args()
    run(args.symbols, args.engine, jev=args.jev, votes=not args.no_votes, draft=args.draft)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
