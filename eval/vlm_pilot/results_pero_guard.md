# PERO as a further engine of the name guard (20 Oct 2026)

Preregistered in docs/devlog.md (20 Oct). PERO read the 558 pages of the preview where the guard had left a name unverified
or replaced it by the session roster (one page failed once in PERO's layout and was read on the second pass). The guard ran
again with PERO among the engines, rules unchanged (eval/pero_guard_delta.py). Of 2,076 names on those pages, PERO changes
the resulting name for 36 (unverified > kept 15, roster replacement > kept 15, unverified > replaced 5, one replacement for
another 1). All 36 were judged on the scan (fewer than 40): eval/vlm_pilot/pero_guard_judged.json.

| verdict | n |
|---|---:|
| right | 21 |
| wrong: a damaged letter read the same by PERO and another engine, so the garble is kept over the right replacement (LOUIFI, WEITLAM, WHITIAM, MEETA, EDARE) | 5 |
| as typed: the original's own misspelling kept over the person's name (SORENSON 5, SOERENSEN 3, LCUTFI, RAMANDAN, DIAZ-CASANEUVA) | 10 |

Gate (at least 95% right, no wrong name the guard would otherwise have left alone): **not passed** (21 of 36 right counting
the as-typed spellings against, 31 of 36 counting them for; 5 wrong names the guard had right without PERO).

What it shows: PERO is independent of Tesseract (57% of the names no Tesseract reads), but not of the vision reader on
damaged type: a struck-out H or a faint L is ambiguous on the page itself, and two readers then agree on the same wrong
letter. Under the rule "read the same by two engines: keep", that agreement overrides the roster's right correction. PERO's
useful effect is the other way round: its reading of a known name replaced 5 unverified garbles, all rightly (KURAL, MEHTA
twice, MALIK, HOARE). A rule that lets PERO propose replacements but never confirm a name would have kept those 5 and
avoided the 15 losses; that is a new rule, to be preregistered and tested on other pages, not this gate's outcome. The 10
as-typed cases also raise a question for the guard itself: whether the text should keep the typist's misspelling while the
speaker field takes the person's usual name.
