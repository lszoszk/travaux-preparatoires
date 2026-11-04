"""Bodies and sessions of the drafting records.

The UN Library's UDHR guide files each record under a body and session. Records outside it
(the UDHR supplement, all Covenant records 1949-66) get them here: the body from the symbol,
the session from the meeting date.
"""
from __future__ import annotations

import re
from collections import defaultdict

# Bodies by symbol prefix, for documents outside the UN Library guide (most specific first)
BODIES = [
    ("E/CN.4/SUB.2/", "Sub-Commission on Prevention of Discrimination and Protection of Minorities"),
    ("E/CN.4/SUB.1/", "Sub-Commission on Freedom of Information and of the Press"),
    ("E/CN.4/AC.1/", "CHR Drafting Committee"),
    ("E/CN.4/AC.2/", "CHR Working Group on the Declaration"),  # its records' masthead: "WORKING GROUP ON THE DECLARATION"
    ("E/CN.4/AC.3/", "CHR Working Group on the Convention"),
    ("E/CN.4/AC.4/", "CHR Working Group on Implementation"),
    ("E/CN.4/", "Commission on Human Rights"),
    ("E/CN.6/", "Commission on the Status of Women"),
    ("E/HR/", "Nuclear Commission on Human Rights"),
    ("E/AC.7/", "ECOSOC Social Committee"),
    ("E/CONF.6/", "UN Conference on Freedom of Information (1948)"),
    ("E/", "Economic and Social Council"),
    ("A/C.3/", "General Assembly Third Committee"),
    ("A/C.1/", "General Assembly First Committee"),
    ("A/PV.", "General Assembly plenary"),
    ("A/RES/", "General Assembly"),
    ("A/", "General Assembly"),
    ("PC/", "Preparatory Commission of the United Nations"),
]


def body_from_symbol(symbol: str) -> str | None:
    return next((b for pre, b in BODIES if symbol.upper().startswith(pre.upper())), None)


# Sessions by meeting date, for records outside the UN Library guide (body, session, first
# and last day; bounds are generous: a body never held two sessions at once)
SESSIONS_1946_48 = [
    ("Preparatory Commission of the United Nations", "1945", "1945-01-01", "1946-01-10"),
    ("Nuclear Commission on Human Rights", "1946", "1946-04-01", "1946-06-01"),
    ("Commission on Human Rights", "1st session (1947)", "1947-01-10", "1947-02-15"),
    ("Commission on Human Rights", "2nd session (1947)", "1947-11-25", "1947-12-20"),
    ("Commission on Human Rights", "3rd session (1948)", "1948-05-20", "1948-06-20"),
    ("CHR Drafting Committee", "1st session (1947)", "1947-02-01", "1947-07-01"),
    ("CHR Drafting Committee", "2nd session (1948)", "1948-05-01", "1948-05-25"),
    ("CHR Working Group on the Declaration", "2nd session (1947)", "1947-11-25", "1947-12-20"),
    ("CHR Working Group on the Convention", "2nd session (1947)", "1947-11-25", "1947-12-20"),
    ("CHR Working Group on Implementation", "2nd session (1947)", "1947-11-25", "1947-12-20"),
    ("Sub-Commission on Freedom of Information and of the Press", "2nd session (1948)", "1948-01-01", "1948-02-10"),
    ("Sub-Commission on Prevention of Discrimination and Protection of Minorities", "1st session (1947)", "1947-10-01", "1947-12-15"),
    ("Commission on the Status of Women", "1st session (1947)", "1947-02-01", "1947-02-28"),
    ("Commission on the Status of Women", "2nd session (1948)", "1948-01-01", "1948-01-31"),
    ("UN Conference on Freedom of Information (1948)", "1948", "1948-03-01", "1948-04-30"),
    ("General Assembly Third Committee", "1st session (1946)", "1946-01-01", "1946-12-31"),
    ("General Assembly Third Committee", "2nd session (1947)", "1947-09-01", "1947-12-31"),
    ("General Assembly Third Committee", "3rd session (1948)", "1948-09-15", "1948-12-15"),
    ("General Assembly First Committee", "1st session (1946)", "1946-01-01", "1946-12-31"),
    ("General Assembly plenary", "1st session (1946)", "1946-01-01", "1946-12-31"),
    ("General Assembly plenary", "3rd session (1948)", "1948-09-15", "1948-12-15"),
    ("General Assembly", "1st session (1946)", "1946-01-01", "1946-12-31"),
    ("General Assembly", "2nd session (1947)", "1947-09-01", "1947-12-31"),
    ("General Assembly", "3rd session (1948)", "1948-08-25", "1948-12-31"),
    ("Economic and Social Council", "1st session (1946)", "1946-01-20", "1946-02-25"),
    ("Economic and Social Council", "2nd session (1946)", "1946-05-20", "1946-06-25"),
    ("Economic and Social Council", "3rd session (1946)", "1946-08-20", "1946-10-15"),
    ("Economic and Social Council", "4th session (1947)", "1947-02-25", "1947-04-05"),
    ("Economic and Social Council", "5th session (1947)", "1947-07-15", "1947-08-20"),
    ("Economic and Social Council", "6th session (1948)", "1948-02-01", "1948-03-15"),
    ("Economic and Social Council", "7th session (1948)", "1948-07-15", "1948-08-31"),
    ("Economic and Social Council", "10th session (1950)", "1950-02-01", "1950-03-15"),
    ("Economic and Social Council", "11th session (1950)", "1950-05-15", "1950-08-31"),
    ("Economic and Social Council", "12th session (1951)", "1951-02-01", "1951-03-31"),
    ("Economic and Social Council", "13th session (1951)", "1951-05-15", "1951-10-31"),
]








def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def session_by_date(body: str | None, date: str | None) -> str | None:
    """The session a meeting on `date` belongs to, labelled as the UN Library guide does
    ("3rd session (1948)")."""
    if not body or not date:
        return None
    hit = next((sess for b, sess, lo, hi in SESSIONS_1946_48 if b == body and lo <= date <= hi), None)
    if hit:
        return hit
    year, month = int(date[:4]), int(date[5:7])
    # the Commission met once a year, in the spring: 5th session 1949 ... 10th 1954
    if body.startswith("Commission on Human Rights") and 1949 <= year <= 1966:
        return f"{ordinal(year - 1944)} session ({year})"
    # a General Assembly session opens in September and can run into the next spring
    if body.startswith("General Assembly") and 1949 <= year <= 1967:
        start = year if month >= 9 else year - 1
        return f"{ordinal(start - 1945)} session ({start})"
    return None


def fix_year(date: str | None, session: str | None) -> str | None:
    """A date whose year contradicts its session's is an OCR slip in the last digit of the
    year ("1941-10-14" in the 1948 session): take the session's year. A General Assembly
    session can run into the next year, so that year is accepted too."""
    m = re.search(r"\((\d{4})\)", session or "")
    if not date or not m:
        return date
    y = int(m.group(1))
    if date[:4] in (str(y), str(y + 1)):
        return date
    # one digit misread ("1941" for 1948, "1967" for 1957): the session's year, or the next one
    # for the months a General Assembly session runs into
    for cand in (str(y), str(y + 1)):
        if sum(a != b for a, b in zip(date[:4], cand)) == 1:
            if cand == str(y + 1) and date[5:7] >= "09":
                continue
            return cand + date[4:]
    return date


def series_key(symbol: str) -> tuple[str, int] | None:
    """("E/CN.4/SR.", 102) for a meeting record."""
    m = re.match(r"(.*?/(?:SR|PV)\.)(\d+)$", symbol)
    return (m.group(1), int(m.group(2))) if m else None


def sessions_for(records: dict[str, tuple[str | None, str | None]]) -> dict[str, str | None]:
    """symbol -> session for records given as symbol -> (body, meeting date). A record whose
    date the OCR lost ("20 May 19. 9") takes the session of the meetings numbered around it,
    when those agree (or when only one side is known and it is at most three meetings away)."""
    out = {sym: session_by_date(body, date) for sym, (body, date) in records.items()}
    series: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for sym in records:
        k = series_key(sym)
        if k:
            series[k[0]].append((k[1], sym))
    for items in series.values():
        items.sort()
        # a misread date ("1956" in a 1950 run) disagrees with the nearest dated meetings on both
        # sides, which agree with each other: drop it (undated meetings in between are skipped)
        dated = [(n, sym) for n, sym in items if out[sym]]
        for i in range(1, len(dated) - 1):
            a, x, b = out[dated[i - 1][1]], out[dated[i][1]], out[dated[i + 1][1]]
            if a == b and x != a:
                out[dated[i][1]] = None
        for i, (n, sym) in enumerate(items):
            if out[sym]:
                continue
            before = next(((m, out[x]) for m, x in reversed(items[:i]) if out[x]), None)
            after = next(((m, out[x]) for m, x in items[i + 1:] if out[x]), None)
            if before and after and before[1] == after[1]:
                out[sym] = before[1]
            elif before and not after and n - before[0] <= 3:
                out[sym] = before[1]
            elif after and not before and after[0] - n <= 3:
                out[sym] = after[1]
    return out
