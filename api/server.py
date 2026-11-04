#!/usr/bin/env python3
"""Local test server for the pilot: JSON API over data/travaux.sqlite3 plus the static site.

Standard library only (pattern from travaux_crpd/server.py). Local use: it also serves
the downloaded UN PDFs so a reading can be checked against the scan.

  GET /api/facets                       delegations, speakers, records, draft articles
  GET /api/search?q=&delegation=&speaker=&symbol=&article=&session=&kind=&offset=
  GET /api/record?symbol=               one record, all segments in order
  GET /api/records                      all records with body, session, date and counts
  GET /api/export?format=csv|json|bibtex|ris&<search params>   all results of a search
  GET /api/symbols                      the symbols in the corpus (to link references)
  GET /api/articles                     the final articles with counts (article index)
  GET /api/article?n=                   one article: drafts across stages, meetings, delegations, votes, amendments
  GET /api/actors                       delegations with counts
  GET /api/actor?delegation=&speaker=   one delegation (or delegate): speakers, sessions, articles, proposals, roll-calls
  GET /api/decisions?article=&outcome=&proposer=&roll=&symbol=&offset=   the vote table
  GET /api/amendments?article=&proposer=   documents cited as amendments or proposals
  GET /pdf/<file>                       local scan (data/raw)
  GET /                                 site/index.html

Usage: python3 api/server.py   (PORT env var, default 8430)
"""
from __future__ import annotations

import csv
import datetime as dt
import difflib
import gzip
import io
import json
import mimetypes
import os
import re
import sqlite3
import ssl
import sys
import threading
import unicodedata
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

# Configuration by environment, so that the same file runs on the laptop and in the container (deploy/):
#   TRAVAUX_ROOT    the directory holding data/concordance, data/gold, eval/ and site/ (default: the repository)
#   TRAVAUX_DB      the SQLite file (default ROOT/data/travaux.sqlite3); opened read-only
#   TRAVAUX_SCANS   a directory of local scans served at /pdf/ (default ROOT/data/raw; none in the container)
#   HOST, PORT      where to listen (default 127.0.0.1:8430; the container sets HOST=0.0.0.0)
#   TRAVAUX_CORS_ORIGINS   origins allowed to call the API from a browser, comma-separated, or *
#   TRAVAUX_CACHE_SECONDS  Cache-Control max-age of the API's answers (default 0: no-store)
#   TRAVAUX_EXPORT_CAP     most rows one export returns (default 5000)
#   TRAVAUX_VERSION        shown by /health
#   VOYAGE_API_KEY         turns on Ask (/api/ask): the question goes to Voyage AI to be embedded and to re-rank the candidates
#   TRAVAUX_VECTORS        the segments' Voyage vectors, ids.json and vectors.npy (eval/semantic_embed.py)
#   TRAVAUX_ASK_DAILY_CAP  most questions a day sent to Voyage (default 1000; a repeated question is answered from memory)
ROOT = Path(os.environ.get("TRAVAUX_ROOT") or Path(__file__).resolve().parents[1])
DB = Path(os.environ.get("TRAVAUX_DB") or ROOT / "data" / "travaux.sqlite3")
SITE = ROOT / "site"
RAW = Path(os.environ.get("TRAVAUX_SCANS") or ROOT / "data" / "raw")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8430"))
CORS_ORIGINS = [o.strip() for o in os.environ.get("TRAVAUX_CORS_ORIGINS", "").split(",") if o.strip()]
CACHE_SECONDS = int(os.environ.get("TRAVAUX_CACHE_SECONDS", "0"))
VERSION = os.environ.get("TRAVAUX_VERSION", "dev")
PAGE_SIZE = 25
EXPORT_CAP = int(os.environ.get("TRAVAUX_EXPORT_CAP", "5000"))  # rows of "all results" in an export
# the publication audit's panel (eval/pub_audit.py) in a container of its own, passed through at /audit/ (deploy/docker-compose.yml)
AUDIT_URL = os.environ.get("TRAVAUX_AUDIT_URL", "").rstrip("/")
VOYAGE_KEY = os.environ.get("VOYAGE_API_KEY", "")
VECTORS = Path(os.environ.get("TRAVAUX_VECTORS") or ROOT / "data" / "cache" / "vectors" / "voyage-3-large")
ASK_DAILY_CAP = int(os.environ.get("TRAVAUX_ASK_DAILY_CAP", "1000"))


def rows(sql: str, params: tuple = ()) -> list[dict]:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, params)]
    finally:
        con.close()


# The database is read-only and replaced only as a whole file, so what a heavy function returns for given arguments is fixed until its
# modification time changes. The answers are kept (a few hundred at most), which spares the repeated work when many readers open the
# same page at once (the amendments table, a delegation's page, the facets).
_MEMO: dict = {}


def memo(fn):
    def wrapper(*args):
        key = (fn.__name__, args, DB.stat().st_mtime_ns)
        hit = _MEMO.get(key)
        if hit is None:
            hit = fn(*args)
            if len(_MEMO) >= 300:
                _MEMO.pop(next(iter(_MEMO)))
            _MEMO[key] = hit
        return hit
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


def fts_query(q: str) -> str:
    """User text to an FTS5 query: phrases, AND/OR/NOT and trailing * pass through;
    every other word is quoted so punctuation can't break the query."""
    parts = re.findall(r'"[^"]*"|\S+', q)
    out = []
    for p in parts:
        if p.startswith('"') or p in ("AND", "OR", "NOT"):
            out.append(p)
        elif p.endswith("*") and re.fullmatch(r"\w+\*", p):
            out.append(p)
        else:
            w = p.replace('"', "")
            if w:
                out.append(f'"{w}"')
    return " ".join(out)


@memo
def facets() -> dict:
    return {
        "delegations": rows("SELECT delegation AS v, COUNT(*) AS n FROM segments WHERE kind='speech' "
                            "AND delegation IS NOT NULL GROUP BY delegation ORDER BY n DESC"),
        "speakers": rows("SELECT speaker AS v, delegation AS d, COUNT(*) AS n FROM segments WHERE kind='speech' "
                         "AND speaker IS NOT NULL GROUP BY speaker, delegation ORDER BY n DESC"),
        "records": rows("SELECT d.symbol AS v, d.body, d.session, d.meeting_date, COUNT(s.id) AS n FROM documents d "
                        "JOIN segments s ON s.symbol=d.symbol AND s.kind='speech' GROUP BY d.symbol "
                        "ORDER BY d.meeting_date, d.symbol"),
        "sessions": rows("SELECT d.body || ' / ' || d.session AS v, d.body, d.session, MIN(d.meeting_date) AS first_date, "
                         "COUNT(s.id) AS n FROM documents d JOIN segments s ON s.symbol=d.symbol "
                         "WHERE s.kind IN ('speech','chair','vote') AND d.body IS NOT NULL AND d.session IS NOT NULL "
                         "GROUP BY d.body, d.session ORDER BY first_date, d.body, d.session"),
        # Final UDHR articles, mapped from each session's draft numbering (pipeline/articles.py)
        "articles": [r for i in INSTRUMENTS for r in rows(
            f"SELECT ? AS i, final_article AS v, COUNT(*) AS n FROM segments WHERE final_article IS NOT NULL "
            f"AND {inst_sql('article_instrument')} AND kind IN ('speech','chair','vote','paragraph') GROUP BY 2 ORDER BY 2", (i, i))],
        "corpora": rows("SELECT d.instrument AS v, COUNT(DISTINCT d.symbol) AS records, SUM(s.kind='speech') AS speeches "
                        "FROM documents d JOIN segments s ON s.symbol = d.symbol GROUP BY 1"),
        "totals": rows("SELECT kind AS v, COUNT(*) AS n FROM segments GROUP BY kind ORDER BY n DESC"),
        "decisions_total": rows("SELECT COUNT(*) AS n FROM decisions")[0]["n"],
        "translations": rows("SELECT COUNT(*) AS n, MAX(translation_model) AS model FROM documents WHERE machine_translated = 1")[0],
        # the questions of general debate given to speeches no article fits (pipeline/topics.py)
        "topics": rows("SELECT t.topic AS v, t.label, t.description, t.articles, COUNT(st.id) AS n FROM topics t "
                       "LEFT JOIN segment_topics st ON st.topic = t.topic GROUP BY t.topic HAVING n > 0 ORDER BY n DESC"),
        "export_cap": EXPORT_CAP,
    }


def _extract_prefixes(p: dict) -> tuple[dict, dict]:
    """Resolve inline field prefixes in q (e.g. speaker:cassin, delegation:poland, art:18, inst:ICCPR, doc:E/CN.4/SR.317)."""
    q = (p.get("q") or "").strip()
    if not q or ":" not in q:
        return p, {}
    p = dict(p)
    resolved: dict = {}
    rest = []
    for tok in re.findall(r'[A-Za-z]+:"[^"]+"|[A-Za-z]+:\S+|"[^"]*"|\S+', q):
        m = re.fullmatch(r'(speaker|sp|delegation|country|del|art|article|inst|instrument|doc|symbol|record|kind|topic):(?:"([^"]+)"|(\S+))', tok, re.I)
        if not m:
            rest.append(tok)
            continue
        k, val = m.group(1).lower(), (m.group(2) or m.group(3) or "").strip()
        if not val:
            continue
        if k in ("speaker", "sp") and not p.get("speaker"):
            hit = rows("SELECT speaker FROM segments WHERE UPPER(speaker) = UPPER(?) AND kind='speech' LIMIT 1", (val,))
            if not hit:
                hit = rows("SELECT speaker FROM segments WHERE UPPER(speaker) LIKE UPPER(?) AND kind='speech' "
                           "GROUP BY speaker ORDER BY COUNT(*) DESC LIMIT 1", (f"%{val}%",))
            p["speaker"] = resolved["speaker"] = hit[0]["speaker"] if hit else val.upper()
        elif k in ("delegation", "country", "del") and not p.get("delegation"):
            hit = rows("SELECT delegation FROM segments WHERE LOWER(delegation) = LOWER(?) AND kind='speech' LIMIT 1", (val,))
            if not hit:
                hit = rows("SELECT delegation FROM segments WHERE LOWER(delegation) LIKE LOWER(?) AND kind='speech' "
                           "GROUP BY delegation ORDER BY COUNT(*) DESC LIMIT 1", (f"%{val}%",))
            p["delegation"] = resolved["delegation"] = hit[0]["delegation"] if hit else val
        elif k in ("art", "article") and not p.get("article"):
            am = re.fullmatch(r"(?:(UDHR|ICCPR|ICESCR)[:/-])?(\d{1,2})", val, re.I)
            if am:
                if am.group(1) and not p.get("instrument"):
                    p["instrument"] = resolved["instrument"] = am.group(1).upper()
                p["article"] = resolved["article"] = am.group(2)
        elif k in ("inst", "instrument") and val.upper() in INSTRUMENTS and not p.get("instrument"):
            p["instrument"] = resolved["instrument"] = val.upper()
        elif k in ("doc", "symbol", "record") and not p.get("symbol"):
            hit = rows("SELECT symbol FROM documents WHERE UPPER(symbol) = UPPER(?) LIMIT 1", (val,))
            p["symbol"] = resolved["symbol"] = hit[0]["symbol"] if hit else val.upper()
        elif k == "kind" and val.lower() in ("speech", "chair", "vote", "paragraph", "all") and not p.get("kind"):
            p["kind"] = resolved["kind"] = val.lower()
        elif k == "topic" and not p.get("topic"):
            p["topic"] = resolved["topic"] = val.lower()
    if resolved.get("article") and not p.get("instrument"):
        resolved["instrument"] = "UDHR"
    p["q"] = " ".join(rest).strip()
    return p, resolved


HIT_COLS = ("s.id, s.symbol, s.seq, s.kind, s.page_start, s.page_end, s.n, s.n_end, s.speaker, s.delegation, "
            "s.speaker_method, s.speaker_raw, s.country_raw, s.article_heading, s.final_article, s.article_mapping, s.vote, "
            "s.article_instrument, s.draft_article, d.instrument, "
            "d.body, d.session, d.meeting_date, d.local_pdf, d.pdf_url, d.machine_translated, d.source_language, "
            "d.translation_model, d.translation_date, (SELECT topic FROM segment_topics st WHERE st.id = s.id) AS topic")


def search(p: dict, limit: int = PAGE_SIZE) -> dict:
    # the default kind is what the filter says it is, "Speeches, chair, votes"; "all" adds the documents' paragraphs and headings.
    # A record chosen by its symbol is shown whole.
    p, resolved = _extract_prefixes(p)
    where, params = ["s.kind != 'masthead'"], []
    if not p.get("kind") and not p.get("symbol"):
        where.append("s.kind IN ('speech', 'chair', 'vote')")
    for key, col in (("delegation", "s.delegation"), ("speaker", "s.speaker"), ("symbol", "s.symbol"),
                     ("article", "s.final_article"), ("kind", "s.kind"),
                     ("session", "d.body || ' / ' || d.session")):
        if p.get(key) and not (key == "kind" and p[key] == "all"):
            where.append(f"{col} = ?")
            params.append(p[key])
    if p.get("topic"):
        where.append("s.id IN (SELECT id FROM segment_topics WHERE topic = ?)")
        params.append(p["topic"])
    # machine translations of French-only documents are in by default; translations=0 leaves them out
    if str(p.get("translations", "1")).lower() in ("0", "false", "no", "off"):
        where.append("d.machine_translated = 0")
    # an article belongs to an instrument; without an article, the instrument picks the records
    if p.get("article"):
        where.append(inst_sql("s.article_instrument"))
        params.append(instrument_of(p))
    elif p.get("instrument") in INSTRUMENTS:
        where.append("d.instrument = ?")
        params.append("UDHR" if p["instrument"] == "UDHR" else "Covenants")
    offset = int(p.get("offset") or 0)
    cols = HIT_COLS
    sort_mode = "date" if (not p.get("q") or p.get("sort") == "date") else "relevance"
    if p.get("q"):
        match = fts_query(p["q"])
        # a query in quotes only ("conception", "moment of conception") is matched word for word, unstemmed
        exact = bool(re.fullmatch(r'\s*(?:"[^"]+"\s*(?:\b(?:OR|AND|NOT)\b\s*)?)+', p["q"]))
        fts, rank = ("segments_fts_exact", "bm25(segments_fts_exact)") if exact else ("segments_fts", "bm25(segments_fts, 1.0, 4.0, 2.0)")
        order_by = "d.meeting_date IS NULL, d.meeting_date, s.symbol, s.seq" if sort_mode == "date" else rank
        base = (f"FROM {fts} f JOIN segments s ON s.id = f.id JOIN documents d ON d.symbol = s.symbol "
                f"WHERE {fts} MATCH ? AND {' AND '.join(where)}")
        try:
            total = rows(f"SELECT COUNT(*) AS n {base}", (match, *params))[0]["n"]
            hits = rows(f"SELECT {cols}, snippet({fts}, 0, '\x01', '\x02', ' … ', 48) AS snippet {base} "
                        f"ORDER BY {order_by} LIMIT ? OFFSET ?",
                        (match, *params, limit, offset))
        except sqlite3.OperationalError as exc:
            return {"error": f"query not understood: {exc}", "total": 0, "results": []}
    else:
        base = f"FROM segments s JOIN documents d ON d.symbol = s.symbol WHERE {' AND '.join(where)}"
        total = rows(f"SELECT COUNT(*) AS n {base}", tuple(params))[0]["n"]
        hits = rows(f"SELECT {cols}, substr(s.text, 1, 320) AS snippet {base} "
                    f"ORDER BY d.meeting_date, s.symbol, s.seq LIMIT ? OFFSET ?", (*params, limit, offset))
    return {"total": total, "offset": offset, "page_size": limit, "sort": sort_mode, "resolved": resolved, "results": hits}


# Ask: a question or a description in a sentence, answered with the passages that match it best, as round 131 measured it
# (eval/semantic_bench.py): voyage-3-large over the segments, fused with BM25 (the question's words joined by OR) by
# reciprocal rank, the top 100 re-ranked by Voyage rerank-2.5. The question goes to Voyage AI; nothing else leaves the server.
# Round 132: on two to five keywords the search above does better, which the page tells a reader who types a few words.
ASK_KINDS = ("speech", "chair", "vote", "procedural", "paragraph")
ASK_STOP = set("""a an the of in on at to for from by with and or not no is are was were be been being as that this these those
it its which who whom whose what when where why how than then there their they them he she his her we our you your i
into over under about between during after before against would could should may might can will shall do does did
had has have also only such any all each other more most some same very upon whether if but so""".split())
_ASK: dict = {}
_ASK_CACHE: dict = {}
_ASK_LOCK = threading.Lock()
_ASK_DAY = {"day": "", "n": 0}  # questions sent to Voyage today: Voyage is paid per question, and the site is open to anyone


def ask_ready() -> bool:
    return bool(VOYAGE_KEY) and (VECTORS / "vectors.npy").exists()


def ask_index():
    """The vectors of the segments still in the database (ids changed by a re-segmentation drop out until re-embedded)."""
    with _ASK_LOCK:
        return _ask_load()


def _ask_load():
    if "m" not in _ASK:
        import numpy as np
        ids = json.loads((VECTORS / "ids.json").read_text())
        inst = {r["id"]: r["instrument"] for r in rows("SELECT s.id, d.instrument FROM segments s JOIN documents d ON d.symbol = s.symbol")}
        keep = [i for i, sid in enumerate(ids) if sid in inst]
        m = np.load(VECTORS / "vectors.npy", mmap_mode="r")[keep].astype(np.float32)
        m /= np.linalg.norm(m, axis=1, keepdims=True)
        _ASK.update(m=m, ids=[ids[i] for i in keep], inst=np.array([inst[ids[i]] for i in keep]))
    return _ASK


def voyage(endpoint: str, payload: dict) -> dict:
    req = urllib.request.Request(f"https://api.voyageai.com/v1/{endpoint}", data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {VOYAGE_KEY}"})
    try:
        import certifi  # (the laptop's Python has no certificates of its own; the container's has)
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = None
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        return json.loads(r.read())


def ask(q: str, instrument: str = "", limit: int = 30) -> dict:
    import numpy as np
    q = " ".join(q.split())[:1000]
    if not q:
        return {"results": []}
    instrument = "UDHR" if instrument == "UDHR" else "Covenants" if instrument in ("ICCPR", "ICESCR", "Covenants") else ""
    key = (q, instrument, DB.stat().st_mtime_ns)
    ranked = _ASK_CACHE.get(key)
    if ranked is None:
        today = dt.date.today().isoformat()
        with _ASK_LOCK:
            if _ASK_DAY["day"] != today:
                _ASK_DAY.update(day=today, n=0)
            if _ASK_DAY["n"] >= ASK_DAILY_CAP:
                return {"error": "Ask has answered as many questions as it can today. Try again tomorrow, or use Search."}
            _ASK_DAY["n"] += 1
        ix = ask_index()
        qv = np.asarray(voyage("embeddings", {"input": [q], "model": "voyage-3-large", "input_type": "query"})["data"][0]["embedding"],
                        dtype=np.float32)
        sims = ix["m"] @ (qv / np.linalg.norm(qv))
        if instrument:
            sims[ix["inst"] != instrument] = -2
        dense = [ix["ids"][j] for j in np.argsort(-sims)[:100] if sims[j] > -2]
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]+", q) if w.lower() not in ASK_STOP]
        lexical = []
        if words:
            lexical = [r["id"] for r in rows(
                f"SELECT s.id FROM segments_fts f JOIN segments s ON s.id = f.id JOIN documents d ON d.symbol = s.symbol "
                f"WHERE segments_fts MATCH ? AND s.kind IN ({','.join('?' * len(ASK_KINDS))}) AND length(trim(s.text)) >= 20"
                + (" AND d.instrument = ?" if instrument else "") + " ORDER BY bm25(segments_fts, 1.0, 4.0, 2.0) LIMIT 100",
                (" OR ".join(f'"{w}"' for w in dict.fromkeys(words)), *ASK_KINDS, *([instrument] if instrument else [])))]
        score: dict = {}
        for lst in (lexical, dense):
            for r, sid in enumerate(lst):
                score[sid] = score.get(sid, 0) + 1 / (60 + r + 1)
        fused = sorted(score, key=lambda s: -score[s])[:100]
        text = {r["id"]: r for r in rows(f"SELECT id, symbol, speaker, delegation, text FROM segments WHERE id IN ({','.join('?' * len(fused))})",
                                          tuple(fused))}

        def unit(r):  # as embedded (eval/semantic_embed.py)
            who = f", {r['speaker']}" + (f" ({r['delegation']})" if r["delegation"] else "") if r["speaker"] else (f", {r['delegation']}" if r["delegation"] else "")
            return f"{r['symbol']}{who}: {' '.join(r['text'].split())}"[:24000]
        rr = voyage("rerank", {"query": q, "documents": [unit(text[s]) for s in fused], "model": "rerank-2.5", "truncation": True})
        # one text repeated in a draft, its amendments and the adopted resolution is shown once, with the other symbols
        ranked, seen = [], {}
        for d in sorted(rr["data"], key=lambda d: -d["relevance_score"]):
            sid = fused[d["index"]]
            same = re.sub(r"[^a-z]+", " ", text[sid]["text"].lower()).strip()[:400]
            if same in seen:
                also = ranked[seen[same]][2]
                if text[sid]["symbol"] not in also and text[sid]["symbol"] != text[ranked[seen[same]][0]]["symbol"]:
                    also.append(text[sid]["symbol"])
                continue
            seen[same] = len(ranked)
            ranked.append((sid, round(d["relevance_score"], 3), []))
        if len(_ASK_CACHE) >= 500:
            _ASK_CACHE.pop(next(iter(_ASK_CACHE)))
        _ASK_CACHE[key] = ranked
    top = ranked[:limit]
    hits = {r["id"]: r for r in rows(f"SELECT {HIT_COLS}, substr(s.text, 1, 600) AS snippet FROM segments s "
                                     f"JOIN documents d ON d.symbol = s.symbol WHERE s.id IN ({','.join('?' * len(top))})",
                                     tuple(s for s, _, _ in top))} if top else {}
    return {"results": [dict(hits[s], score=sc, also=also) for s, sc, also in top if s in hits], "instrument": instrument}


# Check: the citations of the UN travaux in a reader's own text (a draft, a chapter), each held against the record it names,
# after HUDOC Researcher's Check. For every symbol: is the document here; is the cited page or paragraph in it; does the person
# or delegation named with it speak there; and is a quotation just before it in the record, word for word. The text is sent
# by POST and kept nowhere.
CHECK_SYMBOL_RE = re.compile(r"\b((?:A|E)/(?:[A-Z][A-Za-z0-9.]*/)*(?:[A-Z]+\.)?[1-9]\d*(?:\([IVXL]+\))?(?:/(?:Rev|Add|Corr)\.\d+)*)")
CHECK_PIN_RE = re.compile(r"^\s*(?:\((?:\d{1,2} [A-Z][a-z]+ )?\d{4}\))?\s*,?\s*(?:at\s+)?(?:(?P<kind>pp?\.|paras?\.?|§§?|¶¶?)\s*)?"
                          r"(?P<a>\d{1,4})(?:\s*(?:[-–]|to)\s*(?P<b>\d{1,4}))?")
CHECK_WHO_RE = re.compile(r"^\s*\(([^()]{3,80})\)")
CHECK_QUOTE_RE = re.compile(r"[“\"«]([^”\"»]{12,600})[”\"»]")
CHECK_ALIASES = {"ussr": "union of soviet socialist republics", "soviet union": "union of soviet socialist republics",
                 "uk": "united kingdom", "britain": "united kingdom", "us": "united states", "usa": "united states",
                 "byelorussian ssr": "byelorussian soviet socialist republic", "ukrainian ssr": "ukrainian soviet socialist republic"}


def check_norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", t))


def check_quote(quote: str, segs: list[dict]) -> dict:
    """Where a quotation is in a record: verbatim, almost (85% of its words in order), similar (60%), or not at all."""
    q = check_norm(quote)
    if len(q.split()) < 3:
        return {"verdict": "short"}
    best = (0.0, None)
    for s in segs:
        t = check_norm(s["text"])
        if q in t:
            return {"verdict": "verbatim", "segment": s["id"], "pin": pinpoint(s)}
        qw, tw = q.split(), t.split()
        if not tw:
            continue
        m = difflib.SequenceMatcher(None, qw, tw, autojunk=False)
        cover = sum(b.size for b in m.get_matching_blocks()) / len(qw)
        if cover > best[0]:
            best = (cover, s)
    cover, s = best
    if cover >= 0.85:
        return {"verdict": "near", "segment": s["id"], "pin": pinpoint(s), "coverage": round(cover, 2)}
    if cover >= 0.6:
        return {"verdict": "similar", "segment": s["id"], "pin": pinpoint(s), "coverage": round(cover, 2)}
    return {"verdict": "none"}


def check_text(text: str) -> dict:
    text = text[:60000]
    held = {r["symbol"].upper(): r for r in rows("SELECT symbol, n_pages, doc_type, body, meeting_date FROM documents")}
    out, prev_end = [], 0
    for m in CHECK_SYMBOL_RE.finditer(text):
        sym = m.group(1).rstrip(".")
        cite = {"symbol": sym, "start": m.start(), "end": m.end(), "checks": []}
        rest = text[m.end(): m.end() + 120]
        pm = CHECK_PIN_RE.match(rest)
        pin = None
        if pm and (pm.group("kind") or re.match(r"^\s*(?:\([^()]*\d{4}\))?\s*,", rest)):
            kind = pm.group("kind") or ""
            pin = {"type": "para" if kind[:1] in ("p",) and kind.startswith("para") or kind[:1] in ("§", "¶") else "page",
                   "from": int(pm.group("a")), "to": int(pm.group("b") or pm.group("a"))}
            cite["end"] = m.end() + pm.end()
        ym = re.match(r"\s*\(\d{4}\)", text[cite["end"]: cite["end"] + 10])  # a year after the pinpoint (Bluebook, OSCOLA)
        if ym:
            cite["end"] += ym.end()
        wm = CHECK_WHO_RE.match(text[cite["end"]: cite["end"] + 90])
        if wm and re.search(r"\d{4}|^\s*(?:p|pp|para|paras|see)\b", wm.group(1)):  # a date or a pinpoint, not a person
            wm = None
        who = wm.group(1).strip() if wm else ""
        if wm:
            cite["end"] += wm.end()
        # the quotation it supports: the last one closing between the previous citation and this one, close before it
        quote = None
        for qm in CHECK_QUOTE_RE.finditer(text, prev_end, m.start()):
            if m.start() - qm.end() <= 220:
                quote = qm
        prev_end = cite["end"]
        cite.update(pin=pin, who=who, quote=quote.group(1) if quote else "",
                    quote_span=[quote.start(), quote.end()] if quote else None)
        doc = held.get(sym.upper())
        if not doc:
            cite["status"] = "not_held"
            cite["checks"].append({"ok": None, "what": "document", "note": f"{sym} is not in this database: check the UN copy."})
            cite["un_url"] = f"https://undocs.org/{sym}"
            out.append(cite)
            continue
        sym = doc["symbol"]
        cite.update(symbol=sym, doc={k: doc[k] for k in ("doc_type", "body", "meeting_date", "n_pages")})
        segs = rows("SELECT id, symbol, kind, page_start, page_end, n, n_end, speaker, delegation, text FROM segments "
                    "WHERE symbol = ? AND kind != 'masthead' ORDER BY seq", (sym,))
        cite["checks"].append({"ok": True, "what": "document", "note": f"{sym} is in the database."})
        at = segs
        if pin:
            def num(v):
                return int(re.match(r"\d*", v or "").group(0) or 0)
            if pin["type"] == "para":
                at = [s for s in segs if num(s["n"]) and num(s["n"]) <= pin["to"] and (num(s["n_end"]) or num(s["n"])) >= pin["from"]]
                paras = [num(s["n"]) for s in segs if num(s["n"])]
                span = f"paragraphs {min(paras)}–{max(paras)}" if paras else "no numbered paragraphs"
            else:
                at = [s for s in segs if (s["page_start"] or 0) <= pin["to"] and (s["page_end"] or s["page_start"] or 0) >= pin["from"]]
                pages = [s["page_end"] or s["page_start"] for s in segs if s["page_start"]]
                span = f"pages 1–{max(pages)}" if pages else "no pages"
            label = ("para" if pin["type"] == "para" else "p") + (f"s. {pin['from']}–{pin['to']}" if pin["to"] != pin["from"] else f". {pin['from']}")
            if at:
                cite["checks"].append({"ok": True, "what": "pinpoint", "note": f"{label} {'are' if pin['to'] != pin['from'] else 'is'} in the record.",
                                       "segment": at[0]["id"]})
            else:
                printed = pin["type"] == "page" and sym.startswith(("A/C.3/SR", "A/PV", "E/SR", "A/C.3/SC")) and pin["from"] > 20
                cite["checks"].append({"ok": None if printed else False, "what": "pinpoint", "note":
                                       f"{label} {'are' if pin['to'] != pin['from'] else 'is'} not in this record ({span})" + (": the printed volumes (GAOR, ESCOR) number "
                                       "their pages differently; cite the paragraph, which is the same in both." if printed else ".")})
        if who:
            toks = [check_norm(t) for t in re.split(r"[,;]| and ", who) if check_norm(t)]
            toks = [CHECK_ALIASES.get(t, t) for t in toks]

            def speaks(s):
                name, deleg = check_norm(s["speaker"]), check_norm(s["delegation"])
                return any(t and ((name and (t in name.split() or name in t or t in name)) or (deleg and (t == deleg or t in deleg)))
                           for t in toks)
            here = [s for s in at if s["kind"] in ("speech", "chair") and speaks(s)]
            anywhere = [s for s in segs if s["kind"] in ("speech", "chair") and speaks(s)]
            if here:
                cite["checks"].append({"ok": True, "what": "speaker", "note": f"{who} speaks there.", "segment": here[0]["id"]})
            elif anywhere:
                cite["checks"].append({"ok": False, "what": "speaker", "note": f"{who} speaks in this record at {', '.join(dict.fromkeys(pinpoint(s) for s in anywhere[:4]))}, not at the place cited.",
                                       "segment": anywhere[0]["id"]})
            else:
                cite["checks"].append({"ok": None, "what": "speaker", "note": f"No speech by “{who}” found in this record (a name read wrongly by the OCR, or another record?)."})
        if quote:
            q = check_quote(quote.group(1), at if pin and at else segs)
            if q["verdict"] not in ("verbatim", "near") and pin and at:
                q2 = check_quote(quote.group(1), segs)
                if q2["verdict"] in ("verbatim", "near"):
                    q = dict(q2, elsewhere=True)
            notes = {"verbatim": "The quotation is in the record word for word", "near": "The quotation is almost word for word in the record",
                     "similar": "The record says something similar, but the words differ", "none": "The quotation is not in this record",
                     "short": "The quotation is too short to check"}
            where = f" ({q['pin']})" if q.get("pin") else ""
            note = notes[q["verdict"]] + where + (", but not at the place cited" if q.get("elsewhere") else "") + "."
            if q["verdict"] in ("verbatim", "near", "similar") and doc["doc_type"] == "summary_record":
                note += " A summary record paraphrases the speaker: quote it as the record's words."
            cite["checks"].append({"ok": True if q["verdict"] == "verbatim" and not q.get("elsewhere") else
                                   None if q["verdict"] in ("near", "short") else False, "what": "quotation", "note": note,
                                   "segment": q.get("segment")})
        oks = [c["ok"] for c in cite["checks"]]
        cite["status"] = "problem" if False in oks else "check" if None in oks else "ok"
        cite["open"] = next((c["segment"] for c in cite["checks"] if c.get("segment")), segs[0]["id"] if segs else None)
        out.append(cite)
    return {"citations": out, "counts": {k: sum(c["status"] == k for c in out) for k in ("ok", "check", "problem", "not_held")}}


@memo
def records() -> list[dict]:
    rs = rows("SELECT d.symbol, d.body, d.session, d.meeting_date, d.doc_type, d.n_pages, d.pdf_url, d.local_pdf, d.instrument, "
              "d.machine_translated, d.source_language, d.translation_model, d.translation_date, "
              "SUM(s.kind='speech') AS speeches, SUM(s.kind='vote') AS votes "
              "FROM documents d LEFT JOIN segments s ON s.symbol = d.symbol GROUP BY d.symbol")
    return sorted(rs, key=lambda r: (
        r["body"] or "", r["session"] or "", r["meeting_date"] or "9999",
        [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", r["symbol"])]))


def pinpoint(h: dict) -> str:
    if h.get("n"):
        return f"paras. {h['n']}-{h['n_end']}" if h.get("n_end") else f"para. {h['n']}"
    return f"p. {h['page_start']}" if h["page_start"] == h["page_end"] else f"pp. {h['page_start']}-{h['page_end']}"


def chair_role(h: dict) -> str:
    """'President' for the turns of a President (the General Assembly's plenary, ECOSOC), otherwise 'Chairman'."""
    return "President" if re.match(r"\W*(?:\w{1,3}\W+)?The\s+(?:PRES|Pres)", h.get("text") or "") else "Chairman"


def citation(h: dict) -> str:
    who = ""
    if h.get("speaker") and h.get("kind") == "chair":
        # the chair's turns named from the masthead (pipeline/chairs.py): the person and the office, no delegation
        name = h["speaker"].title() if h["speaker"].isupper() else h["speaker"]
        who = f" ({name}, {chair_role(h)})"
    elif h.get("speaker"):
        who = f" ({h['speaker'].title() if h['speaker'].isupper() else h['speaker']}, {h['delegation']})"
    elif h.get("kind") == "chair":
        who = f" ({chair_role(h)})"
    return f"{h['symbol']}, {pinpoint(h)}{who}" + (f" [{translation_note(h, short=True)}]" if h.get("machine_translated") else "")


# the model that translated the French-only documents, as a reader names it (docs/machine_translations.md: each translation was
# compared with the scan by a second model, claude-sonnet-5-5, and settled by the first)
MODEL_LABELS = {"claude-fable-5-1": "Claude Fable 5.1, checked by Claude Sonnet 5.5"}


def model_label(model: str | None) -> str:
    return MODEL_LABELS.get(model or "", model or "a language model")


def translation_note(h: dict, short: bool = False) -> str:
    """The label every passage of a machine-translated document carries."""
    lang = {"fr": "French"}.get(h.get("source_language"), h.get("source_language") or "the original")
    if short:
        return f"machine translation from {lang}, {model_label(h.get('translation_model'))}"
    return (f"Machine translation from {lang} ({model_label(h.get('translation_model'))}, {h.get('translation_date')}); "
            f"not an official UN text. Check the {lang} original before quoting.")


def export(p: dict) -> tuple[bytes, str, str]:
    """All results of a search (up to EXPORT_CAP), as (body, content type, file name)."""
    fmt = p.get("format", "csv")
    res = search({**p, "offset": 0}, limit=EXPORT_CAP)
    hits = res["results"]
    full = {r["id"]: r["text"] for r in rows(
        f"SELECT id, text FROM segments WHERE id IN ({','.join('?' * len(hits))})", tuple(h["id"] for h in hits))} if hits else {}
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    query = {k: v for k, v in p.items() if k not in ("format", "offset") and v}
    if fmt == "json":
        body = {"generated": dt.datetime.now().isoformat(timespec="seconds"), "query": query, "total": res.get("total"),
                "note": "OCR text of UN summary records (paraphrase, not verbatim); check the UN PDF before quoting.",
                "results": [{**{k: h.get(k) for k in ("id", "symbol", "kind", "page_start", "page_end", "n", "speaker",
                                                      "delegation", "article_instrument", "final_article", "draft_article",
                                                      "article_heading", "topic", "body", "session", "meeting_date")},
                             "machine_translation": translation_note(h) if h.get("machine_translated") else None,
                             "citation": citation(h), "text": full.get(h["id"], "")} for h in hits]}
        return json.dumps(body, ensure_ascii=False, indent=1).encode("utf-8"), "application/json", f"travaux-{stamp}.json"
    if fmt in ("bibtex", "ris"):
        docs = {}
        for h in hits:
            docs.setdefault(h["symbol"], h)
        out = []
        for sym, h in docs.items():
            year = (h.get("meeting_date") or "")[:4]
            title = f"{h.get('body') or 'United Nations'}, {h.get('session') or ''}: {sym}".strip()
            url = f"https://undocs.org/{sym}"
            if fmt == "bibtex":
                key = re.sub(r"\W+", "_", sym).strip("_")
                out.append(f"@misc{{{key},\n  title = {{{title}}},\n  author = {{{{United Nations}}}},\n"
                           f"  year = {{{year}}},\n  note = {{UN Doc {sym}}},\n  url = {{{url}}}\n}}")
            else:
                out.append(f"TY  - GEN\nTI  - {title}\nAU  - United Nations\nPY  - {year}\nM1  - {sym}\nUR  - {url}\nER  - ")
        ext, ctype = ("bib", "application/x-bibtex") if fmt == "bibtex" else ("ris", "application/x-research-info-systems")
        return ("\n\n".join(out) + "\n").encode("utf-8"), ctype, f"travaux-{stamp}.{ext}"
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["citation", "symbol", "pinpoint", "kind", "speaker", "delegation", "body", "session",
                "meeting_date", "article_instrument", "final_article", "draft_article", "article_heading",
                "topic", "machine_translation", "text"])
    for h in hits:
        w.writerow([citation(h), h["symbol"], pinpoint(h), h["kind"], h.get("speaker") or "", h.get("delegation") or "",
                    h.get("body") or "", h.get("session") or "", h.get("meeting_date") or "",
                    h.get("article_instrument") or "", h.get("final_article") or "", h.get("draft_article") or "",
                    h.get("article_heading") or "", h.get("topic") or "",
                    translation_note(h) if h.get("machine_translated") else "", full.get(h["id"], "")])
    return ("\ufeff" + buf.getvalue()).encode("utf-8"), "text/csv", f"travaux-{stamp}.csv"


# The drafting stages of the UDHR, in order (pipeline/articles.py numbers each record's articles by one)
STAGES = [
    ("secretariat_outline", "E/CN.4/AC.1/3", "Secretariat outline", "June 1947"),
    ("cassin_rev1", "E/CN.4/AC.1/W.2/Rev.1", "Drafting Committee: Cassin's draft, first revision", "June 1947"),
    ("cassin_draft", "E/CN.4/AC.1/W.2/Rev.2", "Drafting Committee: Cassin's draft", "June 1947"),
    ("drafting_committee_1", "E/CN.4/21", "Drafting Committee, 1st session", "June 1947"),
    ("e_cn4_57", "E/CN.4/57", "Commission's working group on the Declaration (Geneva)", "December 1947"),
    ("geneva_draft", "E/600", "Commission, 2nd session (Geneva draft)", "December 1947"),
    ("drafting_committee_2", "E/CN.4/95", "Drafting Committee, 2nd session", "May 1948"),
    ("chr_3", "E/800", "Commission, 3rd session", "June 1948"),
    ("a777", "A/777", "Third Committee (A/777)", "December 1948"),
]
STAGE_ORDER = {st: i for i, (st, *_) in enumerate(STAGES)}
STAGE_DOCS = {sym for _, sym, *_ in STAGES} | {"A/777", "A/RES/217(III)"}


INSTRUMENTS = {"UDHR": 30, "ICCPR": 53, "ICESCR": 31}
FINAL_DOC = {"UDHR": ("A/RES/217(III)", "10 December 1948"), "ICCPR": ("A/RES/2200(XXI)", "16 December 1966"),
             "ICESCR": ("A/RES/2200(XXI)", "16 December 1966")}
# the Covenants' drafts: the Commission's 1954 texts, as the Secretary-General's annotations reprint them
COVENANT_STAGES = [("uk_draft_1947", "E/CN.4/21", "United Kingdom's draft international bill (E/CN.4/21, annex B)", "June 1947"),
                   ("e_cn4_21_g", "E/CN.4/21", "Drafting Committee: articles for a convention (E/CN.4/21, annex G)", "June 1947"),
                   ("e_cn4_56", "E/CN.4/56", "Commission's working group on the Convention (Geneva)", "December 1947"),
                   ("e600", "E/600", "Commission, 2nd session: draft Covenant (Geneva draft)", "December 1947"),
                   ("chr5", "E/800", "Commission, 3rd session: draft Covenant (E/800, annex B)", "June 1948"),
                   ("chr6", "E/CN.4/350", "Commission, 5th session: draft Covenant (E/1371, annex I)", "June 1949"),
                   ("e1681", "E/1681", "Commission, 6th session: draft Covenant (E/1681, annex I)", "May 1950"),
                   ("e1992", "E/CN.4/640", "Commission, 7th session: draft Covenant (E/1992, annex I)", "May 1951"),
                   ("e2256", "E/CN.4/669", "Commission, 8th session: draft Covenants (E/2256)", "June 1952"),
                   ("e2447", "E/CN.4/689", "Commission, 9th session: draft Covenants (E/2447)", "May 1953"),
                   ("e2573", "A/2929", "Commission on Human Rights, 10th session (E/2573, reprinted in A/2929)", "April 1954"),
                   ("a4625", "A/4625", "Third Committee, 15th session: articles 15-18 as adopted (A/4625, annex)", "December 1960"),
                   ("a5000", "A/5000", "Third Committee, 16th session: articles 19-25 as adopted (A/5000, annex)", "December 1961")]
COVENANT_STAGE_ORDER = {st: i for i, (st, *_) in enumerate(COVENANT_STAGES)}


def inst_sql(col: str) -> str:
    """An article tag of one instrument, counting passages on both covenants (articles 1-5)."""
    both = "'ICCPR+ICESCR'"
    return f"? IN ({col}, CASE {col} WHEN {both} THEN 'ICCPR' END, CASE {col} WHEN {both} THEN 'ICESCR' END)"


def instrument_of(p: dict) -> str:
    return p.get("instrument") if p.get("instrument") in INSTRUMENTS else "UDHR"


def article_titles(instrument: str = "UDHR") -> dict[str, str]:
    with (ROOT / "data" / "concordance" / "articles.csv").open() as f:
        return {r["article"]: r["short_title"] for r in csv.DictReader(f) if r["instrument"] == instrument}


def final_texts(instrument: str = "UDHR") -> dict[str, str]:
    if instrument == "UDHR":
        return json.loads((ROOT / "data" / "concordance" / "udhr_final.json").read_text())["articles"]
    return json.loads((ROOT / "data" / "concordance" / "covenants_final.json").read_text())["instruments"].get(instrument, {})


def word_diff(old: str, new: str) -> list[list[str]]:
    """Word-level changes from old to new: [["eq"|"del"|"ins", text], ...]. Words are compared
    without case or punctuation, so an OCR comma doesn't count as a change."""
    a, b = old.split(), new.split()
    key = lambda w: re.sub(r"\W", "", w.lower())  # noqa: E731
    sm = difflib.SequenceMatcher(None, [key(w) for w in a], [key(w) for w in b], autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            out.append(["eq", " ".join(b[j1:j2])])
        else:
            if i2 > i1:
                out.append(["del", " ".join(a[i1:i2])])
            if j2 > j1:
                out.append(["ins", " ".join(b[j1:j2])])
    return out


SPEECHY = "('speech','chair','vote','paragraph')"


@memo
def articles_index(instrument: str = "UDHR") -> list[dict]:
    titles = article_titles(instrument)
    counts = {r["a"]: r for r in rows(
        f"SELECT final_article AS a, SUM(kind='speech') AS speeches, COUNT(DISTINCT symbol) AS records "
        f"FROM segments WHERE final_article IS NOT NULL AND {inst_sql('article_instrument')} AND kind IN {SPEECHY} GROUP BY 1",
        (instrument,))}
    votes = {r["a"]: r["n"] for r in rows("SELECT final_article AS a, COUNT(*) AS n FROM decisions "
                                           f"WHERE final_article IS NOT NULL AND {inst_sql('article_instrument')} GROUP BY 1", (instrument,))}
    drafts = {}
    for r in rows("SELECT final_article AS a, stage, draft_article FROM draft_texts WHERE final_article IS NOT NULL "
                  "AND instrument = ?", (instrument,)):
        drafts.setdefault(r["a"], []).append(r)
    out = []
    for n in range(1, INSTRUMENTS[instrument] + 1):
        c = counts.get(n, {})
        order = STAGE_ORDER if instrument == "UDHR" else COVENANT_STAGE_ORDER
        by_stage: dict[str, list[str]] = {}  # one chip per stage: "Drafting Cttee I 2,3,4"
        for r in sorted(drafts.get(n, []), key=lambda r: (order.get(r["stage"], 99), int(re.match(r"\d*", str(r["draft_article"])).group(0) or 0))):
            by_stage.setdefault(r["stage"], [])
            if str(r["draft_article"]) not in by_stage[r["stage"]]:
                by_stage[r["stage"]].append(str(r["draft_article"]))
        out.append({"n": n, "title": titles.get(str(n), ""), "speeches": c.get("speeches") or 0,
                    "records": c.get("records") or 0, "decisions": votes.get(n, 0),
                    "drafts": [f"{st}:{','.join(ds)}" for st, ds in by_stage.items()]})
    return out


@memo
def article(n: int, instrument: str = "UDHR") -> dict:
    titles = article_titles(instrument)
    final = final_texts(instrument).get(str(n), "")
    stages = STAGES if instrument == "UDHR" else COVENANT_STAGES
    stage_info = {st: {"symbol": sym, "label": label, "date": date} for st, sym, label, date in stages}
    order = STAGE_ORDER if instrument == "UDHR" else COVENANT_STAGE_ORDER
    # draft numbers such as "15A" and "3 to 6" sort by their number, then their letter
    drafts = sorted(rows("SELECT * FROM draft_texts WHERE final_article = ? AND instrument = ?", (n, instrument)),
                    key=lambda r: (order.get(r["stage"], 99), int(re.match(r"\d*", str(r["draft_article"])).group(0) or 0),
                                   str(r["draft_article"])))
    prev = None
    for d in drafts:
        d.update(stage_info.get(d["stage"], {}))
        # one draft article can hold several final articles (E/800 art. 4: slavery and torture): the others, so the page can say so
        d["also"] = [r["final_article"] for r in rows(
            "SELECT DISTINCT final_article FROM draft_texts WHERE stage = ? AND draft_article = ? AND instrument = ? "
            "AND final_article IS NOT NULL AND final_article != ? ORDER BY 1", (d["stage"], d["draft_article"], instrument, n))]
        d["diff"] = word_diff(prev, d["text"]) if prev else None
        prev = d["text"]
    evolution = drafts + [{"stage": "final", "symbol": FINAL_DOC[instrument][0], "label": "General Assembly (adopted text)",
                           "date": FINAL_DOC[instrument][1], "draft_article": n, "text": final,
                           "diff": word_diff(prev, final) if prev else None}]
    meetings = rows(
        f"SELECT s.symbol, d.body, d.session, d.meeting_date, d.doc_type, SUM(s.kind='speech') AS speeches, "
        f"MIN(s.id) AS first_id, group_concat(DISTINCT coalesce(s.draft_article, s.article_heading)) AS draft_numbers "
        f"FROM segments s JOIN documents d ON d.symbol = s.symbol WHERE s.final_article = ? AND {inst_sql('s.article_instrument')} "
        f"AND s.kind IN {SPEECHY} GROUP BY s.symbol ORDER BY d.meeting_date IS NULL, d.meeting_date, s.symbol", (n, instrument))
    for m in meetings:
        m["delegations"] = [r["delegation"] for r in rows(
            f"SELECT delegation, COUNT(*) AS c FROM segments WHERE symbol = ? AND final_article = ? AND {inst_sql('article_instrument')} "
            "AND kind='speech' AND delegation IS NOT NULL GROUP BY 1 ORDER BY c DESC", (m["symbol"], n, instrument))]
    delegations = rows("SELECT delegation, COUNT(*) AS speeches, COUNT(DISTINCT symbol) AS records FROM segments "
                       f"WHERE final_article = ? AND {inst_sql('article_instrument')} AND kind='speech' AND delegation IS NOT NULL "
                       "GROUP BY 1 ORDER BY speeches DESC", (n, instrument))
    p = {"article": n, "instrument": instrument}
    return {"n": n, "instrument": instrument, "title": titles.get(str(n), ""), "final_text": final, "evolution": evolution,
            "meetings": meetings, "delegations": delegations, "decisions": decisions(p, limit=500)["results"],
            "amendments": amendments(p), "topics": article_topics(n, instrument)}


def article_topics(n: int, instrument: str) -> list[dict]:
    """The questions of general debate that bear on an article (topics.articles: "ICCPR 1; ICESCR 28-45"), with their
    speeches: the general debates that no article tag holds (self-determination for article 1, the federal clause for 50)."""
    out = []
    for t in rows("SELECT topic, label, articles FROM topics WHERE articles != ''"):
        for part in t["articles"].split(";"):
            inst, _, rng = part.strip().partition(" ")
            lo, _, hi = rng.partition("-")
            if inst == instrument and int(lo) <= n <= int(hi or lo):
                c = rows("SELECT COUNT(*) AS speeches, COUNT(DISTINCT s.symbol) AS records FROM segment_topics st "
                         "JOIN segments s ON s.id = st.id WHERE st.topic = ?", (t["topic"],))[0]
                if c["speeches"]:
                    out.append({"topic": t["topic"], "label": t["label"], **c})
    return out


def decisions(p: dict, limit: int = 100) -> dict:
    where, params = ["1=1"], []
    if p.get("article"):
        where.append(f"c.final_article = ? AND {inst_sql('c.article_instrument')}")
        params += [int(p["article"]), instrument_of(p)]
    elif p.get("instrument") in INSTRUMENTS:
        where.append("d.instrument = ?")
        params.append("UDHR" if p["instrument"] == "UDHR" else "Covenants")
    if p.get("outcome"):
        where.append("c.outcome = ?" if p["outcome"] != "failed" else "c.outcome IN ('rejected','defeated')")
        if p["outcome"] != "failed":
            params.append(p["outcome"])
    if p.get("proposer"):
        where.append("c.proposers LIKE ?")
        params.append(f'%"{p["proposer"]}"%')
    if p.get("roll"):
        where.append("c.roll_call IS NOT NULL")
    if p.get("delegation"):
        # the roll-calls that name the delegation (exact name between quotes: "Niger" is not "Nigeria")
        where.append("c.roll_call LIKE ?")
        params.append('%"' + json.dumps(p["delegation"])[1:-1] + '"%')
    if p.get("symbol"):
        where.append("c.symbol = ?")
        params.append(p["symbol"])
    if p.get("figures"):
        where.append("c.yes IS NOT NULL")
    if p.get("limit"):
        limit = max(1, min(EXPORT_CAP, int(p["limit"])))
    offset = int(p.get("offset") or 0)
    base = f"FROM decisions c JOIN documents d ON d.symbol = c.symbol JOIN segments s ON s.id = c.segment_id WHERE {' AND '.join(where)}"
    total = rows(f"SELECT COUNT(*) AS n {base}", tuple(params))[0]["n"]
    res = rows(f"SELECT c.*, d.body, d.session, d.meeting_date, s.page_start, s.page_end, s.n AS para, s.kind {base} "
               f"ORDER BY d.meeting_date IS NULL, d.meeting_date, c.symbol, c.seq LIMIT ? OFFSET ?", (*params, limit, offset))
    for r in res:
        for k in ("proposers", "refs"):
            r[k] = json.loads(r[k] or "[]")
        r["roll_call"] = json.loads(r["roll_call"]) if r["roll_call"] else None
        if p.get("delegation") and r["roll_call"]:
            rc = r["roll_call"]
            r["delegation_vote"] = ("for" if p["delegation"] in rc["yes"] else "against" if p["delegation"] in rc["no"]
                                    else "abstained" if p["delegation"] in rc["abstentions"] else None)
        # a roll-call whose subject is only "A vote was taken by roll-call": the sentence before it says what was voted
        if r["roll_call"] and (len(r["subject"] or "") < 40 or re.match(r"A vote was taken", r["subject"] or "")):
            prev = rows("SELECT text FROM segments WHERE symbol = ? AND seq < ? AND kind != 'masthead' ORDER BY seq DESC LIMIT 1",
                        (r["symbol"], r["seq"]))
            ctx = prev[0]["text"][-260:] if prev else None
            r["context"] = None if ctx and re.search(r"\b(?:Against|Abstaining)\s*:", ctx) else ctx  # (not the list itself)
    return {"total": total, "offset": offset, "results": res}


def report_sponsors() -> dict[str, list[str]]:
    """The sponsors the session reports list for each amendment (data/concordance/amendment_sponsors.csv, checked
    by hand where the parsers disagreed): preferred to those read from the records."""
    path = ROOT / "data" / "concordance" / "amendment_sponsors.csv"
    # (an empty list: a document the hand check found has no sponsor, a compilation such as A/C.3/L.460)
    return {r["symbol"]: [w for w in r["sponsors"].split("|") if w] for r in csv.DictReader(path.open())} if path.exists() else {}


REPORT_SPONSORS = report_sponsors()


def amendments(p: dict) -> list[dict]:
    res = _amendments(str(p.get("instrument") or ""), str(p.get("article") or ""), str(p.get("proposer") or ""))
    q = str(p.get("q") or "").strip().lower()
    if not q:
        return res
    return [a for a in res if q in a["symbol"].lower() or any(q in pr.lower() for pr in a["proposers"])]


@memo
def _amendments(instrument: str, article: str, proposer: str) -> list[dict]:
    """Documents cited as amendments or proposals, with who proposed them (as the records say),
    the articles they were cited on and the decisions that name them."""
    p = {k: v for k, v in (("instrument", instrument), ("article", article), ("proposer", proposer)) if v}
    where, params = ["r.amendment = 1"], []
    if p.get("article"):
        where.append(f"s.final_article = ? AND {inst_sql('s.article_instrument')}")
        params += [int(p["article"]), instrument_of(p)]
    elif p.get("instrument") in INSTRUMENTS:
        where.append("d.instrument = ?")
        params.append("UDHR" if p["instrument"] == "UDHR" else "Covenants")
    refs = rows(f"SELECT r.ref_symbol, r.proposers, s.final_article, s.article_instrument, s.symbol, d.meeting_date FROM refs r "
                f"JOIN segments s ON s.id = r.segment_id JOIN documents d ON d.symbol = s.symbol WHERE {' AND '.join(where)}",
                tuple(params))
    in_corpus = {r["symbol"] for r in rows("SELECT symbol FROM documents")}
    by: dict[str, dict] = {}
    for r in refs:
        sym = r["ref_symbol"]
        # stage texts and meeting records are cited in debate, but they are not proposals
        if sym in STAGE_DOCS or re.search(r"/(?:SR|PV)\.", sym) or sym.startswith("A/PV"):
            continue
        # nor a compilation of amendments (A/C.3/L.460: the hand check found it has no sponsor)
        if sym in REPORT_SPONSORS and not REPORT_SPONSORS[sym]:
            continue
        # nor are reports and notes (E/1992, A/2910/Add.3), or a symbol the OCR cut short ("E/CN.4/1")
        if re.fullmatch(r"[AE]/\d+(?:/(?:Add|Rev|Corr)\.\d+)*|E/CN\.4/\d{1,2}|A/C\.3/\d{1,2}|[AE]/[A-Z]{1,2}\.\d+", sym):
            continue
        a = by.setdefault(sym, {"symbol": sym, "mentions": 0, "records": set(), "articles": {}, "proposers": {},
                                "first": None, "last": None, "in_corpus": sym in in_corpus})
        a["mentions"] += 1
        a["records"].add(r["symbol"])
        if r["final_article"]:
            key = (r["article_instrument"], r["final_article"])
            a["articles"][key] = a["articles"].get(key, 0) + 1
        for who in json.loads(r["proposers"] or "[]"):
            a["proposers"][who] = a["proposers"].get(who, 0) + 1
        if r["meeting_date"]:
            a["first"] = min(filter(None, [a["first"], r["meeting_date"]]))
            a["last"] = max(filter(None, [a["last"], r["meeting_date"]]))
    decided = {}
    for d in rows("SELECT c.refs, c.outcome, c.yes, c.no, c.abstentions, c.unanimous, c.symbol, c.segment_id, "
                  "c.final_article, c.article_instrument FROM decisions c WHERE c.refs != '[]'"):
        # on an article's page or under an article filter, only the votes on that article (an amendment to several
        # articles is put to the vote once for each)
        if p.get("article") and not (d["final_article"] == int(p["article"])
                                     and instrument_of(p) in (d["article_instrument"] or "").split("+")):
            continue
        for sym in json.loads(d["refs"]):
            decided.setdefault(sym, []).append({k: d[k] for k in ("outcome", "yes", "no", "abstentions", "unanimous",
                                                                    "symbol", "segment_id")})
    out = []
    for a in by.values():
        props = sorted(a["proposers"].items(), key=lambda kv: -kv[1])
        # the proposer the records name most often; others are co-sponsors or misreadings
        top = [w for w, c in props if c >= max(1, props[0][1] // 2)] if props else []
        source = "records" if top else None
        if a["symbol"] in REPORT_SPONSORS:
            top, source = REPORT_SPONSORS[a["symbol"]], "report"
        if p.get("proposer") and p["proposer"] not in top:
            continue
        out.append({**a, "records": sorted(a["records"]), "proposers": top, "proposers_from": source,
                    "articles": sorted(a["articles"], key=lambda k: -a["articles"][k]),
                    "decisions": decided.get(a["symbol"], [])})
    return sorted(out, key=lambda a: (a["first"] or "9999", a["symbol"]))


@memo
def actors() -> list[dict]:
    res = rows("SELECT delegation, COUNT(*) AS speeches, COUNT(DISTINCT speaker) AS speakers, "
               "COUNT(DISTINCT symbol) AS records FROM segments WHERE kind='speech' AND delegation IS NOT NULL "
               "GROUP BY 1 ORDER BY speeches DESC")
    from collections import Counter
    voted = Counter()
    for x in rows("SELECT roll_call FROM decisions WHERE roll_call IS NOT NULL"):
        rc = json.loads(x["roll_call"])
        voted.update(set(rc["yes"]) | set(rc["no"]) | set(rc["abstentions"]))  # exact names: "Niger" is not "Nigeria"
    for r in res:
        r["roll_calls"] = voted.get(r["delegation"], 0)
    return res


@memo
def actor(delegation: str, speaker: str | None = None) -> dict:
    cond, params = "kind='speech' AND delegation = ?", [delegation]
    if speaker:
        cond += " AND speaker = ?"
        params.append(speaker)
    params = tuple(params)
    speakers = rows(f"SELECT speaker, COUNT(*) AS speeches, MIN(d.meeting_date) AS first, MAX(d.meeting_date) AS last, "
                    f"COUNT(DISTINCT s.symbol) AS records FROM segments s JOIN documents d ON d.symbol = s.symbol "
                    f"WHERE {cond.replace('kind', 's.kind')} GROUP BY speaker ORDER BY speeches DESC", params)
    sessions = rows(f"SELECT d.body, d.session, COUNT(*) AS speeches, COUNT(DISTINCT s.symbol) AS records, "
                    f"MIN(d.meeting_date) AS first FROM segments s JOIN documents d ON d.symbol = s.symbol "
                    f"WHERE {cond.replace('kind', 's.kind')} GROUP BY d.body, d.session ORDER BY first", params)
    arts = rows(f"SELECT article_instrument AS instrument, final_article AS n, COUNT(*) AS speeches FROM segments "
                f"WHERE {cond} AND final_article IS NOT NULL GROUP BY 1, 2 ORDER BY speeches DESC, 1, 2", params)
    titles = {i: article_titles(i) for i in INSTRUMENTS}
    for a in arts:
        a["title"] = titles.get(a["instrument"], {}).get(str(a["n"]), "")
    out = {"delegation": delegation, "speaker": speaker, "speakers": speakers, "sessions": sessions, "articles": arts}
    if speaker:
        return out
    out["amendments"] = amendments({"proposer": delegation})
    out["proposed"] = decisions({"proposer": delegation}, limit=500)["results"]
    record = []
    for d in decisions({"roll": 1}, limit=500)["results"]:
        rc = d["roll_call"]
        how = "yes" if delegation in rc["yes"] else "no" if delegation in rc["no"] else "abstained" \
            if delegation in rc["abstentions"] else None
        if how:
            record.append({**d, "voted": how})
    out["roll_calls"] = record
    return out


@memo
def quality() -> dict:
    """The measurements behind the About page: OCR error, completeness, speaker checks, counts."""
    out: dict = {"version": VERSION, "built": dt.datetime.fromtimestamp(DB.stat().st_mtime).date().isoformat()}
    bench = ROOT / "eval" / "ocr_bench.json"
    if bench.exists():
        b = json.loads(bench.read_text())
        out["ocr"] = {g: round(v["cer"]["vote"] * 100, 1) for g, v in b["groups"].items()}
        out["ocr"]["all"] = round(b["overall"]["cer"]["vote"] * 100, 1)
        out["ocr_docs"] = b["overall"]["docs"]
    comp = ROOT / "eval" / "completeness_udhr.json"
    if comp.exists():
        rows_ = [r for r in json.loads(comp.read_text()) if r["status"] == "in_db" and r.get("coverage") is not None]
        tot = sum(r["sentences"] for r in rows_)
        out["completeness"] = round(100 * sum(r["coverage"] * r["sentences"] for r in rows_) / tot, 1) if tot else None
    cov = ROOT / "eval" / "coverage.json"  # eval/coverage.py: how much of the record the database holds
    if cov.exists():
        out["coverage"] = json.loads(cov.read_text())
    wrong = ROOT / "eval" / "what_went_wrong.md"  # the mistakes found on the way, dated (the author's text)
    if wrong.exists():
        paras = [x.strip() for x in wrong.read_text().split("\n\n") if x.strip()]
        items = [re.fullmatch(r"- \*\*(.+?)\*\* (.+)", ln.strip(), re.S) for ln in paras[1].splitlines()] if len(paras) > 2 else []
        out["what_went_wrong"] = {"intro": paras[0], "outro": paras[-1],
                                  "items": [{"date": m.group(1).rstrip("."), "text": m.group(2)} for m in items if m]}
    bench = ROOT / "eval" / "model_bench" / "results.json"  # eval/model_bench_score.py: the models on the same fixed items
    if bench.exists():
        out["model_bench"] = json.loads(bench.read_text())
    ledger = ROOT / "eval" / "ledger.json"  # eval/ledger.py: the AI work behind the database, totals only
    if ledger.exists():
        out["ledger"] = json.loads(ledger.read_text())
    gold = ROOT / "data" / "gold"
    out["gold_speeches"] = {p.stem.replace("speakers_", ""): sum(1 for _ in p.open()) for p in sorted(gold.glob("speakers_*.jsonl"))}
    out["counts"] = rows("SELECT d.instrument AS corpus, COUNT(DISTINCT d.symbol) AS documents, "
                         "SUM(s.kind='speech') AS speeches, SUM(s.kind='speech' AND s.speaker IS NOT NULL) AS attributed, "
                         "SUM(s.article_instrument IS NOT NULL AND s.kind='speech') AS tagged "
                         "FROM documents d JOIN segments s ON s.symbol = d.symbol GROUP BY 1")
    out["decisions"] = rows("SELECT COUNT(*) AS n, SUM(roll_call IS NOT NULL) AS roll_calls FROM decisions")[0]
    tags = gold / "article_tags.jsonl"
    if tags.exists():
        judged = [json.loads(l) for l in tags.read_text().splitlines()]
        # the latest hand check of each corpus (a round can cover one corpus only)
        out["tag_precision"] = {}
        # the latest round of each kind of record: the UDHR's, the Third Committee's on the Covenants
        # (1954-66) and the Commission's on the Covenant (1949-54), each numbered and headed differently
        # and the Declaration's 1947-48 drafting (Drafting Committee, Geneva working group), from 1948 apart
        # (a round that measured one change, "/concordance-fix", checked only the tags that change added)
        groups = {"UDHR": lambda st: st.startswith("UDHR") and not st.endswith(("/early", "/concordance-fix")),
                  "UDHR 1947-48": lambda st: st.startswith("UDHR") and st.endswith("/early") and "geneva_plenary" not in st,
                  "Geneva plenary 1947": lambda st: "geneva_plenary" in st,
                  "Covenants": lambda st: st.startswith("Covenants") and "CHR" not in st and not st.endswith("/early"),
                  "Covenant 1948": lambda st: st.startswith("Covenants") and st.endswith("/early"),
                  "Covenants CHR": lambda st: st.startswith("Covenants") and "CHR" in st}
        for name, member in groups.items():
            # the overall audit (strata ending "/audit") is reported on its own, below
            # (and a round that checked only the tags one change made, "-fix", measures that change, not the group;
            # "/check" is a side check: the L-series paragraphs, or the tags of a rule tested and not applied)
            rs = [r for r in judged if member(r["stratum"]) and not r["stratum"].endswith(("/audit", "-fix", "/check"))]
            if rs:
                last = max(r["round"] for r in rs)
                latest = [r for r in rs if r["round"] == last]
                # what the round covered, where its strata name a period ("Covenants/CHR 1953/any": "1953")
                years = sorted({m for r in latest for m in re.findall(r"\b(1\d{3}(?:-\d{2})?)\b", r["stratum"])})
                out["tag_precision"][name] = {"correct": sum(r["correct"] for r in latest), "checked": len(latest), "covers": years}
    audit = gold / "audit.json"  # eval/quality_audit.py: precision across all corpora, and coverage
    if audit.exists():
        out["audit"] = json.loads(audit.read_text())
    return out


def record(symbol: str) -> dict:
    doc = rows("SELECT * FROM documents WHERE symbol = ?", (symbol,))
    segs = rows("SELECT * FROM segments WHERE symbol = ? ORDER BY seq", (symbol,))
    for s in segs:  # (weaker suggestions, the Schabas index pages among them: metadata for our own audits, not served)
        s.pop("possible_article", None)
    prev_sym = next_sym = None
    if doc and doc[0].get("body") and doc[0].get("session"):
        is_sr = "/SR." in symbol
        sibs_rows = rows(
            "SELECT symbol, meeting_date FROM documents WHERE body = ? AND session = ? AND n_pages > 0 "
            "AND (CASE WHEN ? THEN symbol LIKE '%/SR.%' ELSE symbol NOT LIKE '%/SR.%' END)",
            (doc[0]["body"], doc[0]["session"], 1 if is_sr else 0))
        sibs = [r["symbol"] for r in sorted(
            sibs_rows,
            key=lambda r: (r["meeting_date"] or "9999", [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", r["symbol"])]))]
        if symbol in sibs:
            idx = sibs.index(symbol)
            prev_sym = sibs[idx - 1] if idx > 0 else None
            next_sym = sibs[idx + 1] if idx + 1 < len(sibs) else None
    return {"document": doc[0] if doc else None, "segments": segs, "prev_symbol": prev_sym, "next_symbol": next_sym}


def _mcp_respond(msg: dict) -> dict | None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    sys.modules.setdefault("server", sys.modules[__name__])
    from mcp import travaux_mcp  # noqa: PLC0415
    return travaux_mcp.respond(msg)


MCP_GUIDE_HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><title>UN Travaux Préparatoires · MCP</title>
<body style="font:16px/1.55 Georgia,serif;max-width:640px;margin:48px auto;padding:0 16px;color:#242328;background:#faf8f3">
<h1 style="font-weight:500;margin-bottom:8px">UN Travaux Préparatoires — MCP connector</h1>
<p>This address is a <a href="https://modelcontextprotocol.io/" style="color:#8d2f2f">Model Context Protocol</a> (Streamable HTTP) endpoint for AI assistants, not a web page.</p>
<ul>
  <li><b>Claude</b> (claude.ai, Desktop, mobile): Settings → Connectors → Add custom connector → paste <code>https://150.254.115.204/travaux-api/mcp</code></li>
  <li><b>Claude Code</b>: <code>claude mcp add --transport http travaux https://150.254.115.204/travaux-api/mcp -s user</code></li>
  <li><b>Claude Skill</b>: download <a href="/travaux/skills/travaux-research.zip" style="color:#8d2f2f">travaux-research.zip</a> (Settings → Capabilities → Skills → Upload skill) or see <a href="/travaux/skills/travaux-research/SKILL.md" style="color:#8d2f2f">SKILL.md</a></li>
</ul>
<p><a href="/travaux/#view=about&amp;sec=mcp" style="color:#8d2f2f">Full setup guide on the About page</a> · <a href="/travaux/" style="color:#8d2f2f">Open UN Travaux Préparatoires</a></p>
</body></html>""".encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def cors(self) -> None:
        """Let a page on another origin (the site on GitHub Pages) or an MCP client call the API."""
        if urlparse(self.path).path in ("/mcp", "/api/mcp"):
            self.send_header("Access-Control-Allow-Origin", "*")
            return
        if not CORS_ORIGINS:
            return
        self.send_header("Vary", "Origin, Accept-Encoding")
        origin = self.headers.get("Origin")
        if "*" in CORS_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", "*")
        elif origin in CORS_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)

    def send(self, body: bytes, ctype: str, code: int = 200) -> None:
        # text is compressed for a browser that accepts it (the facets are 280 KB, about 40 KB compressed)
        zipped = len(body) > 1024 and "gzip" in (self.headers.get("Accept-Encoding") or "") \
            and ctype.split(";")[0] in ("application/json", "text/html", "text/css", "text/javascript", "application/javascript", "text/plain")
        if zipped:
            body = gzip.compress(body, compresslevel=5)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if zipped:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        api = (self.path.startswith("/api/") and not self.path.startswith("/api/mcp")) or self.path == "/health"
        self.send_header("Cache-Control", f"public, max-age={CACHE_SECONDS}" if api and CACHE_SECONDS and code == 200 else "no-store")
        self.cors()
        self.end_headers()
        if not getattr(self, "_head", False):
            self.wfile.write(body)

    def do_OPTIONS(self):  # the browser's preflight for a cross-origin call or Streamable HTTP MCP
        self.send_response(204)
        self.cors()
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept, Authorization, X-API-Key, Mcp-Protocol-Version, Mcp-Session-Id")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self):
        self._head = False
        if urlparse(self.path).path in ("/mcp", "/api/mcp"):
            return self.send(
                json.dumps({"jsonrpc": "2.0", "error": {"code": -32000, "message": "Method not allowed (stateless server)."}, "id": None}).encode("utf-8"),
                "application/json; charset=utf-8",
                405,
            )
        self.error(405, "method not allowed")

    def proxy_audit(self, method: str) -> None:
        """Pass a request under /audit/ to the audit panel and its answer back (cookies and redirects included)."""
        path = urlparse(self.path).path
        if path == "/audit":
            self.send_response(301)
            self.send_header("Location", "audit/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) if method == "POST" else None
        headers = {k: self.headers[k] for k in ("Cookie", "Content-Type") if self.headers.get(k)}
        req = urllib.request.Request(AUDIT_URL + self.path[len("/audit"):], data=body, method=method, headers=headers)

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        try:
            r = urllib.request.build_opener(NoRedirect).open(req, timeout=60)
        except urllib.error.HTTPError as e:
            r = e
        except OSError:
            return self.error(502, "the audit panel is not running")
        data = r.read()
        self.send_response(r.status if hasattr(r, "status") else r.code)
        for k in ("Content-Type", "Set-Cookie", "Location"):
            if r.headers.get(k):
                self.send_header(k, r.headers[k])
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not getattr(self, "_head", False):
            self.wfile.write(data)

    def do_POST(self):
        self._head = False
        if AUDIT_URL and (self.path == "/audit" or self.path.startswith("/audit/")):
            return self.proxy_audit("POST")
        if urlparse(self.path).path == "/api/ask":  # a POST, so that the question stays out of the access logs
            return self.ask()
        if urlparse(self.path).path == "/api/check":  # a POST: the reader's text stays out of the logs, and is kept nowhere
            try:
                length = int(self.headers.get("Content-Length") or 0)
                p = json.loads(self.rfile.read(length).decode("utf-8")) if 0 < length <= 400_000 else None
                return self.json(check_text(str(p.get("text", ""))))
            except Exception:  # noqa: BLE001
                return self.error(400, "send {\"text\": \"your text\"} as JSON (at most 60,000 characters are checked)")
        if urlparse(self.path).path not in ("/mcp", "/api/mcp"):
            return self.error(404, "not found")
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 1_048_576:
                return self.send(
                    json.dumps({"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request size"}, "id": None}).encode("utf-8"),
                    "application/json; charset=utf-8",
                    400,
                )
            raw = self.rfile.read(length)
            msg = json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return self.send(
                json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}).encode("utf-8"),
                "application/json; charset=utf-8",
                400,
            )
        if isinstance(msg, list):
            outs = [r for m in msg if isinstance(m, dict) if (r := _mcp_respond(m)) is not None]
            if not outs:
                return self.send(b"", "application/json; charset=utf-8", 202)
            return self.json(outs)
        if isinstance(msg, dict):
            out = _mcp_respond(msg)
            if out is None:
                return self.send(b"", "application/json; charset=utf-8", 202)
            return self.json(out)
        return self.send(
            json.dumps({"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": None}).encode("utf-8"),
            "application/json; charset=utf-8",
            400,
        )

    def ask(self) -> None:
        if not ask_ready():
            return self.error(503, "Ask is not available on this server")
        try:
            length = int(self.headers.get("Content-Length") or 0)
            p = json.loads(self.rfile.read(length).decode("utf-8")) if 0 < length <= 8192 else None
            q, instrument = str(p.get("q", "")), str(p.get("instrument", ""))
        except Exception:  # noqa: BLE001
            return self.error(400, "send {\"q\": \"your question\"} as JSON")
        try:
            out = ask(q, instrument)
            return self.error(429, out["error"]) if "error" in out else self.json(out)
        except (urllib.error.URLError, TimeoutError, KeyError) as exc:
            print(f"ask: Voyage did not answer: {exc!r}", file=sys.stderr)
            return self.error(502, "The search service did not answer. Try again in a moment.")

    def error(self, code: int, message: str) -> None:
        self.send(json.dumps({"error": message}).encode("utf-8"), "application/json; charset=utf-8", code)

    def json(self, obj) -> None:
        self.send(json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        self._serve(head=False)

    def do_HEAD(self):  # monitors and crawlers ask with HEAD: the headers of the GET, without its body
        self._serve(head=True)

    def _serve(self, head: bool) -> None:
        self._head = head
        if AUDIT_URL and (self.path == "/audit" or self.path.startswith("/audit/") or self.path.startswith("/audit?")):
            return self.proxy_audit("GET")
        try:
            self.route()
        except (ValueError, OverflowError):  # a parameter that is not the number it should be
            self.send(json.dumps({"error": "bad parameter"}).encode("utf-8"), "application/json; charset=utf-8", 400)
        except Exception as exc:  # noqa: BLE001  the client gets no trace; the log does
            print(f"error on {self.path}: {exc!r}", file=sys.stderr)
            self.send(json.dumps({"error": "server error"}).encode("utf-8"), "application/json; charset=utf-8", 500)

    def route(self):
        u = urlparse(self.path)
        p = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/health":
            return self.json({"ok": True, "version": VERSION, "documents": rows("SELECT COUNT(*) AS n FROM documents")[0]["n"],
                              "ask": ask_ready()})
        if u.path in ("/mcp", "/api/mcp"):
            if "text/html" in (self.headers.get("Accept") or ""):
                return self.send(MCP_GUIDE_HTML, "text/html; charset=utf-8", 200)
            return self.send(
                json.dumps({"jsonrpc": "2.0", "error": {"code": -32000, "message": "Method not allowed (stateless server: use POST /mcp)."}, "id": None}).encode("utf-8"),
                "application/json; charset=utf-8",
                405,
            )
        if u.path == "/api/facets":
            return self.json(facets())
        if u.path == "/api/search":
            return self.json(search(p))
        if u.path == "/api/record":
            return self.json(record(p.get("symbol", "")))
        if u.path == "/api/records":
            return self.json(records())
        if u.path == "/api/article-titles":
            return self.json(article_titles(instrument_of(p)) if p.get("instrument") else
                             {i: article_titles(i) for i in INSTRUMENTS})
        if u.path == "/api/articles":
            return self.json(articles_index(instrument_of(p)))
        if u.path == "/api/article":
            if p.get("instrument") and p["instrument"] not in INSTRUMENTS:
                return self.error(400, "unknown instrument")
            n = int(p.get("n") or 0)
            if not 1 <= n <= INSTRUMENTS[instrument_of(p)]:
                return self.error(404, "no such article")
            return self.json(article(n, instrument_of(p)))
        if u.path == "/api/actors":
            return self.json(actors())
        if u.path == "/api/actor":
            return self.json(actor(p.get("delegation", ""), p.get("speaker")))
        if u.path == "/api/decisions":
            return self.json(decisions(p))
        if u.path == "/api/amendments":
            res = amendments(p)
            if p.get("limit"):  # a page of them (the view asks for 100 at a time); without limit, the whole list as before
                off, lim = max(0, int(p.get("offset") or 0)), max(1, min(500, int(p["limit"])))
                return self.json({"total": len(res), "offset": off, "results": res[off:off + lim]})
            return self.json(res)
        if u.path == "/api/quality":
            return self.json(quality())
        if u.path == "/api/symbols":
            return self.json([r["symbol"] for r in rows("SELECT symbol FROM documents")])
        if u.path == "/api/export":
            body, ctype, name = export(p)
            self.send_response(200)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not self._head:
                self.wfile.write(body)
            return
        if u.path.startswith("/pdf/"):
            f = (RAW / Path(unquote(u.path[5:])).name)
            if f.exists() and f.suffix == ".pdf":
                return self.send(f.read_bytes(), "application/pdf")
            return self.send(b"not found", "text/plain", 404)
        name = "index.html" if u.path in ("", "/") else u.path.lstrip("/")
        f = (SITE / name).resolve()
        if f.is_file() and SITE.resolve() in f.parents:
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            return self.send(f.read_bytes(), ctype + ("; charset=utf-8" if ctype.startswith("text") else ""))
        self.send(b"not found", "text/plain", 404)


if __name__ == "__main__":
    if not DB.exists():
        raise SystemExit("data/travaux.sqlite3 missing: run python3 api/build_db.py first")
    print(f"Travaux DB server: http://{HOST}:{PORT} (db {DB})")

    def warm():  # the first reader should not wait for what every page asks for, nor Ask for its vectors (about 6 s)
        for f in (facets, quality, *((ask_index,) if ask_ready() else ())):
            try:
                f()
            except Exception as exc:  # noqa: BLE001
                print(f"warm-up of {f.__name__} failed: {exc!r}", file=sys.stderr)
    threading.Thread(target=warm, daemon=True).start()
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
