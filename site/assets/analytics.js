/* UN Travaux Préparatoires: usage counts, as HUDOC Researcher and UNHRDB keep them (their analytics-consent.js and who.js).
 *
 * GOATCOUNTER, cookie-free, runs without a banner: one count each time a view is opened, with the view's name only
 * (/travaux/search, /travaux/ask, /travaux/article ...), the referring site cut to origin + path, and the screen size.
 * Never the words of a search, a question, a filter, an article number or the record opened. It is sent as a plain
 * request for an image to GoatCounter, so no script from another site is loaded.
 *
 * GOOGLE ANALYTICS 4 only if a measurement ID is set (config.js: analytics.ga4) and only after the reader allows it in the
 * banner (Consent Mode v2: everything denied by default); it receives the same view names and nothing else.
 *
 * WHO ARE YOU? Once per browser, after real use (40 seconds in view and a click or key press), an optional anonymous
 * question about the reader's role, counted as a GoatCounter event who/travaux/<role> and nothing else.
 *
 * Nothing at all under Do-Not-Track or Global Privacy Control, with ?notrack=1, for automated browsers, or off the
 * production host (config.js: url), so local previews and tests are not counted. The About page shows the choice made
 * and can reset it ([data-consent-ui]).
 */
(function () {
  "use strict";
  var CFG = window.TRAVAUX || {};
  var A = CFG.analytics || {};
  var GOATCOUNTER = A.goatcounter || "";
  var PREFIX = A.path || "/travaux";
  var GA4 = A.ga4 || "";
  var STORE_KEY = "travaux-analytics-consent";
  var WHO_KEY = "who-v1:travaux";
  var POLICY_VERSION = 1;
  var VIEWS = ["search", "ask", "check", "articles", "article", "delegations", "delegation", "votes", "amendments", "records",
               "workspace", "about"];
  var listeners = [];
  var gtagLoaded = false;

  // ---------------------------------------------------------------- who may be counted

  function signalsOptOut() {
    try {
      if (navigator.globalPrivacyControl === true) return true;
      var dnt = navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack;
      return dnt === "1" || dnt === "yes";
    } catch (e) { return true; }
  }

  function suppressed() {
    try {
      if (signalsOptOut()) return true;
      if (navigator.webdriver || /HeadlessChrome/.test(navigator.userAgent || "")) return true;
      if (/[?&]notrack=1\b/.test(location.search)) return true;
      var prod = CFG.url ? new URL(CFG.url).host : "";
      return !prod || location.host !== prod;
    } catch (e) { return true; }
  }

  // ---------------------------------------------------------------- the view, and only the view

  function currentView() {
    var h = new URLSearchParams(location.hash.replace(/^#/, ""));
    var v = h.get("view") || "search";
    if (VIEWS.indexOf(v) === -1) v = "search";
    if (v === "about" && ["methods", "mcp", "news"].indexOf(h.get("part")) !== -1) v = "about/" + h.get("part");
    return v;
  }

  function title(v) {
    return v.split("/").map(function (s) { return s.charAt(0).toUpperCase() + s.slice(1); }).join(" · ");
  }

  function cleanRef(href) {
    if (!href) return "";
    try {
      var u = new URL(href);
      return u.host === location.host ? "" : u.origin + u.pathname;   // our own pages are not a source
    } catch (e) { return ""; }
  }

  // ---------------------------------------------------------------- goatcounter

  function gc(path, t, isEvent) {
    if (!GOATCOUNTER || suppressed()) return;
    var q = ["p=" + encodeURIComponent(path), "t=" + encodeURIComponent(t), "e=" + (isEvent ? "true" : "false"),
             "rnd=" + Math.random().toString(36).slice(2)];
    if (!isEvent) {
      var r = cleanRef(document.referrer);
      if (r) q.push("r=" + encodeURIComponent(r));
      try { q.push("s=" + encodeURIComponent(screen.width + "," + screen.height + "," + (window.devicePixelRatio || 1))); } catch (e) {}
    }
    try { new Image().src = GOATCOUNTER + "?" + q.join("&"); } catch (e) { /* counting must never break the page */ }
  }

  // ---------------------------------------------------------------- ga4, after consent only

  function readChoice() {
    try {
      var p = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
      if (!p || p.v !== POLICY_VERSION || (p.choice !== "granted" && p.choice !== "denied")) return null;
      return p;
    } catch (e) { return null; }
  }
  function writeChoice(choice) {
    try { localStorage.setItem(STORE_KEY, JSON.stringify({ choice: choice, ts: new Date().toISOString(), v: POLICY_VERSION })); } catch (e) {}
  }
  function gtag() { window.dataLayer.push(arguments); }

  function pushDefaults() {
    window.dataLayer = window.dataLayer || [];
    window.gtag = gtag;
    gtag("consent", "default", {
      ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied", analytics_storage: "denied",
      personalization_storage: "denied", functionality_storage: "granted", security_storage: "granted", wait_for_update: 500,
    });
  }

  function startGa4() {
    if (!GA4 || gtagLoaded || suppressed()) return;
    gtagLoaded = true;
    gtag("consent", "update", { analytics_storage: "granted" });
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(GA4);
    document.head.appendChild(s);
    gtag("js", new Date());
    // our own page_view, with the view's name: the automatic one would carry the address, and with it a search
    gtag("config", GA4, { send_page_view: false, allow_google_signals: false, allow_ad_personalization_signals: false });
  }

  function ga4View(v) {
    var c = readChoice();
    if (!GA4 || !gtagLoaded || !c || c.choice !== "granted") return;
    try {
      gtag("event", "page_view", { page_title: title(v), page_location: location.origin + location.pathname + "#view=" + v,
                                   page_referrer: cleanRef(document.referrer) });
    } catch (e) {}
  }

  // ---------------------------------------------------------------- one count per view opened

  var lastView = null;
  function onView() {
    var v = currentView();
    if (v === lastView) return;
    lastView = v;
    gc(PREFIX + "/" + v, "Travaux · " + title(v), false);
    ga4View(v);
  }
  // the site moves between views with history.pushState / replaceState, which fire no event of their own
  ["pushState", "replaceState"].forEach(function (m) {
    var orig = history[m];
    history[m] = function () { var r = orig.apply(this, arguments); setTimeout(onView, 0); return r; };
  });
  addEventListener("hashchange", onView);
  addEventListener("popstate", onView);

  // ---------------------------------------------------------------- the banner (only when GA4 is set)

  function status() {
    if (signalsOptOut()) return { choice: "denied", reason: "dnt", label: "Analytics declined: your browser sends a Do Not Track or Global Privacy Control signal." };
    if (!GA4) return { choice: null, reason: "none", label: "No consent is asked: only the cookie-free counter runs." };
    var c = readChoice();
    if (!c) return { choice: null, reason: "unset", label: "No choice made yet: Google Analytics is off until you choose." };
    return { choice: c.choice, reason: "stored", label: c.choice === "granted" ? "Google Analytics allowed." : "Google Analytics declined." };
  }
  function notify() { listeners.forEach(function (f) { try { f(status()); } catch (e) {} }); }

  function injectStyles() {
    if (document.getElementById("travaux-consent-styles")) return;
    var st = document.createElement("style");
    st.id = "travaux-consent-styles";
    st.textContent =
      ".tx-consent{position:fixed;left:0;right:0;bottom:0;z-index:9999;background:var(--paper);color:var(--ink);" +
      "border-top:1px solid var(--rule);padding:.9rem 1.1rem;display:flex;flex-wrap:wrap;gap:.75rem 1.25rem;align-items:center;" +
      "font-family:var(--body);font-size:.88rem;line-height:1.5;box-shadow:0 -2px 12px rgba(0,0,0,.08)}" +
      ".tx-consent p{flex:1 1 320px;margin:0}.tx-consent-actions{display:flex;gap:.5rem}" +
      ".tx-consent button,.tx-consent-ui button{font:inherit;padding:.4rem 1.1rem;cursor:pointer;border:1px solid var(--ink);" +
      "background:transparent;color:var(--ink)}.tx-consent button:hover,.tx-consent-ui button:hover{background:var(--ink);color:var(--paper)}" +
      ".tx-consent a{color:var(--accent)}.tx-consent-ui{margin:.8rem 0;padding:.75rem 1rem;border:1px solid var(--rule);font-size:.92rem}" +
      ".tx-consent-ui p{margin:0 0 .5rem}@media print{.tx-consent{display:none}}";
    document.head.appendChild(st);
  }

  function dismissBanner() { var b = document.getElementById("tx-consent"); if (b) b.remove(); }

  function mountBanner() {
    if (document.getElementById("tx-consent")) return;
    injectStyles();
    var bar = document.createElement("div");
    bar.id = "tx-consent";
    bar.className = "tx-consent";
    bar.setAttribute("role", "dialog");
    bar.setAttribute("aria-modal", "false");  // never traps the focus or blocks reading
    bar.setAttribute("aria-label", "Analytics");
    bar.innerHTML = "<p>A cookie-free counter records which view is opened. We would also like to use Google Analytics to see " +
      "which views get used; it stays off unless you allow it. Neither ever receives your searches, your questions or the records " +
      "you open. <a href=\"#view=about&sec=licence\">What this means</a>.</p><div class=\"tx-consent-actions\">" +
      "<button type=\"button\" data-consent=\"denied\">Reject</button><button type=\"button\" data-consent=\"granted\">Allow</button></div>";
    bar.addEventListener("click", function (e) {
      var b = e.target.closest("[data-consent]");
      if (b) choose(b.getAttribute("data-consent"));
    });
    document.body.appendChild(bar);
  }

  function choose(choice) {
    writeChoice(choice);
    dismissBanner();
    if (choice === "granted") { startGa4(); ga4View(currentView()); }
    notify();
  }

  function reset() {
    try { localStorage.removeItem(STORE_KEY); } catch (e) {}
    notify();
    if (GA4 && !suppressed()) mountBanner();
  }

  function mountPrivacyUi(root) {
    if (!root || root.dataset.mounted) return;
    root.dataset.mounted = "1";
    injectStyles();
    root.classList.add("tx-consent-ui");
    var p = document.createElement("p");
    var btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Reset analytics choice";
    btn.addEventListener("click", reset);
    function render(s) { p.textContent = "Current choice: " + s.label; btn.hidden = s.reason === "dnt" || s.reason === "none"; }
    render(status());
    listeners.push(render);
    root.appendChild(p);
    root.appendChild(btn);
  }

  // ---------------------------------------------------------------- who are you?

  var ROLES = [["practitioner", "Lawyer / practitioner"], ["researcher", "Researcher / academic"], ["student", "Student"],
               ["ngo", "NGO / civil society"], ["institution", "Court / public institution"], ["other", "Other"]];

  function whoDone() { try { return !!localStorage.getItem(WHO_KEY); } catch (e) { return true; } }
  function whoRemember(v) { try { localStorage.setItem(WHO_KEY, v + " " + new Date().toISOString().slice(0, 10)); } catch (e) {} }

  function showWho() {
    if (document.getElementById("who-card") || document.getElementById("tx-consent") || document.querySelector(".tourwrap.open")) return false;
    var st = document.createElement("style");
    st.textContent =
      "#who-card{position:fixed;left:16px;bottom:64px;z-index:2147483000;max-width:min(360px,calc(100vw - 32px));background:var(--paper);" +
      "color:var(--ink);border:1px solid var(--rule);box-shadow:0 6px 24px rgba(0,0,0,.14);padding:12px 14px;font-family:var(--body);font-size:13.5px;line-height:1.4}" +
      "#who-card h2{font-size:14px;margin:0 22px 2px 0;font-weight:650}#who-card p{margin:0 0 8px;color:var(--ink-3);font-size:12.5px}" +
      "#who-card .who-roles{display:flex;flex-wrap:wrap;gap:6px}#who-card .who-roles button{font:inherit;font-size:12.5px;border:1px solid var(--rule);" +
      "background:var(--paper-2);color:inherit;border-radius:999px;padding:4px 10px;cursor:pointer}" +
      "#who-card .who-roles button:hover,#who-card .who-roles button:focus-visible{border-color:var(--accent);color:var(--accent)}" +
      "#who-card .who-x{position:absolute;top:6px;right:8px;border:0;background:none;font-size:18px;line-height:1;color:var(--ink-3);cursor:pointer;padding:4px}" +
      "@media print{#who-card{display:none}}";
    document.head.appendChild(st);
    var card = document.createElement("div");
    card.id = "who-card";
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-label", "Who are you? An optional, anonymous question");
    card.innerHTML = "<button type=\"button\" class=\"who-x\" aria-label=\"Close, do not ask again\">×</button>" +
      "<h2>Who are you?</h2><p>One anonymous click helps us show funders who uses this database. Nothing else is recorded.</p>" +
      "<div class=\"who-roles\"></div>";
    var roles = card.querySelector(".who-roles");
    ROLES.forEach(function (r) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = r[1];
      b.onclick = function () {
        gc("who/travaux/" + r[0], "Who are you: " + r[0], true);
        whoRemember(r[0]);
        card.innerHTML = "<p style=\"margin:0\">Thank you!</p>";
        setTimeout(function () { card.remove(); }, 1600);
      };
      roles.appendChild(b);
    });
    function close() { whoRemember("closed"); card.remove(); removeEventListener("keydown", esc); }
    function esc(e) { if (e.key === "Escape") close(); }
    card.querySelector(".who-x").onclick = close;
    addEventListener("keydown", esc);
    document.body.appendChild(card);
    return true;
  }

  function scheduleWho() {
    var force = /[?&]who=1\b/.test(location.search);
    if (!force && (suppressed() || whoDone())) return;
    if (force) return showWho();
    var seen = 0, touched = false;
    ["pointerdown", "keydown"].forEach(function (t) { addEventListener(t, function () { touched = true; }, { once: true, passive: true }); });
    var timer = setInterval(function () {
      if (document.visibilityState === "visible") seen++;
      if (seen >= 40 && touched && showWho()) clearInterval(timer);   // (not over the tour or the banner: it waits)
    }, 1000);
  }

  // ---------------------------------------------------------------- start

  pushDefaults();
  window.TravauxAnalytics = { status: status, reset: reset, mountPrivacyUi: mountPrivacyUi, subscribe: function (f) { listeners.push(f); } };

  function boot() {
    if (signalsOptOut()) return;
    onView();
    scheduleWho();
    if (!GA4 || suppressed()) return;
    var c = readChoice();
    if (!c) mountBanner();
    else if (c.choice === "granted") { startGa4(); ga4View(currentView()); }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
