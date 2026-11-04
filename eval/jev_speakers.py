#!/usr/bin/env python3
"""Experiment: can Jev identify the speaker of a speech from its garbled opening line?

For every speech in the given meetings, Jev chooses among the session's attendance list
(pooled as in pipeline/entities.py) from the speech's opening words. Jev is asked about
all speeches, not only those the rules leave unresolved, so its answers can be scored
against the silver reference (data/gold/speakers_<name>.jsonl) and its probabilities
checked for calibration.

Usage: python3 eval/jev_speakers.py chr3 E/CN.4/SR.60 E/CN.4/SR.61 ... [--batch 25]
Writes eval/jev_speakers_<name>.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "eval"))
import entities as E  # noqa: E402
import jev  # noqa: E402
from speaker_eval import CANONICAL, keyed_speeches  # noqa: E402

INSTRUCTIONS = (
    "The state holds the attendance list of a 1948 UN Commission on Human Rights meeting and the opening "
    "words of speech {key} from its summary record. The opening names the speaker as 'Mr. SURNAME "
    "(Delegation)', but the text is OCR of a typewritten copy, so names and delegations are often garbled "
    "(for example 'VHSOB (United Kingdom)' for WILSON, 'CEAUG- (Chim)' for CHANG of China). "
    "Which entry of the attendance list is the speaker of speech {key}?"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--engine", default="layer")
    ap.add_argument("--batch", type=int, default=25)
    args = ap.parse_args()

    # the attendance list exactly as the pipeline pools it for this session
    gaz = E.load_gazetteer()
    rosters = {s: E.meeting_roster(s, gaz) for s in args.symbols}
    pooled = E.session_roster(list(rosters.values()))
    results = {s: E.resolve(s, args.engine, rosters[s], pooled, gaz) for s in args.symbols}
    E.canonical_spellings([segs for segs, _ in results.values()], pooled)
    labels = sorted({f"{p['surname']} ({p['delegation']})" for p in pooled})
    options = {lab: "listed attendee" for lab in labels}

    gold = {(g["symbol"], g["page"], g["n"]): g
            for g in map(json.loads, (ROOT / "data" / "gold" / f"speakers_{args.name}.jsonl").read_text().splitlines())}
    rows = []
    for sym in args.symbols:
        speeches = list(keyed_speeches(sym, args.engine).items())
        for i in range(0, len(speeches), args.batch):
            chunk = speeches[i:i + args.batch]
            state = {"attendance_list": labels,
                     "speeches": {f"S{j}": s["text"][:160] for j, (_, s) in enumerate(chunk)}}
            qs = {f"S{j}": jev.choice(INSTRUCTIONS.format(key=f"S{j}"), options) for j in range(len(chunk))}
            answers = jev.ask(state, qs, task=f"speaker:{args.name}")
            for j, (key, s) in enumerate(chunk):
                a = answers.get(f"S{j}") or {}
                pick = a.get("choice")
                prob = (a.get("probabilities") or {}).get(pick)
                g = gold.get(key)
                ok = None
                if pick and g:
                    surname, _, deleg = pick.rpartition(" (")
                    surname = CANONICAL.get(surname, surname)
                    ok = surname.upper() == g["speaker"].upper() and deleg.rstrip(")") == g["delegation"]
                rule = s.get("speaker")
                rows.append({"key": list(key), "raw": s.get("speaker_raw"), "country_raw": s.get("country_raw"),
                             "rule": rule, "rule_method": s.get("speaker_method"), "jev": pick,
                             "prob": prob, "confidence": a.get("confidence"), "jev_correct": ok,
                             "gold": f"{g['speaker']} ({g['delegation']})" if g else None})
            print(f"  {sym} {i + 1}-{i + len(chunk)}: done", file=sys.stderr)

    scored = [r for r in rows if r["jev_correct"] is not None]
    right = sum(r["jev_correct"] for r in scored)
    print(f"\nJev: {right}/{len(scored)} correct ({right / max(len(scored), 1):.3f})", file=sys.stderr)
    for lo, hi in ((0.9, 1.01), (0.7, 0.9), (0.5, 0.7), (0.0, 0.5)):
        b = [r for r in scored if r["prob"] is not None and lo <= r["prob"] < hi]
        if b:
            print(f"  p in [{lo:.1f},{min(hi, 1):.1f}): {sum(r['jev_correct'] for r in b)}/{len(b)} correct", file=sys.stderr)
    unresolved = [r for r in scored if not r["rule"]]
    print(f"  on speeches the rules left unresolved: {sum(r['jev_correct'] for r in unresolved)}/{len(unresolved)}",
          file=sys.stderr)
    for r in scored:
        if not r["jev_correct"]:
            print(f"  MISS raw={r['raw']!r} ({r['country_raw']}): jev={r['jev']} p={r['prob']} gold={r['gold']}",
                  file=sys.stderr)
    usage = [json.loads(l) for l in jev.USAGE_LOG.read_text().splitlines() if f"speaker:{args.name}" in l]
    tin = sum(u["input_tokens"] or 0 for u in usage)
    tout = sum(u["output_tokens"] or 0 for u in usage)
    print(f"  tokens (all runs of this task): in {tin}, out {tout}, requests {len(usage)}", file=sys.stderr)
    out = ROOT / "eval" / f"jev_speakers_{args.name}.json"
    out.write_text(json.dumps({"options": len(labels), "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
