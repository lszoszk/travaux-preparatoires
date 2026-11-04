"""The deployment bundle (deploy/build_bundle.py): the server started from it, as in the container, answers the API."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "travaux.sqlite3"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="build the database first")
ORIGIN = "https://example.github.io"


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    bundle = tmp_path_factory.mktemp("bundle") / "travaux-bundle"
    subprocess.run([sys.executable, str(ROOT / "deploy" / "build_bundle.py"), "--out", str(bundle), "--no-db"], check=True,
                   capture_output=True)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {"PATH": os.environ["PATH"], "TRAVAUX_ROOT": str(bundle), "TRAVAUX_DB": str(DB), "TRAVAUX_SCANS": str(bundle / "none"),
           "HOST": "127.0.0.1", "PORT": str(port), "TRAVAUX_CORS_ORIGINS": ORIGIN, "TRAVAUX_CACHE_SECONDS": "300",
           "TRAVAUX_VERSION": "test"}
    proc = subprocess.Popen([sys.executable, str(bundle / "api" / "server.py")], env=env, cwd=bundle,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            break
        except OSError:
            time.sleep(0.2)
    else:
        proc.kill()
        pytest.fail("the server from the bundle did not start: " + proc.stderr.read().decode()[-500:])
    yield bundle, base
    proc.kill()


def get(base, path, headers=None):
    req = urllib.request.Request(base + path, headers=headers or {})
    with urllib.request.urlopen(req) as r:
        return r.status, dict(r.headers), r.read()


def test_bundle_holds_no_scans_or_private_material(api):
    bundle, _ = api
    files = [p.relative_to(bundle) for p in bundle.rglob("*") if p.is_file()]
    assert not [f for f in files if f.suffix == ".pdf" or "private" in f.parts]
    assert not (bundle / "data" / "raw").exists() and not (bundle / "data" / "ocr").exists()
    # the site is in the bundle (nginx serves it) with the settings of the deployment, and without the pipeline or the eval material
    assert (bundle / "site" / "index.html").exists() and (bundle / "site" / "config.js").exists()
    assert "/travaux-api" in (bundle / "site" / "config.js").read_text()
    assert not (bundle / "pipeline").exists() and not (bundle / "eval" / "private").exists()
    assert (bundle / "LICENSE").exists() and (bundle / "DATA_LICENSE.md").exists() and (bundle / "CITATION.cff").exists()


def test_public_bundle_needs_an_author_and_a_contact(tmp_path):
    """--public refuses while the site has no author, affiliation, contact or address, or the licence files carry placeholders."""
    r = subprocess.run([sys.executable, str(ROOT / "deploy" / "build_bundle.py"), "--out", str(tmp_path / "b"), "--no-db", "--public",
                        "--site-config", str(tmp_path / "none.json")], capture_output=True, text=True)
    assert r.returncode != 0 and "not a public bundle" in r.stderr and "author" in r.stderr


def test_bundle_check_passes_a_clean_bundle_and_catches_a_leak(api, tmp_path):
    """deploy/check_bundle.py: a clean bundle passes; a local path, a private folder or a stray address fails it."""
    import shutil
    bundle, _ = api
    copy = tmp_path / "b"
    shutil.copytree(bundle, copy)
    run = lambda: subprocess.run([sys.executable, str(ROOT / "deploy" / "check_bundle.py"), str(copy)], capture_output=True, text=True)
    assert run().returncode == 0
    (copy / "site" / "leak.js").write_text("const p = '/Users/someone/project/data';")
    r = run()
    assert r.returncode == 1 and "a local path" in r.stderr
    (copy / "site" / "leak.js").unlink()
    (copy / "eval" / "private").mkdir()
    (copy / "eval" / "private" / "x.txt").write_text("x")
    assert "must not be in a public bundle" in run().stderr
    shutil.rmtree(copy / "eval" / "private")
    (copy / "site" / "note.md").write_text("write to somebody@example.org")
    assert "not the configured contact" in run().stderr


def test_compose_publishes_on_localhost_only_with_the_port_from_env():
    """The container is never exposed to the network directly: nginx proxies to 127.0.0.1:TRAVAUX_PORT (8006; unhrdb-ask-api holds 8003 on the VM)."""
    compose = (ROOT / "deploy" / "docker-compose.yml").read_text()
    assert '"127.0.0.1:${TRAVAUX_PORT:-8006}:8003"' in compose
    assert "./site:/app/site:ro" in compose  # the container serves the site: nginx needs no access to the home folder
    assert "${TRAVAUX_DATA_DIR:-./data}:/data:ro" in compose  # the database may sit on another disk
    assert "TRAVAUX_PORT=" in (ROOT / "deploy" / "env.example").read_text()


# the VM's server file as it was on 4 October 2026, the parts that matter (deploy/nginx_patch_vm.py)
VM_NGINX = """upstream mattermost {
  server 127.0.0.1:8065;
  keepalive 32;
}

server {
  listen 80;
  server_name 150.254.115.204;
  location ^~ /.well-known/acme-challenge/ { root /var/www/html; }
  location / {
    return 301 https://$host$request_uri;
  }
}
server {
  listen 443 ssl http2;
  server_name 150.254.115.204;
  location /ask-api/ {
    proxy_read_timeout 90s;
    gzip off;
  }

  # ---- Mattermost websocket ----
  location ~ /api/v[0-9]+/(users/)?websocket$ {
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_http_version 1.1;
    proxy_pass http://mattermost;
  }

  # ---- Mattermost default ----
  location / {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_pass http://mattermost;
  }
  # >>> aiact (AI Act Commentary) >>>
  location /aiact/ {
    proxy_pass http://127.0.0.1:8005;
  }
}
"""


def test_vm_nginx_patch_replaces_only_mattermost():
    sys.path.insert(0, str(ROOT / "deploy"))
    import nginx_patch_vm as nv
    closed = nv.patch(VM_NGINX, closed=True)
    assert "http://mattermost" not in closed and "upstream mattermost" not in closed and "/(users/)?websocket" not in closed
    # the other services and the port-80 redirect are untouched
    for keep in ("location /ask-api/", "location /aiact/", "return 301 https://$host$request_uri;", "/.well-known/acme-challenge/"):
        assert keep in closed
    assert "location = / { return 302 /travaux/; }" in closed and "location / { return 404; }" in closed
    assert closed.count("auth_basic_user_file /etc/nginx/travaux.htpasswd;") == 2
    assert closed.count("{") == closed.count("}")
    opened = nv.patch(VM_NGINX, closed=False)
    assert "auth_basic" not in opened and "location /travaux/" in opened
    # a file that is no longer as it was, or one already patched, is refused
    with pytest.raises(ValueError):
        nv.patch(VM_NGINX.replace("# ---- Mattermost websocket ----", "# websocket"), closed=True)
    with pytest.raises(ValueError):
        nv.patch(closed, closed=True)


def test_health_and_every_endpoint(api):
    _, base = api
    status, _, body = get(base, "/health")
    assert status == 200 and json.loads(body) == {"ok": True, "version": "test", "documents": json.loads(body)["documents"], "ask": False}
    assert json.loads(body)["documents"] > 1000
    for path in ("/api/facets", "/api/records", "/api/articles?instrument=UDHR", "/api/article?instrument=UDHR&n=18",
                 "/api/actors", "/api/decisions?article=18", "/api/amendments?article=18", "/api/quality", "/api/symbols",
                 "/api/article-titles", "/api/search?q=%22freedom+of+thought%22"):
        status, headers, body = get(base, path)
        assert status == 200, path
        assert json.loads(body), path
    q = json.loads(get(base, "/api/quality")[2])
    assert q["coverage"]["records"]["pct"] > 90 and q["counts"]


def test_text_is_compressed_for_a_browser_that_accepts_it(api):
    import gzip
    _, base = api
    req = urllib.request.Request(base + "/api/facets", headers={"Accept-Encoding": "gzip, deflate, br"})
    with urllib.request.urlopen(req) as r:
        raw = r.read()
        assert r.headers["Content-Encoding"] == "gzip" and "Accept-Encoding" in r.headers["Vary"]
    assert json.loads(gzip.decompress(raw))["delegations"] and len(raw) < 100_000
    _, h, body = get(base, "/api/facets")  # without the header: plain JSON
    assert "Content-Encoding" not in h and json.loads(body)


def test_check_holds_citations_against_the_records(api):
    _, base = api
    text = ('the article "dealt with the rights and freedoms that were above the law and, as it were, outside it" '
            "(E/CN.4/SR.60, p. 7 (Malik, Lebanon)); Cassin too (E/CN.4/SR.60, p. 12 (Cassin, France)); see E/CN.4/SR.999, p. 3.")
    req = urllib.request.Request(base + "/api/check", data=json.dumps({"text": text}).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        d = json.loads(r.read())
    first, cassin, missing = d["citations"]
    assert first["status"] == "ok" and {c["what"] for c in first["checks"]} == {"document", "pinpoint", "speaker", "quotation"}
    assert cassin["status"] == "problem" and "not at the place cited" in cassin["checks"][-1]["note"]
    assert missing["status"] == "not_held" and d["counts"] == {"ok": 1, "check": 0, "problem": 1, "not_held": 1}


def test_ask_without_a_key_says_so(api):
    # Ask needs VOYAGE_API_KEY (and the vectors): without it, a clear 503, and /health says ask: false
    _, base = api
    req = urllib.request.Request(base + "/api/ask", data=json.dumps({"q": "freedom to change one's religion"}).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
        raise AssertionError("expected 503")
    except urllib.error.HTTPError as e:
        assert e.code == 503 and "not available" in json.loads(e.read())["error"]


def test_cors_only_for_the_configured_origin_and_cache_header(api):
    _, base = api
    _, h, _ = get(base, "/api/facets", {"Origin": ORIGIN})
    assert h.get("Access-Control-Allow-Origin") == ORIGIN and "Origin" in h.get("Vary", "")
    assert h.get("Cache-Control") == "public, max-age=300"
    _, h2, _ = get(base, "/api/facets", {"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in h2
    req = urllib.request.Request(base + "/api/search", method="OPTIONS", headers={"Origin": ORIGIN})
    with urllib.request.urlopen(req) as r:
        assert r.status == 204 and r.headers["Access-Control-Allow-Origin"] == ORIGIN


def test_vary_origin_on_every_answer_so_the_cache_keeps_them_apart(api):
    _, base = api
    _, h, _ = get(base, "/api/facets")  # no Origin: the cached copy of this one must not serve the site's calls
    assert "Origin" in h.get("Vary", "") and "Access-Control-Allow-Origin" not in h


def test_bad_parameters_are_a_400_not_a_dropped_connection(api):
    _, base = api
    for path in ("/api/search?offset=abc", "/api/article?n=x", "/api/decisions?article=x", "/api/search?offset=99999999999999999999"):
        with pytest.raises(urllib.error.HTTPError) as e:
            get(base, path)
        assert e.value.code == 400, path


def test_no_scans_in_the_container(api):
    _, base = api
    with pytest.raises(urllib.error.HTTPError) as e:
        get(base, "/pdf/E_CN.4_SR.60-EN.pdf")
    assert e.value.code == 404


def test_no_path_traversal(api):
    _, base = api
    for path in ("/%2e%2e/%2e%2e/etc/passwd", "/..%2f..%2fetc/passwd", "/api/../../etc/passwd", "/pdf/..%2f..%2fetc%2fpasswd"):
        try:
            status, _, body = get(base, path)
        except urllib.error.HTTPError as e:
            status, body = e.code, b""
        assert status in (400, 404) and b"root:" not in body, path
