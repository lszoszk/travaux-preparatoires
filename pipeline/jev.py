"""Client for TypeSafe's Jev (System One): typed judgements with calibrated probabilities.

Request shape as the API validates it (probed 2026-09-23, model jev-1.13.0):
  {"model": "jev-latest", "state": {...},
   "questions": {"<key>": {"type": "choice", "instructions": "...", "criteria": {"option": "description", ...}},
                 "<key>": {"type": "noul",   "instructions": "...", "criteria": {"true": "...", "false": "..."}},
                 "<key>": {"type": "score",  "instructions": "...", "criteria": ["level 0", "level 1", ...]}}}
Answers: choice -> {"choice", "confidence", "probabilities"}; noul -> {"noul"}; score -> {"score", "confidence"}.

Jev only judges; it never writes text. In this project it is a fallback behind the
deterministic rules, and every answer is stored with its probability.

The key comes from TYPESAFE_API_KEY or travaux/.env. Retry and the placeholder-key guard
follow gc-rag-local-share/gc_rag_local.py. Token usage is appended to
data/jev_usage.jsonl so the cost per 1,000 items can be measured.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()

ROOT = Path(__file__).resolve().parents[1]
URL = "https://api.typesafe.ai/v1/systemone"
USAGE_LOG = ROOT / "data" / "jev_usage.jsonl"


def api_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("TYPESAFE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    # a pasted placeholder authenticates as nothing: every call would 401 silently
    if not key or "..." in key or len(key) < 16:
        raise RuntimeError("TYPESAFE_API_KEY missing or a placeholder (set it in travaux/.env)")
    return key


def choice(instructions: str, options: dict[str, str]) -> dict:
    return {"type": "choice", "instructions": instructions, "criteria": options}


def noul(instructions: str, true: str, false: str) -> dict:
    return {"type": "noul", "instructions": instructions, "criteria": {"true": true, "false": false}}


def score(instructions: str, levels: list[str]) -> dict:
    return {"type": "score", "instructions": instructions, "criteria": levels}


def ask(state: dict, questions: dict[str, dict], *, task: str, model: str = "jev-latest",
        timeout: float = 90.0) -> dict[str, dict]:
    """One request: all questions against one shared state. Returns answers by key."""
    body = json.dumps({"model": model, "state": state, "questions": questions}).encode("utf-8")
    key = api_key()
    last = None
    for attempt in range(4):
        req = urllib.request.Request(URL, data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            usage = data.get("usage") or {}
            USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
            with USAGE_LOG.open("a") as f:
                f.write(json.dumps({"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                    "task": task, "model": data.get("model"), "questions": len(questions),
                                    "input_tokens": usage.get("input_tokens"),
                                    "output_tokens": usage.get("output_tokens")}) + "\n")
            return data.get("answers") or {}
        except urllib.error.HTTPError as exc:
            last = f"http_{exc.code}: {exc.read().decode()[:300]}"
            if exc.code in (429, 529, 500, 502, 503) and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(last) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last = str(exc)
            if attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
    raise RuntimeError(f"Jev request failed: {last}")
