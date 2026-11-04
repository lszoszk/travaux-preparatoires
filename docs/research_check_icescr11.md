# Research check: ICESCR article 11 (adequate standard of living; freedom from hunger)

**Date:** 28 September 2026. **Method:** as for ICCPR 6 (`docs/research_check_iccpr6.md`), with a
workflow of 60 agents, read-only on the database.

1. **Ground truth.** Two readers took 73 facts from the UN reports:
   - the Third Committee's A/3525 (1956-57, articles 11 and 12 combined) and A/5655 (1963,
     freedom from hunger);
   - the Commission's E/1992 (1951) and E/CN.4/669 (= E/2256, 1952);
   - A/2929.
2. **Research from the database alone.** Six researchers answered typical questions:
   - how the article came together;
   - the hunger paragraph and FAO's part in it;
   - housing and clothing;
   - "based on free consent";
   - the positions of the United States and the Soviet Union;
   - the 1956-57 votes.
3. **Comparison and verification.** One agent compared the facts with the database, and each
   discrepancy went to a verifier told to refute it.

## Result

**54 of 73 facts** could be found and were right (74%; ICCPR 6 had 67 of 108, 62%, before that
check's fixes). Of 51 discrepancies, the verifiers confirmed 45 and refuted 6. This time the
report paragraphs were tagged, and the researchers could use them: the working party of 1957,
the eleven-Power proposal of 1963 and most votes are in the article's history with their
figures.

## Fixed in this step

- **The spelling fix turned a state into a word.** In the OCR's word-level vote,
  `pipeline/spellfix.py` "corrected" rare words to much commoner ones. It changed "Uganda" into
  "agenda", "Malian" into "mation" and "Rumania" into "Romania". Uganda was missing from the
  roll-calls of 1963-66 (A/5655, A/6546), from the sponsors of L.1175 and L.1177, and from one
  speaker's delegation (A/C.3/SR.1290). The words of state names and adjectives in the
  gazetteer are now never corrected. The vote was redone for the 37 documents whose OCR names
  them, and everything was segmented again. Of the 1,761 segment files, 1,753 are unchanged.
  The other 8 changed only in their text (and in one speaker's country), and **no segment id
  changed**.
- **Symbols read with an I.** "A/C.3/I.1177" is A/C.3/L.1177 (`build_db.fix_symbol`). 79 of the
  80 phantom references are gone.
- **Sponsors.** L.586 (the working party on articles 11 and 12), L.1175, L.1177 and L.1177/Rev.1
  (the hunger paragraph), and E/CN.4/L.48 (USSR) and L.83 (UK) now have their sponsors from the
  reports. `amendment_sponsors_checked.csv` takes "added" rows for documents the reports list
  only in a table, or where the parser reads nothing.
- **A suggestion the sponsors accepted is not a vote.** Examples are "This suggestion was
  adopted by the sponsors of the eleven-Power proposal" and "was accepted by the
  representative of France". There were 23 such decisions without figures. All 23 were
  checked and removed.
- **Votes on procedure carry no article.** Motions to adjourn or to close the debate, and
  challenges to the chair's ruling, now carry no article tag. There were 27 such decisions,
  among them E/CN.4/SR.294's adjournment, which the article-11 vote list had shown as adopted
  10-4-4.

## Still open (confirmed, not fixed)

1. **OCR on two-column pages and dropped lines.** E/CN.4/669 paragraphs 126-132 are interleaved
   and the 1952 paragraphs on articles 23-24 are lost. In E/CN.4/SR.222 the votes on housing
   fall into the gaps. In A/3525 "741st meeting, 24 January" reads "Tilst meeting on 2
   January". `pipeline/ocr_select.py` takes tess3's text for these pages without testing it
   for merged columns. This is the reading-order task (candidate 2 of the outside tasks).
2. **Segmentation.**
   - Headings of the Covenant debates printed in small capitals are missed, e.g. at A/C.3/SR.743.
     Speeches after the vote on article 11 carry draft article 11 into the debate on health.
   - Fused speeches in E/CN.4/SR.222 and SR.294: the M of "Mr." read as K, a speaker line without
     a title.
   - French passages misjudged by `normalize.english_only` split a speech between two speakers
     (A/C.3/SR.1267).
   - FAO's Director-General's statement at SR.1232 sits inside the chair's segment.
   - Report paragraphs whose number the OCR misread (A/3525 paras. 124, 141, 143) are joined to
     the paragraph before.

   Each of these changes segment ids, so it needs a re-segmentation that keeps the ids, or a
   map from the old ids to the new.
3. **Meetings missing from the history.**
   - SR.1266, where the joint text on hunger was announced, needs its heading read as the
     article's.
   - SR.1260, where L.1172 was tabled, has its speeches dropped by Jev with a stale draft number.
   - SR.739-741, where the combining of articles 11 and 12 and the working party were debated,
     is untagged: that is procedure, and the rules leave it out.
   - E/CN.4/SR.203 is not in the collection.
4. **Decisions still missed.** A consent without a vote ("It was so decided", "the Committee
   agreed to combine") gives no decision row. Neither do some votes whose "by" the OCR split
   ("appropriate steps", 143(e)). Some decision subjects run two votes together (the Egyptian
   amendment in E/1992).
5. **Draft texts.** The article history jumps from A/2929 to the final text. It lacks the
   combined text adopted in 1957 and the 1963 paragraph, which are in the reports' annexes
   rather than in a stage of `draft_texts`. The final text still carries a running header ("...
   Third Committee 51").
