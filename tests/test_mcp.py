"""The local MCP server (mcp/travaux_mcp.py) over stdio: handshake, tools, answers."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def talk(*messages: dict) -> dict:
    lines = "\n".join(json.dumps(m) for m in messages) + "\n"
    out = subprocess.run([sys.executable, str(ROOT / "mcp" / "travaux_mcp.py")], input=lines, capture_output=True,
                         text=True, timeout=120, check=True).stdout
    return {m["id"]: m for m in map(json.loads, out.splitlines())}


def test_mcp_server():
    got = talk({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
               {"jsonrpc": "2.0", "method": "notifications/initialized"},
               {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
               {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "search_travaux", "arguments": {
                   "query": "\"first sentence of article 16\"", "instrument": "UDHR"}}},
               {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "article_history_travaux",
                                                                             "arguments": {"instrument": "ICCPR", "article": 18}}},
               {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "nope"}})
    assert got[1]["result"]["protocolVersion"] == "2025-06-18"
    assert {t["name"] for t in got[2]["result"]["tools"]} == {"search_travaux", "lookup_travaux", "article_history_travaux",
                                                             "delegation_travaux", "decisions_travaux", "amendments_travaux"}
    assert "A/C.3/SR.127, pp. 2-3 (Baroody, Saudi Arabia)" in got[3]["result"]["content"][0]["text"]
    assert "have or to adopt" in got[4]["result"]["content"][0]["text"]
    assert got[5]["error"]["code"] == -32602
    assert len(got) == 5  # the notification got no answer
