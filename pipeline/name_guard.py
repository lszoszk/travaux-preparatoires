#!/usr/bin/env python3
"""A guard on the names in the vision reader's text: a reader that reads a page cleanly can still misread a name in a way that
looks right ("ADRI Bey (Egypt)" for AZMI, E/CN.4/SR.203 p13; "Chairman: Mr. KALLK (Lebanon)" for MALIK, E/CN.4/SR.250 p2), and
the database then carries a person who never spoke. eval/vlm_pilot/results_preview_mixed.md.

For every name the page prints at the opening of a turn ("Mr. X (Delegation)", "X Bey (Delegation)") or in the list of officers
("Chairman: Mr. X (Delegation)"):
1. a name already known for that delegation, or read the same by at least two OCR engines at that opening, is kept (known: given by an attendance list at least 4 times in the current
   database, or checked on the scan, or in the gazetteer; compared without spaces, hyphens or accents, so "SØRENSEN" stays);
2. otherwise, if the OCR engines read the same opening (same delegation, same words after it) and a known name of that delegation
   is the most frequent of their readings, their reading replaces the reader's;
3. otherwise, if exactly one known name of that delegation in this body and session (for an officer, also the session's chairs)
   is close to the reader's (ratio >= 75, for an officer >= 60; ten points ahead of the next), it replaces it;
4. otherwise the name is kept and listed as unverified.
Every replacement and every unverified name is returned, for the manifest and for review.

  from name_guard import Guard; g = Guard(); text, log = g.check("E/CN.4/SR.203", 13, text, {"vote": ..., "tess3": ...})
"""
from __future__ import annotations

import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from segment import NAME, POSTTITLE_RE, SPEAKER_RE, TITLE  # noqa: E402

OFFICER_RE = re.compile(rf"^\s*(?P<role>Chairman|Chairmen|Vice-Chairman|Vice-Chairmen|Rapporteur|President|Vice-President)\s*:\s*"
                        rf"(?P<title>{TITLE})[.,]?\s+(?P<name>{NAME})\s*\((?P<country>[^()\n]{{2,100}})\)")
# a name is known when the database gave it by an attendance list at least MIN_SEEN times, or a person checked it on the scan; not a
# name taken as printed (text_name, text_org): those are the OCR's spellings ("INSRRAN", "VAN HGHER")
ROSTER = ("vote_joint", "roster_match", "roster_token", "sole_delegate", "rapporteur (masthead)")
MIN_SEEN = 4


def plain(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").replace("Ø", "O").replace("ø", "o")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z ]", "", s.upper().replace("-", " ")).strip()


def bare(s: str) -> str:
    """For comparing spellings: no spaces, hyphens or accents ("SØRENSEN" = SORENSEN, "SANTA-CRUZ" = SANTA CRUZ)."""
    return plain(s).replace(" ", "")


def family(engine: str) -> str:
    """Tesseract's variants (tess3, tess4, tess6, tess6min) are one reader: they agree on the same garble ("Hasre", "HOPGSCN")."""
    return "tess" if engine.startswith("tess") else engine


def cues(text: str) -> list[dict]:
    """The names printed at turn openings and officer lines, with their line, span, delegation as printed and the next words."""
    out = []
    for k, line in enumerate(text.splitlines()):
        for rx, kind in ((OFFICER_RE, "officer"), (SPEAKER_RE, "turn"), (POSTTITLE_RE, "turn")):
            m = rx.match(line)
            if m:
                out.append({"line": k, "kind": kind, "role": m.groupdict().get("role") or "", "name": m.group("name").strip(), "span": m.span("name"),
                            "country": m.group("country").strip(), "tail": line[m.end():m.end() + 60]})
                break
    return out


class Guard:
    def __init__(self, db: Path = ROOT / "data" / "travaux.sqlite3"):
        con = sqlite3.connect(db)
        self.session = {s: (b, ss) for s, b, ss in con.execute("SELECT symbol, body, session FROM documents")}
        self.known = defaultdict(set)                    # delegation -> names known in any session
        self.in_session = defaultdict(Counter)           # (body, session, delegation) -> names
        self.chairs = defaultdict(Counter)               # (body, session) -> chairs' names
        rows = con.execute("SELECT s.speaker, s.delegation, s.kind, s.speaker_method, d.body, d.session FROM segments s "
                           "JOIN documents d USING(symbol) WHERE s.kind IN ('speech', 'chair') AND s.speaker <> ''").fetchall()
        seen = Counter()
        for sp, dl, kind, method, body, ses in rows:
            if kind == "speech" and dl and method in ROSTER:
                seen[(plain(sp), dl)] += 1
        for sp, dl, kind, method, body, ses in rows:
            name = plain(sp)
            if kind == "chair":
                self.chairs[(body, ses)][name] += 1
                continue
            if not dl or not (method and method.startswith("checked") or method in ROSTER and seen[(name, dl)] >= MIN_SEEN):
                continue
            self.known[dl].add(name)
            self.in_session[(body, ses, dl)][name] += 1
        gaz = ROOT / "data" / "gazetteer" / "delegates.csv"
        self.alias = {}                                  # (delegation, a variant) -> the delegate's surname
        if gaz.exists():
            import csv
            for r in csv.DictReader(gaz.open()):
                for n in [r["surname"], *filter(None, (r.get("variants") or "").split(";"))]:
                    self.known[r["delegation"]].add(plain(n))
                    if plain(n) != plain(r["surname"]):
                        self.alias[(r["delegation"], plain(n))] = plain(r["surname"])
        self.delegations = sorted(self.known)

    def delegation(self, printed: str) -> str | None:
        hit = process.extractOne(printed, self.delegations, scorer=fuzz.token_set_ratio)
        return hit[0] if hit and hit[1] >= 80 else None

    def is_known(self, name: str, dl: str | None) -> bool:
        n = plain(name)
        pool = self.known.get(dl, set()) if dl else set().union(*self.known.values())
        bares = {bare(x) for x in pool}
        return bare(n) in bares or bool(n.split()) and n.split()[-1] in pool

    def canonical(self, name: str, dl: str | None) -> str | None:
        """The database's spelling of a name known for the delegation ("Charles MALIK" -> MALIK, "SØRENSEN" -> SORENSEN), or None."""
        if not dl:
            return None
        pool = self.known.get(dl, set())
        n = plain(name)
        for k in sorted(pool):
            if bare(k) == bare(n):
                return self.alias.get((dl, k), k)  # (a gazetteer variant is its delegate: "HANSA MEHTA" is MEHTA)
        # by the last word: the longest known name that ends with it ("SMIT SANTA-CRUZ", "GANEA CRUZ" -> SANTA CRUZ, not CRUZ)
        last = n.split()[-1] if n.split() else ""
        ends = [k for k in pool if k.split() and k.split()[-1] == last]
        best = max(ends, key=lambda k: (len(k.split()), len(k))) if ends else None
        return self.alias.get((dl, best), best) if best else None

    def session_match(self, symbol: str, name: str, dl: str | None, need: float = 80) -> str | None:
        """The one delegate of the delegation in this body and session whose name is close to a printed one (ratio >= need, ten
        points ahead of the next): a typist's spelling ("SORENSON", "MOROSOV", "DOWIE") is that person, or None."""
        body, ses = self.session.get(symbol, (None, None))
        pool = list(self.in_session.get((body, ses, dl), {}))
        if not pool or not name:
            return None
        ranked = sorted(((fuzz.ratio(bare(name), bare(n)), n) for n in pool), reverse=True)
        if ranked[0][0] >= need and (len(ranked) == 1 or ranked[0][0] - ranked[1][0] >= 10):
            return ranked[0][1]
        return None

    def check(self, symbol: str, page: int, text: str, engines: dict[str, str],
              proposers: frozenset[str] = frozenset()) -> tuple[str, list[dict]]:
        """proposers: engines whose reading may replace a name (step 2) but never keeps one (step 1): PERO reads a damaged
        letter as the vision reader does (eval/vlm_pilot/results_pero_guard.md), so its agreement is no confirmation."""
        body, ses = self.session.get(symbol, (None, None))
        lines = text.splitlines()
        log = []
        other = {e: cues(t) for e, t in engines.items()}
        for c in cues(text):
            dl = self.delegation(c["country"])
            if self.is_known(c["name"], dl):
                continue
            # 2. the OCR engines' reading of the same opening
            readings, same = [], 0
            for e, cs in other.items():
                if e == "vote":  # (the engines' majority, not a reading of its own)
                    continue
                best = max(cs, key=lambda o: fuzz.ratio(o["tail"][:50], c["tail"][:50]), default=None)
                if best and fuzz.ratio(best["tail"][:50], c["tail"][:50]) >= 60 and \
                        fuzz.token_set_ratio(best["country"], c["country"]) >= 60:
                    same += bare(best["name"]) == bare(c["name"]) and e not in proposers
                    if self.is_known(best["name"], dl):
                        readings.append(plain(best["name"]))
            if same >= 2:  # two engines read what the reader read: the name is printed so, known or not ("Mr. WHITE (Australia)")
                continue
            new, how = None, None
            if readings:
                new, how = Counter(readings).most_common(1)[0][0], f"engines ({len(readings)})"
            elif dl:
                pool = Counter(self.in_session.get((body, ses, dl), {}))
                if c["kind"] == "officer":
                    pool.update(self.chairs.get((body, ses), {}))
                ranked = process.extract(plain(c["name"]), list(pool), scorer=fuzz.ratio, limit=2)
                chair = self.chairs.get((body, ses))
                if c["kind"] == "officer" and re.match(r"Chairman|President", c["role"]) and chair:
                    # the session's chair, if one person of this delegation chaired it ("Chairman: Mr. HALLA (Lebanon)": MALIK)
                    top = [n for n, _ in chair.most_common() if n in self.known.get(dl, set())]
                    if len(top) == 1:
                        ranked = [(top[0], 100.0, 0)]
                need = 60 if c["kind"] == "officer" else 75  # (an officer is one of a handful; a turn's speaker one of many)
                if ranked and ranked[0][1] >= need and (len(ranked) == 1 or ranked[0][1] - ranked[1][1] >= 10):
                    new, how = ranked[0][0], f"session roster ({ranked[0][1]:.0f})"
            entry = {"symbol": symbol, "page": page, "read": c["name"], "delegation": dl or c["country"], "kind": c["kind"]}
            if new and bare(new) != bare(c["name"]):
                a, b = c["span"]
                line = lines[c["line"]]
                lines[c["line"]] = line[:a] + new + line[b:]
                log.append({**entry, "now": new, "by": how})
            else:
                log.append({**entry, "now": None, "by": "unverified"})
        return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), log
