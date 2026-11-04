#!/usr/bin/env python3
"""Who was in the chair: the name of the presiding officer for the chair's turns ("The CHAIRMAN said ...").

The mastheads of the meeting records name the chair ("Chairman: Mrs. Franklin D. ROOSEVELT (United States of
America)", "President: Dr. Charles MALIK"). The record also says when someone else presided: in the masthead ("In the
absence of the Chairman, Mr. Farhadi (Afghanistan), Vice-Chairman, presided") or in the course of the meeting ("Mrs.
Begtrup (Denmark) took the Chair", and back: "The Chairman resumed the Chair"). The chair's turns get the name of the
person presiding at that point, read only from these statements; a record whose wording about the chair is anything
else ("presided" in the body, "Temporary Chairman", an unreadable name) gets no name from that point on.

The name is matched to the spelling the database already uses for that person as a delegate (same delegation, close
spelling), otherwise kept as printed. The chair's turns keep kind 'chair' and no delegation: the chair speaks for the
body, not for a country (a chair "speaking as the representative of" a country is a speech of that country only in
the record's words, and stays as it is).

Run from api/build_db.py after the speakers are unified: assign(con) sets speaker and speaker_method = 'chair (masthead)'
or 'chair (took the Chair)'.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# "Chairman: Mr. Eduard MEZINCESCU (Romania)", "President: Dr. Charles MALIK", "Chairman: Mrs. F. D. ROOSEVELT (United ...)"
# (not the Vice-Chairman: "Chaixman: Mrs. Eleanor Roosevelt" / "Vice-Chairman: Dr. P. C. Chang (China)", E/CN.4/AC.1/SR.11)
OFFICER_RE = re.compile(
    r"(?<!Vice-)(?<!Vice )(?<!VICE-)\b(?:"
    r"Cha[il1t]?[rzx]m[ae]n|CHA[IL1T]?[RZX]M[AE]N|"
    r"Chedeman|Chairmn|Chairyer|Chaizmen|Cheirman|Chaimrans|Caosivman|Chadrman|Chatuidn|Choirman|Chairizan|"
    r"Chal\s*ren|Cha\s*lrmans|Chelrrans|Ghaiyman|Chai\s*ruent|Stedrmant|"
    r"President|PRESIDENT"
    r")’?\s*(?:[.:;>~]+\s*[\-+]*\s*|\s+(?=(?:Mr|Mrs|Miss|Mme|Dr|Sir|Lady|Begum|Prof|Professor|M|hrs|Mes|Mesa)\b)|\n\s*(?=(?:Mr|Mrs|Miss|Mme|Dr|Sir|Lady|Begum|Prof|Professor|M)\b))(?P<who>[^\n]{3,90}(?:\n\s*\([^()\n]{3,60}\))?)"
)
# the Rapporteur, whose turns the segmenter reads as the chair's ("The RAPPORTEUR suggested ..."): named from the masthead's
# list of officers, "Rapporteur: Mrs. L. TSALDARIS (Greece)" (round 95)
RAPPORTEUR_RE = re.compile(r"\bRapporteur\s*[:;]+\s*(?P<who>[^\n]{3,90}(?:\n\s*\([^()\n]{3,60}\))?)")
# a masthead that names two chairs for the meeting ("Chairman: Mr. Emile SAINT-LOT (Haiti); later, Mr. C. MALIK (Lebanon)")
# does not say where the second took over: no name until the record says "took the Chair"
LATER_RE = re.compile(r"\blater\b|\bthen\b", re.I)
# the chairs' names as the OCR misread them in mastheads, read against the scans and the sessions' officers
VARIANTS = {
    "GORPHART": "VAN HEUVEN GOEDHART", "GORPUART": "VAN HEUVEN GOEDHART",
    "GOREPHARR": "VAN HEUVEN GOEDHART", "GOREPUART": "VAN HEUVEN GOEDHART",
    "GOEDHART": "VAN HEUVEN GOEDHART", "GOEDRART": "VAN HEUVEN GOEDHART",
    "GOEPUARR": "VAN HEUVEN GOEDHART", "GOEPUART": "VAN HEUVEN GOEDHART",
    "GOEPWART": "VAN HEUVEN GOEDHART", "GOREPHART": "VAN HEUVEN GOEDHART",
    "GORPHARR": "VAN HEUVEN GOEDHART",
    "VAN": "VAN HEUVEN GOEDHART", "VAN HEUVEN": "VAN HEUVEN GOEDHART",
    "BECTRUR": "BEGTRUP", "BRERRUE": "BEGTRUP", "EVARR": "EVATT",
    "EXSTRAND": "EKSTRAND",
    "FICUGROA": "FIGUEROA", "FICURROA": "FIGUEROA", "FIEURROA": "FIGUEROA",
    "BOXWARR": "BOKHARI",
    "MATIX": "MALIK", "MATRIX": "MALIK", "MALIKH": "MALIK", "ALIK": "MALIK", "HALIK": "MALIK",
    "HALIX": "MALIK", "MALIE": "MALIK", "MALIA": "MALIK", "EALIK": "MALIK", "MAD CK": "MALIK",
    "MUPAAUIAR": "MUDALIAR", "MUPAUIAR": "MUDALIAR", "RAMASWAMI MUDALTAR": "MUDALIAR",
    "NUFIEZ": "NUNEZ", "NIFIEZ": "NUNEZ", "NIUIIEZ": "NUNEZ", "NIIIEZ": "NUNEZ",
    "NIIEZ": "NUNEZ", "NUIIEZ": "NUNEZ",
    "WARZAZI": "EMBAREK WARZAZI", "ENBAREK WARZAZI": "EMBAREK WARZAZI",
    "WARZAZ I": "EMBAREK WARZAZI", "EMBAREK WAR": "EMBAREK WARZAZI",
    "CASANUEVA": "DIAZ CASANUEVA", "LOPES": "LOPEZ", "L 0 P E Z": "LOPEZ", "L O P E Z": "LOPEZ",
    "SALVADOR": "LOPEZ",
    "CISEL ET": "CISELET", "AZML": "AZMI",
    "MAHMOUD AZMI": "AZMI", "MAHMOUL AZMI": "AZMI",
    "ROOSEVELT": "ROOSEVELT", "ROOSEVELD": "ROOSEVELT", "ROCSEVELT": "ROOSEVELT",
    "ROUGEVELT": "ROOSEVELT", "ROOSEVEIE": "ROOSEVELT", "ROCS&EVNLT": "ROOSEVELT",
    "ROOCGVIA": "ROOSEVELT", "ROOSSVELT": "ROOSEVELT", "FRANKLIN": "ROOSEVELT",
    "META": "MEHTA", "IEHTA": "MEHTA",
    "AMJAD": "AMJAD ALI", "MELLO": "ALBUQUERQUE MELLO",
}
KNOWN_CHAIRS = {"EMBAREK WARZAZI", "MUDALIAR", "STAMPAR", "BERENDSEN", "AMJAD ALI", "SPAAK"}
ABSENCE_RE = re.compile(
    r"[Ii]n:?[\s_]+the\s+absence\s+of\s+(?:the\s+(?:Chairman|President)(?:\s+and\s+of\s+the\s+Vice-?\s*Chairman)?|Mr\.[^,]{2,40}),\s*"
    r"(?P<who>(?:Mr|Mrs|Miss|Mme|Dr|Sir|Lady|Begum|Prof|Professor|M)[.,]?\s+(?:(?!presided|took\s+the)[^;]){3,120}?),?\s*"
    r"(?:(?:First\s+|Second\s+)?Vice[-~]?\s*[Cc]hairman|Vice[-~]?\s*[Pp]resident|Rapporteur)?,?\s*(?:presided|took\s+the\s+[Cc]hair)",
    re.S,
)
TOOK_RE = re.compile(
    r"(?P<who>(?:Mr|Mrs|Miss|Mme|Dr|Sir|Lady|Begum|Prof|Professor|M|Mro|Mra|Mre)[.,]?\s+[^()]{2,60}?[\({][^(){}]{3,60}[\)}])"
    r"(?:,?\s*(?:(?:First\s+|Second\s+)?(?:Vice|Vico)[-~]?\s*[Cc]hair(?:man|nan)|Vice[-~]?\s*[Pp]resident|Rapporteur),?)?\s+"
    r"(?:was\s+unanimously\s+elected\s+Chairman\s+and\s+)?(?:took|occupied|resumed)\s+the\s+[Cc]hair"
    r"|At\s+this\s+point\s+(?P<who2>Mrs?\.\s+[A-Za-zÀ-ÿ' \-]{3,40})\s+arrived\s+and\s+presided",
    re.S,
)
RESUMED_RE = re.compile(r"\bThe (?:Chairman|CHAIRMAN|President|PRESIDENT)\s+(?:\([^()]{3,60}\)\s+)?resumed the [Cc]hair")
# any other statement about who presides: from there on the chair's name is not known
UNSURE_RE = re.compile(r"\b(?:presided|Temporary Chairman|Acting Chairman|took the [Cc]hair|in the [Cc]hair)\b")
TITLES = {"mr", "mrs", "miss", "mme", "m", "dr", "sir", "lady", "begum", "prof", "professor", "general", "judge", "be", "hr", "hrs", "hra", "mro", "mra", "mre", "mes", "mesa", "er", "kr", "mir"}
ATT_HEAD_RE = re.compile(r"\b(?:Members|Present|Praesent|Eresents|Secretariat|Representatives\s+of\s+specialized\s+agencies|later\s*:)\s*[:;]?", re.I)
COL_CHAIR_RE = re.compile(
    r"(?<!Rapporteur:\s)(?<!Rapporteur:\s\s)(?<!Vice-Chairman:\s)(?<!later,\s)"
    r"\b(?P<who>(?:Mr|Mrs|Miss|Mme|Dr|Sir|Lady|Begum|Prof|Professor|M|Be|Hr|Hrs|Hra|Mro|Mra|Mre|Er|Kr|Mir)[.,]?\s*\n?\s*[A-Za-zÀ-ÿ.'\" \-]{2,50}\s*[\({]\s*[A-Za-z][A-Za-z .>\n-]{2,45}[\)}])"
)


def role(text: str | None) -> str | None:
    """Chairman, President, Secretary or Rapporteur: the officer a chair's turn opens with."""
    from segment import CHAIR_RE, lead_turn
    m = CHAIR_RE.match(text or "")
    if not m:
        # (a turn opened by a phrase: "In reply to Mr. AZKOUL (Lebanon), the CHAIRMAN said ...", "At the request of Mr. BAROODY
        # (Saudi Arabia), the CHAIRMAN called for a separate vote"; round 99)
        kind, info = lead_turn(text or "", "")
        if kind == "chair" and info.get("role"):
            return info.get("role")
        t = (text or "")[:250]
        if re.search(r"\b(?:CHAIRMAN|Chairman|CHAIFMAN|CHAIPMAN)\b", t):
            return "Chairman"
        if re.search(r"\b(?:PRESIDENT|President|Pres(?:ent|went|ment|ipenr|wznr)|PRE,SIDENT|FREeSwENT|Pruswenr)\b", t):
            return "President"
        return None
    r = m.group("role").upper()
    return "Chairman" if r.startswith("CHA") or r.startswith(("C", "G")) and ("MA" in r or re.fullmatch(r"C[HP][A/][IJ1l][RE]M[A‘'{/]N", r)) else "President" if r.startswith("PRES") or r in ("PRE,SIDENT", "FREESWENT", "PRUSWENR") else "Rapporteur" if r.startswith("RAPP") else r.title()


def parse_person(text: str, normalize=None) -> tuple[str | None, str | None]:
    """'Mr. Eduard MEZINCESCU (Romania).' -> ('MEZINCESCU', 'Romania'); the surname is the run of capitals before the
    delegation (or at the end), the first names and the title are dropped."""
    t = re.sub(r"\s+", " ", text).strip().lstrip("{").rstrip(".;,| ")
    m = re.match(r"\s*(?P<name>[^(){}]{2,70}?)\s*(?:[\({](?P<country>[^(){}]{3,60})(?:[\)}]|$)|$|[.;,|]\s*$)", t)
    if not m:
        return None, None
    country = m.group("country")
    raw_words = [w.strip(".,;'\"“”‘’|\\/{}") for w in m.group("name").split()]
    words = [w for w in raw_words if w and re.search(r"[A-Za-z]", w) and w.lower().strip(".") not in TITLES
             and not re.fullmatch(r"(?:[A-Za-z]\.?-?){1,3}", w)]  # ("Roosevelt | |", initials "F. D.", "P.-H.")
    if not country and len(words) >= 2:
        for i in range(1, len(words)):
            w_prev = words[i - 1]
            letters = [c for c in w_prev if c.isalpha()]
            if len(letters) >= 3 and all(c.isupper() for c in letters):
                cand_country = " ".join(words[i:])
                if (normalize and normalize(cand_country)) or re.search(r"\b(?:United|States|America|Lebanon|France|Egypt|Chile|Australia|China|Denmark|India)\b", cand_country, re.I):
                    country = cand_country
                    words = words[:i]
                    break
    caps = []
    for w in reversed(words):
        letters = [c for c in w if c.isalpha()]
        if len(letters) >= 2 and sum(c.isupper() for c in letters) / len(letters) >= 0.6:
            caps.insert(0, w)
        elif caps:
            break
    surname = " ".join(caps) if caps else (words[-1] if words else None)
    if surname:
        surname = VARIANTS.get(surname.upper(), surname)
    if not surname or not re.fullmatch(r"[A-Za-zÀ-ÿ' \-]{3,40}", surname):
        return None, country
    return surname, country


def spelling(con: sqlite3.Connection, surname: str, country: str | None, normalize) -> str | None:
    """The spelling the database uses for this person (a delegate of that country, or anyone), if close enough."""
    from rapidfuzz import fuzz, process
    surname = VARIANTS.get(surname.upper(), surname)
    deleg = normalize(country) if country else None
    q = "SELECT speaker, count(*) FROM segments WHERE kind = 'speech' AND speaker IS NOT NULL"
    rows = con.execute(q + " AND delegation = ? GROUP BY speaker", (deleg,)).fetchall() if deleg else []
    rows = rows or con.execute(q + " GROUP BY speaker HAVING count(*) >= 5").fetchall()
    names = {r[0]: r[1] for r in rows}
    hit = process.extractOne(surname.upper(), list(names), scorer=fuzz.ratio)
    if hit and hit[1] >= (80 if deleg else 92):
        return VARIANTS.get(hit[0], hit[0])
    clean = surname.upper()
    clean = VARIANTS.get(clean, clean)
    return clean if (deleg or country or clean in KNOWN_CHAIRS) and re.fullmatch(r"[A-ZÀ-Ý' \-]{3,40}", clean) else None


def person(con: sqlite3.Connection, text: str, normalize) -> str | None:
    """The chair's name from the words naming them; None unless the delegation is given in brackets or the name is a
    known delegate's (a masthead's list of officers without delegations is read only for names the database knows)."""
    surname, country = parse_person(text, normalize)
    if not surname:
        return None
    name = spelling(con, surname, country, normalize)
    name = VARIANTS.get(name, name)
    if name and (country or name in KNOWN_CHAIRS or con.execute("SELECT 1 FROM segments WHERE kind = 'speech' AND speaker = ? LIMIT 1", (name,)).fetchone()):
        return name
    return None


def _extract_from_mast(con: sqlite3.Connection, mast: str, normalize, has_body_took: bool, allow_col_fallback: bool) -> tuple[str | None, str | None]:
    chair, how = (None, None)
    m = OFFICER_RE.search(mast)
    if m:
        after_who = re.split(r"\b(?:Rapporteur|Members?|Menbers|hembers|Secretariat|Present)\b", mast[m.start("who"):m.end("who") + 35], flags=re.I)[0]
        if not LATER_RE.search(after_who) or has_body_took:
            # (up to the next officer or the members, when the lines are run together: "Mrs. F. D. ROOSEVELT United States of
            # America Members :: ...", E/CN.4/SR.142)
            # (nothing, when the OCR put another officer right after the label: "Mr. CHANG China Chairman: Rapporteur: Mr. AZKOUL", E/CN.4/SR.99)
            who = re.split(r"(?:^|\s+)\W*(?:Members?|Menbers|hembers|Rapporteur|Vice-?\s*Chairman|Secretariat|later|then)\b", m.group("who"), flags=re.I)[0]
            chair = person(con, who, normalize)
            if chair:
                how = "chair (masthead)"
    if not chair and allow_col_fallback and re.search(r"\b(?:Cha[il1t]?[rzx]m[ae]n|Chal\s*ren|Ch[ao]irm[ae]n|Chai\s*ruent|Ghaiyman|Stedrmant|Present|Praesent|Eresents)\s*[.:;~*]*", mast, re.I):
        idx = re.search(r"\b(?:Cha[il1t]?[rzx]m[ae]n|Chal\s*ren|Ch[ao]irm[ae]n|Chai\s*ruent|Ghaiyman|Stedrmant|Present|Praesent|Eresents)\s*[.:;~*]*", mast, re.I).start()
        sub = mast[idx:]
        cm = COL_CHAIR_RE.search(sub)
        if cm:
            after_cm = re.split(r"\b(?:Rapporteur|Members?|Menbers|hembers|Secretariat)\b", sub[cm.start():cm.end() + 30], flags=re.I)[0]
            if not LATER_RE.search(after_cm) or has_body_took:
                chair = person(con, cm.group("who"), normalize)
                if chair:
                    how = "chair (masthead)"
        if not chair:
            m2 = re.search(r"Chairman\s*[:;][\s\S]{0,220}?\b(?P<who>(?:Mr|Mrs|Miss|Dr)[.,]?\s+(?:[A-Za-z]{1,10}\.?\s+){0,3}(?:ROOSEVELT|ROCSEVELT|Roosevelt|MALIK|Malik|CASSIN|AZMI))\b", sub)
            if m2:
                chair = person(con, m2.group("who"), normalize)
                if chair:
                    how = "chair (masthead)"
    a = ABSENCE_RE.search(mast)
    if a:
        p_abs = person(con, a.group("who"), normalize)
        if p_abs:
            chair, how = p_abs, "chair (presiding, masthead)"
    elif UNSURE_RE.search(mast) and not (chair and has_body_took):
        chair, how = (None, None)
    return chair, how


def assign(con: sqlite3.Connection, normalize) -> int:
    """Set the speaker of the chair's turns; returns how many were named."""
    named = 0
    symbols = [r[0] for r in con.execute("SELECT DISTINCT symbol FROM segments WHERE kind = 'chair'")]
    for sym in symbols:
        segs = con.execute("SELECT id, kind, text FROM segments WHERE symbol = ? ORDER BY seq", (sym,)).fetchall()
        # (with what comes before the first turn: a masthead whose contents end on an article read as a heading leaves its list of
        # officers in a passage of its own, "Article 8." / "Chairman; Mrs. F. D. ROOSEVELT United States of America", E/CN.4/SR.142)
        first = next((i for i, (_, k, t) in enumerate(segs) if k in ("chair", "vote", "closing") or (k == "speech" and not (OFFICER_RE.search(t or "") or ATT_HEAD_RE.search(t or "")))), len(segs))
        mast = "\n".join(t or "" for _, k, t in segs[:first] if k in ("masthead", "procedural") or (k == "speech" and (OFFICER_RE.search(t or "") or ABSENCE_RE.search(t or "") or ATT_HEAD_RE.search(t or ""))))
        has_body_took = any(TOOK_RE.search(t or "") for _, k, t in segs if k != "masthead")
        is_ecn = sym.startswith(("E/CN.4/", "E/AC.7/"))
        chair, how = _extract_from_mast(con, mast, normalize, has_body_took, allow_col_fallback=is_ecn)
        if not chair and not UNSURE_RE.search(mast):
            slug = sym.replace("/", "_")
            for subp in ("layer/page-001.txt", "best/page-001.txt", "tesseract/page-001.txt",
                         "layer/page-002.txt", "best/page-002.txt", "tesseract/page-002.txt",
                         "tess6/page-002.txt", "chandra/page-002.txt", "tess3/page-002.txt", "best/page-003.txt"):
                p = ROOT / "data" / "ocr" / slug / subp
                if p.exists():
                    ptxt = p.read_text(errors="ignore")
                    c_idx = ptxt.rfind("CONTENTS")
                    if c_idx != -1:
                        ptxt = ptxt[c_idx:]
                    chair, how = _extract_from_mast(con, ptxt, normalize, has_body_took, allow_col_fallback=is_ecn)
                    if chair:
                        break
        regular = chair
        updates = []
        r_ = RAPPORTEUR_RE.search(mast)
        rapporteur = person(con, r_.group("who"), normalize) if r_ else None
        rapp_deleg = None
        if rapporteur:
            _, country_ = parse_person(r_.group("who"), normalize)
            rapp_deleg = normalize(country_) if country_ else None
            if not rapp_deleg:  # (the masthead gives no delegation: the one the delegate's speeches give)
                row = con.execute("SELECT delegation, count(*) c FROM segments WHERE kind = 'speech' AND speaker = ? AND delegation IS NOT NULL "
                                  "GROUP BY delegation ORDER BY c DESC LIMIT 1", (rapporteur,)).fetchone()
                rapp_deleg = row[0] if row else None
        rapp_updates = []
        for sid, kind, text in segs:
            if kind == "masthead":
                continue
            # (not the Secretary's or the Rapporteur's turns, which the segmenter also reads as the chair's)
            if kind == "chair" and chair and role(text) in ("Chairman", "President"):
                updates.append((chair, how, sid))
            elif kind == "chair" and rapporteur and role(text) == "Rapporteur":
                rapp_updates.append((rapporteur, "rapporteur (masthead)", rapp_deleg, sid))
            # a change of chair takes effect after the passage that reports it
            t = text or ""
            took = TOOK_RE.search(t)
            if took:
                who_t = took.group("who") or took.group("who2")
                chair, how = person(con, who_t, normalize), "chair (took the Chair)"
            elif RESUMED_RE.search(t):
                chair, how = regular, "chair (masthead)"
            elif kind == "procedural" and len(t) < 220 and UNSURE_RE.search(t):
                chair = None
        con.executemany("UPDATE segments SET speaker = ?, speaker_method = ? WHERE id = ?", updates)
        # (the Rapporteur speaks as a member: a speech, with the name and delegation of the masthead)
        con.executemany("UPDATE segments SET kind = 'speech', speaker = ?, speaker_method = ?, delegation = coalesce(?, delegation) WHERE id = ?",
                        rapp_updates)
        named += len(updates) + len(rapp_updates)
    return named - unify(con)


def unify(con: sqlite3.Connection) -> int:
    """One spelling per chair: an OCR variant ("MUPAAUIAR", "LOPES", "CASANUEVA") joins a commoner chair's name that is
    close to it or contains it; a name left that is rare (under 3 turns) and no delegate's is dropped. Returns how many
    turns lost their name."""
    from collections import Counter
    from rapidfuzz import fuzz
    for old, new in VARIANTS.items():
        con.execute("UPDATE segments SET speaker = ? WHERE kind = 'chair' AND speaker = ?", (new, old))
    count = Counter(dict(con.execute("SELECT speaker, count(*) FROM segments WHERE kind = 'chair' AND speaker IS NOT NULL "
                                     "GROUP BY speaker").fetchall()))
    delegates = {r[0] for r in con.execute("SELECT DISTINCT speaker FROM segments WHERE kind = 'speech' AND speaker IS NOT NULL")} | KNOWN_CHAIRS
    for name, n in sorted(count.items(), key=lambda x: x[1]):
        better = [m for m, k in count.items() if k > n and (fuzz.ratio(name, m) >= 75 or f" {name}" in f" {m}")]
        if better:
            best = max(better, key=lambda m: count[m])
            con.execute("UPDATE segments SET speaker = ? WHERE kind = 'chair' AND speaker = ?", (best, name))
            count[best] += n
            count[name] = 0
    dropped = 0
    for name, n in count.items():
        if 0 < n < 3 and name not in delegates:
            dropped += con.execute("UPDATE segments SET speaker = NULL, speaker_method = NULL WHERE kind = 'chair' AND speaker = ?",
                                   (name,)).rowcount
    return dropped
