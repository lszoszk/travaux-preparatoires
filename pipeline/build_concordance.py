#!/usr/bin/env python3
"""Draft-to-final article concordance for the UDHR, from the UN texts themselves.

The drafting bodies numbered the Declaration differently at each stage. For each stage
document, its draft articles are read from the OCR'd text and matched to the final
articles of A/RES/217(III) by text similarity. The result, with the page of each draft
article, goes to data/concordance/drafts.csv. No compilation is used.

A document can hold several drafts (the Declaration and a draft Covenant in E/800; the
Secretariat outline and later drafts in E/CN.4/21), each a run of articles numbered from
1. The run that matches the final Declaration best is taken as the stage's text.

Usage: python3 pipeline/build_concordance.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import safe_name  # noqa: E402
from normalize import english_only, strip_furniture  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OCR = ROOT / "data" / "ocr"
OUT = ROOT / "data" / "concordance" / "drafts.csv"
# draft texts are UN OCR text: kept with the segments (gitignored until publication is cleared)
DRAFT_TEXTS = ROOT / "data" / "segments" / "_draft_texts.json"
FINAL = "A/RES/217(III)"
# stage id -> the UN document that fixes that stage's numbering (in drafting order)
STAGES = [
    ("secretariat_outline", "E/CN.4/AC.1/3"),
    ("cassin_draft", "E/CN.4/AC.1/W.2/Rev.2"),  # the Drafting Committee's working text, June 1947
    ("drafting_committee_1", "E/CN.4/21"),
    ("geneva_draft", "E/600"),
    ("drafting_committee_2", "E/CN.4/95"),
    ("chr_3", "E/800"),
]
# a stage whose articles are one annex of a longer document: E/CN.4/21 annex F holds the Drafting
# Committee's articles for a declaration (its annex A is the Secretariat's outline again)
STAGE_PAGES = {"drafting_committee_1": range(73, 82)}
# "Article 16" alone on its line, or opening it ("Article 16. 1. Individual freedom of …"),
# with the OCR's usual damage: "Article 2k" (24), "Article 2$" (25), "Article. 29",
# "Article 2.1." (21), and joint headings "Articles 17 and 18". A reference in running text
# ("article 16 of the Covenant") breaks the numbering and is dropped by the run logic.
DIG = r"[\dIlOkh^$Sg?]"
HEAD_RE = re.compile(rf"^\W{{0,3}}[A!4][Rr,][Tt]\S{{0,3}}[Cc][Ll1I][Ee](?P<pl>[sS])?[.,']*\s+(?P<a>{DIG}(?:[.,]?{DIG})?)(?!{DIG})"
                     rf"(?:\s*[.,]?[\s_]*and[\s_]+(?P<b>{DIG}(?:[.,]?{DIG})?)(?!{DIG}))?\s*[.:*,]?\s*(?P<rest>(?!\s*[a-z]).*)$")
FINAL_TEXT = ROOT / "data" / "concordance" / "udhr_final.json"
# where a draft article's text ends and the body's notes on it begin ("(Note: The representative
# of the Soviet Union proposed ...)", OCR "(Tote:")
NOTE_RE = re.compile(r"\(\s*[NTMHRL][oa]te\b|\b(?:Note|Comments?|Observations?)\s*:|\bFootnote|"
                     r"\bAlternative\s+te\S*\s+(?:submitted|suggested|proposed)|\bII\s*\.\s+\S{2,8}\s+submitted\s+by|\b(?:[Tt]ext|amendment)\s+(?:was\s+)?(?:submitted|suggested|proposed)\s+by\b|"
                     r"\bThe\s+(?:representative|delegation|Representative|Delegation)s?\s+(?:of|for)\b|"
                     r"\b(?:proposed|suggested)\s+(?:that\s+)?(?:the\s+following|to\s+(?:replace|substitute|add|delete|insert))|"
                     # E/CN.4/95's note on the articles it did not revise, which also heads the next article: "(The Drafting
                     # Committee did not have time to consider this Article)"
                     r"\(?\s*The\s+Drafting\s+Committee\s+did\s+not\s+h\w+\s+(?:the\s+)?time\b|"
                     # the next article's heading in capitals, too damaged for the run of headings ("ARPICIE 37", "ARTICTE 38")
                     r"\bA[RP][A-Z1I]{3,6}\s+\d{1,2}\b")
# an editorial note opening a draft article, not its text: "(The Drafting Committee did not have the time to consider
# this Article)", "(Geneva text)", "(formerly Article 8)"
LEAD_NOTE_RE = re.compile(r"^\(?\s*(?:The\s+Drafting\s+Committee\s+did\s+not\s+h\w+\s+(?:the\s+)?time\s+to\s+consider\s+this\s+Article|"
                          r"Geneva\s+te[xr]t|formerly\s+Article\s+\S{1,4})\s*\)?\s*")


def cut_notes(text: str) -> str:
    """A draft article's own text: up to the first note, alternative text or proposal about it
    (not one that opens the text, as in E/800's "I. Text submitted by ...")."""
    text = re.sub(r"^[\W_]*?(?=\(?\d|[A-Z])", "", " ".join(text.split()))  # ") (1. Every one ..." -> "(1. Every one ..."
    while (lead := LEAD_NOTE_RE.match(text)) and lead.end():
        text = text[lead.end():]
    m = next((m for m in NOTE_RE.finditer(text) if m.start() >= 40), None)
    return (text[:m.start()] if m else text).strip()
# A heading alone on a short line, however damaged: "Article ,9", "Article ih" (14), "Article^ l6",
# "Article-M20", "Article;-£3" (23), "'Article'-lg-" (19). A stray letter before the number is tried
# with and without it; the run's expected number settles which reading is right.
SHORT_HEAD_RE = re.compile(r"^\W{0,3}[A!4][Rr][Tt][Il1i][Cc][Ll1I][Ee][^\w£&$^?]{0,4}(?P<tok>[A-Z£]{0,2}[\dIlLOkh^$Sgi£&j?]{1,2})\W{0,4}$")
FORMERLY_RE = re.compile(rf"\(formerly\s+Article\s+(?P<f>{DIG}{{1,2}})\)", re.I)
# What each OCR character can stand for; ambiguous ones ("Ig" is 15, not 19) are settled by
# the sequence: a heading takes the reading its run expects.
_CAND = {"I": "1", "l": "1", "L": "1", "O": "0", "k": "4", "h": "4", "^": "4", "$": "5", "S": "58", "g": "95", "?": "7",
         "i": "1", "£": "2", "&": "8", "j": "0123456789"}


def ocr_numbers(raw: str | None, question_is_7: bool = True) -> set[int]:
    """Every number an OCR'd article number can be."""
    if not raw or (not question_is_7 and "?" in raw):
        return set()
    out = {""}
    for ch in re.sub(r"[.,]", "", raw):
        opts = ch if ch.isdigit() else _CAND.get(ch, "")
        out = {o + d for o in out for d in opts}
    return {int(n) for n in out if n and 0 < int(n) <= 60}


def ocr_number(raw: str | None, question_is_7: bool = True) -> int | None:
    """The number, when the reading is unambiguous."""
    nums = ocr_numbers(raw, question_is_7)
    return next(iter(nums)) if len(nums) == 1 else None


FR_WORDS = {"le", "la", "les", "des", "du", "et", "est", "une", "qui", "pour", "par", "dans", "aux", "sont", "ne", "pas", "il", "sur"}
EN_WORDS = {"the", "of", "and", "to", "is", "in", "shall", "be", "his", "has", "or", "by", "any", "with"}


def is_french(text: str) -> bool:
    w = re.findall(r"[a-zà-ÿ']+", text.lower())
    return sum(x in FR_WORDS for x in w) > sum(x in EN_WORDS for x in w)


def pages_text(symbol: str) -> list[tuple[int, str]]:
    """(page, English line) for a document's voted OCR text. A page in French is left out when the document has English
    pages: E/CN.4/AC.1/3 gives articles 1-5 in English on p. 2 and in French on p. 3, and the run of headings took the
    French ones."""
    import json
    d = OCR / safe_name(symbol)
    sel = json.loads((d / "selection.json").read_text()) if (d / "selection.json").exists() else {}
    pages = []
    for p in sorted((d / "vote").glob("page-*.txt")):
        body, _ = strip_furniture(p.read_text(encoding="utf-8"), first_page=p.name == "page-001.txt")
        if sel.get(p.name, {}).get("two_column"):
            body, _ = english_only(body)
        pages.append((int(p.stem.split("-")[1]), body))
    if any(not is_french(b) for _, b in pages):
        pages = [(n, b) for n, b in pages if not is_french(b)]
    return [(n, ln) for n, b in pages for ln in b.splitlines() if ln.strip()]


def article_runs(lines: list[tuple[int, str]], question_is_7: bool = True, cap: int | None = 1200) -> list[list[dict]]:
    """Runs of consecutive article headings numbered 1, 2, 3 ... with the text under each."""
    heads = []
    for i, (page, ln) in enumerate(lines):
        m = HEAD_RE.match(ln.strip())
        short = SHORT_HEAD_RE.match(ln.strip()) if not m and len(ln.strip()) <= 20 else None
        if short:
            tok = short.group("tok")
            cands = set().union(*(ocr_numbers(tok[k:], question_is_7) for k in range(min(3, len(tok)))))
            if cands:
                heads.append((i, cands, page, "", None))
            continue
        if m:
            a = ocr_numbers(m.group("a"), question_is_7)
            if a:
                f = FORMERLY_RE.search(ln)
                heads.append((i, a, page, m.group("rest"), ocr_number(f.group("f")) if f else None))
                b = ocr_numbers(m.group("b"), question_is_7)
                if b:  # "Articles 17 and 18": one text for both; only the first is matched
                    heads.append((i, b, page, m.group("rest"), "joint"))
    runs, run = [], []
    for k, (i, cands, page, rest, formerly) in enumerate(heads):
        expected = run[-1]["n"] + 1 if run else 1
        if expected in cands:
            n = expected
        elif len(cands) == 1:
            n = next(iter(cands))
        else:
            continue  # ambiguous and not what the run expects
        nxt = next((h[0] for h in heads[k + 1:] if h[0] > i), None)
        end = nxt if nxt is not None else min(len(lines), i + 40)
        joint = formerly == "joint"
        art = {"n": n, "page": page, "formerly": None if joint else formerly, "joint": joint,
               "text": (rest + " " + " ".join(ln for _, ln in lines[i + 1:end]))[:cap]}
        if run and n == run[-1]["n"] + 1:
            run.append(art)
        elif n == 1:
            if len(run) >= 5:
                runs.append(run)
            run = [art]
        elif run and n > run[-1]["n"] + 1 and n <= run[-1]["n"] + 5:  # OCR-missed headings
            run.append(art)
    if len(run) >= 5:
        runs.append(run)
    return runs


def match(text: str, finals: dict[int, str]) -> tuple[int | None, float, float]:
    scores = sorted(((fuzz.token_set_ratio(text[:400].lower(), f[:400].lower()), n) for n, f in finals.items()), reverse=True)
    best, runner = scores[0], scores[1] if len(scores) > 1 else (0, None)
    return best[1], best[0], best[0] - runner[0]


def align(A: list[dict], B: list[dict], floor: float = 50) -> list[tuple[int, int, float]]:
    """Order-preserving alignment of two stages' articles by text similarity: (i, j, similarity)
    pairs maximising the total similarity above `floor`. Drafts mostly keep their order from one
    stage to the next, and a text is far closer to its next version than to the final one."""
    S = [[fuzz.token_set_ratio(a["text"][:400].lower(), b["text"][:400].lower()) for b in B] for a in A]
    n, m = len(A), len(B)
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = max(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1] + S[i - 1][j - 1] - floor)
    pairs, i, j = [], n, m
    while i and j:
        if S[i - 1][j - 1] > floor and dp[i][j] == dp[i - 1][j - 1] + S[i - 1][j - 1] - floor:
            pairs.append((i - 1, j - 1, S[i - 1][j - 1]))
            i, j = i - 1, j - 1
        elif dp[i][j] == dp[i - 1][j]:
            i -= 1
        else:
            j -= 1
    return pairs[::-1]


CHAIN_MIN = 60  # similarity to the next stage's article needed to inherit its final number


def best_run(lines: list[tuple[int, str]], finals: dict[int, str]):
    # "?" is often a misread 7 ("Articles 1? and 18"), but elsewhere it breaks a run: try
    # both readings and keep the one whose best run matches more articles
    best = None
    for q7 in (True, False):
        for run in article_runs(lines, q7):
            ms = [match(a["text"], finals) for a in run]
            good = sum(1 for m in ms if m[1] >= 55 and m[2] >= 5)
            cand = (good, sum(m[1] for m in ms) / len(ms), run, ms)
            if best is None or cand[:2] > best[:2]:
                best = cand
    return best


def main() -> int:
    # The final text as the UN publishes it (A/RES/217(III)); the OCR of the printed
    # resolution loses headings, which shifts the matches.
    import json
    finals = {int(k): v for k, v in json.loads(FINAL_TEXT.read_text())["articles"].items()}
    print(f"final text: {len(finals)} articles ({FINAL}, from {FINAL_TEXT.name})", file=sys.stderr)
    if len(finals) < 25:
        print("  too few final articles found; stopping", file=sys.stderr)
        return 1
    symbol_of = dict(STAGES)
    order = [st for st, _ in STAGES]
    runs: dict[str, list[dict]] = {}
    direct: dict[str, dict[int, tuple]] = {}
    for stage, symbol in STAGES:
        best = best_run([(pg, ln) for pg, ln in pages_text(symbol) if pg in STAGE_PAGES.get(stage, range(1, 10000))], finals)
        if best is None:
            print(f"  {stage} ({symbol}): no article run found", file=sys.stderr)
            continue
        _, mean, run, ms = best
        for a in run:
            a["text"] = cut_notes(a["text"])
        runs[stage] = run
        direct[stage] = {a["n"]: m for a, m in zip(run, ms) if not a.get("joint")}  # a joint heading's text belongs to its first article
        print(f"  {stage} ({symbol}): run of {len(run)} articles, mean similarity to the final text {mean:.0f}", file=sys.stderr)

    # Resolve from the last stage back: each draft article takes the final number of its own
    # closest final article, or of the next stage's article it continues, whichever text is closer.
    resolved: dict[str, dict[int, dict]] = {}
    for k in range(len(order) - 1, -1, -1):
        stage = order[k]
        if stage not in runs:
            continue
        symbol, run = symbol_of[stage], runs[stage]
        chain = {}
        nxt = next((st for st in order[k + 1:] if st in runs), None)
        if nxt:
            for i, j, sim in align(run, runs[nxt]):
                b = runs[nxt][j]["n"]
                r = resolved[nxt].get(b)
                if r and r["final_article"] and sim >= CHAIN_MIN:
                    chain[run[i]["n"]] = (int(r["final_article"]), sim, b)
            # an article that moved (E/CN.4/95 art. 2 became E/800 art. 27): out of order, so the
            # alignment skips it; take it when one next-stage text is clearly its continuation
            for a in run:
                if a["n"] in chain or a.get("joint"):
                    continue
                sims = sorted(((fuzz.token_set_ratio(a["text"][:400].lower(), b["text"][:400].lower()), b["n"])
                               for b in runs[nxt]), reverse=True)
                (best, b), runner = sims[0], sims[1][0] if len(sims) > 1 else 0
                r = resolved[nxt].get(b)
                if best >= 75 and best - runner >= 10 and r and r["final_article"]:
                    chain[a["n"]] = (int(r["final_article"]), best, b)
        mapped: dict[int, dict] = {}
        n_direct = n_chain = 0
        for a in run:
            base = {"instrument": "UDHR", "stage": stage, "stage_symbol": symbol, "draft_article": a["n"],
                    "source_pinpoint": f"p. {a['page']}"}
            final, score, margin = direct[stage].get(a["n"], (None, 0, 0))
            ok = final is not None and score >= 55 and margin >= 5
            c = chain.get(a["n"])
            if c and (not ok or c[1] >= score or c[0] == final):
                note = f"continues {symbol_of[nxt]} article {c[2]} (text similarity {c[1]:.0f})"
                if ok and c[0] == final:
                    note += f"; its own text matches final article {final} (similarity {score:.0f})"
                elif ok:
                    note += f"; its own text is nearest final article {final} (similarity {score:.0f})"
                mapped[a["n"]] = {**base, "final_article": c[0], "note": note, "_score": c[1]}
                n_chain += 1
            else:
                mapped[a["n"]] = {**base, "final_article": final if ok else "", "_score": score,
                                  "note": f"text similarity {score:.0f} (margin {margin:.0f})" + ("" if ok else "; no clear match")}
                n_direct += ok
        # Several drafts of one stage on one final article: articles were merged, but a short
        # final text ("Everyone has the right to life, liberty and security of person") also
        # attracts weak matches. Keep the closest, and a second only if it is close too.
        by_final: dict[int, list[int]] = {}
        for n, r in mapped.items():
            if r["final_article"]:
                by_final.setdefault(int(r["final_article"]), []).append(n)
        for fin, ns in by_final.items():
            ns.sort(key=lambda n: -mapped[n]["_score"])
            for rank, n in enumerate(ns):
                if rank >= 2 or (rank == 1 and mapped[n]["_score"] < 70):
                    mapped[n]["note"] += f"; set aside: draft article {ns[0]} is closer to final article {fin}"
                    mapped[n]["final_article"] = ""
        # Fill a gap only where it is unambiguous: between two matched drafts k1 -> f1 and
        # k2 -> f2 with k2 - k1 == f2 - f1, the drafts in between map one-to-one in order
        # (E/800: 13 -> 15 and 16 -> 18 give 14 -> 16 and 15 -> 17).
        known = sorted((n, int(r["final_article"])) for n, r in mapped.items() if r["final_article"])
        inferred = 0
        for (k1, f1), (k2, f2) in zip(known, known[1:]):
            if k2 - k1 == f2 - f1 and k2 - k1 > 1:
                for n in range(k1 + 1, k2):
                    # not where the draft's own text points elsewhere: articles also moved
                    own, own_score, _ = direct[stage].get(n, (None, 0, 0))
                    if own is not None and own_score >= 45 and own != f1 + (n - k1):
                        continue
                    if n not in mapped or not mapped[n]["final_article"]:
                        mapped[n] = {"instrument": "UDHR", "stage": stage, "stage_symbol": symbol, "draft_article": n,
                                     "final_article": f1 + (n - k1), "source_pinpoint": mapped.get(n, {}).get("source_pinpoint", ""),
                                     "note": f"inferred from the neighbouring articles {k1} -> {f1} and {k2} -> {f2}"}
                        inferred += 1
        resolved[stage] = mapped
        print(f"  {stage}: {n_direct} by own text, {n_chain} through {symbol_of.get(nxt, '-')}, {inferred} inferred, "
              f"{sum(1 for r in mapped.values() if not r['final_article'])} unmatched", file=sys.stderr)

    # "Article 5 (formerly Article 8)": the document itself states the previous stage's number.
    # A stated correspondence outranks a text match or an inference for the same draft number.
    n_formerly = 0
    for k, stage in enumerate(order[1:], 1):
        prev_stage = order[k - 1]
        for a in runs.get(stage, []):
            r = resolved[stage].get(a["n"])
            if a.get("formerly") and r and r["final_article"] and prev_stage in resolved:
                resolved[prev_stage][a["formerly"]] = {
                    "instrument": "UDHR", "stage": prev_stage, "stage_symbol": symbol_of[prev_stage],
                    "draft_article": a["formerly"], "final_article": r["final_article"],
                    "source_pinpoint": f"{symbol_of[stage]} {r['source_pinpoint']}",
                    "note": f"stated in {symbol_of[stage]}: article {a['n']} (formerly article {a['formerly']})"}
                n_formerly += 1
    print(f"  'formerly' notes used: {n_formerly}", file=sys.stderr)
    rows = [resolved[st][n] for st in order if st in resolved for n in sorted(resolved[st])]
    draft_texts = [{"stage": st, "stage_symbol": symbol_of[st], "draft_article": a["n"], "page": a["page"],
                    "final_article": resolved[st].get(a["n"], {}).get("final_article") or None, "text": a["text"][:1500]}
                   for st in order if st in runs for a in runs[st]]
    DRAFT_TEXTS.parent.mkdir(parents=True, exist_ok=True)
    DRAFT_TEXTS.write_text(json.dumps(draft_texts, ensure_ascii=False, indent=1), encoding="utf-8")
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["instrument", "stage", "stage_symbol", "draft_article", "final_article",
                                          "source_pinpoint", "note"])
        w.writeheader()
        w.writerows({k: v for k, v in r.items() if not k.startswith("_")} for r in rows)
    print(f"-> {OUT.relative_to(ROOT)} ({len(rows)} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
