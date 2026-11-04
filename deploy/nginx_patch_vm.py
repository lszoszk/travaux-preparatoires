#!/usr/bin/env python3
"""On the AMU VM, once: put the Travaux DB where Mattermost was in nginx.

  ssh -t amuvmuser@150.254.115.204 'sudo python3 /home/amuvmuser/travaux/nginx_patch_vm.py'          # closed preview (a password)
  ssh -t amuvmuser@150.254.115.204 'sudo python3 /home/amuvmuser/travaux/nginx_patch_vm.py --open'   # open to anyone

What it does, and nothing else:
 1. copies /etc/nginx/sites-enabled/default to /etc/nginx/_backups/default.bak-travaux-<time>;
 2. removes the `upstream mattermost` block and Mattermost's two locations (its websocket and `location /`); it refuses to run if
    any of the three is not found exactly once, i.e. if the file is no longer as it was on 4 October 2026;
 3. puts in their place: `/` -> 302 to /travaux/, any other unknown path -> 404 (both went to Mattermost), `/travaux-api/` (the API)
    and `/travaux/` (the site), both proxied to the travaux-api container (127.0.0.1:TRAVAUX_PORT from the bundle's .env);
 4. writes /etc/nginx/conf.d/travaux.conf (the upstream, the cache zone, the rate-limit zone);
 5. unless --open: asks twice for the testers' password and writes /etc/nginx/travaux.htpasswd (user "testers"; the hash only);
    both locations then ask for it and tell search engines not to index;
 6. runs `nginx -t`: if it fails, puts every file back as it was; if it passes, reloads nginx.
To undo later: copy the backup back, delete conf.d/travaux.conf, `nginx -t`, reload (the script prints the commands).
"""
from __future__ import annotations

import argparse
import getpass
import grp
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SITE = Path("/etc/nginx/sites-enabled/default")
BACKUPS = Path("/etc/nginx/_backups")
CONF = Path("/etc/nginx/conf.d/travaux.conf")
HTPASSWD = Path("/etc/nginx/travaux.htpasswd")
ENV = Path("/home/amuvmuser/travaux/.env")

UPSTREAM_RE = re.compile(r"^upstream mattermost \{[^{}]*\}\n\n?", re.M)
WEBSOCKET_RE = re.compile(r"\n[ \t]*# ---- Mattermost websocket ----\n[ \t]*location ~ /api/v\[0-9\]\+/\(users/\)\?websocket\$ \{[^{}]*\}\n")
DEFAULT_RE = re.compile(r"\n[ \t]*# ---- Mattermost default ----\n[ \t]*location / \{[^{}]*proxy_pass http://mattermost;[^{}]*\}\n")

AUTH = """    auth_basic "Travaux DB, closed preview";
    auth_basic_user_file /etc/nginx/travaux.htpasswd;
    add_header X-Robots-Tag "noindex, nofollow" always;
"""

LOCATIONS = """
  # ---- Travaux DB (in place of Mattermost, removed on 4 Oct 2026) ----
  # the host's root opens the Travaux DB; any other unknown path is a 404 (both went to Mattermost)
  location = / { return 302 /travaux/; }
  location / { return 404; }

  location /travaux-api/ {
{auth}    rewrite ^/travaux-api/(.*)$ /$1 break;
    proxy_pass http://travaux_api;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    limit_req zone=travaux_rl burst=30 nodelay;
    proxy_cache travaux;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$scheme$request_uri$http_origin";
    proxy_cache_use_stale error timeout updating;
    add_header X-Cache-Status $upstream_cache_status;
    gzip on;
    gzip_types application/json text/csv;
    gzip_min_length 1024;
    proxy_read_timeout 30s;
  }

  location = /travaux { return 301 /travaux/; }
  location /travaux/ {
{auth}    proxy_pass http://travaux_api/;
    proxy_set_header Host $host;
    limit_req zone=travaux_rl burst=30 nodelay;
    proxy_hide_header Cache-Control;
    add_header Cache-Control "public, max-age=300";
    gzip on;
    gzip_types text/css application/javascript image/svg+xml;
  }
"""

HTTP_PART = """# The Travaux DB (deploy/nginx_patch_vm.py): the container on localhost, a 100 MB cache, 10 requests a second per address
upstream travaux_api {{
  server 127.0.0.1:{port};
}}
proxy_cache_path /var/cache/nginx/travaux levels=1:2 keys_zone=travaux:10m max_size=100m inactive=24h use_temp_path=off;
limit_req_zone $binary_remote_addr zone=travaux_rl:10m rate=10r/s;
"""


def patch(text: str, closed: bool) -> str:
    """The server file with Mattermost's blocks replaced; ValueError if any of them is not there exactly once."""
    for name, rx in (("upstream mattermost", UPSTREAM_RE), ("Mattermost websocket", WEBSOCKET_RE), ("Mattermost default", DEFAULT_RE)):
        n = len(rx.findall(text))
        if n != 1:
            raise ValueError(f"{name}: found {n} times, expected once; the file is not as it was, nothing changed")
    if "location /travaux-api/" in text:
        raise ValueError("the file already has the Travaux locations; nothing changed")
    text = UPSTREAM_RE.sub("", text, count=1)
    text = WEBSOCKET_RE.sub("\n", text, count=1)
    text = DEFAULT_RE.sub(LOCATIONS.replace("{auth}", AUTH if closed else ""), text, count=1)
    if re.search(r"http://mattermost|upstream mattermost", text):
        raise ValueError("a reference to Mattermost is left after the edit; nothing changed")
    return text


def port() -> str:
    for line in ENV.read_text().splitlines() if ENV.exists() else []:
        if line.startswith("TRAVAUX_PORT="):
            return line.split("=", 1)[1].strip()
    return "8006"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", action="store_true", help="no password (only once the UN Library has approved publication)")
    args = ap.parse_args()
    if os.geteuid() != 0:
        sys.exit("run it with sudo")
    if CONF.exists():
        sys.exit(f"{CONF} exists already: the patch was applied; nothing changed")
    old = SITE.read_text()
    try:
        new = patch(old, closed=not args.open)
    except ValueError as e:
        sys.exit(str(e))
    made_password = False
    if not args.open and not HTPASSWD.exists():
        pw = getpass.getpass("Password for the testers (user 'testers'): ")
        if len(pw) < 10 or pw != getpass.getpass("Again: "):
            sys.exit("the two entries differ, or the password is shorter than 10 characters; nothing changed")
        hashed = subprocess.run(["openssl", "passwd", "-apr1", "-stdin"], input=pw + "\n", capture_output=True, text=True, check=True).stdout.strip()
        HTPASSWD.write_text(f"testers:{hashed}\n")
        os.chown(HTPASSWD, 0, grp.getgrnam("www-data").gr_gid)
        os.chmod(HTPASSWD, 0o640)
        made_password = True
    BACKUPS.mkdir(exist_ok=True)
    backup = BACKUPS / f"default.bak-travaux-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(SITE, backup)
    Path("/var/cache/nginx").mkdir(parents=True, exist_ok=True)  # nginx makes the travaux folder in it, as its own user
    CONF.write_text(HTTP_PART.format(port=port()))
    SITE.write_text(new)
    test = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    if test.returncode != 0:
        shutil.copy2(backup, SITE)
        CONF.unlink()
        if made_password:
            HTPASSWD.unlink()
        sys.exit("nginx -t failed, every file is back as it was:\n" + test.stderr)
    subprocess.run(["systemctl", "reload", "nginx"], check=True)
    print(f"done: Mattermost's locations replaced, nginx reloaded; the API on 127.0.0.1:{port()}; "
          f"{'closed preview (user testers)' if not args.open else 'open to anyone'}")
    print(f"backup: {backup}")
    print(f"to undo: sudo cp {backup} {SITE} && sudo rm {CONF} && sudo nginx -t && sudo systemctl reload nginx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
