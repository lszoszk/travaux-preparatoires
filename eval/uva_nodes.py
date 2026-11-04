#!/usr/bin/env python3
"""The UN symbol and file link of each UVA item (eval/uva_list.py), read from its node page, one request every 6 s.

Adds "symbol" and "file" to data/private/uva/items.json; resumable.
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from uva_list import BASE, OUT, fetch  # noqa: E402


def main() -> int:
    d = json.loads(OUT.read_text())
    todo = [k for k, v in d.items() if k != "_done" and "symbol" not in v]
    for i, node in enumerate(todo, 1):
        time.sleep(6)
        try:
            s = fetch(BASE + node)
        except Exception as exc:  # noqa: BLE001
            print(f"  !! {node}: {exc}", file=sys.stderr)
            continue
        t = " ".join(html.unescape(re.sub(r"<!--.*?-->|<[^>]+>", " ", s, flags=re.S)).split())
        m = re.search(r"UN Document Symbol (.+?) (?:Session|UN Human Rights Treaties|Document Type|Organ|Convention)", t)
        d[node]["symbol"] = m.group(1).strip() if m else None
        f = re.findall(r'https?://uvallsc\.s3\.amazonaws\.com/[^"\s]+\.pdf', s)
        d[node]["file"] = f[0] if f else None
        if i % 20 == 0 or i == len(todo):
            OUT.write_text(json.dumps(d, indent=1, ensure_ascii=False))
            print(f"  {i}/{len(todo)}", file=sys.stderr)
    OUT.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
