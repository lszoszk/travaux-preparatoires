# Research check: UDHR 18 and ICCPR 18 (freedom of thought, conscience and religion)

**Date:** 28 September 2026. **Method:** as for ICCPR 6 and ICESCR 11, with a workflow of 91
agents, read-only on the database. It adds a first step: the pinpoints of the book's wiki note
(`The Book/00_PROJECT/wiki/entities/article-18-udhr-iccpr-travaux.md`) were looked up in the
database. Only the note's UN pinpoints were used. No Schabas text or Zotero file was read.

- **Ground truth:** 98 facts from UN reports:
  - E/CN.4/21, E/CN.4/95, E/800 and A/777 for the UDHR, 1947-48;
  - E/CN.4/350, E/1681, E/1992, E/CN.4/669, E/CN.4/705, A/2929 and A/4625 for the ICCPR, 1949-60.
- **Research:** six researchers answered questions from the database alone:
  - thought and its manifestation;
  - the freedom to change religion in 1948;
  - "to have or to adopt" in 1950-60;
  - coercion (18(2));
  - parents (18(4));
  - thought and expression.
- **Comparison and verification** as before.

## The book note's pinpoints: all found, all supported

| Pinpoint | In the database | Notes for the book |
|---|---|---|
| E/CN.4/AC.1/SR.31, p. 6 | e_cn.4_ac.1_sr.31-0014, Malik (Lebanon), tagged ICCPR 18 | Supports the claim. The paragraph was split to separate inner belief from practice. The text concerns the **draft Covenant** article (Geneva text art. 16, the French-Lebanese-UK redraft E/CN.4/AC.1/35), not the Declaration's. |
| E/CN.4/SR.60, p. 10 | e_cn.4_sr.60-0033, Cassin (France), UDHR 18 | Supports the claim. Every OCR engine reads "possible to **attach** it indirectly". The typescript probably has that typo for "attack", so a direct quotation should keep [sic] or check the French record. Malik's reply on p. 11 (adding thought, splitting his amendment), once inside Cassin's segment, is now its own (-0036). |
| E/CN.4/SR.60, pp. 12-13 | -0038 to -0044: Wilson (UK), Pavlov (USSR), Fontaina (Uruguay), the Chairman, Cassin, Lopez (Philippines), Chang (China) | Supports the claim. The debate ends on p. 14 (Wilson, then the sub-committee), so "pp. 12-14" is more complete. |
| E/CN.4/SR.164, p. 4 | e_cn.4_sr.164-0012, Azkoul (Lebanon), para. 10, ICCPR 19 | Supports the claim. The speaker can be named (Azkoul) and the paragraph given (para. 10). |
| Third Committee, Nov. 1948: the USSR on thought, science and free-thinkers | A/C.3/SR.127 (9 Nov. 1948), a_c.3_sr.127-0005, Pavlov, PDF p. 2 = GAOR p. 391, UDHR 18 | Supports the claim. See also SR.127 p. 13 (GAOR p. 402) and his explanation of vote at SR.128. |
| The same debate: keep only the first sentence of art. 16 | a_c.3_sr.127-0006, Baroody (Saudi Arabia), A/C.3/247, PDF p. 2 = GAOR p. 391 | Supports the claim; the proposer is Baroody. He withdrew it (SR.127, PDF p. 7, GAOR p. 396) and proposed instead to delete only the words on changing religion (A/C.3/247/Rev.1), which was rejected 22-12-8 at SR.128. |

## Result

**63 of 98 facts** could be found and were right (64%). Of 81 discrepancies, the verifiers
confirmed 64. They fall into seven groups.

1. **The 1947-48 records** (Drafting Committee, the Commission's 2nd-3rd sessions, the Third
   Committee 1948) are where most errors are:
   - speakers merged into another's segment (garbled chair lines, "Ma," for "Mr.", a title after
     the name: "AZMI Bey");
   - joint and plural headings ("Articles 5, 6 and 7", "Articles 17 and 18") not read as
     headings;
   - a heading copied onto the wrong passages;
   - two-column bilingual pages that let French text into English segments.

   As a result, some speeches on the religion article are tagged UDHR 12, 14, 15, 16, 17 or 27,
   or not at all.
2. **Reports and annexes still untagged:**
   - the Drafting Committee's 1947 report E/CN.4/21, with the UK draft art. 13 and the draft
     Convention (annex G, so ICCPR 18 has no 1947 stage);
   - the sub-committee report E/CN.4/113;
   - the Covenant texts in the annexes of E/CN.4/350 and E/1992 (kept as one "none" row each);
   - the text of art. 18 in the A/4625 annex.
3. **Decisions:**
   - figures in words ("by twelve votes for, none against, and four abstentions");
   - OCR damage before "with N abstentions";
   - active sentences ("the Commission approved article 16 by 11 votes to none");
   - subjects that reach back past the previous vote;
   - a motion credited to its seconder;
   - roll-calls that lose a state ("United Kingdom of Great Britain and Northern Ireland" split
     at "and").
4. **The Third Committee 1950-54** debated the religion clause, but those speeches carry no
   ICCPR 18 tag. The article's history lists no General Assembly meeting between 1952 and 1960.
   A/2929's documentation tables name those meetings (see the untracked
   `pipeline/a2929_documentation.py`, the maintainer's work in progress).
5. **A/777 is staged as "final"**, so the UDHR 18 history lacks A/777 and the plenary vote on
   the article (tagged 19 by A/777's numbering).
6. **Amendment texts not in the collection** (E/CN.4/L.187, L.155, L.143, A/C.3/L.875-877,
   E/CN.4/626, 628). They could be added only by a new download.
7. **Sponsors:**
   - a symbol split by the OCR ("A/C.3/ 247");
   - UK "prescribed by law" cited as L.145;
   - the "or to adopt" vote (54-0-15) credited only to Brazil and the Philippines.

## Fixed: the 1947-48 segmentation (group 1)

The segment ids above are those after this fix (`data/id_maps/2026-09-28-2.json` maps the old
ones). `pipeline/segment.py` now reads:
- "Ma," "M:" and "Lr." for "Mr.";
- a curly or square bracket that the OCR read for the "(" before a delegation;
- a title after the name ("AZMI Bey (Egypt)");
- garbled chair lines ("The CHAIPMAN");
- joint and plural headings ("Articles 5, 6 and 7").

`pipeline/resegment.py` changed 285 records and split 311 segments; the gold, Jev's caches, the
tagger's lists and the sponsors moved with their passages. A joint heading sets its first
article; Jev's choice among the meeting's articles now also offers the heading's others
(E/CN.4/SR.268: "Articles 20, 21 and 22"). The chair's "covered by article 5" no longer replaces
the article under discussion (E/CN.4/SR.182, 14 speeches on ICCPR 7). Speeches went from 24,899
to 25,135 and tagged speeches from 9,418 to 9,618. Blind checks (round 49): 26 of 30 new
segments split right, 29 of 30 speakers right, and 25 of 26 tags right. The 4 wrong splits are
further speakers the OCR garbled beyond the new patterns ("SEMI Bey (Ezrpt)", "Mire NISOT").

## Fixed: the reports and annexes (group 2)

- **E/CN.4/21** (the Drafting Committee's report, June 1947) is tagged article by article. It
  has 281 annex rows and 9 body rows:
  - the Secretariat outline;
  - the United Kingdom's draft bill (its art. 13 is ICCPR 18);
  - the US suggestions;
  - Cassin's articles, in English and French (art. 21 is UDHR 18);
  - the Committee's revised articles (art. 20);
  - the articles for a convention (annex G: its art. 8 is ICCPR 18).

  The UK draft and annex G are also two new stages of the Covenant drafts
  (`uk_draft_1947`, `e_cn4_21_g`), so ICCPR 18's history now opens in June 1947.
- **E/CN.4/113** (the sub-committee on art. 16, June 1948): para. 1 is UDHR 18, paras. 2-3 are
  UDHR 19.
- The draft covenant texts in the annexes of E/CN.4/350, E/1992, E/CN.4/669 and E/CN.4/689
  are now split into one row per article (and per alternative text), where each had been a
  single untagged row.
- A/4625's annex (arts. 15-18 as adopted in 1960) is tagged.

Each document was read by one agent and checked by a second. 1,114 passages gained a tag.
Blind check (round 50): 28 of 30 right; the two errors (a sentence on torture inside the
right-to-life article, a stray heading) were fixed.

## Fixed: decisions (group 3)

`pipeline/decisions.py` now reads more ways of recording a vote:
- active sentences ("the Commission approved Article 16 by eleven votes to none, with four
  abstentions", E/CN.4/SR.62);
- figures that come first ("By 38 votes to 2, with 7 abstentions, the words were retained");
- results in brackets ("(Adopted by 8 votes to 1)");
- figures in words with "for" and "against" ("by twelve votes for, none against, and four
  abstentions");
- the OCR's damage ("vas", "wae", "auopted", "by ,10", "to i none T with", "epstentions",
  "votes to, with").

A vote's subject no longer takes in the whole vote before it: only what that vote was on.
Roll-calls keep "United Kingdom of Great Britain and Northern Ireland" and "Trinidad and
Tobago" as one state each. A seconder, a supporter or a delegation that only suggested a
change is not counted as a proposer. The decisions went from 5,002 to 5,304; complete
roll-calls went from 86 to 156. UDHR 18 now has 24 votes (it had 20), and ICCPR 18 has 44
(it had 40). Blind check of 40 new decisions (round 51): all 40 are decisions with the right
outcome, and 33 have the right figures. The misses were OCR-garbled digits (four), and three
lost abstentions, which are now read.

## Fixed: A/777 and the plenary of 10 December 1948 (group 5)

A/777, the Third Committee's text, is now a stage of its own (`a777`), no longer the final
numbering. The plenary deleted its article 3 (on Trust and Non-Self-Governing Territories),
whose substance became the second paragraph of final article 2. A/777 article N is therefore
final article N-1 from article 4 on (`data/concordance/overrides.csv`). The plenary records
(A/PV.180-183) and the amendments to A/777 (A/784, A/778) use that numbering. The vote on
the religion article, "Article 19" at A/PV.183 (45-0-4), is now UDHR 18.

A/777's own text is read article by article (one reader, one checker): its segments carry
their final articles, and its 31 articles are a stage in every article's history. UDHR 18's
history now runs from E/800 art. 16 through A/777 art. 19 to the final text. Votes on the
preamble, on resolutions B-E, on the Declaration as a whole or on a group of articles
("Articles 4 to 13") carry no article.

## Fixed: sponsors and references (group 7)

- **Symbols the OCR spaced out or misread** are now read as the documents they are:
  - "A/C.3/ 247", "A/C.3 /232", "A /C.3/289 /Rev.1";
  - "A/C. 3/1.656" and "A/C.3/l.650" for the L-series;
  - "A/C.38/L.875", "E/CN4/L.143".

  The Third Committee's 1948 amendments to the religion article (Peru A/C.3/225, Cuba
  A/C.3/232, Saudi Arabia A/C.3/247 and 247/Rev.1, Sweden A/C.3/252) are now cited with their
  sponsors. Many revisions that had lost their "/Rev.N" keep it.
- **L.145 at E/CN.4/SR.319** is L.143 on the scan ("prescribed by law"). A per-passage table
  (`data/concordance/ref_fixes.csv`) corrects it there only, because L.145 is right at SR.325.
- **"Or to adopt"** (54-0-15) was the United Kingdom's oral suggestion (Hoare, A/C.3/SR.1027).
  The Brazil-Philippines sponsors accepted it (`data/concordance/decision_proposers_checked.csv`).
- **The adjournment motion** at A/C.3/SR.1024 is credited to its mover, Afghanistan, and no
  longer to the Philippines, whose suggestion it concerned.
- **Sponsors added by hand** for 15 documents the reports do not list:
  - the 1947-48 texts E/CN.4/AC.1/20 (United States), E/CN.4/82/Add.8 (France), E/CN.4/99
    (India and the United Kingdom), E/CN.4/272 (USSR) and E/CN.4/301 (France);
  - the 1948 amendments above;
  - A/C.3/L.75 and L.75/Rev.1 (Egypt) and A/C.3/L.422 (Saudi Arabia).

  A/C.3/L.460, the compilation of amendments, has no sponsor instead of "Brazil".
- **Names joined by a hyphen** ("the India-United Kingdom text", "the joint United
  Kingdom-Indian amendment") and a "document" before the symbol are read.
- **"His amendment"** is no longer credited to the speaker when the sentence names another
  delegation's representative first ("He hoped that the Netherlands representative would not
  press his amendment").

## Suggested order of fixes

1. The 1947-48 segmentation (group 1), now that `pipeline/resegment.py` keeps the ids.
2. Hand-read sections for E/CN.4/21 and E/CN.4/113 and per-article rows for the Covenant texts
   in the annexes (group 2): data only.
3. Decisions (group 3): figures in words and active sentences.
4. The 1950-54 Third Committee meetings from A/2929's documentation tables (group 4), when the
   maintainer's `a2929_documentation.py` is ready.
