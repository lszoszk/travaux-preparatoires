# Deploying the Travaux DB

Two parts: the **API** (`api/server.py`, in a container on the VM next to unhrdb-api) and the **site** (`site/`, static, served by
nginx from the same VM at `/travaux/`; GitHub Pages is the alternative, step 4). Nothing here is deployed by the pipeline; publication
also waits for the UN Library's reply (`docs/un_library_permission_request.md`).

## What runs where

| Part | Where | Size |
|---|---|---|
| API container `travaux-api` | the VM, `TRAVAUX_PORT` (localhost, 8006; 8000-8005 and 8080 are taken), nginx route `/travaux-api/` | image ~150-250 MB, RAM <= 512 MB (the database file is 238 MB) |
| Database `data/travaux.sqlite3` | the VM, mounted read-only into the container | ~230 MB |
| Site `site/` | the same container serves it from the bundle's `site/` (mounted read-only), nginx route `/travaux/`; or GitHub Pages | under 1 MB |
| Scans (`data/raw`, 2 GB), OCR (`data/ocr`) | stay on the laptop; the site links to the UN's copy | |

The VM had 4.9 GB free (90% used) on 30 September 2026: the API needs about 0.5 GB, and the same again while a new
database is copied in. Free space first if it is short (`docker image prune -a`, `docker builder prune`).

## 1. Build the bundle (laptop)

Once, write who answers for the site: copy `deploy/site_config.example.json` to `deploy/site_config.json` (not committed) and fill in
`author`, `affiliation`, `contact` (an email address or a web address for corrections) and `url`; replace `<AUTHOR>` in `LICENSE` and
`DATA_LICENSE.md`, and `<AUTHOR>`, `<DATE-RELEASED>` and `<URL>` in `CITATION.cff`.

```bash
python3 pipeline/build_all.py data/manifest/harvest_*.json    # if the data changed
python3 eval/coverage.py
python3 deploy/build_bundle.py --public   # dist/travaux-bundle/, with the database and the site
python3 deploy/check_bundle.py            # last look: no private folder, scan, local path, key or stray address in the bundle
```

`--public` refuses to build while the site has no author, affiliation, contact or address, or while the licence files still carry their
placeholders (without it the builder only warns, which is right for a test). The bundle holds the Dockerfile, compose file, nginx snippet,
`api/server.py`, the small data files the server reads, the database, and the site (`site/`, with a `config.js` written from
`site_config.json`: the API at the relative path `/travaux-api`, scans linked to the UN's copy). It does not hold the scans, the OCR,
the pipeline or `eval/private`.

## 2. Copy it to the VM and start it

(On the AMU VM the database is on another disk: use the two `rsync`s of "The database on another disk" below, not this one.)

```bash
rsync -av --delete --filter='P .env' dist/travaux-bundle/ amuvmuser@150.254.115.204:/home/amuvmuser/travaux/
ssh amuvmuser@150.254.115.204 'cd /home/amuvmuser/travaux && cp -n env.example .env && nano .env'   # once: set the site's origin
ssh amuvmuser@150.254.115.204 'cd /home/amuvmuser/travaux && docker compose up -d --build'
```

If `docker compose up` says `port is already allocated`, something else holds the port: list the used ones
(`docker ps --format "{{.Names}}\t{{.Ports}}"; ss -ltn`), set a free `TRAVAUX_PORT` in `.env`, and use the same number in the nginx
upstream.

The settings live in `.env` on the VM (from `env.example`); `--filter='P .env'` keeps `rsync --delete` from removing it.

Check it: `curl -s http://127.0.0.1:$TRAVAUX_PORT/health` on the VM (the port of `.env`) (`{"ok": true, ...}`), and `docker ps` shows `healthy`.

From the laptop, once nginx is set up (step 3), `deploy/smoke_test.sh https://HOST/travaux` fetches the front page, the site
settings and every endpoint one after the other, checks the error codes, that the database and the private folders are not
served, and that the API sends no CORS header to a foreign origin. It exits 1 at the first failure.

## 3. nginx

**On the AMU VM (done once, 4 October 2026, in place of Mattermost):** the bundle carries `nginx_patch_vm.py`, which replaces
Mattermost's `upstream` and its two locations in `/etc/nginx/sites-enabled/default` with the Travaux locations (`/` redirects to
`/travaux/`), writes `/etc/nginx/conf.d/travaux.conf`, keeps a backup in `/etc/nginx/_backups/`, and puts everything back if
`nginx -t` fails. By default it closes the preview with a password (it asks for it; see below); `--open` leaves it open:

```bash
ssh -t amuvmuser@150.254.115.204 'sudo python3 /home/amuvmuser/travaux/nginx_patch_vm.py'
```

Elsewhere, by hand:

Put PART 1 of `nginx-snippet.conf` in `/etc/nginx/conf.d/travaux-cache.conf` and PART 2 (the `location /travaux-api/` block for the API and the
`location /travaux/` block for the site, whose `alias` is the bundle's `site/` folder on the VM) in the server block next to `/unhrdb-api/`;
then `sudo nginx -t && sudo systemctl reload nginx`. The API is then at `https://<host>/travaux-api/api/search?q=...` and the site at
`https://<host>/travaux/`. Both are on one host, so no CORS setting is needed (leave `TRAVAUX_CORS_ORIGINS` empty in `.env`).

### Closed preview (until the UN Library replies)

Until the UN Library has approved republication, the site and the API ask for a password (user `testers`), so that only the people
you give it to can open them, and they tell search engines not to index. `nginx_patch_vm.py` sets this up; by hand, it is a password
file (`sudo -v && H=$(openssl passwd -apr1) && [ -n "$H" ] && printf 'testers:%s\n' "$H" | sudo tee /etc/nginx/travaux.htpasswd > /dev/null`; the
`sudo -v` first makes sudo ask for its password before openssl asks for the new one, otherwise both prompts read the keyboard at once, and
the `&&` chain writes nothing if the two entries differ: a plain pipe would still save `testers:` with no hash) and these lines in
both locations:

```nginx
  auth_basic "Travaux DB, closed preview";
  auth_basic_user_file /etc/nginx/travaux.htpasswd;
  add_header X-Robots-Tag "noindex, nofollow" always;
```

The browser asks once and sends the same credentials to the API (same host, same realm). Check it with
`TRAVAUX_AUTH=testers:PASSWORD deploy/smoke_test.sh https://150.254.115.204/travaux`, which also checks that a visitor without the
password is turned away. At launch: delete the three lines in both locations, `sudo nginx -t && sudo systemctl reload nginx`.

## 4. The site

The site reads its settings from `site/config.js`, which `build_bundle.py` writes from `deploy/site_config.json`:

```js
window.TRAVAUX = { api: "/travaux-api", scans: "un", label: "working edition v0.9", version: "v0.9",
                   author: "...", affiliation: "...", contact: "...", url: "https://<host>/travaux/" };
```

- `api`: the API's base URL (empty when the site is served by the API itself, as on the laptop; a full URL on GitHub Pages).
- `scans: "un"`: links to the UN's own copy (undocs.org) instead of local PDFs.
- `label`, `version`: the words in the header, the footer and the "how to cite" line.
- `author`, `affiliation`, `contact`, `url`: shown in the footer and on the About page; nothing is shown that is not filled in.
  While the preview is closed, leave `url` out of `site_config.json`: the About page's "how to cite" line then has no address that does not exist yet.
  With an email address as `contact`, every result and passage also gets a "Report an error" link that opens a message to it, filled with the passage, its citation and a link back (`docs/tester_guide.md` is the guide for testers). `--public` refuses to build until `url` is back.

On GitHub Pages instead, `deploy/github-pages-workflow.yml` (copy it to `.github/workflows/pages.yml` in the repository that
publishes the site) writes `config.js` from the repository variable `TRAVAUX_API_URL` and publishes only `site/`; it must also set the
fields above. Do not publish this whole repository: `eval/private` holds printed compilations that must never be public.

## 5. Updating the data

Build a new bundle, `rsync` it again as in step 2 (only the changed files move) and run `docker compose up -d --build` on
the VM. The database is read from the mounted file at each request, but the small data files (`data/concordance`,
`data/gold`, `eval/*.json`) are copied into the image, so a rebuild is what picks them up (`restart` would not).
Answers are cached for five minutes (nginx and browser); `TRAVAUX_CACHE_SECONDS` changes that.

## The database on another disk (the AMU VM since 12 October 2026)

The VM keeps `travaux.sqlite3` on `/mnt/data2` (ext4, `nofail` in `/etc/fstab`, so a missing disk cannot stop the boot), in
`/mnt/data2/travaux/data`; `.env` names it:

```
TRAVAUX_DATA_DIR=/mnt/data2/travaux/data
```

The small files (`data/concordance`, `data/gold`) stay in `~/travaux/data`: the image is built from them. So an update is two
copies, the bundle without the database and then the database, and a rebuild (the bundle's `docker-compose.yml` reads
`TRAVAUX_DATA_DIR`, so put that line in `.env` first):

```bash
H=amuvmuser@150.254.115.204
rsync -av --delete --exclude 'data/travaux.sqlite3' --filter='P .env' dist/travaux-bundle/ $H:/home/amuvmuser/travaux/
rsync -av dist/travaux-bundle/data/travaux.sqlite3 $H:/mnt/data2/travaux/data/
ssh $H 'cd /home/amuvmuser/travaux && docker compose up -d --build && sleep 15 && curl -s http://127.0.0.1:8006/health'
```

A plain `rsync` of the whole bundle would put a second copy of the database in `~/travaux/data` that the container never reads:
the update would look done and the site would keep showing the old data. `docker inspect travaux-api --format
'{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'` shows where the container really reads from.

## What the API exposes

`/health`, `/api/search`, `/api/record`, `/api/records`, `/api/facets`, `/api/articles`, `/api/article`, `/api/actors`,
`/api/actor`, `/api/decisions`, `/api/amendments`, `/api/quality`, `/api/symbols`, `/api/export` (CSV, JSON, BibTeX, RIS;
capped by `TRAVAUX_EXPORT_CAP`, 2,000 rows in the compose file; the export menu of the site says when a search has more). It is read-only;
`/pdf/` answers 404 in the container. `HEAD` is answered. The heavy answers (facets, a delegation, an article, the amendments) are kept in memory
and follow the database file's modification time, so a new database is picked up without a restart.
Machine-translated documents are marked in every answer (`docs/machine_translations.md`).

## Options

- A fully static site (no API): the database would have to be split and read in the browser with SQLite compiled to
  WebAssembly (sql.js-httpvfs); the database must first shrink under GitHub's 100 MB file limit (the two full-text
  indexes each keep a copy of the text). Not done: the API on the VM is simpler.
- A public MCP server: the local one (`mcp/travaux_mcp.py`) is a thin client of `api/server.py`; a public one waits for the
  UN Library's approval.
