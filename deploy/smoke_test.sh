#!/usr/bin/env bash
# A look at a deployed site: every page and endpoint answers, the headers are right and nothing private shows.
#
#   deploy/smoke_test.sh https://150.254.115.204/travaux    (the site, without a trailing slash; the API at the host's /travaux-api)
#   deploy/smoke_test.sh http://localhost:8430 ""           (the laptop's server: site and API on one root)
#   TRAVAUX_AUTH=testers:PASSWORD deploy/smoke_test.sh https://150.254.115.204/travaux   (the closed preview: also checks that a
#                                                           visitor without the password is turned away)
#
# One request after the other, no hammering. Exit 1 on the first failed check, with the line that failed.
set -u
BASE="${1:?usage: smoke_test.sh SITE_URL [API_PREFIX]}"
BASE="${BASE%/}"
API="${2-/travaux-api}"
ORIGIN="$(printf '%s' "$BASE" | sed -E 's#^(https?://[^/]+).*#\1#')"   # the API's prefix is from the host's root
fail=0
# a browser's User-Agent: once the site is open, nginx refuses the data to scripting clients such as curl (deploy/open_vm.py)
UA="Mozilla/5.0 (compatible; travaux-smoke-test)"
AUTH=()
[ -n "${TRAVAUX_AUTH:-}" ] && AUTH=(-u "$TRAVAUX_AUTH")

check() {  # name, expected status, url, [grep pattern the body must hold]
  local name="$1" want="$2" url="$3" pat="${4:-}"
  local body code
  body="$(mktemp)"
  code="$(curl -A "$UA" ${AUTH[@]+"${AUTH[@]}"} -sS -L --max-time 30 -o "$body" -w '%{http_code}' "$url" 2>/dev/null || echo 000)"
  if [ "$code" != "$want" ]; then echo "FAIL $name: $url answered $code, wanted $want"; fail=1
  elif [ -n "$pat" ] && ! grep -Eq -- "$pat" "$body"; then echo "FAIL $name: $url lacks /$pat/"; fail=1
  else echo "ok   $name"; fi
  rm -f "$body"
}

check "front page"            200 "$BASE/"                         "Travaux"
check "site config"           200 "$BASE/config.js"                "window.TRAVAUX"
check "stylesheet"            200 "$BASE/assets/app.css"
check "script"                200 "$BASE/app.js"
check "health"                200 "$ORIGIN$API/health"               "\"ok\": true"
check "facets"                200 "$ORIGIN$API/api/facets"           "delegations"
check "quality"               200 "$ORIGIN$API/api/quality"          "version"
check "search"                200 "$ORIGIN$API/api/search?q=torture&limit=3" "results"
check "article page"          200 "$ORIGIN$API/api/article?instrument=UDHR&n=18" "final_text"
check "unknown article"       404 "$ORIGIN$API/api/article?instrument=UDHR&n=99"
check "bad instrument"        400 "$ORIGIN$API/api/article?instrument=XYZ&n=1"
check "records"               200 "$ORIGIN$API/api/records"
check "decisions"             200 "$ORIGIN$API/api/decisions?limit=3" "results"
check "amendments"            200 "$ORIGIN$API/api/amendments?limit=3" "results"
check "actors"                200 "$ORIGIN$API/api/actors"

# nothing the public must not see
cfg="$(curl -A "$UA" ${AUTH[@]+"${AUTH[@]}"} -sS --max-time 30 "$BASE/config.js" 2>/dev/null || true)"
if printf '%s' "$cfg" | grep -Eq '/Users/|Desktop/AI|<AUTHOR>|<URL>'; then echo "FAIL site config holds a local path or a placeholder"; fail=1; else echo "ok   site config clean"; fi
for p in "data/travaux.sqlite3" "data/raw/" "eval/private/" "../etc/passwd" ".env"; do
  code="$(curl -A "$UA" ${AUTH[@]+"${AUTH[@]}"} -sS --max-time 30 -o /dev/null -w '%{http_code}' "$BASE/$p" 2>/dev/null || echo 000)"
  case "$code" in 404|403|401|400) echo "ok   /$p closed ($code)";; *) echo "FAIL /$p answered $code"; fail=1;; esac
done

# a closed preview turns away a visitor without the password, on the site and on the API
if [ -n "${TRAVAUX_AUTH:-}" ]; then
  for u in "$BASE/" "$ORIGIN$API/health"; do
    code="$(curl -A "$UA" -sS --max-time 30 -o /dev/null -w '%{http_code}' "$u" 2>/dev/null || echo 000)"
    if [ "$code" = 401 ]; then echo "ok   closed without the password: $u"; else echo "FAIL $u answered $code without the password"; fail=1; fi
  done
fi

# the API sends a CORS header only to its own origin
hdr="$(curl -A "$UA" ${AUTH[@]+"${AUTH[@]}"} -sS --max-time 30 -D - -o /dev/null -H 'Origin: https://evil.example' "$ORIGIN$API/health" 2>/dev/null || true)"
if printf '%s' "$hdr" | grep -qi 'access-control-allow-origin: \*\|access-control-allow-origin: https://evil.example'; then echo "FAIL CORS open to a foreign origin"; fail=1; else echo "ok   CORS closed to a foreign origin"; fi

exit $fail
