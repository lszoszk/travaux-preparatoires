# Article concordance

- `articles.csv`: the final articles of each instrument (UDHR done; ICCPR and ICESCR added in Phase 3).
- `drafts.csv`: one row per draft article at each drafting stage, mapped to the final article.

Draft numbering changed at every stage. For example, the right to freedom of thought sits under a different number in the Secretariat outline, the Geneva draft, the E/800 draft and the Third Committee text. `drafts.csv` is filled **only from the primary documents themselves**: each row cites the UN symbol and page where that stage's text shows the numbering. Nothing is taken from Schabas, Bossuyt or Saul, which may be used only as checks.

`drafts.csv` columns:

| column | meaning |
|---|---|
| instrument | UDHR / ICCPR / ICESCR |
| stage | short stage id, e.g. `secretariat_outline`, `geneva_draft`, `e800`, `third_committee` |
| stage_symbol | the UN document that fixes that stage's text, e.g. `E/CN.4/AC.1/3`, `E/600`, `E/800` |
| draft_article | the article number (or label) used at that stage |
| final_article | the article of the adopted text it became (blank if dropped) |
| source_pinpoint | page or ¶ in `stage_symbol` showing the mapping |
| note | merges, splits, deletions |

UDHR stages to cover:
1. the Secretariat outline (E/CN.4/AC.1/3)
2. the Drafting Committee's first-session text (E/CN.4/21)
3. the Geneva draft (E/600, Annex A)
4. the Drafting Committee's second-session text / the CHR draft sent to ECOSOC (E/800)
5. Third Committee numbering (A/C.3 records; the sub-committee A/C.3/SC.4)
6. the final text (A/RES/217(III))
