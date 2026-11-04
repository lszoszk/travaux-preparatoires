"""Text normalisation for OCR'd UN records: page furniture first.

Mimeographed records (1946-54) carry, on every page after the first:
- a running head: the symbol ("E/CN.4/SR.60", OCR'd as "ii/cE.Vsn.60", "B/H.'/SR.60")
  and a page line ("Page 10", OCR'd as "Pa-3 10", "Pasa 10", "Pttgo 1^.");
- a catchword at the foot: the first words of the next page after a slash ("/ He would").
Both repeat text that is not part of the record and break sentences across pages.

The rules are deliberately narrow: only short lines at the very top or bottom of a page
are candidates. Anything they remove is returned, so it can be audited, and ambiguous
lines can later be sent to Jev (noul: "is this line page furniture?").
"""
from __future__ import annotations

import re

# A short token that looks like a (garbled) UN symbol: slashes, few spaces, <= 24 chars.
SYMBOL_HEAD_RE = re.compile(r"^[\W_]*[A-Za-z0-9]{1,3}\s?/[\w.'/ \-^•]{2,20}$")
# "Page 10" and its OCR variants ("Pa-3 10", "Pttgo 1^.", "Page 5-", "Pave 1h."):
# P + 1-4 chars, then 1-3 digit-like characters, then punctuation only.
PAGE_LINE_RE = re.compile(r"^[\W_]*P\S{1,4}[\s.:\-]*[\dOoIlh^|]{1,3}[\s.:°,\-]*$")
# A catchword: a short last line starting with a slash.
CATCHWORD_RE = re.compile(r"^\s*(?:/\s*\S.{0,40}|\[\s?[A-Za-z][a-z]{1,12})$")  # ("[New", "[subjective": the slash misread)
# Lines that are page furniture wherever the OCR puts them (in a two-column page, the running head can come out
# between the lines of a column): found in the speeches by the segmentation audit on page images (October 2026).
# Each is a whole line that no sentence of a record can be.
ANYWHERE_RES = [
    # printed records' running heads: "414 General Assembly — Twenty-first Session — Third Committee",
    # "A/C.3/SR.925 88 General Assembly — Fourteenth Session — Third Committee", "162 General Assembly - Thirteenth ..."
    re.compile(r"^[\W\d_]*(?:A/C\.3/SR\.\d+\s+)?(?:\d{1,4}\s+)?General\s+Assembly\s*[—–\-~]+\s*[A-Z][\w\-~]+\s+Session\s*[.—–\-~]+"
               r"\s*(?:Third|Fourth|Fifth|Sixth|First|Second)\s+Committee[\W\d]*$"),
    # "1446th meeting — 2 December 1966 413", "382nd Meeting—10 January 1952 205", and the OCR's "58let meeting — 11 November 1954 199"
    re.compile(r"^[\W\d_]*\d{1,4}[A-Za-z]{1,3}\s+[Mm]eeting\s*[—–\-~]+\s*\d{1,2}\s+[A-Z][a-z]+\s+19\d\d[\W\d]*$"),
    # the verbatim plenary's running head: "182nd plenary meeting", "909 182nd plenary meeting", "1123 Fifty-fifth Plenary Meeting",
    # "932 10 December 1948"
    re.compile(r"^[\W\d_]*\d{1,3}(?:st|nd|rd|th)\s+[Pp]lenary\s+[Mm]e?\w{2,4}ing[\W\d]*$|^[\W\d_]*[A-Z][a-z]+(?:-[a-z]+)?\s+Plenary\s+Meeting[\W\d]*$"),
    re.compile(r"^\W*\d{2,4}\s+\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+19\d\d\W*$"),
    # the printer's line: "Litho in U.N. 77301—March 1963—2,125", "SPI—93250—February 1952—3,350"
    re.compile(r"^\W*Litho(?:ed)?\s+[i1l]n\s+U\.?\s?N\.?\b.{0,60}$"),  # (the OCR's "Litho 1n U.N,", round 109)
    re.compile(r"^\W*[A-Z]{2,4}\s*[—–\-]+\s*\d{4,6}\s*[—–\-]+\s*[A-Z][a-z]+\s+19\d\d\s*[—–\-]+\s*[\d,. ]+\W*$"),
    # a page line or a symbol with its page, in lower case or with a colon: "page 12", "pase 20", "B/cNo4/SR.298: Page 11",
    # "E/CH.4/SR.249 Para 22", "E/CN.4/SR.479 English Page 16", "Page 8 ;"
    re.compile(r"^[\W_]*(?:[A-Za-z0-9]{1,3}\s?/[\w.,'/ \-^•]{2,22}[:,.;]?\s*)?(?:English\s+|French\s+)?(?:[PpFf]a[gsc]e|[Pp]ara)\s*[\dOoIl1hy^|]{1,3}[\s.:;|°,\-]*$"),
]
# Only for meeting records: in a document (a report, a compilation of comments) a line of this kind at a page boundary can be what
# separates two paragraphs, and taking it out joins them (E/1992 p. 34), which breaks the hand-read sections that are matched on it.
RECORD_RES = [
    # the printer's line without "Litho in U.N.": "77301-January 1959-2,075", "M—77301—March 1957—2,150", "Printed in U.S.A."
    # (and as the OCR misreads it: "M—77301—December 1955} 875", "7791—June 1960—2,025"; round 109)
    re.compile(r"^\W*(?:[A-Z]{1,4}\s*[—–\-]+\s*)?\d{4,5}\s*[—–\-~]+\s*[A-Z][a-z]+\s+19\d\d\s*[—–\-~}]+\s*[\d,. ]+\W*$|^\W*Printed\s+in\s+U\.?S\.?A\.?\W*$"),
    # a record's own symbol with its page numbers: "A/C.3/SR.388 242", "241 A/C.3/SR.388 242", "E/CN.4/SUB.2/SR.11" alone
    re.compile(r"^\W*(?:\d{1,4}\s+)?[AE]/(?:[A-Za-z0-9.]+/)*(?:SR|PV)[.,]\s?\d+(?:\s+\d{1,4})?\W*$"),
    # (round 109's audit on page images) the 1960s plenary's running head, "6 General Assembly — Twenty-first Session — Plenary
    # Meetings", "g& General Assembly ..."; the Third Committee's split over two lines by the OCR, "352 General Assembly—Sixth" /
    # "Session—Third Comunittee"
    re.compile(r"^(?:[\W\d_]|[a-z](?=\W))*\s*General\s+Assembly\s*[—–\-~]+\s*[A-Z][\w\-~]+\s+Session\s*[.—–\-~]+\s*Plenary\s+Meetings[\W\d]*$"),
    re.compile(r"^\W*\d{1,4}\s+General\s+Assembly\s*[—–\-~]+\s*[A-Z][a-z]+(?:-[a-z]+)?\W*$"),
    re.compile(r"^\W*Session\s*[—–\-~]+\s*(?:Third|Fourth|Fifth|Sixth|First|Second)\s+Com\w{4,9}\W*$"),
]
# the date with the page number, "29 October 1957 167": not on a first page, where the masthead's own date can read so ("20 May
# 1949 59", round 111)
DATE_PAGE_RE = re.compile(r"^\W*\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+19\d\d\s+\d{2,4}\W*$")
# a bare page number, or the language tag of a running head, only at the very top or foot of a page
EDGE_RES = [re.compile(r"^\W*\d{1,4}\W*$"), re.compile(r"^\W*(?:English|French)\W*$")]
# Meeting records only, from the segmentation audits on page images (rounds 68, 72, 73: the running heads, catchwords and
# printers' lines the rules above missed). At the top of a page: the symbol as the OCR garbles it, with a comma or a bar
# ("E/CN,4/SR.391", "E/CN.1|/3R.67"), and the page line after a handwritten folio ("~ 70 Page 11").
RECORD_TOP_RES = [re.compile(r"^[\W_]*[A-Za-z0-9#]{1,3}\s?/[\w.,'/ \-^•|¥÷+]{2,22}$"),
                  re.compile(r"^[\W\d_]{0,8}[PpFfTt]a\S{1,3}\s*[\dOoIl1h^|]{0,3}[\s.:;°,\-]*$"),
                  # the typed records' "Page 13" as the OCR read it: "Bago 13", "Page iO", "page BT - | |", "Page' 13'", "Page k",
                  # "i page 5 —" (the audit on random pages of round 80)
                  re.compile(r"^(?:[a-z]\s)?[\W\d_]{0,8}[PpFfBbTt]a[gsq][eo0]\W?\s*(?:[\dOoIl1hikB^|]{1,3}|[A-Za-z]{1,2})?[\s.:;°,'’\-|—–]*$"),
                  # (round 86, the audits of rounds 84-85: "Feige 10", "Fogo 3", "Pages 11", "page 1%", "page & Se", "Page 12 q",
                  # "Page 10 ~"; the symbol with marks the rule above lacks, "E/CN.4/SR.4 ›c", "B/GN 'Q~ lit- a |", "£/cn, ¥/sR. 61",
                  # "B/cn. B/on, [nos /9R: ya": a slash after at most three letters or figures, and no word of five letters)
                  # (with its number, or a mark for it: "persons." and "tegory A" at the top of a page are text)
                  re.compile(r"^(?:[a-z]\s)?[\W\d_]{0,8}[PpFfBbTt][aeio][a-z]?[gsq][eo0]s?\W?\s*[\dOoIl1hikB^|%&@$]{1,3}"
                             r"(?:\s+(?:[A-Za-z]{1,2}|[\W\d]{1,3}))?[\s.:;°,'’\-|—–~]*$"),
                  re.compile(r"^[\W_]*(?:[A-Za-z0-9#]{1,3})?\s?/(?!.*[A-Za-z]{5})[^\n]{2,24}$")]
# at the foot: the typist's date mark ("10/6 a.m.", "27/4 p.m.", the OCR's "10/6 on.")
RECORD_FOOT_RES = [re.compile(r"^\W*\d{1,2}\s*/\s*\d{1,2}\s*(?:[ap]\.?\s?m|on|pm|am)\W*$")]
# anywhere in a line, where the OCR ran a printed record's running head into the text: "the 276 General Assembly — Twenty-first
# Session — Third Committee", "worthy of 909 182nd plenary meeting democratic", "repre- 1124 11 December 1946 sentative",
# "1123 Fifty-fifth Plenary Meeting", "1259th meeting ~ 11 November 1963 249", "Printed in France"
MONTHS = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
INLINE_HEAD_RES = [
    re.compile(r"(?:^|\s)\d{1,4}\s+General\s+Assembly\s*[—–\-~]+\s*[A-Z][\w\-~]+\s+Session\s*[.—–\-~]+\s*(?:Third|Fourth|Fifth|Sixth|First|Second)\s+Committee\b"),
    re.compile(r"(?:^|\s)\d{3,4}(?:st|nd|rd|th|let)\s+[Mm]eeting\s*[—–~\-]+\s*\d{1,2}\s+" + MONTHS + r"\s+19\d\d(?:\s+\d{1,4}\b)?"),
    re.compile(r"(?:^|\s)\d{3,4}\s+\d{1,3}(?:st|nd|rd|th)\s+plenary\s+me?\w{2,4}ing(?:\s+\d{3,4}\b)?", re.I),
    re.compile(r"(?:^|\s)\d{3,4}\s+[A-Z][a-z]+(?:-[a-z]+)?\s+Plenary\s+Meeting\b"),
    re.compile(r"(?:^|\s)\d{3,4}\s+\d{1,2}\s+" + MONTHS + r"\s+19\d\d\b(?!\s*,)"),
    re.compile(r"\s*\bPrinted\s+in\s+(?:France|Canada|Switzerland|the\s+Netherlands|U\.?S\.?A\.?|the\s+United\s+States(?:\s+of\s+America)?)\b\.?"),
    # the French half of the bilingual plenary's running head, in the English text: "23 septembre 1948"
    re.compile(r"(?:^|\s)\d{1,2}\s+(?:janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|d[ée]cembre)\s+19\d\d\b"),
    # the scanning library's stamp at the foot of a page, which hides the catchword after it from the rule that finds it
    re.compile(r"\s*Digiti[sz]ed\s+by\s+(?:the\s+)?Dag\s+Hammarskj\S{0,3}(?:ld)?(?:\s+Library\.?)?"),
    # the typist's date mark run into the line after it: "10/6 on. | The meeting rose at 5.45 p.m"
    re.compile(r"^\W*\d{1,2}\s*/\s*\d{1,2}\s+(?:[ap]\.?\s?m\.?|on\.)\s*\|?"),
]


def meeting_number(symbol: str) -> str | None:
    m = re.search(r"/(?:SR|PV)\.(\d+)", symbol or "")
    return m.group(1) if m else None


def strip_furniture(text: str, first_page: bool = False, record: bool = False, notes: list[str] | None = None,
                    number: str | None = None, printed: bool = False) -> tuple[str, list[str]]:
    """Remove running head lines and the catchword from one page of OCR text.

    Returns (body, removed_lines). The first page of a record has a masthead instead of
    a running head and is left alone here.
    """
    lines = text.splitlines()
    removed: list[str] = []
    if not first_page:
        # up to three leading non-empty lines, stopping at the first body line
        i, seen = 0, 0
        while i < len(lines) and seen < 3:
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            # (meeting records: the garbled symbol and folio, and a short line with the meeting's own number, "Hen AS 135" for
            # "E/CN.4/SR 135")
            def head(line: str) -> bool:
                return bool(len(line) <= 24 and (SYMBOL_HEAD_RE.match(line) or PAGE_LINE_RE.match(line))
                            or record and len(line) <= 30 and (any(r.match(line) for r in RECORD_TOP_RES)
                                                               or number and re.search(rf"(?<!\d){number}(?!\d)", line)
                                                               and (len(line.split()) <= 5 and not re.search(r"[a-z]{4,}", line)
                                                                    or len(line) <= 16 and len(line.split()) <= 3
                                                                    and not re.match(r"^\W*(?:Articles?|Paragraphs?|Part|Chapter|Section|Point|Annex|Item|Rule|Resolution)\b", line, re.I))))
            if head(line):
                removed.append(line)
                lines.pop(i)
                seen += 1
                continue
            # (debris of a few marks above the head, "eee" / "B/CN.4/5R. 308", "es ae" / "Ning deen 308": round 86)
            after = next((ln.strip() for ln in lines[i + 1:] if ln.strip()), "")
            if record and len(line) <= 6 and not re.search(r"[A-Za-z]{4}", line) and head(after):
                removed.append(line)
                lines.pop(i)
                seen += 1
                continue
            break
    filled = [k for k, ln in enumerate(lines) if ln.strip()]
    edge = set(filled[:4] + filled[-4:])
    edge2 = set(filled[:2] + filled[-2:])
    if record:
        # (the printer's line run into the last line of the text: "... embark on a trivial speech. Litho.in U.N.")
        lines = [re.sub(r"\s+Litho(?:ed)?[.\s]*[i1l]n\s+U\.?\s?N\.?\W{0,3}(?:\d{5}.{0,40})?$", "", ln) for ln in lines]
        emptied = set()
        for rx in INLINE_HEAD_RES:
            for k, ln in enumerate(lines):
                if rx.search(ln):
                    removed.extend(m.group(0).strip() for m in rx.finditer(ln))
                    lines[k] = rx.sub(" ", ln).rstrip()
                    if not lines[k].strip():
                        emptied.add(k)
        lines = [ln for k, ln in enumerate(lines) if k not in emptied]
        # a page number inside a word hyphenated across the page break: "para- _ 187 graph"
        lines = [re.sub(r"(?<=[a-z])-\s+[_|.\s]{0,4}\d{1,4}\s+(?=[a-z])", "", ln) for ln in lines]
    # the printer's job number at the foot of a page ("65-25443", "61-23698", the OCR's "65-25hh5", "5h..08378"): alone on one of
    # the last lines, or run onto the last line of text (round 82)
    # (also with four digits after the hyphen, "52-1878", or none, "5928355", "6123579 Ap.")
    job = r"(?<![\w/.-])[4-6][\dhk](?:\s?[-–~.]{1,2}\s?[\dOolIhkB]{4,5}|[\dOolIhkB]{5})(?![\w/-])(?:\s+[A-Za-z]{1,3}\.?)?"
    tail = [k for k, ln in enumerate(lines) if ln.strip()][-3:]
    for k in tail:
        if re.fullmatch(r"\W{0,3}" + job + r"\W{0,3}", lines[k].strip()):
            removed.append(lines[k].strip())
            lines[k] = ""
        elif k == tail[-1] and re.search(r"\s" + job + r"\W{0,3}$", lines[k]):
            removed.append(re.search(job + r"\W{0,3}$", lines[k]).group(0))
            lines[k] = re.sub(r"\s+" + job + r"\W{0,3}$", "", lines[k])
    for k in range(len(lines) - 1, -1, -1):
        t = lines[k].strip()
        if len(t) > 90:
            continue
        # (a page line alone, "page 155.", only near the top or the foot: in a column it can end a sentence that cites a page)
        # (a capitalised head, "Page 16", "Fage ly", lands mid-column in two-column pages; "page 155." in lower case can end a sentence)
        head = record and re.sub(r"^[\W_]+", "", t)[:1] in ("P", "F") and not t.rstrip().endswith(".")
        if any(r.match(t) for r in ANYWHERE_RES[:-1]) or ANYWHERE_RES[-1].match(t) and (k in edge or "/" in t or head) \
                or record and (any(r.match(t) for r in RECORD_RES) or not first_page and DATE_PAGE_RE.match(t)
                               or any(r.match(t) for r in EDGE_RES) and k in edge2
                               or any(r.match(t) for r in RECORD_FOOT_RES) and k in edge):
            removed.append(lines.pop(k).strip())
    if record:
        # lines of the printed page in the middle of a column (round 80): its number alone ("which had been conceived and
        # drafted in a" / "878" / "liberal and generous spirit"; not a year, nor a number in brackets), the record's own symbol
        # ("A/C,3/SR,1268"), the printer's "Litho m U.N." and job line ("77301~November 1958=-2,075")
        mid = [re.compile(r"^[\s._\-|]*(?!19\d\d)\d{3,4}[\s._\-|]*$" if printed else r"(?!)"),  # (the printed records only)
               re.compile(r"^\W{0,3}[AE]\s?/\s?[A-Z]{1,3}[.,]?\s?\d?\s?/\s?(?:SR|PV)[.,]\s?\d{1,4}\W{0,3}$"),
               re.compile(r"^\W{0,3}Litho(?:ed)?\W{0,3}(?:in|m|ln|1n|ir|i)?\W{0,3}U\.?\s?N\.?\W{0,3}[\w\-~=,.]{0,40}$"),
               re.compile(r"^\W{0,3}\d{5}\W{0,3}" + MONTHS + r"\s+19\d\d\W{0,4}[\d,.]{0,8}\W*$")]
        keep = []
        for ln in lines:
            if any(rx.match(ln.strip()) for rx in mid):
                removed.append(ln.strip())
            else:
                keep.append(ln)
        lines = keep
        _drop_footnotes(lines, removed, notes)
    else:
        _drop_doc_footnotes(lines, removed, notes)
    _drop_stamps(lines, removed)
    # a printed running head broken over two lines, the meeting and its date: "1259th meeting -" / "11 November 1963 249",
    # "145th plenary meeting" / "27 September 1948" (a date alone is text: "the period from 17 January 1946 to" / "15 July 1946.")
    if record:
        head = re.compile(r"^\W*\d{2,4}\W*\d{2,4}(?:st|nd|rd|th|let)\s+(?:[Pp]lenary\s+)?[Mm]e?\w{2,4}ing\W*\d{0,4}\W*$|"
                          r"^\W*\d{2,4}(?:st|nd|rd|th|let)\s+(?:[Pp]lenary\s+)?[Mm]e?\w{2,4}ing\W*\d{0,4}\W*$")
        date = re.compile(r"^\W*(?:\d{2,4}\s+)?\d{1,2}\s+" + MONTHS + r"\s+19\d\d\W*(?:\d{1,4}\W*)?$")
        drop = set()
        for k, ln in enumerate(lines):
            if head.match(ln.strip()):
                drop.add(k)
                for j in (k - 1, k + 1):
                    if 0 <= j < len(lines) and date.match(lines[j].strip()):
                        drop.add(j)
        removed.extend(lines[k].strip() for k in sorted(drop))
        lines = [ln for k, ln in enumerate(lines) if k not in drop]
    # a page number left next to the running head that was taken out of a column ("889" / "182nd plenary meeting")
    if record:
        lines = [ln for k, ln in enumerate(lines) if not (re.match(r"^\W*\d{2,4}\W*$", ln) and any(
            r.match(lines[j].strip()) for j in (k - 1, k + 1) if 0 <= j < len(lines) for r in ANYWHERE_RES[:4] + RECORD_RES[:1]))]
    # the catchword: last line that holds words (the stamps and speckle after it are a line or two of debris)
    j = len(lines) - 1
    while j >= 0 and len(re.sub(r"[^A-Za-z]", "", lines[j])) < 3:
        j -= 1
    if j >= 0 and CATCHWORD_RE.match(lines[j]):
        removed.extend(l.strip() for l in lines[j:] if l.strip())
        del lines[j:]
    elif j >= 0 and record:
        # (meeting records, round 89: the catchword behind a little debris, "| _ 4 ~ “/Rise BOWIE |", "» /The CHAIRMAN", or run
        # onto the page's last line of text, "... rejected by 4 votes to 3 /The CHAIRMAN", "or /with requests")
        m = re.search(r"(?:^[\W\d_\s]{0,12}|\s)[“\"'‘]?/\s?(?!(?:Add|Rev|Corr|Sub|SR|AC|PV|Ac|L|C)\b)[A-Za-z][^/()]{0,40}$", lines[j])
        if m and len(re.findall(r"[A-Za-z]+", lines[j][m.start():])) <= 5:
            removed.append(lines[j][m.start():].strip())
            lines[j] = lines[j][:m.start()].rstrip()
            removed.extend(l.strip() for l in lines[j + 1:] if l.strip())
            del lines[j + 1:]
            if not re.search(r"[A-Za-z]{2}", lines[j]):
                del lines[j]
    return "\n".join(lines), removed


# The foot of a page of a meeting record carries footnotes: "1See Annex 17, page 296.", "1/ See Official Records of the General
# Assembly, Fifteenth Session, / Annexes, agenda item 35, document A/4636.", "* Indicates the item number on the agenda." In the
# printed records they sit at the foot of the left column, i.e. in the middle of the text the OCR reads, and were found spliced
# into a sentence by the segmentation audit on page images (October 2026). A marker line takes up to two lines after it that read
# as citation text.
FOOTNOTE_START_RE = re.compile(r"^\s*(?:\W{0,3}\d{1,2}\s*[./]?|\W{0,2}[A-Za-z]{1,3}\s)\s*See\b|^\s*\d{1,2}\s*/\s+[A-Z]|"
                               r"^\s*\*\s*(?:Indicates|See\b|Voir|Ibid|Articles?\b|Document|Resolution|The revised|Subsequently)")
# More markers and openers the audits of rounds 73-76 found missed: "*" and "+" and the apostrophe the OCR makes of a marker, a digit
# with no space after it ("1The omission was rectified in document A/C.3/L.337/" / "Corr.2."), and the footnotes that begin with no
# "See": "Resumed from", "Subsequently circulated", "Decision taken at", "Official Records", "Ibid.", "This document reads", "Document
# A/C.3/L.237 was submitted", and the Third Committee's 1948 "Article 24 of the draft universal declaration of human rights (A/777)",
# which the bilingual page sets in the middle of the English column with no marker at all.
FOOTNOTE_OPENERS = (r"(?:See\b|Ibid\b|Resumed\s+from|Subsequently|Documents?\s+(?:A|E)/|Official\s+Records|Decision\s+taken|This\s+document|"
                    r"The\s+omission\s+was\s+rectified|United\s+Nations\s+publication|Indicates|Article\s+\d{1,2}\s+of\s+the\s+draft\s+universal)")
FOOTNOTE_MARKED_RE = re.compile(rf"^\s*[^\w\s]{{0,2}}\s?(?:\d{{1,2}}|[*+†'‘’]|[IJl]\s?/)\s*[/.]?\s*{FOOTNOTE_OPENERS}")
FOOTNOTE_UNMARKED_RE = re.compile(r"^\s*[^\w\s]{0,3}\s*Article\s+\d{1,2}\s+of\s+the\s+draft\s+universal\s+declaration\s+of\s+human")
FOOTNOTE_CONT_RE = re.compile(r"\b(?:Session|Supplement|Annex(?:es)?|Official|Plenary|Meetings?|Records?|document|paras?|pages?|vol|Sales|"
                              r"No|Council|Assembly|Committee|meeting|publication|Yearbook|chap|agenda|item)\b|^\s*\d|\d{3}|^\s*(?:Corr|Add|Rev|Supp)\b", re.I)


def _drop_footnotes(lines: list[str], removed: list[str], notes: list[str] | None = None) -> None:
    k = 0
    while k < len(lines):
        # (not among the first lines of a page: a footnote is never at the head)
        if k >= 2 and lines[k].strip() and (FOOTNOTE_START_RE.match(lines[k]) or FOOTNOTE_MARKED_RE.match(lines[k])
                                            or FOOTNOTE_UNMARKED_RE.match(lines[k])):
            end = k + 1
            unmarked = bool(FOOTNOTE_UNMARKED_RE.match(lines[k]))
            # (a continuation starts with a capital or a digit, or follows a hyphenated line; the text that goes on after a footnote
            # at the foot of a column goes on from the sentence it interrupted, in lower case. A footnote can run to four lines, and
            # a short line that ends the sentence after a line that does not ("rights (A/777)." after "...of human") is its end)
            while end < len(lines) and end < k + 5 and not re.search(r"\.\W{0,3}$", lines[end - 1].strip()) \
                    and lines[end].strip() and not (FOOTNOTE_START_RE.match(lines[end]) or FOOTNOTE_MARKED_RE.match(lines[end])) \
                    and (FOOTNOTE_CONT_RE.search(lines[end]) and (re.match(r"^\s*[A-Z0-9(]", lines[end]) or lines[end - 1].rstrip().endswith("-"))
                         or re.search(r"[\-/]$", lines[end - 1].rstrip()) and len(lines[end].strip()) <= 45
                         or unmarked and len(lines[end].strip()) <= 45 and re.search(r"\.\W{0,3}$", lines[end].strip())):
                end += 1
            removed.extend(l.strip() for l in lines[k:end] if l.strip())
            if notes is not None:
                # (kept apart: segment.py gives it a segment of its own; a word hyphenated at a line end is joined, as in the body)
                notes.append(re.sub(r"([a-z])-\s+(?=[a-z])", r"\1", " ".join(l.strip() for l in lines[k:end] if l.strip())))
            del lines[k:end]
            continue
        k += 1


# A document's footnotes (round 83): the marked ones at the foot of the page ("1/ Official Records of the Economic and Social
# Council, eighteenth session, Supplement No. 7, annex I (E/2573)"), and the sessions' reports' notes of sources, which close a
# column ("22 E/CN.4/618, E/CN.4/SR.236 and 237, E/CN.4/L.10/Add.6."; "23 E/CN.4/AC.14/2, ..., E/" / "CN.4/872, ..."); not a
# numbered paragraph ("12. Official Records show ...": a full stop after the number)
DOC_NOTE_MARKED_RE = re.compile(r"^\s*[^\w\s]{0,2}\s?(?:\d{1,2}\s?/|[*+†])\s*\S")
DOC_NOTE_SOURCE_RE = re.compile(r"^\s*\d{1,3}\s+[ABE£]\s?/\s?[A-Z]")
DOC_NOTE_CONT_RE = re.compile(r"^\s*(?:[A-Z]{1,3}\.?\d?/|CN\.|SR\.|Corr|Add|Rev|\d{1,4}\s*(?:,|and\b)|[a-z]|\(?[A-Z][a-z]+\s+(?:session|Records|Supplement)|E/|A/)")


DOC_NOTE_MARK = "\x00FOOTNOTE "


def _drop_doc_footnotes(lines: list[str], removed: list[str], notes: list[str] | None = None) -> None:
    if notes is None:
        return  # (only for the segmenter, which reads the mark; the OCR's selection and the votes read the page as it is)
    filled = [k for k, ln in enumerate(lines) if ln.strip()]
    foot = set(filled[-6:])
    k = 2
    while k < len(lines):
        ln = lines[k]
        marked = k in foot and DOC_NOTE_MARKED_RE.match(ln) and FOOTNOTE_CONT_RE.search(ln) and not re.match(r"^\s*\d{1,2}\s*[.)]", ln)
        source = DOC_NOTE_SOURCE_RE.match(ln) and len(re.findall(r"[ABE£]\s?/\s?[A-Z]", ln)) >= 1 and len(re.findall(r"\b[a-z]{4,}\b", ln)) <= 3
        if not (marked or source):
            k += 1
            continue
        end = k + 1
        while end < len(lines) and end < k + 5 and lines[end].strip() and not (DOC_NOTE_MARKED_RE.match(lines[end]) or DOC_NOTE_SOURCE_RE.match(lines[end])) \
                and (source and DOC_NOTE_CONT_RE.match(lines[end]) and len(re.findall(r"\b[a-z]{4,}\b", lines[end])) <= 3
                     or marked and end in foot and (FOOTNOTE_CONT_RE.search(lines[end]) or re.search(r"[\-/,]$", lines[end - 1].rstrip())
                                                     or re.match(r"^\s*[a-z]", lines[end]))):
            end += 1
        removed.extend(l.strip() for l in lines[k:end] if l.strip())
        # (left where it stood, as one line the segmenter makes a footnote of: the report annexes' hand-read anchors can name it)
        note = re.sub(r"([a-z])-\s+(?=[a-z])", r"\1", " ".join(l.strip() for l in lines[k:end] if l.strip()))
        lines[k:end] = [DOC_NOTE_MARK + note]
        foot = {i - (end - k - 1) if i > k else i for i in foot}
        k += 1


# The archive's stamp on a page ("RECEIVED" / "MAY 14 1948" / "UNITED NATIONS" / "ARCHIVES", "|RECEIVED| ~ oa) gg DEC 15 1948 UNITED
# NATIONS ; RCHIVES"), as the OCR read it (round 83): a short line with RECEIVED or ARCHIVES alone (not "HAVING RECEIVED the
# report", "COMMUNICATION RECEIVED FROM CANADA") and the short lines around it with no word in lower case; or the stamp run onto
# the end of a line of text ("... racial discrimination. RECEIVED 2:3 OCT 1947")
STAMP_ANCHOR_RE = re.compile(r"^[\W\d_]{0,6}\|?(?:RECEIVED|[A-Z]?RCHIVES|UNITED\s+NATI\S{2,3}\s+ARCHIVES)\|?(?![\w ]*\b(?:FROM|THE|BY)\b)[\W\w]{0,24}$")
# (the stamp's other lines: a date, its own words, or debris of a few letters; not a heading in capitals, "ERRATUM")
STAMP_PART_RE = re.compile(r"^(?:\W{0,4}(?:[A-Z][a-z]{2}|[A-Z]{3})\.?\s*[\d\s?il]{1,3}\W{0,3}[\d?il]{2,4}\W*|"
                           r"[\W\d]*(?:UNITED|NATI\S{2,3}|ARCHIVES|[A-Z]?RCHIVES|RECEIVED|LIBRARY|INDEX)\b[^a-z]{0,20}|[\W\d_]{0,6}[A-Za-z]{0,3}[\W\d_]{0,6})$")
STAMP_TAIL_RE = re.compile(r"(?<=[.;:,\"”])\s+\|?RECEIVED\|?\s*(?:[\d:\s]{1,6}[A-Z]{3}\.?\s*[\d\s]{4,5}|[A-Z]{3}\s*[\d\s]{1,4}\s*[\dil]{4})?\s*$")


def _drop_stamps(lines: list[str], removed: list[str]) -> None:
    drop = set()
    for k, ln in enumerate(lines):
        t = ln.strip()
        if t and len(t) <= 30 and STAMP_ANCHOR_RE.match(t) and not re.search(r"\b[a-z]{4,}\b", t):
            drop.add(k)
            for j in list(range(k - 3, k)) + list(range(k + 1, k + 4)):
                if 0 <= j < len(lines) and lines[j].strip() and STAMP_PART_RE.match(lines[j].strip()) \
                        and not re.search(r"\b(?:ARTICLE|CHAPTER|PART|SECTION|ANNEX|COMMISSION|COMMITTEE|COUNCIL|ASSEMBLY|DRAFT|ORIGINAL|Distr|LIMITED|RESTRICTED)\b", lines[j], re.I) \
                        and not re.fullmatch(r"\W*(?:AND|ET|ECONOMIC|SOCIAL|CONSEIL|ECONOMIQUE|GENERAL|ASSEMBLEE|NATIONS\s+UNIES)\W*", lines[j].strip(), re.I):
                    drop.add(j)
        m = STAMP_TAIL_RE.search(ln)
        if m and k not in drop:
            removed.append(m.group(0).strip())
            lines[k] = ln[:m.start()]
    for k in sorted(drop, reverse=True):
        removed.append(lines[k].strip())
        del lines[k]


# English only, for the bilingual printed Official Records (1948): Tesseract's layout
# mode keeps the English and French columns apart but outputs both, block by block.
EN_WORDS = set("the of and to that in was be which would it he had not for by with as is on his "
               "should have were an this from at or they their been its".split())
FR_WORDS = set("le la les des du et que qui en au aux est une un pour par dans sur pas il elle "
               "son sa ses ce cette ne se leur été être avait sont été".split())
ACCENTS = re.compile(r"[éèêàâçîôûù]")


def line_evidence(line: str) -> tuple[int, int]:
    """A line's English and French function words (accents and French titles count for French)."""
    # function words count only in lower-case tokens: names in capitals ("AUJAY DE LA DURE", "ESTRADA DE LA HOZ")
    # and the delegation in brackets are not French text
    plain = re.sub(r"\([^()]{0,100}\)", " ", line)
    words = [w for w in re.findall(r"[A-Za-zàâçéèêëîïôûùüÿœÀ-Ý']+", plain) if w == w.lower()]
    en = sum(w in EN_WORDS for w in words)
    # accents count only in lower-case words: names ("JIMÉNEZ DE ARÉCHAGA") are not French text
    lower_words = " ".join(w for w in re.findall(r"\S+", line) if w == w.lower())
    fr = sum(w in FR_WORDS for w in words) + min(len(ACCENTS.findall(lower_words)), 2)
    if re.match(r"^\W{0,3}(?:M\.|Mme|Mlle)\s+[A-Z]", line):  # French titles: "M. Baroody", "Mme Corbet"
        fr += 3
    return en, fr


def line_language(line: str) -> str | None:
    en, fr = line_evidence(line)
    return "en" if en > fr else "fr" if fr > en else None


def english_only(text: str) -> tuple[str, int]:
    """Drop the French lines of a two-column page. Returns (text, lines dropped).

    Each line is labelled by its function words (and accents, for French). Lines with no
    evidence take the label of the nearest labelled line before them, since the columns
    come out as runs of lines.
    """
    lines = text.splitlines()
    labels = [line_language(line) for line in lines]
    last = "en"
    for i, lab in enumerate(labels):
        if lab is None:
            labels[i] = last
        else:
            last = lab
    # (a document's footnote, marked where it stood, is judged on its own words, not by its neighbours': round 83)
    for i, ln in enumerate(lines):
        if ln.startswith(DOC_NOTE_MARK):
            note = ln[len(DOC_NOTE_MARK):]
            words = [w for w in re.findall(r"[A-Za-zàâçéèêëîïôûùüÿœÀ-Ý']+", note) if w == w.lower()]
            fr = sum(w in FR_WORDS for w in words) + min(len(ACCENTS.findall(note)), 2)
            labels[i] = "fr" if fr > sum(w in EN_WORDS for w in words) or re.match(r"^\W*\d{0,2}\s*\W?\s*Voir\b", note) else "en"
    kept = [ln for ln, lab in zip(lines, labels) if lab == "en"]
    return "\n".join(kept), len(lines) - len(kept)


# French on a page not marked two-column (v2, 28 Oct 2026): a printed rule between the columns hides the gutter from
# ocr_select.two_column, a French page faces an English one (E/CN.4/21's annexes), a 1947 sheet prints the French under the
# English. A run of French lines (with the lines without evidence between them) goes when it has five French lines and 40
# French function words, or 20 when it is not a quotation: A/3525's statement in French, opened in the English line before,
# stays, and so do the short runs (A/C.3/L.1417's corrections quoting the French text)
QUOTE_OPEN_RE = re.compile(r"^\W{0,3}[\"“«]")


def _quote_left_open(line: str) -> bool:
    return line.count('"') % 2 == 1 or line.count("“") > line.count("”") or line.count("«") > line.count("»")


def drop_french_runs(text: str) -> tuple[str, int]:
    """Drop the long runs of French lines of a page. Returns (text, lines dropped)."""
    lines = text.splitlines()
    ev = [line_evidence(ln) for ln in lines]
    lab = ["en" if en > fr else "fr" if fr > en else None for en, fr in ev]
    drop: set[int] = set()
    i = 0
    while i < len(lines):
        if lab[i] != "fr":
            i += 1
            continue
        j = last = i
        while j + 1 < len(lines) and lab[j + 1] != "en":
            j += 1
            if lab[j] == "fr":
                last = j
        n = sum(lab[k] == "fr" for k in range(i, last + 1))
        fr = sum(ev[k][1] for k in range(i, last + 1))
        quoted = bool(QUOTE_OPEN_RE.match(lines[i])) or i > 0 and _quote_left_open(lines[i - 1])
        if n >= 5 and (fr >= 40 or fr >= 20 and not quoted):
            drop.update(range(i, last + 1))
        i = last + 1
    if drop and "en" not in lab:  # a French page: its headings and furniture go too ("ARTICLE 6" above E/CN.4/21's p. 12)
        drop = set(range(len(lines)))
    return "\n".join(ln for k, ln in enumerate(lines) if k not in drop), len(drop)
