"""Meeting dates checked against the order of the meetings, and repaired from the scans' text.

Meetings of one series (E/CN.4/SR.n, A/C.3/SR.n, ...) are numbered in the order they were
held, so their dates cannot go down as the numbers go up. In each series the longest run of
dates that never goes down is taken as right. A date outside it is looked for again on the
record's first pages, in every OCR engine's reading, between the dates of the meetings
before and after it: a date written out in full, or a weekday, a day and a year whose month
the OCR mangled ("on Friday, 27 /.pril 1951"). One candidate only is accepted; with none,
the record is left without a date rather than with a wrong one.
"""
from __future__ import annotations

import bisect
import datetime as dt
import re
from collections import defaultdict
from pathlib import Path

from common import safe_name
from segment import DATE_RE, masthead_date

OCR = Path(__file__).resolve().parents[1] / "data" / "ocr"
SERIES_RE = re.compile(r"(.+/(?:SR|PV))\.(\d+)")
WEEKDAY_DATE_RE = re.compile(r"\b(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)\w{0,3}day\W{1,4}(\S{1,3})\s+\S{2,10}\s+(19[4-6]\d)", re.I)


def longest_run(dates: list[str]) -> set[int]:
    """Indices of a longest non-decreasing subsequence of ISO dates."""
    tails, tail_idx, prev = [], [], [-1] * len(dates)
    for i, d in enumerate(dates):
        k = bisect.bisect_right(tails, d)
        if k == len(tails):
            tails.append(d)
            tail_idx.append(i)
        else:
            tails[k], tail_idx[k] = d, i
        prev[i] = tail_idx[k - 1] if k else -1
    keep, i = set(), tail_idx[-1] if tail_idx else -1
    while i >= 0:
        keep.add(i)
        i = prev[i]
    return keep


def out_of_order(dates: dict[str, str | None]) -> dict[str, tuple[str | None, str | None]]:
    """Records whose date breaks their series' order -> (date before, date after) from the run."""
    series = defaultdict(list)
    for sym, d in dates.items():
        m = SERIES_RE.fullmatch(sym)
        if m and d:
            series[m.group(1)].append((int(m.group(2)), d, sym))
    out = {}
    for rows in series.values():
        rows.sort()
        keep = longest_run([d for _, d, _ in rows])
        for i, (_, _, sym) in enumerate(rows):
            if i not in keep:
                before = next((rows[j][1] for j in range(i - 1, -1, -1) if j in keep), None)
                after = next((rows[j][1] for j in range(i + 1, len(rows)) if j in keep), None)
                out[sym] = (before, after)
    return out


def page_candidates(symbol: str, pages: int = 2) -> tuple[set[dt.date], set[tuple[str, int, int]]]:
    """Dates written out on a record's first pages in any engine, and (weekday, day, year)
    readings whose month (or day: None) the OCR spoilt."""
    full, partial = set(), set()
    for d in sorted((OCR / safe_name(symbol)).glob("*")):
        for n in range(1, pages + 1):
            f = d / f"page-{n:03d}.txt"
            if not f.is_file():
                continue
            text = " ".join(f.read_text(encoding="utf-8").split())
            for m in DATE_RE.finditer(text):
                iso = masthead_date(m.group(0))
                if iso:
                    full.add(dt.date.fromisoformat(iso))
            for m in WEEKDAY_DATE_RE.finditer(text):
                day = m.group(2).strip(".,")
                partial.add((m.group(1).lower(), int(day) if day.isdigit() else None, int(m.group(3))))
    return full, partial


def missing(dates: dict[str, str | None]) -> dict[str, tuple[str | None, str | None]]:
    """Records of a series with no date -> (date of the meeting before, date of the one after)."""
    series = defaultdict(list)
    for sym, d in dates.items():
        m = SERIES_RE.fullmatch(sym)
        if m:
            series[m.group(1)].append((int(m.group(2)), d, sym))
    out = {}
    for rows in series.values():
        rows.sort()
        for i, (_, d, sym) in enumerate(rows):
            if not d:
                before = next((rows[j][1] for j in range(i - 1, -1, -1) if rows[j][1]), None)
                after = next((rows[j][1] for j in range(i + 1, len(rows)) if rows[j][1]), None)
                if before and after:
                    out[sym] = (before, after)
    return out


def repair(dates: dict[str, str | None]) -> dict[str, str | None]:
    """New dates for the records whose date breaks their series' order, and for the records
    with none (between two dated neighbours) whose scans give one."""
    fixes = {}
    bad = out_of_order(dates)
    unread = {s: b for s, b in missing({s: (None if s in bad else d) for s, d in dates.items()}).items() if s not in bad}
    for sym, (before, after) in {**bad, **unread}.items():
        lo = dt.date.fromisoformat(before) if before else None
        hi = dt.date.fromisoformat(after) if after else None
        lo = lo or (hi - dt.timedelta(days=30) if hi else None)
        hi = hi or (lo + dt.timedelta(days=30) if lo else None)
        if not lo:
            continue
        full, partial = page_candidates(sym)
        # a year with one digit misread ("5 April 1956" among the 1950 meetings) is the neighbours' year
        years = {lo.year, hi.year}
        def near(y: int) -> set[int]:
            return {y} | {n for n in years if sum(a != b for a, b in zip(str(y), str(n))) == 1}
        full = {d.replace(year=y) for d in full for y in near(d.year) if not (d.month == 2 and d.day == 29)}
        partial = {(wd, day, y) for wd, day, year in partial for y in near(year)}
        fits = {d for d in full if lo <= d <= hi}
        for wd, day, year in partial:
            d = lo
            while d <= hi:
                # the day as read, or with a digit lost ("3 April" for 30 April), or unread in a week's window
                day_ok = day is None and (hi - lo).days <= 7 or day is not None and (
                    d.day == day or len(str(d.day)) == len(str(day)) + 1 and str(day) in str(d.day))
                if day_ok and d.year == year and d.strftime("%A").lower().startswith(wd):
                    fits.add(d)
                d += dt.timedelta(days=1)
        if len(fits) == 1:
            fixes[sym] = min(fits).isoformat()
        elif sym in bad:
            fixes[sym] = None
    return fixes
