"""Unit tests for the text parsers: decisions, sessions, article headings, database helpers."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "api"))

import build_db  # noqa: E402
sys.path.insert(0, str(ROOT / "eval"))
from ocr_bench import locate, locate_span  # noqa: E402
from build_concordance import HEAD_RE, SHORT_HEAD_RE, cut_notes, is_french, ocr_numbers  # noqa: E402
from decisions import decisions, number, proposers_in, state_list  # noqa: E402
from sessions import fix_year, session_by_date, sessions_for  # noqa: E402


# ---------- decisions ----------
def test_decision_with_figures():
    d = decisions("The Lebanese amendment (A/C.3/260) was adopted by 17 votes to 13, with 7 abstentions.")
    assert len(d) == 1
    assert (d[0]["outcome"], d[0]["yes"], d[0]["no"], d[0]["abstentions"]) == ("adopted", 17, 13, 7)
    assert d[0]["proposers"] == ["Lebanon"]
    assert d[0]["refs"] == ["A/C.3/260"]


def test_decision_number_words_and_none():
    d = decisions("The amendment was rejected by four votes to one. Article 3 was adopted by 36 votes to none, with 1 abstention.")
    # "rejected by four votes to one": four against, one in favour
    assert [(x["outcome"], x["yes"], x["no"]) for x in d] == [("rejected", 1, 4), ("adopted", 36, 0)]
    assert d[1]["article"] == "3"


def test_decision_unanimous_and_tally():
    assert decisions("Article 18 was adopted unanimously.")[0]["unanimous"]
    d = decisions("There were 6 votes in favour, 6 against and 4 abstentions; the proposal was therefore rejected.")
    assert (d[0]["yes"], d[0]["no"], d[0]["abstentions"]) == (6, 6, 4)


def test_not_a_decision():
    assert decisions("It would be sufficient if they were adopted by the Assembly.") == []
    assert decisions("The work of the Charter had been carried out in this way.") == []
    # a speaker recounting a vote is not a decision
    assert decisions("He recalled that article 3 had been adopted and that the text was adopted by 12 votes.",
                     speech=True) == []


def test_short_subject_takes_previous_sentence():
    d = decisions("The CHAIRMAN put the Swedish amendment (A/C.3/252) to the vote. That amendment was rejected by 27 votes to 10.")
    assert "Swedish amendment" in d[0]["subject"]
    assert d[0]["proposers"] == ["Sweden"]


def test_roll_call():
    text = ("A vote was taken by roll-call as follows: In favour: Argentina, Australia, Brazl!, Chile. "
            "Against: France, Mexico. Abstaining: Canada. The amendment was adopted by 4 votes to 2, with 1 abstention.")
    d = decisions(text)
    rc = d[0]["roll_call"]
    assert rc["yes"] == ["Argentina", "Australia", "Brazil", "Chile"]
    assert rc["no"] == ["France", "Mexico"] and rc["abstentions"] == ["Canada"]
    assert rc["complete"]


def test_proposers_only_authors():
    assert proposers_in("Iceland, having been drawn by lot, was called upon to vote first. That part") == []
    assert proposers_in("the amendment submitted by the delegations of Uruguay and Belgium") == ["Uruguay", "Belgium"]
    assert proposers_in("the joint Belgian and Uruguayan proposal") == ["Belgium", "Uruguay"]


def test_number_and_states():
    assert number("twenty-one") == 21 and number("none") == 0 and number("l7") == 17
    assert state_list("Byelorussian Soviet Socalist Republic, Union of Soviet Socialist Republics") == [
        "Byelorussian Soviet Socialist Republic", "Union of Soviet Socialist Republics"]


# ---------- sessions ----------
def test_sessions_by_date():
    assert session_by_date("Commission on Human Rights", "1952-05-02") == "8th session (1952)"
    assert session_by_date("General Assembly Third Committee", "1957-01-10") == "11th session (1956)"
    assert session_by_date("General Assembly Third Committee", "1966-10-10") == "21st session (1966)"
    assert session_by_date("Commission on Human Rights", "1947-02-05") == "1st session (1947)"


def test_fix_year():
    assert fix_year("1941-10-14", "3rd session (1948)") == "1948-10-14"
    assert fix_year("1957-01-10", "11th session (1956)") == "1957-01-10"
    assert fix_year("1967-10-22", "12th session (1957)") == "1957-10-22"


def test_sessions_from_neighbours():
    b = "Commission on Human Rights"
    got = sessions_for({"E/CN.4/SR.101": (b, "1949-05-19"), "E/CN.4/SR.102": (b, None),
                        "E/CN.4/SR.103": (b, "1949-05-20"), "E/CN.4/SR.175": (b, "1956-04-28"),
                        "E/CN.4/SR.174": (b, "1950-04-27"), "E/CN.4/SR.176": (b, "1950-04-28")})
    assert got["E/CN.4/SR.102"] == "5th session (1949)"
    assert got["E/CN.4/SR.175"] == "6th session (1950)"  # the misread 1956 disagrees with both neighbours


# ---------- article headings and draft texts ----------
def test_headings():
    assert HEAD_RE.match("Article 16")
    assert not HEAD_RE.match("Article 16 by the following text (unofficial translation):")
    assert ocr_numbers("2k") == {24} and ocr_numbers("Ig") == {19, 15}
    m = SHORT_HEAD_RE.match("Article;-£3")
    assert m and m.group("tok") == "£3"


def test_cut_notes():
    text = ("Everyone has the right to freedom of thought, conscience and religion. (Note: The representative of "
            "the Soviet Union proposed to replace ...")
    assert cut_notes(text).endswith("religion.")
    assert cut_notes("I. Text submitted by the Conference: Every one shall have the right") .startswith("I. Text")


def test_cut_notes_editorial_notes():
    # E/CN.4/95 p. 5: the note on an unrevised article opens it and the next one, whose heading the OCR lost
    text = ("(The Drafting Committee did not have the time to consider this Article) ALL men are born free end equal in "
            "dignity and rights. They are endowed by nature with reason and conscience, and should act towards one another "
            "Like brothers, (The Drafting Committee did not have time to consider this Article) In the exercise of his rights")
    assert cut_notes(text) == ("ALL men are born free end equal in dignity and rights. They are endowed by nature with reason "
                               "and conscience, and should act towards one another Like brothers,")
    assert cut_notes("(formerly Article 5) (Geneva text) No one shall be deprived of his personal liberty").startswith("No one")
    # E/CN.4/AC.1/3 p. 12: the next heading, too damaged for the run of headings, ends the text
    assert cut_notes("Every one has the right to education. Each State has the duty to require. ARPICIE 37 Every one has "
                     "the right and the duty to perform socially useful work").endswith("duty to require.")


def test_is_french():
    assert is_french("Tout individu a droit à la vie. Ce droit ne peut être refusé qu'aux personnes qui ont été condamnées")
    assert not is_french("Every one has the right to life. This right can be denied only to persons who have been convicted")


# ---------- database helpers ----------
def test_cited_documents():
    got = build_db.cited("the Cuban amendment (A/C.3/232) to the draft (E/CN.U/95) of A/C.3", "A/C.3/SR.120")
    assert got["A/C.3/232"] == (True, ["Cuba"])
    assert "E/CN.4/95" in got and "A/C.3" not in got


def test_fix_case_and_instrument():
    assert build_db.fix_case("AZKouL") == "AZKOUL"
    assert build_db.fix_case("de QUIJANO") == "de QUIJANO"
    assert build_db.instrument_named("DRAFT INTERNATIONAL COVENANT ON HUMAN RIGHTS") == "covenant"
    assert build_db.instrument_named("article 14 of the draft Covenant on Economic, Social and Cultural Rights") == "icescr"
    assert build_db.instrument_named("B. OBSERVATIONS ON THE DRAFT DECLARATION") == "declaration"
    assert build_db.instrument_named("the Declaration and the Covenant") is None


def test_normalize_delegation():
    n = build_db.normalize_delegation
    assert n("Internetional Lebour Organization") == "International Labour Organisation"
    assert n("International Labour Organisation (ILO") == "International Labour Organisation"
    assert n("Lebanon •• •• , J~OVIC )B )1onal") == "Lebanon"
    assert n("Director of the Human Rights Division") == "UN Secretariat"
    assert n("AF of L") == "American Federation of Labor"
    assert n("United States of America") == "United States of America"
    assert n("continued") is None and n("artlole 1") is None


# ---------- OCR voting and correction ----------
def test_vote_prefers_honorifics():
    from vote import vote_page
    texts = {"layer": "My. CASSIN (France) said", "tess3": "Mr. CASSIN (France) said", "vision": "Me. CASSIN (France) said"}
    assert vote_page(texts, "layer", {"layer": 1, "tess3": 1, "vision": 1})[0].startswith("Mr.")


def test_spellfix_only_non_words():
    import spellfix
    spellfix._freq = spellfix.Counter({"that": 5000, "thet": 3, "and": 9000, "end": 400, "logically": 60})
    spellfix.correction.cache_clear()
    text, n = spellfix.fix_text("He said thet the end was near. Logicully, CASSIN agreed")
    assert text == "He said that the end was near. Logically, CASSIN agreed" and n == 2
    spellfix._freq = None
    spellfix.correction.cache_clear()


def test_openings_join_wrapped_delegation(tmp_path, monkeypatch):
    import vote
    d = tmp_path / "X_SR.1" / "tess3"
    d.mkdir(parents=True)
    (d / "page-002.txt").write_text("Mr. PavLov (Union of Soviet Socialist Re-\npublics) pointed out that the USSR delegation had\n"
                                    "voted for the text.\nMrs. Corset (United Kingdom) stated that her delegation had voted\n"
                                    "against the amendment.\n", encoding="utf-8")
    monkeypatch.setattr(vote, "OCR", tmp_path)
    vote._cache.clear()
    seg = {"text": "Mr. PavLov (Union of Soviet Socialist Republics) pointed out that the USSR delegation had voted for the text.",
           "page_start": 2}
    got = vote.speaker_votes("X/SR.1", seg, engines=["tess3"])
    assert [(v["name"], v["country"]) for v in got] == [("PavLov", "Union of Soviet Socialist Republics")]
    # the neighbouring opening is never taken for this one, however alike the words
    seg2 = {"text": "Mr. PAVLOV (Union of Soviet Socialist Republics) stated that her delegation had voted against the amendment.",
            "page_start": 2}
    (d / "page-002.txt").write_text("Mrs. Corset (United Kingdom) stated that her delegation had voted\nagainst the amendment.\n",
                                    encoding="utf-8")
    vote._cache.clear()
    assert vote.speaker_votes("X/SR.1", seg2, engines=["tess3"]) == []
    vote._cache.clear()


def test_printed_stranger():
    from entities import printed_stranger
    votes = [{"name": "SINHA", "country": "India", "engine": e} for e in ("layer", "tess3", "vision")]
    assert printed_stranger("A/C.3/SR.1401", votes, {"surname": "SAKSENA"})
    # typed records: engines can agree on garbage ("AZECUL" for AZKOUL)
    assert not printed_stranger("E/CN.4/SR.268", votes, {"surname": "SAKSENA"})
    # one name inside the other is the same person; a close name is a misreading
    assert not printed_stranger("A/C.3/SR.1374", [{**v, "name": "SEKANINOVA"} for v in votes], {"surname": "SEKANINOVA-CAKRTOVA"})
    assert not printed_stranger("A/C.3/SR.1401", [{**v, "name": "SINHAA"} for v in votes], {"surname": "SINHA"})
    assert not printed_stranger("A/C.3/SR.1401", votes[:2], {"surname": "SAKSENA"})  # two readings are not enough


def test_commission_covenant_stages():
    stage, article = build_db.covenant_stage, build_db.covenant_article
    assert stage("Commission on Human Rights", "1950-04-12", "6th session (1950)") == "chr6"
    assert stage("Commission on Human Rights", "1952-05-02", "8th session (1952)") == "chr8"
    assert stage("Commission on Human Rights", "1953-04-10", "9th session (1953)") == "chr9"
    assert stage("Commission on Human Rights", "1951-04-10", "7th session (1951)") == "chr7"  # whole meetings only
    assert stage("General Assembly Third Committee", "1950-10-20", "5th session (1950)") is None  # not tagged
    assert stage("General Assembly Third Committee", "1955-10-10", "10th session (1955)") == "tc1955"  # A/3077's meeting lists
    conc = build_db.load_covenant_concordance()
    # E/1371 article 10, imprisonment for debt, became ICCPR article 11
    assert article("chr6", None, "10", conc)[0] == 11 and article("chr6", None, "10", conc)[2] == "ICCPR"
    assert article("chr6", "implementation", "10", conc)[0] is None  # the measures of implementation's own numbers
    # E/1681's footnotes: the sixth session discussed it at SR.150 and SR.199, not at SR.197
    assert article("chr6", None, "10", conc, 150)[0] == 11 and article("chr6", None, "10", conc, 197)[0] is None
    # E/1992 article 20 (work), debated at SR.275-278 (E/2256's footnotes): ICESCR article 6
    assert article("chr8", None, "20", conc, 276)[::2] == (6, "ICESCR") and article("chr8", None, "20", conc, 290)[0] is None


def test_procedural_speeches():
    proc = build_db.PROCEDURAL_RE
    assert proc.search("Miss O'LEARY (Ireland) requested that the vote should be postponed until the following meeting.")
    assert proc.search("He had voted for the establishment of the Working Group on the understanding that")
    assert proc.search("the Commission should devote two weeks to measures of implementation")
    # a vote on the article's own words is about the article
    assert not proc.search("Mr. VALENZUELA (Chile) asked that a separate vote should be taken on the words")
    assert not proc.search("It laid down the procedure to be followed by the authority which decided on the expulsion")
    med = build_db.MEDIUM_PROCEDURAL_RE
    assert med.search("the time~limit fixed for the submission of amendments to article 19")
    assert not med.search("asked why it was necessary to fix a time-limit, within which States should adopt legislative measures")


def test_meeting_dates():
    from segment import masthead_date
    from dates import longest_run
    # the date of issue comes first in typed records; the meeting's follows its weekday
    assert masthead_date("E/CN.4/SR.219 4 June 1951 ... held at the Palais des Nations, on Monday, 30 April 1951") == "1951-04-30"
    assert masthead_date("held on Monday, 36 April 1951") == "1951-04-30"  # the weekday settles a misread day
    assert masthead_date("Friday, 4 June 1948") == "1948-06-04"
    assert longest_run(["1951-04-17", "1951-06-04", "1951-04-18", "1951-04-19"]) == {0, 2, 3}


def test_missing_dates_are_bounded_by_neighbours():
    from dates import missing
    got = missing({"A/C.3/SR.1": "1960-11-14", "A/C.3/SR.2": None, "A/C.3/SR.3": "1960-11-16", "A/C.3/SR.9": None})
    assert got == {"A/C.3/SR.2": ("1960-11-14", "1960-11-16")}  # SR.9 has no dated meeting after it


def test_early_udhr_stages():
    from articles import final_article, load_concordance
    conc = load_concordance()
    # read by hand: E/CN.4/21 annex F art. 18 is nationality, E/600 art. 16 religion, W.1 art. 6 life
    assert final_article("drafting_committee_1", "18", conc)[0] == 15
    assert final_article("geneva_draft", "16", conc)[0] == 18
    assert final_article("cassin_rev1", "6", conc)[0] == 3 and final_article("cassin_draft", "6", conc)[0] == 2
    assert final_article("secretariat_outline", "40", conc)[0] is None  # split across final arts. 22 and 25
    # the meeting decides the text: the draft Covenant (May 1948) and the Geneva plenary get no Declaration article
    assert build_db.EARLY_MEETINGS["E/CN.4/AC.1/SR.9"] == "cassin_rev1"
    assert build_db.EARLY_MEETINGS["E/CN.4/SR.31"] is None  # general debate: the Sub-Commission's report
    assert build_db.tags_udhr("geneva_draft", None) and not build_db.tags_udhr(None, None)
    # another delegation's declaration is not the text under discussion
    assert build_db.article_mentions("an alternative form of this Article in Article 8 of the Declaration submitted by Panama "
                                     "and in Article 6 of the Declaration proposed by the United States", "UDHR") == []
    assert build_db.article_mentions("The CHAIRMAN put Article 23 of the Declaration to the vote", "UDHR") == [("23", 27)]


def test_geneva_draft_covenant():
    conc = build_db.load_covenant_concordance()
    # the Drafting Committee's May 1948 meetings on the Geneva draft Covenant (E/600, annex B): ICCPR tags
    assert build_db.EARLY_MEETINGS["E/CN.4/AC.1/SR.31"] == "e600"
    assert build_db.covenant_article("e600", None, "16", conc)[::2] == (18, "ICCPR")  # religion
    assert build_db.covenant_article("e600", "covenant", "21", conc)[0] == 20  # advocacy of hostility
    assert build_db.covenant_article("e600", None, "25", conc)[0] is None  # the colonial clause, dropped
    assert build_db.covenant_article("e600", "declaration", "16", conc)[0] is None
    # in those meetings the Covenant is the text under discussion, the Declaration the other one
    assert build_db.article_mentions("a statement on Article 8 of the Draft Covenant", "UDHR", "Covenants") == [("8", 24)]
    assert build_db.article_mentions("the relevant Article 5 of the Declaration", "UDHR", "Covenants") == []
    # a later article named as what a decision waits for is not the article in force
    assert build_db.article_mentions("postponed until the final wording of Article 4 of the Draft Covenant", "UDHR", "Covenants") == []


def test_geneva_plenary_two_texts():
    from articles import load_concordance
    conc, cov = load_concordance(), build_db.load_covenant_concordance()
    # E/CN.4/SR.34-42 took up the Working Groups' Declaration (E/CN.4/57) and Convention (E/CN.4/56) together
    assert build_db.EARLY_MEETINGS["E/CN.4/SR.37"] == "geneva_plenary"
    two = lambda instr, n: build_db.two_text_article("geneva_plenary", instr, n, conc, cov)[::2]
    assert two("declaration", "10.3") == (5, "UDHR")  # the Declaration's article 10, para. 3: torture
    assert two("covenant", "13") == (15, "ICCPR")  # the Convention's article 13: no retroactive penal law
    assert two(None, "13") == (None, None)  # a passage the record does not place
    # run-in headings: a pair is numbered by its Declaration article, and keeps its Convention articles
    head = build_db.heading_context
    assert head("Article 8 of the Declaration and Articles 8 and 9 of the Convention", "UDHR") == ("declaration", "8", ["8", "9"])
    assert head("Declaration Article 13 and Convention Article 10", "UDHR") == ("declaration", "13", ["10"])
    assert head("Article2 of Convention", "UDHR") == ("covenant", "2", [])
    assert head("Resolution 2 of the Convention Report", "UDHR") == ("other", None, [])
    # a heading run into the end of a passage, not a sentence of a speech
    assert build_db.tail_heading("... adopted by sixteen votes. 4. Article 4 of the Convention.")[1] == "Article 4 of the Convention"
    assert build_db.tail_heading("He said that there was no doubt that Article 38 had a bearing on Article 8.") is None
    # mentions in running text: which text each belongs to; a place or a source of words is not the article taken up
    t = "The CHAIRMAN pointed out that Articles 21 and 22 of the Declaration and Article 16 of the Convention dealt with information"
    assert [build_db.mention_text(t, e) for _, e in build_db.article_mentions(t, "UDHR", "both")] == ["declaration", "covenant"]
    assert build_db.article_mentions("they would appear in the Convention after Article 3", "UDHR", "both") == []
    assert build_db.paired("as in Article 37 of the Declaration, and one with less chance, namely Article 20 of the Convention",
                           build_db.article_mentions("as in Article 37 of the Declaration, and one with less chance, namely Article 20 of the Convention",
                                                     "UDHR", "both")) is None


def test_1948_concordance_fixes_and_draft_texts():
    from articles import final_article, load_concordance
    conc = load_concordance()
    # E/CN.4/95 keeps the Geneva numbers from article 17: 'Articles 17 and 18' is one text (19), 26 is social security (22)
    assert final_article("drafting_committee_2", "18", conc)[0] == 19
    assert final_article("drafting_committee_2", "26", conc)[0] == 22
    assert final_article("drafting_committee_2", "23.1", conc)[0] == 23
    assert final_article("chr_3", "7", conc)[0] == 9  # E/800 art. 7: arbitrary arrest
    # "contained in document E/CN.4/82/Add.8 as article 28": another text's number
    assert build_db.article_mentions("the article contained in document E/CN. 4/82/Add.8 as article 28.", "UDHR") == []
    # the 1947 texts are cut from the OCR by hand-set anchors
    import early_draft_texts as edt
    a = {"stage": "e600", "draft_article": "16", "page_start": 33, "start": "Every nerson of full age",
         "page_end": 33, "end": "determine whet religious teaching he shall receive."}
    try:
        text = edt.cut("E/600", a)
    except ValueError:
        return  # the OCR pages are not in this checkout
    assert text.startswith("Every nerson of full age") and text.endswith("he shall receive.")


def test_commission_1952_53_meeting_lists():
    article, conc = build_db.covenant_article, build_db.load_covenant_concordance()
    # 1952: E/1992's civil and political articles, with E/2256's meetings: art. 3 (life) at SR.309-311
    assert article("chr8", None, "3", conc, 310)[::2] == (6, "ICCPR") and article("chr8", None, "3", conc, 325)[0] is None
    assert article("chr8", None, "18", conc, 328)[0] == 5  # existing standards, not the ESC limitations article (32)
    # 1953: the rest of the Human Rights Committee articles in E/2256's numbering
    assert article("chr9", None, "53", conc, 386)[0] == 44 and article("chr9", None, "49", conc, 354)[0] is None
    # the additional articles of 1953 had no number: their meetings alone are listed (ICCPR 27 at SR.368-371)
    meets = lambda st, fin: conc.get((st, "meetings", "ICCPR", fin), set())
    assert {368, 369, 370, 371} <= meets("chr9", "27") and 371 in meets("chr9", "10")
    # meetings given to other business are listed too, so that they are not taken for one article's
    assert 382 in meets("chr9", "general") and 382 in meets("chr9", "23")
    # "Article 29 as a whole was adoster": the OCR's "adopted" ends the article
    assert build_db.ADOPTED_WHOLE_RE.search("Article 29 as a whole was adoster by le votes to 5")


def test_third_committee_1966():
    stage, article = build_db.covenant_stage, build_db.covenant_article
    conc = build_db.load_covenant_concordance()
    assert stage("General Assembly Third Committee", "1966-11-16", "21st session (1966)") == "tc1966"
    assert stage("General Assembly Third Committee", "1965-11-16", "20th session (1965)") == "e2573"  # no report read
    assert stage("General Assembly plenary", "1966-12-16", "21st session (1966)") == "e2573"  # not the Committee's lists
    # A/6546: article 26 at SR.1407-1412 is the ICESCR's signature clause, not the ICCPR's equality article
    assert article("tc1966", None, "26", conc, 1408)[::2] == (26, "ICESCR") and article("tc1966", None, "26", conc, 1430)[0] is None
    # "article 41" (conciliation) became ICCPR 42; "paragraph 1 of article 33" is article 33's (ICCPR 34)
    assert article("tc1966", "covenant", "41", conc, 1429)[::2] == (42, "ICCPR")
    assert article("tc1966", "iccpr", "33.1", conc, 1424)[0] == 34
    # the Optional Protocol's articles are not the Covenant's
    assert article("tc1966", None, "2", conc, 1446)[0] is None


def test_third_committee_1962_63():
    stage, article = build_db.covenant_stage, build_db.covenant_article
    conc = build_db.load_covenant_concordance()
    assert stage("General Assembly Third Committee", "1962-12-10", "17th session (1962)") == "tc1962"
    assert stage("General Assembly Third Committee", "1963-11-10", "18th session (1963)") == "tc1963"
    # A/5365: articles 3 and 5 adopted for both covenants in the same terms at the 1206th meeting
    assert article("tc1962", None, "3", conc, 1206)[::2] == (3, build_db.BOTH)
    assert article("tc1962", "icescr", "3", conc, 1206)[::2] == (3, "ICESCR")
    # article 2 is two different texts: at the 1207th meeting (both listed) a bare number is neither
    assert article("tc1962", None, "2", conc, 1207)[0] is None and article("tc1962", None, "2", conc, 1204)[::2] == (2, "ICESCR")
    # A/5655: ICCPR article 4 at the 1259th-1262nd meetings, not at the 1257th
    assert article("tc1963", None, "4", conc, 1261)[::2] == (4, "ICCPR") and article("tc1963", None, "4", conc, 1257)[0] is None


def test_audit_fixes():
    article, conc = build_db.covenant_article, build_db.load_covenant_concordance()
    # the Commission's paragraph numbers are their article's, under the meeting check (E/1371 art. 9 at SR.144)
    assert article("chr6", None, "9.2", conc, 144)[0] == article("chr6", None, "9", conc, 144)[0]
    # the chair looking ahead is not taking up another article
    assert build_db.article_mentions("The CHAIRMAN said the Committee would go into the question again when considering article 15.", "Covenants") == []
    assert build_db.article_mentions("the vote being deferred until after the discussion on article 40. (2) Article 40 and the amendment",
                                     "Covenants") == [("40", 80)]
    # a speech whose opening the OCR ran into a heading's tail
    assert build_db.SPEECH_LIKE_RE.match("A/C.3/L.625) (continued) 1. Mr. MASSOUD-ANSARI (Iran) said")
    # 1966: the number of ratifications under draft article 26 is ICESCR 27
    s = {"_stage": "tc1966", "kind": "speech", "text": "Mr. FINK (Denmark) considered that the question of the minimum number of "
         "ratifications necessary for the Covenant to enter into force should be considered carefully."}
    assert build_db.stage_1966_entry(s, 26, "ICESCR") and not build_db.stage_1966_entry(s | {"_stage": "e2573"}, 26, "ICESCR")


def test_article_choice_options():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
    import csv
    import jev_article_choice as jc
    conc = build_db.load_covenant_concordance()
    titles = {(r["instrument"], r["article"]): r["short_title"] for r in
              csv.DictReader((Path(__file__).resolve().parents[1] / "data/concordance/articles.csv").open())}
    # 1966, SR.1411: the options name the record's numbers; draft 28 (deleted) is an option of its own, so that
    # "article 28" is not taken for the final article 28 (which was draft 27)
    opts = jc.options_for("tc1966", 1411, [("ICESCR", "28")], conc, titles)
    assert opts["ICESCR 28"].startswith("draft article 27") and "marker:former-28" in opts and jc.NONE in opts
    assert build_db.CHOICE_THRESHOLD >= 0.9


def test_1948_headings_footnote_digit():
    # the printed records' footnote marker read as a last digit: "ARTICLE 71" is article 7, "ARTICLE 201" article 20
    assert build_db.unglue_1948("71", False, False, 6) == 7
    assert build_db.unglue_1948("201", False, False, 19) == 20
    assert build_db.unglue_1948("21", False, False, 1) == 2       # after article 1
    assert build_db.unglue_1948("12", False, False, None) == 1    # the first heading (SR.95)
    assert build_db.unglue_1948("25", False, False, 24) == 25     # after article 24: a plain 25
    assert build_db.unglue_1948("21", False, False, 28) == 21     # back to article 21 (Sub-Committee 3's report)
    assert build_db.unglue_1948("16", True, False, None) == 16    # "ARTICLE 16}": the marker read as a sign
    assert build_db.unglue_1948("11", False, False, 9) == 11      # the Sub-Committee 4 report: no footnotes
    # run into the passage before, misread, in small capitals; not the prose "Article 28, as amended, was adopted"
    assert build_db.runin_headings_1948("... by the end of the month. ARTICLE 201") == [(29, "201", False, False)]
    assert build_db.runin_headings_1948("human rights (E/800) (continued ) Axticte 3 (continued )")[0][1:] == ("3", False, True)
    assert build_db.runin_headings_1948("Article 17 was adopted. ArticLe 18")[0][1] == "18"
    assert build_db.runin_headings_1948("Article 28, as amended, was adopted.") == []
    assert build_db.runin_headings_1948("Article 24, as amended, was adopted. ARTICLES 25 AND 26") == []


def test_article_choice_1948_options():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
    import jev_article_choice as jc
    # the options name E/800's numbers; "another article" keeps a speech on an unlisted article or the preamble out
    opts = jc.options_1948([(22, "20"), (23, "21")], {("UDHR", "22"): "Social security"})
    assert opts["UDHR 22"].startswith("draft article 20 of E/800 (Social security") and jc.OTHER in opts and jc.NONE in opts


def test_research_check_fixes():
    # vote figures the OCR runs together or misreads ("votesto", "hy", "wes"), 1957 and 1952
    d = decisions("The second sentence was rejected by 31 votesto 20, with 17 abstentions.")[0]
    assert (d["yes"], d["no"], d["abstentions"]) == (20, 31, 17)
    d = decisions("The paragraph wes adopted hy 13 votes to 4, with 1 abstention.")[0]
    assert (d["outcome"], d["yes"], d["no"], d["abstentions"]) == ("adopted", 13, 4, 1)
    assert build_db.fix_symbol("E/ON.4/L.140") == "E/CN.4/L.140" and build_db.fix_symbol("E/AC.7/SR.147") == "E/AC.7/SR.147"
    # the Commission's agenda gives the article a meeting continues (1949: SR.98 has no heading for it)
    m = build_db.CONTINUED_AGENDA_RE.search("CONTENTS Draft International Covenant - Article 5 (discussion continued) and article 9")
    assert m and m.group(1) == "5"


def test_report_sections():
    rows = [{"para_first": 1, "para_last": 3, "final": None, "instrument": "none", "draft_article": "", "note": "introduction"},
            {"para_first": 4, "para_last": 9, "final": 6, "instrument": "ICCPR", "draft_article": "6", "note": "article 6"}]
    rows.append({"para_first": 10, "para_last": 12, "final": 7, "instrument": "ICCPR", "draft_article": "7", "note": "article 7"})
    p = lambda n, text, kind="paragraph": {"n": n, "text": text, "kind": kind}
    segs = [p("1", "1. The Committee ..."), p("4", "4. Article 6 ..."), p(None, '"2. In countries where ..."'),
            p("2", "2. a quoted paragraph read as 2"), p("5", "5. Amendments ..."),
            p(None, "ARTICLE 7", "heading"), p("16", "16. [10. misread] Article 7 ..."), p("11", "11. Amendments"),
            p(None, "B. Another question"), p(None, "text under it"), p(None, "ANNEX I", "heading"), p("4", "4. annex text")]
    build_db.report_tags("A/0000", segs, rows)
    assert [s["_fixed"][0] for s in segs] == [None, 6, 6, 6, 6, 7, 7, 7, None, None, None, None]


def test_report_annex_sections():
    rows = [{"para_first": 1, "para_last": 2, "final": None, "instrument": "none", "draft_article": "", "note": "introduction"}]
    annex = [{"page": 10, "anchor": "COMMENTS BY THE REPRESENTATIVE OF INDIA", "final": 6, "instrument": "ICCPR",
              "draft_article": "5", "author": "India", "note": "Indian comment on article 5"},
             {"page": 11, "anchor": "Article 2", "final": None, "instrument": "none", "draft_article": "", "author": "", "note": "several"}]
    p = lambda n, text, page, kind="paragraph": {"n": n, "text": text, "kind": kind, "page_start": page, "delegation": "Philippines"}
    segs = [p("1", "1. The Commission ...", 1), p(None, "ANNEX II", 10, "heading"),
            p(None, "COMMENTS BY THE  REPRESENTATIVE OF INDIA on article 5", 10), p(None, "She thought ...", 10),
            p(None, "Article 2 of the draft", 11)]
    build_db.report_tags("E/CN.4/0", segs, rows, annex)
    assert [s["_fixed"][0] for s in segs] == [None, None, 6, 6, None]
    assert [s["delegation"] for s in segs[2:]] == ["India", "India", None] and not build_db.ANNEX_LOG


def test_amendment_sponsors_from_reports():
    import amendment_sponsors as sp
    text = ("85. Amendments were submitted by Colombia and Uruguay (A/C.3/L.644), France (A/C.3/L.645), the Philippines "
            "(L.646) and Belgium, Brazil, El Salvador, Mexico and Morocco (A/C.3/L.654). 99. In its report (A/C.3/L.655/Corr.1), "
            "the Working Party said ... The Netherlands amendment (A/C.3/L.651) to replace ... and the amendment of Costa Rica "
            "to the Netherlands amendment (A/C.3/L.648)")
    got, prev = {}, 0
    for m in sp.SYMBOL_RE.finditer(text):
        opened = text.rfind("(", max(0, m.start() - 3), m.start() + 1)
        who = sp.sponsors_before(text, opened if opened >= 0 else m.start(), prev)
        after = sp.BODY_AFTER_RE.match(text, m.end())
        if not who and after:
            who = ["Working Party"]
        prev = text.find(")", m.end()) + 1
        got[sp.symbol(m, "A/C.3")] = who
    assert got["A/C.3/L.644"] == ["Colombia", "Uruguay"] and got["A/C.3/L.645"] == ["France"]
    assert got["A/C.3/L.646"] == ["Philippines"] and len(got["A/C.3/L.654"]) == 5
    assert got["A/C.3/L.655/Corr.1"] == ["Working Party"] and got["A/C.3/L.651"] == ["Netherlands"]
    assert got["A/C.3/L.648"] is None  # "the amendment of Costa Rica to the Netherlands amendment": not read, not guessed


def test_icescr11_check_fixes():
    import spellfix
    # the spelling fix never turns a state name into a commoner word ("Uganda" was read as "Agenda")
    assert spellfix.correction("uganda") is None and spellfix.correction("malian") is None
    assert build_db.fix_symbol("A/C.3/I.1177") == "A/C.3/L.1177" and build_db.fix_symbol("E/CN.4/l.48") == "E/CN.4/L.48"
    # a suggestion the sponsors accepted is no vote; a motion to adjourn is a vote on procedure
    assert decisions("This suggestion was adopted by the sponsors of the eleven-Power proposal (A/C.3/L.1177).") == []
    d = decisions("Mr. AZMI moved the adjournment. The motion for adjournment was adopted by 10 votes to 4, with 4 abstentions.")[0]
    assert d["procedural"] and d["yes"] == 10
    assert not decisions("Article 11 was adopted by 12 votes to none, with 6 abstentions.")[0]["procedural"]


def test_decisions_other_verbs_and_consent():
    d = decisions("The words 'or intentionally' were deleted by 7 votes to 4, with 2 abstentions.")[0]
    assert (d["outcome"], d["yes"], d["no"], d["abstentions"]) == ("deleted", 7, 4, 2)
    assert decisions("The word was deleted.") == []  # a text's history, not a vote
    d = decisions("It was decided, by 7 votes to 6, with 1 abstention, to retain the word 'arbitrarily'.")[0]
    assert d["outcome"] == "decided" and d["subject"].startswith("to retain") and (d["yes"], d["no"]) == (7, 6)
    d = decisions("The CHAIRMAN proposed that articles 11 and 12 should be combined. It was so decided.")[0]
    assert d["without_vote"] and "combined" in d["subject"]
    assert decisions("The CHAIRMAN proposed that articles 11 and 12 should be combined. It was so decided.", speech=True) == []
    assert decisions("The Chairman's ruling was upheld by 10 votes to 5.")[0]["procedural"]
    # a query entirely in quotes is matched word for word (the unstemmed index)
    import re
    assert re.fullmatch(r'\s*(?:"[^"]+"\s*(?:\b(?:OR|AND|NOT)\b\s*)?)+', '"arbitrarily" OR "arbitrary"')


def test_resegment_alignment():
    import resegment
    s = lambda i, t: {"id": f"x-{i:04d}", "text": t}
    old = [s(1, "The CHAIRMAN opened the meeting."), s(2, "Mr. A (France) said one thing. Mr. B (Chile) said another thing."),
           s(3, "Mr. C (Peru) agreed fully with the text"), s(4, "of the article as drafted."), s(5, "The meeting rose.")]
    new = [s(1, "The CHAIRMAN opened the meeting."), s(2, "Mr. A (France) said one thing."), s(3, "Mr. B (Chile) said another thing."),
           s(4, "Mr. C (Peru) agreed fully with the text of the article as drafted."), s(5, "The meeting rose.")]
    m, how, opening = resegment.align(old, new)
    assert m["x-0001"] == "x-0001" and how["x-0001"] == "same"
    assert how["x-0002"] == "split" and m["x-0002"] in ("x-0002", "x-0003")
    # (a split speech's own data follows its opening, Mr. A's turn, whichever part holds more of its words)
    assert opening == {"x-0002": "x-0002"}
    assert m["x-0003"] == m["x-0004"] == "x-0004" and how["x-0004"] == "merged"
    assert m["x-0005"] == "x-0005"


def test_segmentation_fixes_2026_09_28():
    import segment as sg
    # a Covenant heading read in small capitals (A/C.3/SR.743), and a range
    assert sg.COVENANT_HEAD_RE.match("ARTICLE 13 oF THE DRAFT CovENANT ON ECONOMIC, SOCIAL AND CULTURAL RIGHTS")
    assert sg.COVENANT_HEAD_RE.match("ARTICLES 11-12 OF THE DRAFT COVENANT")
    assert not sg.COVENANT_HEAD_RE.match("article 13 of the draft covenant was adopted")
    # "Kr." for "Mr.", curly quotes before the paragraph number, a long delegation (FAO's Director-General)
    assert sg.SPEAKER_RE.match("Kr. MOROZOV (Union of Soviet Socialist Republics) said")
    assert sg.SPEAKER_RE.match("“12. Mr. CASSIN (France) said")
    assert sg.SPEAKER_RE.match("4, Mr. SEN (Director-General of the Food and Agriculture Organization of the United Nations) said")
    assert sg.CHAIR_RE.match("• The CHAIRMAN put to the vote")
    assert sg.ARTICLE_HEAD_RE.match("Article 5 (discussion continued)")
    # a report paragraph number the OCR garbled counts only as the next number
    m = sg.PARA_START_FUZZY_RE.match("12h. The Guatemalan amendment")
    assert m and m.group("n").translate(sg.OCR_PARA_DIGITS) == "124"


def test_1947_48_speaker_lines():
    from segment import classify
    # OCR titles: "Ma," and "M:" for "Mr.", "Lr." ; a curly bracket read for "("; the title after the name
    for line, name, country in [("Ma, CASSIN (France) said that", "CASSIN", "France"),
                                ("M: PAVLOV (Union of Soviet Socialist Republics) said", "PAVLOV", "Union of Soviet Socialist Republics"),
                                ("Lr. MALIK (Lebanon) said", "MALIK", "Lebanon"),
                                ("Mr. CHANG {China) said", "CHANG", "China"),
                                ("AZMI Bey (Egypt) said that", "AZMI", "Egypt")]:
        kind, info = classify(line)
        assert (kind, info["name"], info["country"]) == ("speech", name, country), line
    assert classify("The CHAIPMAN asked the Commission whether")[0] == "chair"
    # joint headings: the first article (the others go to Jev's choice among the meeting's articles)
    assert classify("Articles 5, 6 and 7") == ("heading", {"article": "5"})
    assert classify("Articles 17 and 18.") == ("heading", {"article": "17"})


def test_covenant_chair_reference_not_taken():
    # E/CN.4/SR.182: article 7 stays under discussion; "covered by article 5" names where something else belongs
    text = ("The CHAIRMAN asked the Commission whether it wished to state that it thought the atrocities contemplated "
            "under article 7 were definitely and categorically covered by article 5.")
    assert [n for n, _ in build_db.article_mentions(text, "Covenants")] == ["7"]


def test_annex_anchor_full_length():
    # E/CN.4/669 annex I B: two paragraphs open "1. Everyone shall have the right to ..." (religion, then opinion); the
    # row for the opinion article must land on its own segment, not on the first that shares 30 characters
    segs = [{"seq": 1, "kind": "heading", "page_start": 49, "text": "Article 15", "n": None},
            {"seq": 2, "kind": "paragraph", "page_start": 49, "text": "1. Everyone shall have the right to freedom of thought, conscience and religion.", "n": 1},
            {"seq": 3, "kind": "paragraph", "page_start": 49, "text": "1. Everyone shall have the right to hold opinions without interference.", "n": 1}]
    rows = [{"page": 49, "anchor": "Article 15", "final": 18, "instrument": "ICCPR", "draft_article": "15", "author": "", "note": "art. 15"},
            {"page": 49, "anchor": "1. Everyone shall have the right to hold", "final": 19, "instrument": "ICCPR", "draft_article": "16",
             "author": "", "note": "art. 16"}]
    build_db.report_tags("X/1", segs, [], rows)
    assert [s["_fixed"][0] for s in segs] == [18, 18, 19]


def test_decision_active_fronted_bracketed():
    d = decisions("37. At its 399th meeting, the Commission rejected the Polish proposal by 7 votes to 3, with 7 abstentions.")
    assert [(x["outcome"], x["yes"], x["no"], x["abstentions"], x["proposers"]) for x in d] == [("rejected", 3, 7, 7, ["Poland"])]
    d = decisions("The Commission approved the new text of Article 21 by eleven votes to four with one abstention,")
    assert [(x["outcome"], x["yes"], x["no"], x["abstentions"], x["article"]) for x in d] == [("approved", 11, 4, 1, "21")]
    d = decisions("Abstaining: Bolivia. By 38 votes to 2, with 7 abstentions, the words were retained.")
    assert [(x["outcome"], x["yes"], x["no"], x["abstentions"]) for x in d] == [("retained", 38, 2, 7)]
    d = decisions('"... Court of Justice." (Adopted by 8 votes to 1)')
    assert [(x["outcome"], x["yes"], x["no"]) for x in d] == [("adopted", 8, 1)]
    d = decisions("By 19 votes to 12, the Committee decided to meet on that date.")
    assert [(x["outcome"], x["yes"], x["no"], x["subject"]) for x in d] == [("decided", 19, 12, "to meet on that date")]


def test_decision_figures_in_words_and_ocr():
    assert [(x["yes"], x["no"], x["abstentions"]) for x in decisions("It was adopted by twelve votes for, none against, and four abstentions.")] == [(12, 0, 4)]
    assert [(x["outcome"], x["yes"], x["no"]) for x in decisions("The proposal was defeated by one vote in favour to seven against.")] == [("defeated", 1, 7)]
    assert [(x["outcome"], x["yes"], x["abstentions"]) for x in decisions("The words were auopted by 9 votes to 4 with 4 abstentions.")] == [("adopted", 9, 4)]
    # no figure against printed: none against (15 of 15 such votes read on the page images print none; the French
    # column of the bilingual records says "contre zéro", round 78)
    assert [(x["yes"], x["no"], x["abstentions"]) for x in decisions("The first paragraph was adopted by 35 votes, with 5 abstentions.")] == [(35, 0, 5)]
    assert [(x["yes"], x["no"], x["abstentions"]) for x in decisions("Article 7, as amended, was accepted by a vote of four to none with one abstention.")] == [(4, 0, 1)]
    assert [(x["yes"], x["no"], x["abstentions"]) for x in decisions("The USSR resolution was rejected by 45 vote. to 6, with 3 abstentions.")] == [(6, 45, 3)]
    assert [(x["yes"], x["no"], x["abstentions"]) for x in decisions('The words were adopted by ik votes to 4, with no abstentions.')] == [(14, 4, 0)]
    assert [(x["yes"], x["no"]) for x in decisions("Operative paragraph 1, as amended, was adopted by 61.votes to none, with 27 abstentions.")] == [(61, 0)]
    assert [(x["yes"], x["no"], x["abstentions"]) for x in decisions("The ruling wes upheld >y 7 votes to, with 7 abstentions.")] == [(7, None, 7)]
    # "if he so desires" is the words voted on, not a condition on the vote
    assert len(decisions('The CHAIRMAN put to the vote the words "if he so desires". Those words were adopted by 9 votes to 4.')) == 1


def test_decision_subject_and_roll_call_names():
    # the sentence before is another vote: only what it was on is taken in
    d = decisions("The first part was adopted by 9 votes to 2. It was then rejected by 5 votes to 4.")
    assert "9 votes" not in d[1]["subject"]
    assert state_list("Sweden, United Kingdom of Great Britain and Northern Ireland, United States of America") == \
        ["Sweden", "United Kingdom", "United States of America"]
    assert proposers_in("the motion of Lebanon, seconded by Chile") == ["Lebanon"]


def test_decision_anaphor_resolved_to_the_vote_put():
    # "The amendment": the sentence that put it to the vote, past the roll-call list (A/C.3/SR.309)
    text = ("The CHAIRMAN put to the vote the Lebanese amendment (A/C.3/L.86) to paragraph 2 (c).\n\n"
            "A vote was taken by roll-call. In favour: France, Greece. Against: Iraq. Abstaining: Chile. "
            "The amendment was adopted by 2 votes to 1, with 1 abstention.")
    d = decisions(text)[-1]
    assert d["proposers"] == ["Lebanon"] and d["refs"] == ["A/C.3/L.86"]
    # the result of the part before, run on with a comma by the OCR, is not the clause (A/C.3/SR.315)
    d = decisions("The CHAIRMAN put to the vote successively the first and second paragraphs of the USSR amendment. "
                  "The first paragraph was rejected by 20 votes to 8, with 11 abstentions, The second paragraph was adopted by 16 votes to 15.")
    assert "20 votes" not in d[-1]["subject"] and d[-1]["proposers"] == ["Union of Soviet Socialist Republics"]
    # a clause that names its proposer is not an anaphor
    assert decisions("Mr. ROY (Haiti) opposed that motion. The Afghan motion was adopted by 28 votes to 2.")[-1]["subject"] == "The Afghan motion"
    # the mover of an adjournment, from the turn before the chair put it (A/C.3/SR.179)
    d = decisions("The motion was adopted by 18 votes to 9.", context="Mr. Carrera ANDRADE (Ecuador) moved the adjournment of the meeting.\n\n"
                  "The CHAIRMAN put the motion for the adjournment of the meeting to the vote.")
    assert d[0]["proposers"] == ["Ecuador"]
    # no figures after "Is there any objection?": a decision without a vote (A/PV.7)
    d = decisions("Is there any objection? Decision: Paragraphs 4 (b) and (c) of the resolution were adopted.")
    assert d[0]["without_vote"] and not decisions("Paragraph 25 was accepted.")[0]["without_vote"]
    assert decisions("Paragraph 25 was accepted without comment.")[0]["without_vote"]


def test_a777_numbering():
    # A/777's article 3 was deleted in the plenary (its substance went into final article 2): 4-31 are final 3-30
    from articles import final_article, load_concordance, stage_of
    conc = load_concordance()
    assert [final_article("a777", str(n), conc)[0] for n in (1, 2, 3, 4, 19, 31)] == [1, 2, 2, 3, 18, 30]
    assert stage_of("A/777", "", None) == "a777" and stage_of("A/RES/217(III)", "A/777", None) == "final"


def test_charter_article_with_paragraph():
    text = "The PRESIDENT read the notification under Article 12, paragraph 2, of the Charter."
    assert build_db.article_mentions(text, "UDHR") == []


def test_symbols_spaced_and_misread():
    from decisions import symbols_in
    text = "Peru (A/C.3/ 225), Cuba (A/C.3 /232) and Saudi Arabia (A/C.3/247 /Rev.1), in A /C.3/289 /Rev.1; the A/C.3 met"
    assert symbols_in(text) == ["A/C.3/225", "A/C.3/232", "A/C.3/247/Rev.1", "A/C.3/289/Rev.1"]
    assert [build_db.fix_symbol(m.group(1)) for m in build_db.REF_RE.finditer("(A/C. 3/1.656), (A/C.38/L.875), E/CN4/ L.143")] == \
        ["A/C.3/L.656", "A/C.3/L.875", "E/CN.4/L.143"]
    assert symbols_in("the Greek amendment (A/C.3/ 1027th meeting") == []


def test_proposers_hyphen_document_mover():
    from decisions import SYMBOL_RE, proposers_of
    for s, who in [("the joint United Kingdom-Indian amendment (document E/CN.4/99) was", ["United Kingdom", "India"]),
                   ("accepted the India-United Kingdom text (E/CN.4/99)", ["India", "United Kingdom"])]:
        m = SYMBOL_RE.search(s)
        assert proposers_of(s, m.start(), m.end()) == who
    assert proposers_in("PAZHWAK (Afghanistan) further proposed that the meeting should be adjourned to allow for consultations "
                        "on the Philippine suggestion. The motion for adjournment") == ["Afghanistan"]


def test_own_amendment_rule():
    # "his amendment" is the speaker's, unless the sentence names another delegation's representative first
    assert build_db.cited("He withdrew his amendment (A/C.3/L.578) but reserved", "X", "Afghanistan") == {"A/C.3/L.578": (True, ["Afghanistan"])}
    assert build_db.cited("He hoped that the Netherlands representative would not press his amendment (A/C.3/L.557) to the", "X",
                          "Saudi Arabia") == {"A/C.3/L.557": (True, [])}
    assert build_db.cited("the Indian representative's wording; the formula of her delegation's amendment (A/C.3/L.1352)", "X",
                          "United Kingdom") == {"A/C.3/L.1352": (True, ["United Kingdom"])}


def test_cited_skips_own_symbol_after_own_amendment():
    # (the document's own symbol is never a reference, also after a "his amendment" earlier in the passage)
    out = build_db.cited("He withdrew his amendment (A/C.3/L.578). See A/2929, chapter VI.", "A/2929", "Afghanistan")
    assert "A/2929" not in out


def test_amended_article_beats_later_reference():
    text = ("said her delegation was willing to withdraw the amendment it had submitted to article 26 in favour of the French "
            "amendment; moreover, its terms were in accordance with those used in article 23.")
    named = build_db.article_mentions(text, "Covenants")
    assert [n for n, e in named if build_db.AMENDMENT_TO_RE.search(text[max(0, e - 130):e])] == ["26"]
    # "covered by the provision against discrimination in Article 3": where something else belongs (E/CN.4/SR.66)
    assert build_db.article_mentions("the principle was adequately covered by the provision against discrimination in Article 3", "UDHR") == []


def test_masthead_date_after_held_on():
    from segment import masthead_date
    # the date of issue comes first; the meeting's follows "held ... on", its weekday garbled ("Hondas", E/CN.4/SR.203)
    assert masthead_date("AND 2 April 1951 COMMISSION ON HUMAN RIGHTS Seventh Session SUMMARY RECORD held at the Palais des "
                         "Nations, Geneva, on Hondas, 16 april 1951, at 3 p.m.") == "1951-04-16"


def test_ocr_article_headings_and_second_reading():
    from segment import classify
    assert classify("Artigle 18 | So | Be") == ("heading", {"article": "18"})
    assert classify("Articlo 9 (continued)") == ("heading", {"article": "9"})
    # the second reading (E/CN.4/SR.200): the number that counts is the first reading's
    assert classify("Article 1k (former articl:: 17) (B/GN 4/610, page 30)") == ("heading", {"article": "17"})
    assert classify("Article 25 of the Covenant provides")[0] == ""


def test_second_reading_numbers_must_agree():
    cov = build_db.load_covenant_concordance()
    assert build_db.second_reading_agrees("14", "17", cov) and build_db.second_reading_agrees("1k", "17", cov)
    assert build_db.second_reading_agrees("6", "9", cov)
    # "Article 6 (fomany article 2)": the OCR's 2 is a 9 (E/CN.4/SR.199)
    assert not build_db.second_reading_agrees("6", "2", cov)


def test_decision_more_ocr_forms():
    assert [(x["outcome"], x["yes"], x["no"], x["abstentions"]) for x in decisions("Paragraph 2 was adonted by 14 votes to 3, with 1 abstention.")] == [("adopted", 14, 3, 1)]
    assert [(x["yes"], x["no"], x["abstentions"]) for x in decisions("The French amendment was adopted in its entirety by 8 votes to 6, with 3 abstentions.")] == [(8, 6, 3)]
    assert [(x["outcome"], x["yes"], x["no"]) for x in decisions("The remainder was rejected on a roll-call by 11 votes to 5, with 2 abstentions.")] == [("rejected", 5, 11)]


def test_symbols_with_ocr_punctuation_and_recapitulations():
    from decisions import repair_symbols, symbols_in
    assert symbols_in("the seven-Power amendment (A/C,3/L,929 and Add,1), the India-Indonesia amendment (A/C.3/L»923/Rev.2)") == \
        ["A/C.3/L.923/Rev.2", "A/C.3/L.929"]
    assert repair_symbols("document E/CN.V117 and #/CN.4/434") == "document E/CN.4/117 and E/CN.4/434"
    # a document that recapitulates the amendments is not one of them
    out = build_db.cited("The amendments were recapitulated in document A/C.3/294/Rev.1. The amendment of Peru (A/C.3/225) was put.", "X")
    assert out["A/C.3/294/Rev.1"][0] is False and out["A/C.3/225"] == (True, ["Peru"])


def test_amendment_list_keeps_each_sponsor():
    text = ("Annex III, section A, contains the text of amendments submitted to parts I and II of the draft Covenant by the "
            "representatives of India (E/CN.4/563/Rev.1), of Yugoslavia (E/CN.4/573), of Egypt (E/CN.4/626) and of the United "
            "Kingdom (E/CN.4/628).")
    assert {k: v for k, v in build_db.cited(text, "E/1992").items()} == {
        "E/CN.4/563/Rev.1": (True, ["India"]), "E/CN.4/573": (True, ["Yugoslavia"]),
        "E/CN.4/626": (True, ["Egypt"]), "E/CN.4/628": (True, ["United Kingdom"])}
    assert proposers_in("the India-Indonesia amendment (A/C.3/L.923/Rev.2)") == ["India", "Indonesia"]


def test_paragraph_debris_is_never_an_english_word():
    from segment import classify
    # "in reply to Mr. SAPOZHNIKOV (USSR)" wraps to a line that starts "to Mr. ...": not a new speech (A/C.3/SR.1076)
    assert classify("to Mr. SAPOZHNIKOV (Union of Soviet Socialist Republics), that his delegation")[0] == ""
    assert classify("by Mr. ORDONNEAU (France) said")[0] == ""
    # while the OCR's debris before a paragraph number is still read
    assert classify("yo, Miss BOWIE (United Kingdom) thought it inappropriate")[1]["name"] == "BOWIE"
    assert classify("de My. WHLTLAM (Australia) drew attention")[1]["name"] == "WHLTLAM"


def test_tess3_across_marks_interleaved_pages(tmp_path):
    import ocr_select
    d = tmp_path
    for e in ("tess3", "vision", "layer"):
        (d / e).mkdir()
    text = " ".join(f"Everyone shall have the right to word{i} and article{i} of the draft Covenant." for i in range(40))
    (d / "vision" / "page-002.txt").write_text(text.replace(". ", ".\n"))
    (d / "layer" / "page-002.txt").write_text(text.replace(". ", ".\n"))
    # the automatic layout read two columns across: lines twice as long, words interleaved
    across = "\n".join(f"{a} {b}" for a, b in zip(text.split(". ")[::2], text.split(". ")[1::2]))
    (d / "tess3" / "page-002.txt").write_text(across)
    assert ocr_select.tess3_across(d, "page-002.txt")
    (d / "tess3" / "page-002.txt").write_text(text.replace(". ", ".\n"))
    assert not ocr_select.tess3_across(d, "page-002.txt")



def test_decision_ocr_figures_2():
    for text, want in [("The Commission adopted the Article by 11 votes with h abstentions.", (11, None, 4)),
                       ("Paragraph 2: was Adopted by 11 votes 1 to 3 with 4 abstentions.", (11, 3, 4)),
                       ("The Uruguayan amendment was rejected by five votes to throe, with seven abstentions.", (3, 5, 7)),
                       ("The first phrase was adopted by 11 votes to 6, with-1 abstention.", (11, 6, 1)),
                       ("The paragraph was adopted by 11 votes | to 3 3, with 1 abstention.", (11, 3, 1))]:
        assert [(x["yes"], x["no"], x["abstentions"]) for x in decisions(text)] == [want], text


def test_turns_inside_a_line_and_garbled_titles():
    import segment

    def turns(line):
        return [(segment.classify(x)[0], segment.classify(x)[1].get("name")) for _, x in segment.split_turns([(1, line)])]
    # (the segmentation audit's cases: a turn run into the line before, a title the OCR garbled, a turn opened by a phrase)
    assert turns("complaints made by one State against another. Mee Mr. RAMADAN (Egypt) thought that")[-1] == ("speech", "RAMADAN")
    assert turns("by the United Kingdom amendment. 56, bir. NISOT (Belgium) asked whether")[-1] == ("speech", "NISOT")
    assert turns("would therefore support it. 35. . Mr.. ALEMAYEHOU (Ethiopia) said that")[-1] == ("speech", "ALEMAYEHOU")
    assert turns("the French proposal. At the CHAIRMAN's request Mr. HUMPHREY (Secretariat) explained that")[-1] == ("speech", "HUMPHREY")
    assert turns("the Commission. 436 In reply to Mr. RAMADAN (Egypt), Mr. CASSIN (France) thought: the")[-1] == ("speech", "CASSIN")
    # not a turn: a name inside a sentence, the end of a joint statement begun on the line before, a paragraph number
    assert turns("the proposal of Mr. CASSIN (France) was adopted by 5 votes.") == [("", None)]
    assert turns("clarify the matter. As Mr. ENTEZAM (Iran) was also dissatisfied") == [("", None)]
    assert turns("and Mr. JEVREMOVIC (Yugoslavia) said that it would be difficult") == [("", None)]
    assert turns("40. Mr. YANCY (Liberia) said that, having studied") == [("speech", "YANCY")]
    assert turns("ROOSEVELT (United States of America) said that her delegation") == [("", None)]


def test_chair_turns_inside_a_line_and_running_heads():
    import segment
    from normalize import strip_furniture

    def kinds(line):
        return [segment.classify(x)[0] for _, x in segment.split_turns([(1, line)])]
    assert kinds("the vote on article 8. 33. The CHAIRMAN said that the Committee would vote") == ["", "chair"]
    assert kinds("Thank you. The PRESIDENT: I take it that we can consider paragraph 4 (e) approved.") == ["", "chair"]
    assert kinds("on article 3. 12. The CHAIRMAN's suggestion was adopted.") == [""]
    page = "\n".join(["Page 4", "first line of text", "second line", "414 General Assembly — Twenty-first Session — Third Committee",
                      "third line", "page 155.", "fourth line", "fifth", "sixth", "seventh", "Litho in U.N. 77301—March 1963—2,125"])
    body, removed = strip_furniture(page)
    assert "General Assembly" not in body and "Litho" not in body and "page 155." in body  # (a page cited mid-column stays)


def test_rejected_vote_with_the_minority_figure_lost():
    # "rejected by 20 votes to 6": the majority comes first and voted against; when the 6 is misread the 20 is still against
    d = decisions("The amendment was rejected by 20 votes to ó, with 11 abstentions.")
    assert d and d[0]["outcome"] == "rejected" and d[0]["no"] == 20 and d[0]["yes"] is None
    d = decisions("The amendment was rejected by 20 votes to 6, with 11 abstentions.")
    assert d[0]["yes"] == 6 and d[0]["no"] == 20


def test_more_running_heads_and_chair_after_a_decision():
    import segment
    from normalize import strip_furniture
    page = "\n".join(["first line of text", "E/CH.4/SR.249 Para 22", "second line", "382nd Meeting—10 January 1952 205", "third line",
                      "SPI—93250—February 1952—3,350", "fourth line", "fifth", "sixth", "seventh", "[New"])
    body, removed = strip_furniture(page)
    assert "Para 22" not in body and "382nd" not in body and "SPI" not in body and "[New" not in body and "third line" in body
    assert [segment.classify(x)[0] for _, x in segment.split_turns([(1, "It was so agreed. The CHAIRMAN suggested that the Commission take no action")])] == ["", "chair"]
    assert [segment.classify(x)[0] for _, x in segment.split_turns([(1, "He said it was adopted. The Chairman's ruling stood.")])] == [""]


def test_printers_lines_own_symbols_and_page_numbers():
    from normalize import strip_furniture
    page = "\n".join(["167", "first line of text", "A/C.3/SR.822 298", "second line (A/C.3/L.45)", "77301-January 1959-2,075", "third",
                      "241 A/C.3/SR.388 242", "fourth", "Page ly", "12", "fifth", "sixth", "Printed in U.S.A.", "326"])
    body, removed = strip_furniture(page, record=True)
    assert body.split("\n") == ["first line of text", "second line (A/C.3/L.45)", "third", "fourth", "12", "fifth", "sixth"]
    # (in a document such lines can be what separates two paragraphs: left alone)
    assert "167" in strip_furniture(page)[0] and "77301-January 1959-2,075" in strip_furniture(page)[0]


def test_openings_the_audit_found_missed():
    """Turns whose opening the OCR damaged or the printer wrapped (segmentation audit on page images, October 2026)."""
    import segment

    def kind_name(line):
        k, info = segment.classify(line)
        return k, info.get("name")
    assert kind_name("12. ‘Mr. PAZHWAK (Afghanistan) said that, as he") == ("speech", "PAZHWAK")      # a quote mark after the number
    assert kind_name("13. Mr. A, A. MOHAMMED (Nigeria) recalled that his delegation") == ("speech", "MOHAMMED")  # initials with a comma
    assert kind_name("48. Mr. FOMIN’ (Union of Soviet Socialist Republics)") == ("speech", "FOMIN")   # a quote after the name
    assert kind_name("18. Mrs. RAMAHOLIMIHASO (Madagascar}endorsed the Polish") == ("speech", "RAMAHOLIMIHASO")  # a brace for the bracket
    assert kind_name("18... Mr. HOARE (United Kingdom) said that when")[0] == "speech"                 # a number with three dots
    assert segment.classify("104. ‘The CHAIRMAN considered the Philippine suggestion")[0] == "chair"
    assert segment.classify("36, - -The CHAIRMAN, speaking as the representative of the United States, agreed")[0] == "chair"
    # a chair turn opened by a phrase needs a paragraph number and the chair doing something
    assert segment.classify("31. In accordance with the request of the Japanese representative, the CHAIRMAN put sub-paragraph")[0] == "chair"
    assert segment.classify("6. In answer to a question from Mr. AZNAR (Spain), the CHAIRMAN stated that the ten-minute")[0] == "chair"
    assert segment.classify("14. He would not oppose the Chairman's suggestion but proposed that the fourth")[0] == ""
    assert segment.classify("8. He was sorry that the Chairman had not interrupted the United States representative")[0] == ""
    assert segment.classify("In accordance with the request of the Japanese representative, the CHAIRMAN put")[0] == ""  # no number: not a turn


def _record(monkeypatch, tmp_path, symbol, pages):
    import segment
    d = tmp_path / segment.safe_name(symbol) / "vote"
    d.mkdir(parents=True)
    for i, text in enumerate(pages, 1):
        (d / f"page-{i:03d}.txt").write_text(text, encoding="utf-8")
    monkeypatch.setattr(segment, "OCR", tmp_path)
    return segment.segment_record(symbol, "vote")


def test_masthead_that_runs_past_page_3_and_what_the_body_holds(monkeypatch, tmp_path):
    """The Commission's records of 1951-53: a long contents page and an attendance table; the body starts on page 4. Joint
    statements, decisions and headings between the turns, footnotes at the foot of a page."""
    pages = [
        "UNITED NATIONS\nECONOMIC AND SOCIAL COUNCIL\nCOMMISSION ON HUMAN RIGHTS\nSUMMARY RECORD OF THE FIFTIETH MEETING\nheld on Friday, 17 April 1953, at 3 p.m.\nCONTENTS:\nArticle 5 and amendments thereto",
        "Present:\nChairman: Mr. AZMI (Egypt)\nRapporteur: Mr. KAECKENBEECK (Belgium)",
        "Members:\nMr. WHITLAM Australia\nMr. DIAZ-CASANUEVA Chile",
        "The CHAIRMAN invited the Commission to take up article 5.\n"
        "Mr. PAZHWAK (Afghanistan), supported by\nMiss BERNARDINO (Dominican Republic), asked that the list of speakers\nshould not be closed.\n"
        "Mr. MALIK (Lebanon) said that the text was clear.\nIt was so agreed.\n"
        "Paragraphs 22 to 26 were adopted.\nMIGRATION\nMr. HOARE (United Kingdom) said that the migration text\nshould stay.\n"
        "1See Annex 33.\nand then he went on.\n/Mr. SMITH\n|\n",
    ]
    segs = _record(monkeypatch, tmp_path, "E/CN.4/SR.50", pages)
    kinds = [(s["kind"], s["text"][:30]) for s in segs]
    assert kinds[0][0] == "masthead" and "Present" in segs[0]["text"] and "AZMI" in segs[0]["text"]   # the attendance table is not a speech
    assert [s["kind"] for s in segs[1:3]] == ["chair", "speech"]
    pazhwak = segs[2]
    assert "Miss BERNARDINO" in pazhwak["text"] and pazhwak["speaker_raw"] == "PAZHWAK"                # a joint statement is one turn
    assert not any(s.get("speaker_raw") == "BERNARDINO" for s in segs)
    decision = next(s for s in segs if s["text"].startswith("It was so agreed"))                       # the decision is not Malik's
    assert "agreed" not in next(s for s in segs if s.get("speaker_raw") == "MALIK")["text"]
    assert decision["kind"] in ("procedural", "vote") and "Paragraphs 22 to 26 were adopted" in decision["text"]   # the results run together
    heading = next(s for s in segs if s["text"] == "MIGRATION")
    assert heading["kind"] == "heading" and heading.get("agenda") and heading["article_heading"] is None   # display only: sets no article
    hoare = next(s for s in segs if s.get("speaker_raw") == "HOARE")
    assert "Annex" not in hoare["text"] and "SMITH" not in hoare["text"] and hoare["text"].endswith("went on.")
    note = next(s for s in segs if s["kind"] == "footnote")                                            # the footnote has its own segment
    assert note["text"] == "1See Annex 33." and segs.index(note) > segs.index(hoare)


def test_wrapped_opening_and_footnote_blocks(monkeypatch, tmp_path):
    import segment
    pages = ["28. In reply to a question from Mr. NUTTING\n(Canada), Mr. SCHWELB (Secretary of the Committee)\nrecalled that the Committee had divided its meetings.\n"
             "29. The CHAIRMAN suggested a vote.\n3/ See Official Records of the General Assembly, Fifteenth Session,\n"
             "Annexes, agenda item 35, document A/4636, annex,\npara. 12 of the draft.\n"]
    lines = segment.load_lines("A/C.3/SR.9", "vote") if False else None
    segs = _record(monkeypatch, tmp_path, "A/C.3/SR.9", pages)
    assert segs[0]["speaker_raw"] == "SCHWELB" and segs[0]["n"] == "28"                                  # the wrapped opening is Schwelb's turn
    assert segs[1]["kind"] == "chair" and "Official Records" not in segs[1]["text"]
    foot = [s for s in segs if s["kind"] == "footnote"]
    assert len(foot) == 1 and foot[0]["text"].startswith("3/ See Official Records") and "document A/4636" in foot[0]["text"]
    assert "para. 12 of the draft." in segs[1]["text"]                                                   # the line after the footnote is body


def test_stage_directions_and_decisions_of_a_verbatim_plenary(monkeypatch, tmp_path):
    """The verbatim records print (A vote was taken ...) and "Decision: ..." between the President's turns."""
    pages = ["The PRESIDENT (Translation from the French): I will put to the vote paragraph (d).\n"
             "(A vote was taken by a show of hands.)\nDecision: Paragraph (d) was adopted.\n"
             "The PRESIDENT (Translation from the French): I propose that the meeting be adjourned.\n"
             "(The meeting was adjourned at 4.45 p.m.)\nMr. DIHIGO (Cuba) said that his delegation agreed."]
    segs = _record(monkeypatch, tmp_path, "A/PV.9", pages)
    assert [s["kind"] for s in segs] == ["chair", "vote", "chair", "procedural", "speech"]
    assert not any("vote was taken" in s["text"] or "4.45" in s["text"] for s in segs if s["kind"] == "chair")


def test_roll_calls_results_and_notes_the_ocr_ran_into_a_turn(monkeypatch, tmp_path):
    """The segmentation audit's largest class (round 68): a roll-call block, the chair's result, a decision by a count of votes,
    the meeting suspended and a member taking the chair, run by the OCR into the turn before them; and a speech that only
    reports an earlier vote stays whole."""
    pages = ["1. Mr. PAVLOV (Union of Soviet Socialist Republics) asked that the vote should be taken by roll-call. "
             "A vote was taken by roll-call as follows: In favour: Byelorussian Soviet Socialist Republic, Poland.\n"
             "Against: Australia, Belgium.\n"
             "2. The CHAIRMAN put the words \"within its territory and\" to the vote separately. The words \"within its territory and\" were\n"
             "retained in paragraph 1 by 55 votes to 10, with 19 abstentions.\n"
             "3. Mr. WILSON (United Kingdom) said that the text was clear. It was agreed by a vote of three to one with two abstentions\n"
             "that paragraph (c) should be retained.\n"
             "4. Mr. CASSIN (France) recalled that at the fifth session the article was adopted by 10 votes to 2 and\n"
             "that nothing had changed since. The meeting was suspended at 4.25 p.m. and resumed at 4.45 p.m.\n"
             "Mr. Ghorbal (United Arab Republic), Vice-Chairman,\ntook the Chair.\n"
             "5. Mrs. MEHTA (India) said that she agreed."]
    segs = _record(monkeypatch, tmp_path, "A/C.3/SR.1259", pages)
    kinds = [(s["kind"], s["text"][:24]) for s in segs]
    pavlov = next(s for s in segs if s.get("speaker_raw") == "PAVLOV")
    assert "In favour" not in pavlov["text"] and pavlov["text"].endswith("by roll-call.")
    roll = next(s for s in segs if s["text"].startswith("A vote was taken by roll-call"))
    assert roll["kind"] in ("procedural", "vote") and "Against: Australia" in roll["text"]
    chair = next(s for s in segs if s["kind"] == "chair")
    assert chair["text"].endswith("to the vote separately.")
    result = next(s for s in segs if s["text"].startswith("The words"))
    assert result["kind"] in ("procedural", "vote") and "55 votes to 10" in result["text"]   # ("retained" is no vote outcome)
    wilson = next(s for s in segs if s.get("speaker_raw") == "WILSON")
    assert wilson["text"].endswith("the text was clear.")
    assert any(s["text"].startswith("It was agreed by a vote of three") for s in segs)
    cassin = next(s for s in segs if s.get("speaker_raw") == "CASSIN")
    assert "adopted by 10 votes to 2" in cassin["text"] and "suspended" not in cassin["text"]   # a reported vote is the speaker's
    assert any(s["kind"] == "procedural" and s["text"].startswith("The meeting was suspended") for s in segs)
    took = next(s for s in segs if "took the Chair" in s["text"])
    assert took["kind"] == "procedural" and not took.get("speaker_raw"), kinds                    # a note, not Ghorbal's speech
    assert segs[-1].get("speaker_raw") == "MEHTA"


def test_turns_the_ocr_or_the_layout_hid(monkeypatch, tmp_path):
    """Missed turns from the segmentation audits (rounds 68-74): titles and numbers the OCR garbled, an opening broken before
    its delegation or its verb, the chair's turn opened by a phrase without a paragraph number; and a phrase that only mentions
    the chair stays in the speech."""
    pages = ["1. Mr. CASSIN (France) said that the text was clear and that the matter was settled by the Secretariat Draft. Mr. WILSON\n"
             "(United Kingdom) opposed the idea of presenting any draft at all.\n"
             "50; Mrs, AFNAN (Iraq) asked for a separate vote on the words.\n"
             "In reply to Mr. HOARE (United Kingdom), the CHAIRMAN said that the proposal was in order.\n"
             "Migs BOWIE (United Kingdom), supported by Mrs. MEHTA (India),\n"
             "urged the Commission to decide at once.\n"
             "15. The Marquis DE VALDEIGLESIAS (Spain) fully approved of the spirit of the text.\n"
             "After a further exchange of views, in which Mr. INGLES (Philippines),\n"
             "Mr. NISOT (Belgium) and Mr. CASSIN (France) took part, the CHAIRMAN\n"
             "proposed that the Commission should adopt his last proposal.\n"
             "16. Mr. MALIK (Lebanon) said that, in accordance with the Chairman's ruling, the CHAIRMAN had\n"
             "been right."]
    segs = _record(monkeypatch, tmp_path, "E/CN.4/SR.9", pages)
    turns = [(s["kind"], s.get("speaker_raw")) for s in segs if s["kind"] in ("speech", "chair")]
    assert turns == [("speech", "CASSIN"), ("speech", "WILSON"), ("speech", "AFNAN"), ("chair", None), ("speech", "BOWIE"),
                     ("speech", "DE VALDEIGLESIAS"), ("chair", None), ("speech", "MALIK")], turns
    assert segs[0]["text"].endswith("Secretariat Draft.")


def test_footnotes_with_other_markers_and_openers(monkeypatch, tmp_path):
    """Footnotes the audits of rounds 73-76 found left in a speech: "*" and "+" and an apostrophe for a marker, a digit with no space
    after it, "Resumed from", "Ibid.", the 1948 "Article N of the draft universal declaration" with no marker, a line that goes on
    after a slash; and numbered paragraphs that open with the same words stay in the text."""
    from normalize import strip_furniture
    page = "\n".join(["first line of the speech", "second line of the speech", "that the Charter laid upon the United Nations an obliga-",
                     "* Resumed from 745th meeting.", "tion that could not be set aside.", "9. The omission of a reference to sovereignty was noted.",
                     "she consequently requested the", "Article 24 of the draft universal declaration of human", "rights (A/777).", "inclusion of the article in the text.",
                     "1The omission was rectified in document A/C.3/L.337/", "Corr.2.", "4 Ibid., Sixteenth Session, Supplement No. 12, pp. 22 and",
                     "34, and Supplement No. 12A, pp. 1, 2 and 3."])
    notes: list[str] = []
    body, removed = strip_furniture(page, record=True, notes=notes)
    assert "Resumed from" not in body and "Ibid" not in body and "Corr.2" not in body and "A/777" not in body
    assert "tion that could not be set aside." in body and "inclusion of the article in the text." in body
    assert "9. The omission of a reference to sovereignty was noted." in body         # a paragraph, not a footnote
    assert any(n.startswith("* Resumed from") for n in notes) and any("Corr.2." in n for n in notes) and len(notes) == 4


# ---------- Schabas's index ----------
def test_possible_text_joins_readers_and_schabas():
    possible = {"a-1": "UDHR 3 (one reader, or two readers apart)"}
    schabas = {"a-1": ["UDHR 18 (Schabas index p. 2044)"], "a-2": ["UDHR 19 (Schabas index p. 2045, 2046)"]}
    assert build_db.possible_text("a-1", None, possible, schabas) == \
        "UDHR 3 (one reader, or two readers apart); UDHR 18 (Schabas index p. 2044)"
    assert build_db.possible_text("a-2", None, possible, schabas) == "UDHR 19 (Schabas index p. 2045, 2046)"
    assert build_db.possible_text("a-1", 18, possible, schabas) is None
    assert build_db.possible_text("a-3", None, possible, schabas) is None


def test_locate_span_returns_the_window():
    hyp = "the commission should not retain it if it did not wish to establish a completely new legal theory"
    score, dist, a, b = locate_span("should not retian it if", hyp)
    assert (score, dist) == locate("should not retian it if", hyp)
    assert hyp[a:b] == "should not retain it if"


def test_article_heading_after_a_speck():
    from segment import ARTICLE_HEAD_RE
    for line in (".:.Article 25 :.", ". Article 16", ".. Article 22", "Article 25"):
        assert ARTICLE_HEAD_RE.match(line), line
    assert not ARTICLE_HEAD_RE.match("the provisions of article 25 were adopted")


def test_speaker_carry_keeps_old_speakers_and_counts_new_turns():
    from speaker_carry import carry
    sp = lambda i, who, deleg, text: {"id": i, "kind": "speech", "speaker": who, "delegation": deleg, "method": "vote_joint",
                                      "text": text}
    old = [sp("r-1", "HEYWARD", "Australia", "Mr. HEYWOOD (Australia) said that the article should be kept as it stood"),
           sp("r-2", "MALIK", "Lebanon", "Mr. MALIK (Lebanon) agreed with him. Mr. CASSIN (France) thought the text too long "
                                         "and proposed to delete the second sentence")]
    new = [sp("r-1", "HEYWOOD", "Australia", "Mr. HEYWOOD (Australia) said that the article should be kept as it stood"),
           sp("r-2", "MALIK", "Lebanon", "Mr. MALIK (Lebanon) agreed with him."),
           sp("r-3", "CASSIN", "France", "Mr. CASSIN (France) thought the text too long and proposed to delete the second sentence")]
    rows, n, turns = carry(old, new)
    assert [(r["segment_id"], r["speaker"]) for r in rows] == [("r-1", "HEYWARD")]
    assert n["continues an old speech"] == 2 and n["new turn (split from an old speech)"] == 1
    assert [t["id"] for t in turns] == ["r-3"]


def test_drop_french_runs_takes_columns_not_quotations():
    from normalize import drop_french_runs
    english = ["Mr. CASSIN (France) thought the proposal made by the representative of Egypt should be dealt with first",
               "and agreed that the Committee must decide whether the questions of rights and duties were to be dealt with."]
    column = ["M. CASSIN (France) juge qu'il y a lieu d'examiner en premier lieu la proposition du représentant de l'Egypte,",
              "et reconnaît que c'est bien à la Commission qu'il appartient de décider si la question des droits",
              "et la question des devoirs doivent être traitées dans des chapitres séparés. S'il en était ainsi décidé,",
              "la déclaration de Bogota pourrait utilement être prise pour guide. Le comte CARTON DE WIART est d'accord",
              "avec le représentant de l'Egypte et demande qu'on définisse le fond du débat. Il est indispensable que la",
              "Commission sache si elle doit étudier seulement le projet de déclaration ou si la question des devoirs."]
    text, n = drop_french_runs("\n".join(english + column))
    assert text.splitlines() == english and n == 6
    # a statement quoted in French, opened in the English line before (A/3525), and a short French quotation stay
    quoted = english[:1] + ['include a statement that "la commission,'] + column[1:] + ['and the Committee agreed to it.']
    assert drop_french_runs("\n".join(quoted))[1] == 0
    short = english + column[:2] + english
    assert drop_french_runs("\n".join(short))[1] == 0
    # a French page facing an English one goes whole, its headings too
    page = ["ARTICLE 6"] + column
    assert drop_french_runs("\n".join(page)) == ("", 7)
