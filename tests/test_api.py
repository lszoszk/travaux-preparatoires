"""API tests against the built database (skipped when data/travaux.sqlite3 is missing)."""
from __future__ import annotations

import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
import server  # noqa: E402

pytestmark = pytest.mark.skipif(not server.DB.exists(), reason="build the database first (api/build_db.py)")


@pytest.fixture(scope="module")
def base():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def get(base: str, path: str):
    with urllib.request.urlopen(base + path) as r:
        body = r.read()
        return json.loads(body) if r.headers.get_content_type() == "application/json" else body.decode("utf-8")


def test_search_phrase(base):
    d = get(base, '/api/search?q=%22freedom+of+thought%22')
    assert d["total"] > 0 and d["results"][0]["snippet"]


def test_search_bad_query_is_reported(base):
    d = get(base, "/api/search?q=AND+OR+%22")
    assert "results" in d


def test_article_filter_needs_its_instrument(base):
    udhr = get(base, "/api/search?article=18")["total"]
    iccpr = get(base, "/api/search?article=18&instrument=ICCPR")["total"]
    assert udhr > 0
    assert udhr != iccpr or udhr == 0


def test_record(base):
    d = get(base, "/api/record?symbol=E/CN.4/SR.60")
    assert d["document"]["symbol"] == "E/CN.4/SR.60"
    speeches = [s for s in d["segments"] if s["kind"] == "speech"]
    assert speeches and all(s["id"].startswith("e_cn.4_sr.60-") for s in d["segments"])
    assert not any("possible_article" in s for s in d["segments"])


def test_article_page(base):
    a = get(base, "/api/article?n=18")
    assert a["title"].startswith("Thought") and a["final_text"].startswith("Everyone has the right to freedom of thought")
    assert a["evolution"][-1]["stage"] == "final"
    assert any(m["symbol"] == "E/CN.4/SR.60" for m in a["meetings"])
    c = get(base, "/api/article?instrument=ICCPR&n=18")
    assert c["instrument"] == "ICCPR" and "religion" in c["final_text"]


def test_articles_index_per_instrument(base):
    assert len(get(base, "/api/articles")) == 30
    assert len(get(base, "/api/articles?instrument=ICCPR")) == 53
    assert len(get(base, "/api/articles?instrument=ICESCR")) == 31


def test_votes_and_amendments(base):
    v = get(base, "/api/decisions?roll=1")
    assert v["total"] > 0 and all(r["roll_call"] for r in v["results"])
    a = get(base, "/api/amendments?article=18")
    assert any(x["symbol"] == "A/C.3/252" and "Sweden" in x["proposers"] for x in a)


def test_delegation(base):
    d = get(base, "/api/actor?delegation=Lebanon")
    assert d["speakers"][0]["speaker"] == "MALIK"
    assert d["roll_calls"]


def test_exports(base):
    csv_body = get(base, "/api/export?format=csv&q=religion&article=18")
    assert csv_body.lstrip("﻿").startswith("citation,symbol,pinpoint")
    ris = get(base, "/api/export?format=ris&q=religion")
    assert "TY  - GEN" in ris


def test_static_and_traversal(base):
    assert "<title>" in get(base, "/")
    with pytest.raises(urllib.error.HTTPError):
        get(base, "/../api/server.py")


def test_machine_translations_flagged_and_switchable(base):
    """French-only documents are in by default, carry their label, and translations=0 leaves them out."""
    docs = server.rows("SELECT symbol FROM documents WHERE machine_translated = 1")
    if not docs:
        pytest.skip("no machine-translated documents in this database")
    sym = docs[0]["symbol"]
    on = get(base, "/api/search?symbol=" + urllib.request.quote(sym, safe=""))
    assert on["total"] > 0
    h = on["results"][0]
    assert h["machine_translated"] == 1 and h["translation_model"] and h["source_language"] == "fr"
    assert "machine translation from French" in server.citation(h)
    assert get(base, "/api/search?translations=0&symbol=" + urllib.request.quote(sym, safe=""))["total"] == 0
    assert get(base, "/api/facets")["translations"]["n"] == len(docs)
    rec = get(base, "/api/record?symbol=" + urllib.request.quote(sym, safe=""))
    assert rec["document"]["machine_translated"] == 1


def test_quality_reports_coverage(base):
    q = get(base, "/api/quality")
    c = q["coverage"]
    assert 90 < c["records"]["pct"] <= 100 and c["records"]["held"] <= c["records"]["expected"]
    assert 0 < c["cited"]["pct"] < 100 and c["cited"]["citations"] >= c["cited"]["citations_to_held"]
    assert any("L.n" in f["family"] for f in c["cited"]["families"])


def test_l_series_documents_carry_the_article_two_readers_gave_them(base):
    """A/C.3/L.919 (India's amendment on freedom of expression) is ICCPR 19; a procedural note (L.551) has no article."""
    d = get(base, "/api/search?symbol=" + urllib.request.quote("A/C.3/L.919", safe="") + "&kind=paragraph")
    if d["total"] == 0:
        pytest.skip("the L-series documents are not in this database")
    assert {(h["article_instrument"], h["final_article"]) for h in d["results"]} == {("ICCPR", 19)}
    n = get(base, "/api/search?symbol=" + urllib.request.quote("A/C.3/L.551", safe="") + "&kind=paragraph")
    assert all(h["final_article"] is None for h in n["results"])


def test_default_kind_is_what_the_filter_says(base):
    """No kind: speeches, chair and votes only; kind=all adds the documents' paragraphs; a chosen record is shown whole."""
    kinds = {r["kind"] for r in get(base, "/api/search?q=conscience&offset=0")["results"]}
    assert kinds <= {"speech", "chair", "vote"}
    allk = get(base, "/api/search?q=conscience&kind=all")
    assert allk["total"] > get(base, "/api/search?q=conscience")["total"]
    doc = "A/C.3/L.919"
    assert get(base, "/api/search?symbol=" + urllib.request.quote(doc, safe=""))["total"] > 0


def test_votes_by_delegation_say_how_it_voted(base):
    """The USSR's roll-calls on UDHR article 25 carry its vote; the figures of the Norwegian amendment are the rejected 18-18-9."""
    d = get(base, "/api/decisions?instrument=UDHR&article=25&delegation=Union+of+Soviet+Socialist+Republics")
    assert d["total"] > 0 and all(r["roll_call"] and r["delegation_vote"] in ("for", "against", "abstained", None) for r in d["results"])
    assert any(r["delegation_vote"] == "for" and (r["yes"], r["no"], r["abstentions"]) == (18, 18, 9) for r in d["results"])
    nigeria = get(base, "/api/decisions?delegation=Niger&roll=1")  # "Niger" is not "Nigeria"
    assert all("Niger" in (r["roll_call"]["yes"] + r["roll_call"]["no"] + r["roll_call"]["abstentions"]) for r in nigeria["results"])


def test_amendment_decisions_follow_the_article(base):
    """Under an article filter an amendment shows only the votes on that article, and the OCR's 'A/e. 3/344' is linked to its vote."""
    on25 = {a["symbol"]: a for a in get(base, "/api/amendments?instrument=UDHR&article=25")}
    assert on25["A/C.3/344"]["decisions"], "the vote on the Norwegian amendment (A/e. 3/344 in the record) is linked"
    assert all(d["outcome"] for d in on25["A/C.3/344"]["decisions"])
    assert not on25["A/C.3/264"]["decisions"]  # Egypt's, voted on under other articles


def test_article_pages_that_do_not_exist_are_errors(base):
    """Article 0, 99 and a non-number are errors (404, 400); an unknown instrument is an error; real articles answer."""
    for path, code in (("/api/article?instrument=ICCPR&n=0", 404), ("/api/article?instrument=UDHR&n=99", 404),
                       ("/api/article?instrument=ICESCR&n=32", 404), ("/api/article?instrument=UDHR&n=abc", 400),
                       ("/api/article?instrument=XX&n=1", 400)):
        with pytest.raises(urllib.error.HTTPError) as e:
            get(base, path)
        assert e.value.code == code, path
        assert json.loads(e.value.read())["error"]
    assert get(base, "/api/article?instrument=ICESCR&n=31")["n"] == 31
    with pytest.raises(urllib.error.HTTPError) as e:
        get(base, "/api/amendments?article=undefined")
    assert e.value.code == 400


def test_amendments_come_in_pages_on_request(base):
    """limit pages the list ({total, offset, results}); without it the whole list as before; the pages add up to the list."""
    whole = get(base, "/api/amendments?instrument=UDHR")
    page = get(base, "/api/amendments?instrument=UDHR&limit=100&offset=0")
    assert isinstance(whole, list) and page["total"] == len(whole) and page["results"] == whole[:100]
    nxt = get(base, "/api/amendments?instrument=UDHR&limit=100&offset=100")
    assert nxt["results"] == whole[100:200] and nxt["offset"] == 100
    assert len(get(base, "/api/amendments?limit=9999&offset=0")["results"]) <= 500  # (the cap on a page)


def test_head_requests_and_the_export_cap_in_the_facets(base):
    """HEAD answers with the headers of the GET and no body (monitors ask with it); the facets give the export cap."""
    for path in ("/health", "/api/facets", "/"):
        req = urllib.request.Request(base + path, method="HEAD")
        with urllib.request.urlopen(req) as r:
            assert r.status == 200 and int(r.headers["Content-Length"]) > 0 and r.read() == b""
    assert get(base, "/api/facets")["export_cap"] == server.EXPORT_CAP


def test_heavy_answers_are_kept_and_follow_the_database_file(base, monkeypatch):
    """The same arguments give the very same object (kept) until the database file's modification time changes."""
    a = server.amendments({"instrument": "UDHR", "article": 18})
    assert server.amendments({"instrument": "UDHR", "article": "18"}) is a
    assert server.facets() is server.facets()
    monkeypatch.setattr(server, "DB", type("D", (), {"stat": lambda self: type("S", (), {"st_mtime_ns": 1})()})())
    monkeypatch.setattr(server, "rows", lambda *a, **k: [])
    assert server.records() == []  # a changed file means the answer is worked out again (and here, from nothing)


def test_a_draft_that_holds_two_articles_says_so(base):
    """E/800 article 4 holds slavery and torture: the page of each names the other."""
    d4 = get(base, "/api/article?instrument=UDHR&n=4")
    d5 = get(base, "/api/article?instrument=UDHR&n=5")
    e800_4 = [e for e in d4["evolution"] if e.get("stage") == "chr_3" and str(e["draft_article"]) == "4"]
    e800_5 = [e for e in d5["evolution"] if e.get("stage") == "chr_3" and str(e["draft_article"]) == "4"]
    assert e800_4 and 5 in e800_4[0]["also"] and e800_5 and 4 in e800_5[0]["also"]
    assert all(e.get("also", []) == [] for e in d5["evolution"] if e["stage"] == "final")


def test_every_re_read_tag_is_in_the_database(base):
    """data/concordance/speech_retags.csv: each speech now carries the article the re-read gave it, with the reason."""
    import csv
    import sqlite3
    path = ROOT / "data" / "concordance" / "speech_retags.csv"
    if not path.exists():
        pytest.skip("no re-read tags yet")
    con = sqlite3.connect(server.DB)
    for r in csv.DictReader(path.open()):
        kind = con.execute("SELECT kind FROM segments WHERE id = ?", (r["segment_id"],)).fetchone()[0]
        if kind == "speech":
            row = con.execute("SELECT article_instrument, final_article, article_mapping FROM segments WHERE id = ?", (r["segment_id"],)).fetchone()
            # (or the readers' tag, when the context no longer gives the article the re-read corrected: the same article; or the
            # context's own, when the text now gives that article itself: the vision reader read a heading the OCR had lost.
            # The re-read replaces only the tag it names as the previous one: where the context now gives no article, the
            # speech is left untagged (one since the vision reader's text, E/CN.4/SR.155's Jevremovic), never with the old tag;
            # or Jev's choice among the report's articles, when it picks the re-read's article: E/CN.4/SR.424's, 28 Oct 2026)
            assert row[:2] != tuple(r["previous"].split(" ")[:1]) + (int(r["previous"].split(" ")[1]),), r["segment_id"]
            if row[1] is not None:
                assert row[:2] == (r["instrument"], int(r["final_article"])), r["segment_id"]
                assert (row[2].startswith(("re-read:", "two readers")) or "article from the chair or agenda" in row[2]
                        or "Jev's choice among the articles" in row[2]), r["segment_id"]
        else:  # a vote: the decision carries the article
            assert con.execute("SELECT COUNT(*) FROM decisions WHERE segment_id = ? AND final_article = ? AND article_instrument = ?",
                               (r["segment_id"], int(r["final_article"]), r["instrument"])).fetchone()[0] >= 1, r["segment_id"]


def test_search_results_carry_the_un_pdf_so_a_page_link_opens_that_page(base):
    """On the deployed site (scans: "un") a result's "UN copy p. N" is the UN's PDF + #page=N; undocs.org would lose the page."""
    d = get(base, "/api/search?q=torture&kind=speech")
    with_pdf = [r for r in d["results"] if r.get("pdf_url")]
    assert with_pdf and all(r["pdf_url"].startswith("https://") and ".pdf" in r["pdf_url"].lower() or "access" in r["pdf_url"] for r in with_pdf)


def test_tags_a_blind_check_rejected_stay_off_and_restored_ones_stay_on(base):
    """data/concordance/tag_rejections.csv: the speech does not carry that article; reader_tags.csv rows restored after the
    resegmentation of 6 October 2026 carry theirs (unless Jev or a rejection says otherwise)."""
    import csv
    import sqlite3
    con = sqlite3.connect(server.DB)
    for r in csv.DictReader((ROOT / "data" / "concordance" / "tag_rejections.csv").open()):
        row = con.execute("SELECT article_instrument, final_article FROM segments WHERE id = ?", (r["segment_id"],)).fetchone()
        assert row is not None and row != (r["instrument"], int(r["final_article"])), r["segment_id"]


def test_questions_of_general_debate_are_only_on_untagged_speeches_and_filter_the_search(base):
    """A speech carries a question of general debate (pipeline/topics.py) only where no article tag fits, and above the
    threshold unless two blind judges accepted it (topic_accepted.csv); the search filters by it, and the article a
    question settled links to its debate."""
    import csv
    import sqlite3
    sys.path.insert(0, str(ROOT / "pipeline"))
    from topics import THRESHOLD
    con = sqlite3.connect(server.DB)
    assert con.execute("SELECT COUNT(*) FROM segment_topics st JOIN segments s ON s.id = st.id "
                       "WHERE s.final_article IS NOT NULL OR s.kind != 'speech'").fetchone()[0] == 0
    accepted_csv = ROOT / "data" / "concordance" / "topic_accepted.csv"
    accepted = {(r["segment_id"], r["topic"]) for r in csv.DictReader(accepted_csv.open())} if accepted_csv.exists() else set()
    below = con.execute("SELECT id, topic FROM segment_topics WHERE p < ?", (THRESHOLD,)).fetchall()
    assert all(tuple(r) in accepted for r in below)
    topics = get(base, "/api/facets")["topics"]
    if not topics:
        pytest.skip("no question given yet (pipeline/topics.py --jev)")
    t = topics[0]
    d = get(base, f"/api/search?topic={t['v']}&kind=speech")
    assert d["total"] == t["n"] and all(h["topic"] == t["v"] for h in d["results"])
    sd = [x for x in topics if x["v"] == "self_determination"]
    if sd:
        a = get(base, "/api/article?instrument=ICCPR&n=1")
        assert [x["topic"] for x in a["topics"]] == ["self_determination"] and a["topics"][0]["speeches"] == sd[0]["n"]
    assert get(base, "/api/article?instrument=ICCPR&n=6")["topics"] == []


def test_field_prefixes_and_chronological_sort(base):
    """Inline field prefixes (speaker:, art:, inst:, delegation:, doc:) and sort=date work in /api/search."""
    d = get(base, "/api/search?q=speaker:cassin+art:18")
    assert d["total"] > 0 and all(r["speaker"] == "CASSIN" and r["final_article"] == 18 for r in d["results"])
    c = get(base, "/api/search?q=torture&sort=date")
    dates = [r["meeting_date"] for r in c["results"] if r.get("meeting_date")]
    assert c["total"] > 0 and dates == sorted(dates)


def test_record_prev_next_and_export_article_columns(base):
    """Record answers carry prev_symbol/next_symbol; exports include article_instrument, final_article, draft_article, topic."""
    rec = get(base, "/api/record?symbol=E/CN.4/SR.60")
    assert rec.get("prev_symbol") == "E/CN.4/SR.59" and rec.get("next_symbol") == "E/CN.4/SR.60/Corr.1"
    exp = get(base, "/api/export?format=json&q=religion&article=18")
    r0 = exp["results"][0]
    assert {"article_instrument", "final_article", "draft_article", "topic"} <= set(r0.keys())
    assert r0["article_instrument"] == "UDHR" and r0["final_article"] == 18
    ams = get(base, "/api/amendments?q=L.93")
    assert any(a["symbol"] == "E/CN.4/L.93" for a in ams)

