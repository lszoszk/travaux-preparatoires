# Research check: UDHR 5 (torture) and UDHR 8 (effective remedy)

**Date:** 4 October 2026. **Why:** UDHR 5 had 4 tagged speeches and UDHR 8 had 1, against 70 on
article 4 and 127 on article 7. A reader of the Declaration's history would take that for a gap in
the database. **Method:** two readers (Claude Opus and Claude Sonnet) read each of 67 meeting
records whole, without seeing each other's answer, and listed every speech mainly about article 5
or 8, whatever tag it had. The 67 are the UDHR records with any speech that mentions torture,
cruel, inhuman or degrading treatment, remedy, recourse, *amparo* or the competent national
tribunals, plus the Third Committee's meetings 108 to 115. No Schabas, Saul or Bossuyt text and no
Zotero file was read.

## What the concordance says

The draft-to-final concordance is right in both cases. The cause of the low counts lies elsewhere.

- **Article 5** was never an article of its own before the Third Committee. The torture clause was
  the second paragraph of E/800 article 4 (slavery, then torture), and in the Geneva-era drafts it
  stood beside the presumption of innocence (E/CN.4/21 draft article 10, E/600 article 7,
  E/CN.4/95 article 8). The Third Committee debated paragraph 2 together with slavery at
  A/C.3/SR.109 and 110, so those speeches carry the tag of the article under discussion, 4. The
  article page now says which drafts hold two articles ("also holds art. 11", "also holds art. 4").
- **Article 8** has one draft only, A/777 article 9. It began as the Mexican amendment
  (A/C.3/308, then the joint revised text A/C.3/309), which the Third Committee debated inside the
  debate on draft article 6 (final article 7) at SR.111 to 113. The vote that adopted it (46 to
  none, 3 abstentions, SR.113) was filed under article 7 as well.
- The torture debates of 1947 and 1948 in the Drafting Committee and the Commission often concern
  the draft Covenant's article (ICCPR 7), and that tag is right. Nine speeches the readers
  called "UDHR 5" are of this kind and were left alone.

## Result

The readers gave 61 speeches; both gave the same article for 45 (23 for article 5, 22 for 8). Of
these, 5 already carried the right tag. For the rest the rules were stricter than for an untagged
speech, because a wrong override loses a right tag:

- an **untagged** speech needed both readers on the same article, one of them sure, and Jev at
  0.7 or more;
- a speech **tagged with the article its debate was filed under** (UDHR 4 for 5, UDHR 7 for 8)
  needed both readers sure, and Jev at 0.7 or more;
- a speech tagged otherwise (the Covenant articles, for instance) was not touched.

Eighteen speeches met the first two rules, 14 of them with Jev at 0.7 or more. Two blind judges
(a third on a split) then read each of the 14 in its record. Three were rejected and one passed
only by two judges to one:

- a speech by Malik (Drafting Committee, E/CN.4/AC.1/SR.23) that is about the draft Covenant's
  article, not the Declaration's;
- a speech by Santa Cruz (E/CN.4/AC.1/SR.40) that only accepts moving the torture paragraph;
- a speech by Plaza (A/C.3/SR.112) that is half on equality;
- a brief withdrawal by Chang (A/C.3/SR.113), which two judges took for a speech on the amendment
  and one for procedure. It is left out, because a split is not enough to override a tag.

The other 10 were accepted: 8 moved from article 7 to article 8 (`data/concordance/speech_retags.csv`),
2 newly tagged with article 5 (`data/concordance/reader_tags.csv`). The vote at SR.113 that adopted
the Mexican amendment, whose text is the final article 8 word for word, moved from 7 to 8 as well
(Jev 0.96, checked by reading). The build applies the retags last and only to the tag each row
names as the previous one.

| | Speeches before | Speeches after |
|---|---|---|
| UDHR 5 | 4 | 6 |
| UDHR 8 | 1 | 9 |
| UDHR 7 | 127 | 119 |

## What the counts still do not show

- **Mixed speeches stay with the article of their debate.** Ten Third Committee speeches that both
  readers saw as partly on torture or remedy (SR.109, 110, 112, 113) keep their tag, 4 or 7.
  Splitting a speech is not possible at this level, and the speaker's emphasis is a judgement the
  database does not make. An article-5 search for those meetings therefore starts from the article
  4 and 7 tags.
- **Only the 67 records were read.** A speech on torture in a record without any of the keywords
  would not have been listed.
- **The readers answered for the Declaration.** They do not decide between the Declaration and the
  Covenant in the 1947-48 records; the blind check did, and it removed one such speech. The
  speeches the readers saw as Covenant ones were not added to ICCPR 7, which they already carry.
- **Nine speeches on article 8 are what the database holds.** The Mexican amendment was debated
  for three meetings, but most of the other speeches mix it with equality before the law or only
  speak to procedure, and those keep article 7. Three more speeches (Uruguay on article 5 at SR.109,
  Cuba on article 8 at SR.112 and SR.113) were stopped by Jev at 0.64 to 0.69, below the 0.7 the
  rule asks for.
