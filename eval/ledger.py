#!/usr/bin/env python3
"""The ledger: how much AI work went into the database, from the Claude Code transcripts of the project.

Reads the session transcripts (~/.claude/projects/<project>/*.jsonl, with their subagents and workflow agents) and
writes only totals to eval/ledger.json: prompts, model turns, agents and workflows, tokens by model and by kind,
tokens by kind of work, and a day-by-day series. No text of the transcripts leaves them.

Counting rules:
- A model turn is one API response (deduplicated by message id: a response written as several lines counts once).
- Tokens: output (generated, thinking included), input, cache writes and cache reads, kept apart. Cache reads are the
  same context read again at each turn: they dwarf the rest and are shown with that caveat.
- A prompt is a message the person typed (origin "human"), not a tool result, a reminder or a task notification.
- Kind of work: the main session is "direction and engineering"; each workflow agent is classed by its workflow's name
  and its own label (reading documents by hand, quality checks, research checks, sources and translation, ...). The
  classes are keyword rules, so the split is an approximation, and says so.
- Work without the models: OCR pages, PDFs fetched, Jev (TypeSafe) answers, commits, from the project's own files;
  Jev's calls, questions and tokens from its usage log (data/jev_usage.jsonl).
- Active hours: the hours (UTC) with at least one model turn, any agent's, and the main session's alone.

Usage: python3 eval/ledger.py [--project-dir ~/.claude/projects/-Users-lszoszk-Desktop-AI-travaux]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "ledger.json"
DEFAULT_PROJECT = Path.home() / ".claude" / "projects" / "-Users-lszoszk-Desktop-AI-travaux"
DEFAULT_AGY = Path.home() / ".gemini" / "antigravity" / "brain" / "5fc80764-bcc9-4f12-94dc-53b91657baf4"

# kind of work, from a workflow's name and an agent's label (first match wins)
KINDS = [
    ("research checks on articles", r"research|ground truth|researcher"),
    ("sources and translation", r"missing|find-missing|translat|harvest|uva"),
    ("quality checks (blind judges, audits)", r"judge|audit|check|verif|refute|round|coverage-round|review|critic|split"),
    ("reading reports and texts by hand", r"rows|annex|anchor|report|section|concordance|meeting-list|assign|texts?\b|maps|foi|a6546|a777|e1681|chr-|covenant|draft|stage|reconcile|read-"),
    ("tagging and extraction", r"tag|sponsor|speaker|decision|vote|amend|symbol|ref"),
]
MAIN = "direction and engineering (main session)"
OTHER = "other agents"


def kind_of(text: str) -> str:
    t = text.lower()
    for name, pat in KINDS:
        if re.search(pat, t):
            return name
    return OTHER


def scan(path: Path, kind: str, acc: dict, seen: dict) -> None:
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = j.get("type")
        day = (j.get("timestamp") or "")[:10]
        if t == "user" and kind == MAIN and (j.get("origin") or {}).get("kind") == "human" and not j.get("isMeta"):
            content = (j.get("message") or {}).get("content")
            text = content if isinstance(content, str) else " ".join(
                b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")
            if text.strip() and not text.lstrip().startswith(("<task-notification", "<local-command", "<command-", "<system-reminder")):
                acc["prompts"] += 1
                acc["days"][day]["prompts"] += 1
        if t != "assistant":
            continue
        m = j.get("message") or {}
        u = m.get("usage")
        mid = m.get("id") or j.get("requestId")
        if not u or not mid or m.get("model") in (None, "<synthetic>"):
            continue
        # a response is written as several lines while it streams, each with the usage so far: keep the largest
        tok = {"output": u.get("output_tokens") or 0, "input": u.get("input_tokens") or 0,
               "cache_write": u.get("cache_creation_input_tokens") or 0, "cache_read": u.get("cache_read_input_tokens") or 0}
        prev = seen.get(mid)
        if prev:
            prev["tok"] = {k: max(v, prev["tok"][k]) for k, v in tok.items()}
        else:
            seen[mid] = {"model": m["model"], "kind": kind, "day": day, "hour": (j.get("timestamp") or "")[:13], "tok": tok}


def scan_agy(path: Path, kind: str, acc: dict, seen: dict, model: str = "gemini-4-argon") -> tuple[set[str], int]:
    """Scan an Antigravity transcript.jsonl file; returns (subagent_conversation_ids, multi_agent_workflow_steps)."""
    if not path.exists():
        return set(), 0
    cid = path.parents[2].name
    sub_ids: set[str] = set()
    wf_steps = 0
    for line in path.open(encoding="utf-8", errors="replace"):
        for m in re.findall(r"sender=([0-9a-f-]{36})(?!/task-)", line):
            if m != cid:
                sub_ids.add(m)
        if '"default_api:invoke_subagent"' in line:
            wf_steps += 1
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = j.get("type")
        ts = j.get("created_at") or ""
        day, hour = ts[:10], ts[:13]
        if t == "USER_INPUT" and kind == MAIN and j.get("source") == "USER_EXPLICIT":
            if (j.get("content") or "").strip():
                acc["prompts"] += 1
                acc["days"][day]["prompts"] += 1
        if t != "PLANNER_RESPONSE":
            continue
        out_tok = j.get("output_tokens") or 0
        in_tok = j.get("input_tokens") or 0
        cache_read = j.get("cache_read_tokens") or 0
        if not (out_tok or in_tok or cache_read):
            continue
        mid = f"agy:{cid}:{j.get('step_index')}"
        seen[mid] = {
            "model": model,
            "kind": kind,
            "day": day,
            "hour": hour,
            "tok": {"output": out_tok, "input": max(0, in_tok - cache_read), "cache_write": 0, "cache_read": cache_read},
        }
    return sub_ids, wf_steps


def aggregate(acc: dict, seen: dict) -> None:
    for r in seen.values():
        model, kind, day, tok = r["model"], r["kind"], r["day"], r["tok"]
        acc["turns"] += 1
        acc["by_model"][model]["turns"] += 1
        for k, v in tok.items():
            acc["by_model"][model][k] += v
            acc["by_kind"][kind][k] += v
            acc["days"][day][k] += v
        acc["by_kind"][kind]["turns"] += 1
        acc["days"][day]["turns"] += 1
        acc["days"][day]["models"][model] += tok["output"]
        if r["hour"]:  # an hour (UTC) with at least one model turn; the main session's apart from the agents'
            acc["hours"].add(r["hour"])
            if kind == MAIN:
                acc["main_hours"].add(r["hour"])
        if day:
            acc["first"] = min(acc["first"] or day, day)
            acc["last"] = max(acc["last"] or day, day)


def workflow_names(project: Path) -> dict[str, str]:
    """Run id -> workflow name and description: from the saved scripts (name-wf_xxxx.js), and from the Workflow tool's
    answers in the session transcripts ("Summary: ...", "Run ID: wf_...") for the runs of scripts saved without the id."""
    names: dict[str, str] = {}
    for p in project.glob("*/workflows/scripts/*.js"):
        m = re.match(r"(.+)-(wf_[0-9a-f-]+)\.js$", p.name)
        if m:
            names[m.group(2)] = m.group(1)
    for s in project.glob("*.jsonl"):
        for line in s.open(encoding="utf-8", errors="replace"):
            if "Run ID: wf_" not in line:
                continue
            for text in re.findall(r"Summary: ([^\\]+?)\\n.*?Run ID: (wf_[0-9a-f-]+)", line):
                names[text[1]] = f"{names.get(text[1], '')} {text[0]}".strip()
            for m in re.finditer(r"scripts/([a-z0-9-]+?)(?:-wf_[0-9a-f-]+)?\.js.{0,400}?Run ID: (wf_[0-9a-f-]+)", line):
                names[m.group(2)] = f"{m.group(1)} {names.get(m.group(2), '')}".strip()
    return names


def local_work() -> dict:
    out = {}
    pages = pdfs = 0
    for p in (ROOT / "data" / "manifest").glob("harvest_*.json"):
        for e in json.loads(p.read_text()).values():
            if e.get("status") == "ok":
                pdfs += 1
                pages += e.get("pages") or 0
    out["pdfs"] = pdfs
    out["pages"] = pages
    jev = 0
    for p in (ROOT / "data" / "cache").glob("jev_*.json"):
        try:
            jev += len(json.loads(p.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    out["jev_answers"] = jev
    # Jev's own usage log (pipeline/jev.py): calls, questions and tokens, by task ("speaker:chr3" -> "speaker")
    usage = ROOT / "data" / "jev_usage.jsonl"
    if usage.exists():
        tasks: dict = defaultdict(Counter)
        for line in usage.open():
            try:
                u = json.loads(line)
            except json.JSONDecodeError:
                continue
            task = (u.get("task") or "other").split(":")[0]
            if task.startswith(("echr", "unhrdb")):  # other projects' clients write to the same log
                continue
            t = tasks[task]
            t["calls"] += 1
            t["questions"] += u.get("questions") or 0
            t["input"] += u.get("input_tokens") or 0
            t["output"] += u.get("output_tokens") or 0
        total = sum(tasks.values(), Counter())
        out["jev"] = {**dict(total), "by_task": {k: dict(v) for k, v in sorted(tasks.items(), key=lambda x: -x[1]["questions"])}}
    try:
        out["commits"] = int(subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=ROOT, capture_output=True,
                                            text=True, check=True).stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        out["commits"] = None
    out["tests"] = sum(len(re.findall(r"^def test_", p.read_text(), re.M)) for p in (ROOT / "tests").glob("test_*.py"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT)
    ap.add_argument("--agy-dir", type=Path, default=DEFAULT_AGY)
    args = ap.parse_args()
    project = args.project_dir
    zero = lambda: Counter()  # noqa: E731
    acc = {"prompts": 0, "turns": 0, "first": None, "last": None, "hours": set(), "main_hours": set(),
           "by_model": defaultdict(zero), "by_kind": defaultdict(zero),
           "days": defaultdict(lambda: {"prompts": 0, "turns": 0, "output": 0, "input": 0, "cache_write": 0, "cache_read": 0,
                                        "models": Counter()})}
    seen: dict = {}
    sessions = sorted(project.glob("*.jsonl"))
    for s in sessions:
        scan(s, MAIN, acc, seen)
    names = workflow_names(project)
    agents = workflows = 0
    for sdir in project.glob("*/subagents"):
        for p in sdir.glob("agent-*.jsonl"):  # agents started by the main session
            meta = p.with_suffix(".meta.json")
            label = json.loads(meta.read_text()).get("description", "") if meta.exists() else ""
            scan(p, kind_of(label) if label else OTHER, acc, seen)
            agents += 1
        for wf in sorted((sdir / "workflows").glob("wf_*")):
            workflows += 1
            wname = names.get(wf.name, "")
            for p in wf.glob("agent-*.jsonl"):
                meta = p.with_suffix(".meta.json")
                label = json.loads(meta.read_text()).get("description", "") if meta.exists() else ""
                k = kind_of(wname) if wname and kind_of(wname) != OTHER else kind_of(label)
                scan(p, k, acc, seen)
                agents += 1
    n_sessions = len(sessions)
    agy_tr = args.agy_dir / ".system_generated" / "logs" / "transcript.jsonl"
    if agy_tr.exists():
        n_sessions += 1
        sub_ids, agy_wfs = scan_agy(agy_tr, MAIN, acc, seen)
        workflows += agy_wfs
        for sid in sorted(sub_ids):
            sub_tr = args.agy_dir.parent / sid / ".system_generated" / "logs" / "transcript.jsonl"
            try:
                if sub_tr.exists():
                    scan_agy(sub_tr, "quality checks (blind judges, audits)", acc, seen)
                    agents += 1
            except OSError:
                pass
    aggregate(acc, seen)
    total = {k: sum(m[k] for m in acc["by_model"].values()) for k in ("output", "input", "cache_write", "cache_read")}
    result = {
        "generated": dt.date.today().isoformat(),
        "period": {"first": acc["first"], "last": acc["last"], "active_days": sum(1 for d in acc["days"].values() if d["turns"]),
                   "active_hours": len(acc["hours"]), "main_session_hours": len(acc["main_hours"])},
        "sessions": n_sessions, "prompts": acc["prompts"], "model_turns": acc["turns"],
        "agents": agents, "workflows": workflows,
        "tokens": {**total, "processed": sum(total.values())},
        "by_model": {m: dict(v) for m, v in sorted(acc["by_model"].items(), key=lambda x: -x[1]["output"])},
        "by_kind": {k: dict(v) for k, v in sorted(acc["by_kind"].items(), key=lambda x: -x[1]["output"])},
        "days": {d: {**{k: v for k, v in x.items() if k != "models"}, "output_by_model": dict(x["models"])}
                 for d, x in sorted(acc["days"].items()) if d},
        "local": local_work(),
        "notes": ["Tokens are counted from the API usage the transcripts record, one count per response.",
                  "Cache reads are the same context read again at every turn; 'output' is what the models generated.",
                  "The split by kind of work classes each agent by keywords in its workflow's name and its label: an approximation.",
                  "Human work (decisions, reading, checking) is not in these numbers."],
    }
    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")
    t = result["tokens"]
    print(f"{result['period']['first']}..{result['period']['last']} ({result['period']['active_days']} days): "
          f"{result['prompts']} prompts, {result['model_turns']} model turns, {agents} agents in {workflows} workflows; "
          f"output {t['output'] / 1e6:.1f}M, processed {t['processed'] / 1e9:.2f}B tokens -> {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
