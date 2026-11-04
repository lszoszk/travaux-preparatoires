#!/usr/bin/env python3
"""MCP server over the UN Travaux Préparatoires database (stdio and Streamable HTTP).

Six tools over the same functions as api/server.py, reading data/travaux.sqlite3 directly:

  search_travaux            full-text and field-prefix search over speeches, chair turns, votes and paragraphs
  lookup_travaux            one passage in full (with how its article tag was set and a link to the scan), or a record's outline
  article_history_travaux   an article's final text, draft stages, meetings, votes and amendments
  delegation_travaux        a delegation's (or delegate's) speeches by article, sessions, amendments and roll-call votes
  decisions_travaux         search the 6,768 recorded decisions and 302 roll-call votes by article, outcome or delegation
  amendments_travaux        search the 2,716 indexed amendments and proposals (L-series) by article, proposer or symbol

Transports:
  1. Streamable HTTP: served by api/server.py at POST /mcp (https://150.254.115.204/travaux-api/mcp)
  2. Local stdio: newline-delimited JSON-RPC 2.0 on stdin and stdout:
       claude mcp add --scope user travaux -- python3 /ABSOLUTE/PATH/TO/travaux/mcp/travaux_mcp.py
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "api") not in sys.path:
    sys.path.insert(0, str(ROOT / "api"))
import server  # noqa: E402


def _coverage() -> str:
    """One sentence from eval/coverage.json: how much of the record is held, and what is not."""
    path = ROOT / "eval" / "coverage.json"
    if not path.exists():
        return ""
    c = json.loads(path.read_text())
    return (
        f"Coverage: {c['records']['pct']:.1f}% of the meeting records ({c['records']['held']} of {c['records']['expected']}) "
        f"and {c['documents']['pct']:.1f}% of other drafting documents ({c['documents']['held']} of {c['documents']['expected']}) are held; "
        f"of the documents cited inside speeches, {c['cited']['pct']}% ({c['cited']['held']} of {c['cited']['distinct']}) are held in full text "
        f"(for the remaining L-series amendments, their sponsors and vote outcomes are indexed from the meeting records and session reports). "
    )


COVERAGE = _coverage()
VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
INSTRUCTIONS = (
    "UN Travaux Préparatoires of the UDHR (1946–48), the ICCPR and the ICESCR (1949–66): 2,160 UN drafting documents "
    "(836 on the Declaration, 1,324 on the Covenants) split into 29,694 speeches (each with its speaker and delegation), chair turns, "
    "6,768 decisions (302 roll-call votes) and 2,716 indexed amendments, with speaker, delegation, date, page or paragraph pinpoint, "
    "and the article under discussion mapped from each session's draft numbering to the final articles. "
    "Cite by UN symbol and pinpoint as given (e.g. 'A/C.3/SR.290, paras. 7–15 (Hoffmeister, Czechoslovakia)' or "
    "'E/CN.4/SR.60, p. 10 (Malik, Lebanon)'). Summary records (SR) paraphrase what delegates said in the third person; "
    "plenary records (A/PV) and draft texts are verbatim. The text is multi-engine OCR (0.5% character error overall): "
    "check the linked UN scan (lookup_travaux gives the page) before quoting. "
    "Article tags come from the record's headings, the chair and the session reports' meeting lists, checked by a classifier "
    "(95% ± 4 precision on the Round 127 stratified blind audit). "
    + COVERAGE +
    "Speeches in general debates that no single article fits carry a topic tag instead (search_travaux topic: self_determination, "
    "two_covenants, implementation, petitions, federal_clause, territorial_clause, reservations, form_of_bill, or general). "
    "Ten documents exist only in French in UN archives; they are machine-translated and marked '** Machine translation from French': "
    "never quote them as official UN English text, and always cite the French original."
)

TOOLS = [
    {
        "name": "search_travaux",
        "description": (
            "Search the drafting records of the UDHR, ICCPR and ICESCR. Returns passages (speeches, chair's statements, "
            "votes, document paragraphs) with citation, date, body, session and the final/draft article tag. "
            "Supports Boolean operators (AND, OR, NOT), exact phrases in quotes, prefix wildcards (scientif*), "
            "and field prefixes (speaker:cassin, delegation:france, art:18, inst:iccpr, doc:A/C.3/SR.127, topic:implementation)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search words, \"exact phrase\", Boolean AND/OR/NOT, prefix*, or field prefixes. Omit to list passages matching the filters in chronological record order.",
                },
                "instrument": {"type": "string", "enum": ["UDHR", "ICCPR", "ICESCR"]},
                "article": {"type": "integer", "description": "Final article number (UDHR 1–30, ICCPR 1–53, ICESCR 1–31; defaults to UDHR if instrument omitted)"},
                "delegation": {"type": "string", "description": "Canonical UN delegation name, e.g. 'France', 'United Kingdom', 'United States of America', 'Poland'"},
                "speaker": {"type": "string", "description": "Delegate surname in capitals as recorded, e.g. 'CASSIN', 'MALIK', 'ROOSEVELT'"},
                "symbol": {"type": "string", "description": "UN document symbol, e.g. 'A/C.3/SR.127', 'E/CN.4/SR.317'"},
                "session": {"type": "string", "description": "Body and session filter, e.g. 'Commission on Human Rights|8th session (1952)'"},
                "kind": {"type": "string", "enum": ["speech", "chair", "vote", "heading", "paragraph", "all"]},
                "topic": {
                    "type": "string",
                    "enum": [
                        "self_determination", "two_covenants", "implementation", "petitions",
                        "federal_clause", "territorial_clause", "reservations", "form_of_bill", "general",
                    ],
                    "description": "Cross-cutting general debate question for speeches not tied to a single article.",
                },
                "sort": {"type": "string", "enum": ["relevance", "date"], "description": "'relevance' (default for queries) or 'date' (chronological)"},
                "include_translations": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include the 10 French-only documents as clearly marked machine translations (false excludes them).",
                },
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                "offset": {"type": "integer", "default": 0, "minimum": 0},
            },
        },
    },
    {
        "name": "lookup_travaux",
        "description": (
            "Read one passage in full by its id (from search_travaux): full text, citation, date, article tag provenance, "
            "the heading or chair's announcement before it, and the UN scan link. Or pass a UN document symbol to get "
            "the record's complete outline (every speech, chair turn, vote and paragraph with its id and pinpoint)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Passage id, e.g. 'a_c.3_sr.127-0005'"},
                "symbol": {"type": "string", "description": "UN document symbol, e.g. 'A/C.3/SR.127'"},
            },
        },
    },
    {
        "name": "article_history_travaux",
        "description": (
            "The complete drafting history of one article (UDHR 1–30, ICCPR 1–53, ICESCR 1–31): its adopted text, "
            "the draft texts stage by stage (with draft article numbers and dates), the meetings that debated it "
            "(with participating delegations), the votes taken (figures and outcomes) and the amendments submitted."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["article"],
            "properties": {
                "instrument": {"type": "string", "enum": ["UDHR", "ICCPR", "ICESCR"], "default": "UDHR"},
                "article": {"type": "integer", "description": "Final article number (UDHR 1–30, ICCPR 1–53, ICESCR 1–31)"},
            },
        },
    },
    {
        "name": "delegation_travaux",
        "description": (
            "Profile of one delegation (or one individual delegate within a delegation): its speakers, sessions attended, "
            "speeches by article (sorted from most-debated article down), amendments sponsored, proposals put to the vote, "
            "and how it voted in roll-calls."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["delegation"],
            "properties": {
                "delegation": {"type": "string", "description": "Delegation name as recorded, e.g. 'France', 'Poland', 'India', 'United Kingdom', 'International Labour Organisation'"},
                "speaker": {"type": "string", "description": "Optional speaker surname in capitals (e.g. 'CASSIN', 'ROOSEVELT') to scope to one delegate."},
            },
        },
    },
    {
        "name": "decisions_travaux",
        "description": (
            "Search the 6,768 recorded votes and decisions (including 302 roll-call votes) across the drafting of the UDHR, "
            "ICCPR and ICESCR. Filter by instrument, final article, outcome (adopted/rejected), delegation (proposer or roll-call voter), "
            "roll-call only, or text query."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "instrument": {"type": "string", "enum": ["UDHR", "ICCPR", "ICESCR"]},
                "article": {"type": "integer", "description": "Final article number"},
                "outcome": {"type": "string", "enum": ["adopted", "rejected"]},
                "delegation": {"type": "string", "description": "Delegation name (matches proposers and roll-call voters)"},
                "roll_call_only": {"type": "boolean", "default": False, "description": "True to return only roll-call votes with per-country breakdown"},
                "query": {"type": "string", "description": "Substring filter on subject, symbol or proposer"},
                "limit": {"type": "integer", "default": 25, "minimum": 1, "maximum": 100},
                "offset": {"type": "integer", "default": 0, "minimum": 0},
            },
        },
    },
    {
        "name": "amendments_travaux",
        "description": (
            "Search the 2,716 documents cited as amendments or proposals (L-series and working papers), with their sponsor "
            "delegations (from session reports and meeting records), target articles, meeting symbols, whether full text is "
            "in the database, and the votes taken on them."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "instrument": {"type": "string", "enum": ["UDHR", "ICCPR", "ICESCR"]},
                "article": {"type": "integer", "description": "Final article number"},
                "proposer": {"type": "string", "description": "Sponsoring delegation name, e.g. 'Belgium', 'Poland'"},
                "query": {"type": "string", "description": "Symbol or sponsor substring, e.g. 'L.93' or 'A/C.3/L.'"},
                "limit": {"type": "integer", "default": 25, "minimum": 1, "maximum": 100},
                "offset": {"type": "integer", "default": 0, "minimum": 0},
            },
        },
    },
]


def tag(h: dict) -> str:
    if not h.get("final_article"):
        return ""
    draft = h.get("draft_article")
    return f"{h['article_instrument']} art. {h['final_article']}" + (
        f" (draft {draft})" if draft and str(draft) != str(h["final_article"]) else ""
    )


def clean(s: str | None) -> str:
    return " ".join((s or "").replace("\x01", "").replace("\x02", "").split())


def search_travaux(a: dict) -> str:
    p = {k: a[k] for k in ("instrument", "article", "delegation", "speaker", "symbol", "session", "kind", "topic") if a.get(k)}
    if a.get("query") or a.get("q"):
        p["q"] = a.get("query") or a.get("q")
    if a.get("sort") == "date":
        p["sort"] = "date"
    if a.get("include_translations") is False or str(a.get("translations", "1")).lower() in ("0", "false"):
        p["translations"] = "0"
    p["offset"] = int(a.get("offset") or 0)
    r = server.search(p, limit=max(1, min(int(a.get("limit") or 10), 50)))
    if r.get("error"):
        return r["error"]
    resolved = f" (filters: {', '.join(f'{k}={v}' for k, v in r['resolved'].items())})" if r.get("resolved") else ""
    lines = [f"{r['total']} passages{resolved}; showing {p['offset'] + 1}-{p['offset'] + len(r['results'])}."]
    for h in r["results"]:
        meta = ", ".join(
            x for x in (
                h.get("meeting_date") or "undated",
                h.get("body"),
                h.get("session"),
                tag(h),
                f"general debate: {h['topic']}" if h.get("topic") else "",
            ) if x
        )
        mt = f"\n  ** {server.translation_note(h)}" if h.get("machine_translated") else ""
        lines.append(f"\n{server.citation(h)} [{meta}] id={h['id']}{mt}\n  {clean(h.get('snippet'))[:600]}")
    return "\n".join(lines)


def lookup_travaux(a: dict) -> str:
    if a.get("id"):
        rows = server.rows(
            "SELECT s.*, d.body, d.session, d.meeting_date, d.pdf_url, d.local_pdf, d.machine_translated, "
            "d.source_language, d.translation_model, d.translation_date FROM segments s "
            "JOIN documents d ON d.symbol = s.symbol WHERE s.id = ?",
            (a["id"],),
        )
        if not rows:
            return f"No passage {a['id']}."
        h = rows[0]
        before = server.rows(
            "SELECT kind, text FROM segments WHERE symbol = ? AND seq < ? AND (kind = 'heading' OR "
            "(kind IN ('chair', 'procedural', 'vote') AND lower(text) LIKE '%article%')) "
            "ORDER BY seq DESC LIMIT 1",
            (h["symbol"], h["seq"]),
        )
        out = [server.citation(h), f"{h.get('meeting_date') or 'undated'} · {h.get('body')} · {h.get('session')}"]
        if h.get("final_article"):
            conf = f", classifier confidence {h['article_confidence']:.2f}" if h.get("article_confidence") is not None else ""
            out.append(f"Article: {tag(h)} ({h.get('article_mapping')}{conf})")
        elif h.get("article_mapping"):
            out.append(f"No article tag: {h['article_mapping']}")
        if h.get("machine_translated"):
            out.append("** " + server.translation_note(h))
        if before:
            out.append(f"Set by the {before[0]['kind']}: {clean(before[0]['text'])[:300]}")
        out.append(
            f"Scan: {h.get('pdf_url') or 'https://undocs.org/' + h['symbol']} page {h['page_start']}"
            + (f" (local: data/raw/{h['local_pdf']})" if h.get("local_pdf") else "")
        )
        out.append("\n" + clean(h["text"]))
        return "\n".join(out)
    if a.get("symbol"):
        rec = server.record(a["symbol"])
        doc = rec["document"]
        if not doc:
            return f"No record {a['symbol']} in corpus (check https://undocs.org/{a['symbol']})."
        out = [
            f"{doc['symbol']} · {doc.get('meeting_date') or 'undated'} · {doc.get('body')} · {doc.get('session')} · "
            f"{doc.get('n_pages')} pages · {doc.get('pdf_url') or 'https://undocs.org/' + doc['symbol']}"
        ]
        if doc.get("machine_translated"):
            out.append("** " + server.translation_note(doc))
        for s in rec["segments"]:
            if s["kind"] == "masthead":
                continue
            full = {**doc, **s}
            head = server.citation(full) if s["kind"] in ("speech", "chair") else f"{s['kind']}, {server.pinpoint(full)}"
            out.append(f"- {head}{' [' + tag(s) + ']' if tag(s) else ''} id={s['id']}: {clean(s['text'])[:140]}")
        return "\n".join(out)
    return "Give an id (from search_travaux) or a symbol."


def article_history_travaux(a: dict) -> str:
    inst = a.get("instrument") or "UDHR"
    if inst not in server.INSTRUMENTS:
        return f"Unknown instrument '{inst}'. Use UDHR, ICCPR or ICESCR."
    n = int(a["article"])
    if not (1 <= n <= server.INSTRUMENTS[inst]):
        return f"{inst} has articles 1–{server.INSTRUMENTS[inst]} (got {n})."
    art = server.article(n, inst)
    out = [f"{inst} article {art['n']}: {art['title']}", f"Final text: {clean(art['final_text'])}", "\nDrafts:"]
    for d in art["evolution"]:
        out.append(
            f"- {d.get('label') or d.get('stage')} ({d.get('symbol')}, {d.get('date') or ''}), "
            f"article {d.get('draft_article')}: {clean(d.get('text'))[:400]}"
        )
    out.append(f"\nMeetings and documents ({len(art['meetings'])}):")
    for m in art["meetings"]:
        out.append(
            f"- {m['symbol']} {m.get('meeting_date') or 'undated'} {m.get('body')}: {m.get('speeches')} speeches; "
            f"{', '.join((m.get('delegations') or [])[:12])}"
        )
    out.append(f"\nVotes ({len(art['decisions'])}):")
    for d in art["decisions"]:
        fig = f"{d['yes']}-{d['no']}-{d['abstentions']}" if d.get("yes") is not None else ("unanimously" if d.get("unanimous") else "")
        out.append(
            f"- {d['symbol']} {d.get('meeting_date') or ''}: {d.get('outcome')} {fig} | {clean(d.get('subject'))[:160]}"
            + (f" | proposers: {', '.join(d['proposers'])}" if d.get("proposers") else "")
        )
    out.append(f"\nAmendments ({len(art['amendments'])}):")
    for m in art["amendments"]:
        out.append(f"- {m.get('symbol')}: {', '.join(m.get('proposers') or []) or 'proposer not read'}")
    return "\n".join(out)


def delegation_travaux(a: dict) -> str:
    r = server.actor(a["delegation"], a.get("speaker"))
    if not r["speakers"]:
        return f"No speeches recorded for '{a['delegation']}' (use the canonical UN name, e.g. 'United Kingdom', 'United States of America')."
    header = f"{r['delegation']}" + (f" — {r['speaker']}" if r.get("speaker") else "")
    out = [
        header,
        "Speakers: " + "; ".join(f"{s['speaker']} ({s['speeches']} speeches, {s['first']} to {s['last']})" for s in r["speakers"][:20]),
        "\nSessions: " + "; ".join(f"{s['body']} {s['session']} ({s['speeches']} speeches)" for s in r.get("sessions", [])[:15]),
        "\nSpeeches by article:",
    ]
    out += [f"- {x['instrument']} {x['n']} {x['title']}: {x['speeches']}" for x in r["articles"][:30]]
    if not r.get("speaker"):
        out.append(f"\nAmendments sponsored ({len(r.get('amendments', []))}):")
        for m in r.get("amendments", [])[:30]:
            arts = ", ".join(f"{i} {n}" for i, n in (m.get("articles") or [])[:4])
            out.append(f"- {m['symbol']} ({m.get('first') or 'undated'}){' [' + arts + ']' if arts else ''}: {', '.join(m.get('proposers') or [])}")
        out.append(f"\nProposals put to the vote ({len(r.get('proposed', []))}):")
        for d in r.get("proposed", [])[:30]:
            out.append(f"- {d['symbol']} {d.get('meeting_date') or ''}: {d.get('outcome')} | {clean(d.get('subject'))[:140]}")
        out.append(f"\nRoll-call votes ({len(r.get('roll_calls', []))}):")
        for d in r.get("roll_calls", [])[:30]:
            out.append(f"- {d['symbol']} ({d.get('meeting_date') or ''}): voted {d['voted']} | {clean(d.get('subject'))[:120]}")
    return "\n".join(out)


def decisions_travaux(a: dict) -> str:
    p = {}
    if a.get("instrument"):
        p["instrument"] = a["instrument"]
    if a.get("article"):
        p["article"] = str(a["article"])
        if not p.get("instrument"):
            p["instrument"] = "UDHR"
    if a.get("outcome"):
        p["outcome"] = a["outcome"]
    if a.get("delegation"):
        p["delegation"] = a["delegation"]
    if a.get("roll_call_only") or a.get("roll"):
        p["roll"] = "1"
    if a.get("query") or a.get("q"):
        p["q"] = a.get("query") or a.get("q")
    off = max(0, int(a.get("offset") or 0))
    lim = max(1, min(100, int(a.get("limit") or 25)))
    p["offset"] = off
    p["limit"] = lim
    r = server.decisions(p)
    lines = [f"{r['total']} decisions; showing {off + 1}-{off + len(r['results'])}."]
    for d in r["results"]:
        fig = f"{d['yes']}–{d['no']}–{d.get('abstentions') if d.get('abstentions') is not None else '?'}" if d.get("yes") is not None else ("unanimously" if d.get("unanimous") else "no tally")
        art = f" [{d['article_instrument']} art. {d['final_article']}]" if d.get("final_article") else ""
        props = f" | proposers: {', '.join(d['proposers'])}" if d.get("proposers") else ""
        rc_str = ""
        if d.get("roll_call"):
            rc = d["roll_call"]
            rc_str = f"\n  Roll-call — Yes ({len(rc.get('yes', []))}): {', '.join(rc.get('yes', []))}; No ({len(rc.get('no', []))}): {', '.join(rc.get('no', []))}; Abst. ({len(rc.get('abstentions', []))}): {', '.join(rc.get('abstentions', []))}"
        lines.append(f"- {d['symbol']} ({d.get('meeting_date') or 'undated'}){art} seg={d.get('segment_id')}: {d.get('outcome')} ({fig}){props} | {clean(d.get('subject'))[:220]}{rc_str}")
    return "\n".join(lines)


def amendments_travaux(a: dict) -> str:
    p = {}
    if a.get("instrument"):
        p["instrument"] = a["instrument"]
    if a.get("article"):
        p["article"] = str(a["article"])
        if not p.get("instrument"):
            p["instrument"] = "UDHR"
    if a.get("proposer"):
        p["proposer"] = a["proposer"]
    if a.get("query") or a.get("q"):
        p["q"] = a.get("query") or a.get("q")
    all_res = server.amendments(p)
    off = max(0, int(a.get("offset") or 0))
    lim = max(1, min(100, int(a.get("limit") or 25)))
    page = all_res[off:off + lim]
    lines = [f"{len(all_res)} amendments; showing {off + 1}-{off + len(page)}."]
    for m in page:
        arts = ", ".join(f"{i} art. {n}" for i, n in (m.get("articles") or [])[:5])
        decs = "; ".join(
            f"{d['outcome']}" + (f" {d['yes']}–{d['no']}" if d.get("yes") is not None else "") + f" ({d['symbol']})"
            for d in (m.get("decisions") or [])[:3]
        )
        in_db = "full text in corpus" if m.get("in_corpus") else "cited in records"
        lines.append(
            f"- {m['symbol']} ({m.get('first') or 'undated'}, {in_db}): "
            f"proposers: {', '.join(m.get('proposers') or []) or 'not recorded'}"
            + (f" | articles: {arts}" if arts else "")
            + (f" | records: {', '.join((m.get('records') or [])[:5])}" if m.get("records") else "")
            + (f" | votes: {decs}" if decs else "")
        )
    return "\n".join(lines)


HANDLERS = {
    "search_travaux": search_travaux,
    "lookup_travaux": lookup_travaux,
    "article_history_travaux": article_history_travaux,
    "delegation_travaux": delegation_travaux,
    "decisions_travaux": decisions_travaux,
    "amendments_travaux": amendments_travaux,
}


def respond(msg: dict) -> dict | None:
    method, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if mid is None:  # a notification (notifications/initialized ...): no answer
        return None
    if method == "initialize":
        asked = params.get("protocolVersion")
        result = {
            "protocolVersion": asked if asked in VERSIONS else VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "travaux", "version": "0.9.0"},
            "instructions": INSTRUCTIONS,
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        name = params.get("name")
        if name not in HANDLERS:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool {name}"}}
        try:
            result = {"content": [{"type": "text", "text": HANDLERS[name](params.get("arguments") or {})}], "isError": False}
        except Exception as exc:  # a tool error is the tool's answer, not a protocol failure
            traceback.print_exc(file=sys.stderr)
            result = {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> int:
    if not server.DB.exists():
        print("data/travaux.sqlite3 missing: run python3 api/build_db.py first", file=sys.stderr)
        return 1
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            out = respond(msg)
        if out is not None:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
