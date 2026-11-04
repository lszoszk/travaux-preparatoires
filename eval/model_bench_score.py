#!/usr/bin/env python3
"""Score a model's answers to the fixed benchmark (eval/model_bench_build.py) and add the run to eval/model_bench/results.json.

  python3 eval/model_bench_score.py answers.json --label "2026-09-30 workflow run"

answers.json: {model: {task: [answer, ...]}}, as eval/model_bench/run.js returns it. Scores, per task:
  speaker  surname right, delegation right (accents, case and "Republic of" style aliases ignored)
  vote     outcome right; all three figures right (missing counts as wrong)
  sponsor  the set of delegations equal to the gold; and the share of gold delegations found (recall)
  tag      accuracy against the checked label (chance is 50%: the items are balanced)
A model that gives no answer to an item is scored wrong on it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import unicodedata
from pathlib import Path

BENCH = Path(__file__).resolve().parent / "model_bench"
ALIASES = {"ussr": "union of soviet socialist republics", "soviet union": "union of soviet socialist republics",
           "united states": "united states of america", "usa": "united states of america", "us": "united states of america",
           "uk": "united kingdom", "united kingdom of great britain and northern ireland": "united kingdom",
           "great britain": "united kingdom", "byelorussian ssr": "byelorussian soviet socialist republic",
           "china (republic of)": "china", "republic of china": "china", "the philippines": "philippines",
           "philippine republic": "philippines", "uar": "united arab republic"}


def norm(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9() ]+", " ", s)
    s = re.sub(r"^(the|mr|mrs|miss|sir|lady|dr|general|prof|professor|madame|m)\b\.? ", "", " ".join(s.split()))
    return ALIASES.get(s, s)


def score(answers: dict, items: list[dict], gold: dict) -> dict:
    by_task: dict[str, list[dict]] = {}
    for a in answers.values() if isinstance(answers, dict) else []:
        pass
    res = {}
    for task, rows in answers.items():
        got = {r["id"]: r for r in rows}
        ids = [i["id"] for i in items if i["task"] == task]
        n = len(ids)
        if task == "speaker":
            sp = sum(1 for i in ids if i in got and norm(got[i]["speaker"]) == norm(gold[i]["speaker"]))
            de = sum(1 for i in ids if i in got and norm(got[i]["delegation"]) == norm(gold[i]["delegation"]))
            res[task] = {"n": n, "speaker": round(sp / n, 3), "delegation": round(de / n, 3)}
        elif task == "vote":
            oc = sum(1 for i in ids if i in got and got[i]["outcome"] == gold[i]["outcome"])
            fg = sum(1 for i in ids if i in got and (got[i]["yes"], got[i]["no"], got[i]["abstentions"]) ==
                     (gold[i]["yes"], gold[i]["no"], gold[i]["abstentions"]))
            res[task] = {"n": n, "outcome": round(oc / n, 3), "figures": round(fg / n, 3)}
        elif task == "sponsor":
            eq = rec = 0.0
            for i in ids:
                g = {norm(x) for x in gold[i]["proposers"]}
                a = {norm(x) for x in got[i]["proposers"]} if i in got else set()
                eq += a == g
                rec += len(a & g) / len(g) if g else 1
            res[task] = {"n": n, "exact": round(eq / n, 3), "recall": round(rec / n, 3)}
        elif task == "tag":
            ok = sum(1 for i in ids if i in got and bool(got[i]["about"]) == gold[i]["about"])
            res[task] = {"n": n, "accuracy": round(ok / n, 3)}
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("answers", type=Path)
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    items = json.loads((BENCH / "items.json").read_text())
    gold = json.loads((BENCH / "gold.json").read_text())
    answers = json.loads(args.answers.read_text())
    out_path = BENCH / "results.json"
    runs = json.loads(out_path.read_text()) if out_path.exists() else []
    for model, tasks in answers.items():
        runs.append({"model": model, "date": dt.date.today().isoformat(), "label": args.label, "scores": score(tasks, items, gold)})
        print(model, json.dumps(runs[-1]["scores"]))
    out_path.write_text(json.dumps(runs, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
