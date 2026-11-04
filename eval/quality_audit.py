#!/usr/bin/env python3
"""The overall quality audit of the article tags: precision across all corpora and coverage.

Precision: the audit round's hand-judged tags (data/gold/article_tags.jsonl, strata ending
"/audit"), drawn from every kind of record in proportion to its tags; each kind's precision is
weighted by its share of the tags now in the database.

Coverage: untagged speeches judged for whether they are nonetheless about one specific
article (data/gold/coverage.jsonl): sample R1 from records with at least one tag, R2 from
records with none (both only speeches over 150 characters). Coverage = correct tags /
(correct tags + the untagged speeches about an article), over speeches over 150 characters.

Writes data/gold/audit.json (read by the About page).

Usage: python3 eval/quality_audit.py
"""
from __future__ import annotations

import csv
import json
import math
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "gold"
EARLY = {r["symbol"]: r["stage"] for r in csv.DictReader((ROOT / "data/concordance/udhr_early_meetings.csv").open())}
LONG = 150


def stratum(corpus: str, stage: str | None, symbol: str, body: str | None, session: str | None, art_instr: str | None) -> str:
    """The audit's kinds of record (the About page's groups, the Third Committee split at 1962)."""
    m = re.match(r"(\d+)", session or "")
    if corpus == "UDHR":
        st = EARLY.get(symbol)
        if st == "geneva_plenary":
            return "UDHR/geneva_plenary/early/audit"
        if art_instr and art_instr != "UDHR":
            return "Covenants/e600/early/audit"
        if symbol in EARLY:
            return "UDHR early (other)"
        return f"UDHR/{stage or 'none'}/audit"
    if body == "Commission on Human Rights":
        return "Covenants/CHR 1949-54/audit"
    if m and int(m.group(1)) in (17, 18, 21):
        return "Covenants/Third Committee 1962-66/audit"
    return "Covenants/e2573 1954-61/audit"


def group(st: str) -> str:
    return "UDHR early (other)" if st.startswith("UDHR/") and st.endswith("/early/audit") and "geneva_plenary" not in st else st


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p, d = k / n, 1 + z * z / n
    c, h = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def main() -> int:
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    rows = con.execute("SELECT s.symbol, s.final_article, s.article_instrument, length(s.text), d.instrument, d.stage, d.body, d.session "
                       "FROM segments s JOIN documents d USING(symbol) WHERE s.kind='speech'").fetchall()
    pop = defaultdict(int)
    tagged_long = 0
    tagged_docs = {r[0] for r in rows if r[1] is not None}
    untagged = {"R1": 0, "R2": 0}
    for sym, fin, ai, ln, corpus, stage, body, sess in rows:
        if fin is not None:
            pop[stratum(corpus, stage, sym, body, sess, ai)] += 1
            tagged_long += ln > LONG
        elif ln > LONG:
            untagged["R1" if sym in tagged_docs else "R2"] += 1
    judged = [json.loads(line) for line in (GOLD / "article_tags.jsonl").read_text().splitlines()]
    audit_round = max(r["round"] for r in judged if r["stratum"].endswith("/audit"))
    by = defaultdict(lambda: [0, 0])
    reports = [0, 0]  # the reports' paragraphs (from round 43): measured on their own, the weights are the speeches'
    for r in judged:
        if r["round"] == audit_round and r["stratum"].endswith("/audit"):
            tally = reports if "/reports/" in r["stratum"] else by[group(r["stratum"])]
            tally[0] += r["correct"]
            tally[1] += 1
    total = sum(pop.values())
    est = var = 0.0
    strata = {}
    for s, (k, n) in sorted(by.items(), key=lambda t: -pop[t[0]]):
        w, p = pop[s] / total, k / n
        est += w * p
        var += w * w * p * (1 - p) / n
        lo, hi = wilson(k, n)
        strata[s] = {"correct": k, "checked": n, "tags": pop[s]}
        print(f"{s:42} {k:3}/{n:3} = {100 * p:5.1f}% ({100 * lo:.0f}-{100 * hi:.0f})  {pop[s]} tags")
    half = 1.96 * math.sqrt(var)
    print(f"precision, weighted by tags: {100 * est:.1f}% (+/- {100 * half:.1f}); raw {sum(v[0] for v in by.values())}/{sum(v[1] for v in by.values())}")
    cov = [json.loads(line) for line in (GOLD / "coverage.jsonl").read_text().splitlines()]
    cov_round = max(c["round"] for c in cov)
    cov = [c for c in cov if c["round"] == cov_round]  # the latest measure's (it can be later than the precision round)
    missed = {}
    for sample in ("R1", "R2"):
        xs = [c for c in cov if c["sample"] == sample]
        k = sum(c["about_article"] for c in xs)
        missed[sample] = untagged[sample] * k / len(xs)
        print(f"{sample}: {k}/{len(xs)} untagged speeches about one article -> ~{missed[sample]:.0f} of {untagged[sample]}")
    good = tagged_long * est
    within, overall = good / (good + missed["R1"]), good / (good + missed["R1"] + missed["R2"])
    print(f"coverage: {100 * within:.0f}% within records with tags, {100 * overall:.0f}% overall")
    # the samples of untagged speeches are small (50 and 60) and vary more than the change a round measures:
    # pooled over the last three measures with the same design, the estimate is steadier
    allcov = [json.loads(line) for line in (GOLD / "coverage.jsonl").read_text().splitlines()]
    last3 = sorted({c["round"] for c in allcov if c["round"] >= 37})[-3:]
    pooled = {}
    for sample in ("R1", "R2"):
        xs = [c for c in allcov if c["round"] in last3 and c["sample"] == sample]
        pooled[sample] = untagged[sample] * sum(c["about_article"] for c in xs) / len(xs)
    p_within, p_overall = good / (good + pooled["R1"]), good / (good + pooled["R1"] + pooled["R2"])
    print(f"pooled over rounds {last3}: {100 * p_within:.0f}% within records with tags, {100 * p_overall:.0f}% overall")
    why = defaultdict(int)
    for c in cov:
        if c["about_article"]:
            why[c["untagged_because"].split(" (")[0]] += 1
    print("untagged but about an article, because:", dict(why))
    if reports[1]:
        lo, hi = wilson(*reports)
        print(f"report paragraphs: {reports[0]}/{reports[1]} ({100 * lo:.0f}-{100 * hi:.0f})")
    out = {"round": audit_round, "checked": max(r["checked"] for r in judged if r["round"] == audit_round),
           "precision": {"weighted": round(est, 3), "half_interval": round(half, 3),
                         "correct": sum(v[0] for v in by.values()), "checked": sum(v[1] for v in by.values()), "strata": strata},
           "coverage": {"within_tagged_records": round(within, 2), "overall": round(overall, 2), "judged": len(cov),
                        "missed_because": dict(why), "round": cov_round, "checked": max(c["checked"] for c in cov),
                        "pooled": {"rounds": last3, "within_tagged_records": round(p_within, 2), "overall": round(p_overall, 2)}}}
    if reports[1]:
        out["reports"] = {"correct": reports[0], "checked": reports[1]}
    earlier = json.loads((GOLD / "audit.json").read_text()) if (GOLD / "audit.json").exists() else {}
    same = (earlier.get("round"), earlier.get("coverage", {}).get("round", earlier.get("round"))) == (audit_round, cov_round)
    if earlier.get("round") and not same:
        out["previous"] = {k: earlier[k] for k in ("round", "checked", "precision", "coverage")}
    elif earlier.get("previous"):
        out["previous"] = earlier["previous"]
    (GOLD / "audit.json").write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
