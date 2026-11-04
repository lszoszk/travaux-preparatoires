#!/usr/bin/env python3
"""On the AMU VM, once, at the opening: take the testers' password off the Travaux DB, and keep scrapers off its data.

  ssh -t amuvmuser@150.254.115.204 'sudo python3 /home/amuvmuser/travaux/open_vm.py'
  ssh -t amuvmuser@150.254.115.204 'sudo python3 /home/amuvmuser/travaux/open_vm.py --undo'

People read the database in the site; programs and AI agents use the MCP server (/travaux-api/mcp), which this leaves open.
What it does, and nothing else (deploy/nginx_patch_vm.py wrote the locations it edits):
 1. copies /etc/nginx/sites-enabled/default to /etc/nginx/_backups/default.bak-open-<time>;
 2. takes the password (auth_basic) off /travaux/ and /travaux-api/; the site may now be indexed, the API still may not;
 3. in /travaux-api/: the data (/travaux-api/api/...) is refused (403, with a pointer to the MCP server) to cloud data centres
    (the networks of ~/traffic-stats/nginx-cloud-nets.inc, as the paid Ask questions of UNHRDB already are) and to known AI
    crawlers and scripting clients by their User-Agent; Ask questions are capped at 30 a minute in all, records and exports at
    20 a minute per address (the 10 a second per address of every request stays);
 4. answers /robots.txt for the whole host: /travaux/ allowed, /travaux-api/ disallowed (no other app is named, so nothing
    changes for them: a missing robots.txt allowed everything);
 5. writes /etc/nginx/conf.d/travaux_guard.conf (the maps and the two limit zones);
 6. runs `nginx -t`: if it fails, every file goes back as it was; if it passes, reloads nginx.
--undo puts back the newest backup and deletes travaux_guard.conf (the password file /etc/nginx/travaux.htpasswd is left in place).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SITE = Path("/etc/nginx/sites-enabled/default")
BACKUPS = Path("/etc/nginx/_backups")
GUARD = Path("/etc/nginx/conf.d/travaux_guard.conf")
ASK_GUARD = Path("/etc/nginx/conf.d/ask_guard.conf")   # defines $cloud_net (~/traffic-stats/install_ask_guard.sh)
NETS = Path("/home/amuvmuser/traffic-stats/nginx-cloud-nets.inc")

AUTH = """    auth_basic "Travaux DB, closed preview";
    auth_basic_user_file /etc/nginx/travaux.htpasswd;
    add_header X-Robots-Tag "noindex, nofollow" always;
"""
API_HEAD = """  location /travaux-api/ {
"""
API_GUARD = """  location /travaux-api/ {
    # people read the data in the site; programs and AI agents use the MCP server (deploy/open_vm.py, conf.d/travaux_guard.conf)
    if ($travaux_block) { return 403 '{"error": "The Travaux data is read in the site. Programs and AI assistants: please use the MCP server, see https://150.254.115.204/travaux/#view=about&part=mcp"}'; }
    limit_req zone=travaux_ask burst=30 nodelay;
    limit_req zone=travaux_docs burst=20 nodelay;
    limit_req_status 429;
    add_header X-Robots-Tag "noindex, nofollow" always;
"""
SITE_HEAD = """  location /travaux/ {
"""
ROBOTS = """  location = /robots.txt { default_type text/plain; return 200 "User-agent: *\\nAllow: /travaux/\\nDisallow: /travaux-api/\\n"; }
  location = / { return 302 /travaux/; }"""

GUARD_CONF = """# The Travaux DB's data kept for people and the MCP server (deploy/open_vm.py). $cloud_net comes from {geo_from}.
{geo}map $http_user_agent $travaux_bot {{
  default 0;
  "~*(GPTBot|ChatGPT-User|OAI-SearchBot|CCBot|ClaudeBot|Claude-Web|anthropic-ai|Bytespider|PerplexityBot|Amazonbot|Google-Extended|Applebot-Extended|meta-externalagent|FacebookBot|Diffbot|ImagesiftBot|cohere-ai|YouBot|Timpibot|omgili|DataForSeoBot|PetalBot|SemrushBot|AhrefsBot|MJ12bot|python-requests|python-urllib|aiohttp|httpx|Go-http-client|curl/|Wget|Scrapy|node-fetch|axios|okhttp|libwww-perl|Java/|HeadlessChrome|PhantomJS)" 1;
}}
# the data endpoints (not /travaux-api/mcp, /travaux-api/health or the audit panel): refused to clouds and to the agents above
map "$cloud_net$travaux_bot:$request_uri" $travaux_block {{
  default 0;
  "~^(10|01|11):/travaux-api/api/" 1;
}}
map $request_uri $travaux_ask_key {{ default ""; "~^/travaux-api/api/ask(\\?|$)" "ask"; }}
map $request_uri $travaux_docs_key {{ default ""; "~^/travaux-api/api/(record|export)" $binary_remote_addr; }}
# ($request_uri, not $uri: the location rewrites $uri before the limits are counted)
limit_req_zone $travaux_ask_key zone=travaux_ask:1m rate=30r/m;
limit_req_zone $travaux_docs_key zone=travaux_docs:10m rate=20r/m;
"""


def patch(text: str) -> str:
    if "travaux_block" in text:
        raise ValueError("the guard is in the file already; nothing changed")
    n = text.count(AUTH)
    if n != 2:
        raise ValueError(f"the password block found {n} times, expected twice (/travaux-api/ and /travaux/); nothing changed")
    for head in (API_HEAD, SITE_HEAD, "  location = / { return 302 /travaux/; }"):
        if text.count(head) != 1:
            raise ValueError(f"{head.strip()!r} not found exactly once; nothing changed")
    text = text.replace(AUTH, "")
    text = text.replace(API_HEAD, API_GUARD, 1)
    if "location = /robots.txt" not in text:
        text = text.replace("  location = / { return 302 /travaux/; }", ROBOTS, 1)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--undo", action="store_true")
    args = ap.parse_args()
    if os.geteuid() != 0:
        sys.exit("run it with sudo")
    if args.undo:
        backups = sorted(BACKUPS.glob("default.bak-open-*"))
        if not backups:
            sys.exit("no backup to put back")
        shutil.copy2(backups[-1], SITE)
        GUARD.unlink(missing_ok=True)
        subprocess.run(["nginx", "-t"], check=True)
        subprocess.run(["systemctl", "reload", "nginx"], check=True)
        print(f"put back {backups[-1]}, removed {GUARD}; the password is on again")
        return 0
    old = SITE.read_text()
    try:
        new = patch(old)
    except ValueError as e:
        sys.exit(str(e))
    has_geo = ASK_GUARD.exists() and "geo $cloud_net" in ASK_GUARD.read_text()
    if not has_geo and not NETS.exists():
        sys.exit(f"neither {ASK_GUARD} (geo $cloud_net) nor {NETS} found; nothing changed")
    geo = "" if has_geo else f"geo $cloud_net {{ default 0; include {NETS}; }}\n"
    BACKUPS.mkdir(exist_ok=True)
    backup = BACKUPS / f"default.bak-open-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(SITE, backup)
    GUARD.write_text(GUARD_CONF.format(geo=geo, geo_from=ASK_GUARD if has_geo else "the geo line below"))
    SITE.write_text(new)
    test = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    if test.returncode != 0:
        shutil.copy2(backup, SITE)
        GUARD.unlink()
        sys.exit("nginx -t failed, every file is back as it was:\n" + test.stderr)
    subprocess.run(["systemctl", "reload", "nginx"], check=True)
    print("done: the password is off; the data is refused to clouds and bots, which are pointed to the MCP server; nginx reloaded")
    print(f"backup: {backup}\nto undo: sudo python3 {Path(__file__).resolve()} --undo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
