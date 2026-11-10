// Travaux DB frontend: search over speeches, a record reader (dossier), a records list and
// a workspace of saved passages. State lives in the URL hash, so any view can be linked.
const $ = (id) => document.getElementById(id);
// the 90-second film (About, and the tour's first slide): played from the author's site on GitHub Pages, which serves byte ranges
const FILM = { src: "https://lszoszk.github.io/assets/video/travaux-film.mp4", poster: "assets/film-poster.jpg" };
const CFG = { api: "", scans: "local", label: "working edition", version: "", author: "", affiliation: "", contact: "", url: "", ...(window.TRAVAUX || {}) };
const API = CFG.api;
if (CFG.title) document.title = CFG.title;
// Where to open the scan of a record (or of a passage of it): the API's own copy, or the UN's.
function scanBase(doc) {
  if (CFG.scans === "un") return doc.pdf_url || `https://undocs.org/${doc.machine_translated && doc.source_language ? doc.source_language + "/" : ""}${doc.symbol}`;
  return doc.local_pdf ? `${API}/pdf/${encodeURIComponent(doc.local_pdf)}` : null;
}
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const marked = (s) => esc(s).replace(/\u0001/g, '<mark class="hl">').replace(/\u0002/g, "</mark>");
// "CASSIN" -> "Cassin", "de QUIJANO" -> "de Quijano", "SANTA CRUZ" -> "Santa Cruz"
const nameCase = (s) => (s || "").split(" ").map((w) => (w === w.toUpperCase() && w.length > 1 ? w[0] + w.slice(1).toLowerCase() : w)).join(" ");
const FILTERS = ["symbol", "session", "delegation", "speaker", "instrument", "article", "topic", "kind"];
let articleFacets = [];
let allTitles = {};
let searchSort = ""; // "" (default: relevance for q, record order otherwise) or "date" (chronological for q)

let offset = 0;
let corpusSymbols = new Set();
let delegationNames = []; // for the Votes view's delegation filter
let topicLabels = {}; // the questions of general debate, by key (facets)

// ---------- citations ----------
function pinpoint(h) {
  if (h.n) return h.n_end ? `paras. ${h.n}–${h.n_end}` : `para. ${h.n}`;
  return h.page_start === h.page_end ? `p. ${h.page_start}` : `pp. ${h.page_start}–${h.page_end}`;
}
// the translating model as a reader names it (each translation was compared with the scan by a second model: docs/machine_translations.md)
const MODEL_LABELS = { "claude-fable-5-1": "Claude Fable 5.1, checked by Claude Sonnet 5.5" };
const modelLabel = (m) => MODEL_LABELS[m] || m || "a language model";
function mtNote(h) {
  const lang = { fr: "French" }[h.source_language] || h.source_language || "the original";
  return `Machine translation from ${lang} (${modelLabel(h.translation_model)}, ${h.translation_date}); not an official UN text. Check the ${lang} original before quoting.`;
}
// the chair's turns: "President" in the plenary and ECOSOC, otherwise "Chairman"; named where the masthead says who presided
function chairRole(h) { return /^\W*(?:\w{1,3}\W+)?The\s+(?:PRES|Pres)/.test(h.text || "") ? "President" : "Chairman"; }
function citation(h) {
  const who = h.kind === "chair" ? (h.speaker ? ` (${nameCase(h.speaker)}, ${chairRole(h)})` : ` (${chairRole(h)})`)
    : h.speaker ? ` (${nameCase(h.speaker)}, ${h.delegation})` : "";
  const mt = h.machine_translated ? ` [machine translation from ${{ fr: "French" }[h.source_language] || h.source_language}, ${modelLabel(h.translation_model)}]` : "";
  return `${h.symbol}, ${pinpoint(h)}${who}${mt}`;
}
function dateLabel(d) {
  if (!d) return "";
  return new Date(d + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

// ---------- narrow screens: the reader is a panel of its own, the filters fold away ----------
const NARROW = window.matchMedia("(max-width: 1100px)");
const BEHIND_READER = [".mast", ".searchbar", ".ocr-banner", ".filters", "#results-pane", "#site-foot"];
let readerOpener = null;  // the link that opened the reader, to give the keyboard back to it
function setReaderOpen(open) {
  $("reader").classList.toggle("is-open", open);
  // (on a phone the panel covers the page: what is behind it is out of reach for the keyboard and for screen readers)
  for (const sel of BEHIND_READER) { const el = document.querySelector(sel); if (el) el.inert = open && NARROW.matches; }
  if (open) readerOpener = document.activeElement && document.activeElement !== document.body ? document.activeElement : readerOpener;
}
NARROW.addEventListener("change", () => setReaderOpen($("reader").classList.contains("is-open")));
function closeReader(restoreFocus = true) {
  if (!$("reader").classList.contains("is-open")) return;
  setReaderOpen(false);
  if (restoreFocus && readerOpener && document.contains(readerOpener)) readerOpener.focus();
}
function setFilters(open) {
  $("filters").classList.toggle("collapsed", !open);
  $("filters-toggle").setAttribute("aria-expanded", String(open));
}
function filtersLabel() {
  const n = FILTERS.filter((id) => $(id).value).length;
  $("filters-toggle").textContent = n ? `Filters (${n} on)` : "Filters";
}

// ---------- URL state ----------
function readHash() {
  return new URLSearchParams(location.hash.replace(/^#/, ""));
}
// A step the reader takes (a view, a submitted search, a record opened) is a history entry, so Back goes one step back;
// restoring a state from the address (Back, Forward, a pasted link) only rewrites the entry it is on.
let appliedHash = null; // the hash the page shows: our own writes must not be applied again by hashchange/popstate
const FOREIGN_VIEW_KEYS = ["qa", "qi", "vi", "va", "vd", "vo", "vr", "vf", "ai", "aa", "ap", "aq", "rc", "i", "n", "d", "sp", "sec"];
const SITE_URL = CFG.url || "https://150.254.115.204/travaux/";
const SITE_CITATION = {
  apa: `Szoszkiewicz, Ł. (2026). UN Travaux Préparatoires: A speech-level companion to the drafting records of the UDHR, ICCPR and ICESCR [Database]. Adam Mickiewicz University. ${SITE_URL}`,
  bibtex: `@misc{szoszkiewicz2026travaux,\n  author       = {Szoszkiewicz, {\\L}ukasz},\n  title        = {{UN Travaux Pr{\\'e}paratoires}: A Speech-Level Companion to the Drafting Records of the {UDHR}, {ICCPR} and {ICESCR}},\n  year         = {2026},\n  howpublished = {Database, Adam Mickiewicz University},\n  url          = {${SITE_URL}},\n  note         = {CC BY-NC-SA 4.0}\n}`,
};
function writeHash(changes, push = false) {
  const h = readHash();
  if (changes.view === "search") {
    for (const fk of FOREIGN_VIEW_KEYS) h.delete(fk);
  }
  for (const [k, v] of Object.entries(changes)) {
    if (v) h.set(k, v);
    else h.delete(k);
  }
  const next = "#" + h.toString();
  if (next !== location.hash) history[push ? "pushState" : "replaceState"](null, "", next);
  appliedHash = location.hash;
}
function syncFromAddress() {
  if (location.hash === appliedHash) return;
  appliedHash = location.hash;
  applyHash();
}
function searchState() {
  const st = { q: $("q").value.trim(), sort: searchSort };
  for (const id of FILTERS) st[id] = $(id).value;
  st.translations = $("translations").checked ? "" : "0"; // machine translations of French-only documents: in unless unticked
  return st;
}

// ---------- facets ----------
function option(select, value, label) {
  const o = document.createElement("option");
  o.value = value;
  o.textContent = label;
  select.appendChild(o);
}
// A failed request is an Error with a message for the reader, not a blank page.
const getJSON = async (url) => {
  let r;
  try {
    r = await fetch(API + url);
  } catch (e) {
    throw new Error("The server did not answer. Check your connection and try again.");
  }
  if (!r.ok) {
    throw new Error(r.status === 404 ? "There is no such page." : r.status === 400 ? "That address was not understood."
      : `The server answered with an error (${r.status}). Try again in a moment.`);
  }
  return r.json();
};
// The long lists (records, sessions, delegations, speakers): the box above each keeps the options that contain every word
// typed ("325" leaves E/CN.4/SR.325 and A/C.3/SR.325); Enter takes one of them, Escape clears the box
const NARROWED = ["symbol", "session", "delegation", "speaker"];
function narrow(id) {
  const sel = $(id);
  const words = document.querySelector(`[data-narrow="${id}"]`).value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  sel._all ||= [];
  const known = new Set(sel._all);
  for (const o of sel.options) if (!known.has(o)) sel._all.push(o);  // options added since (a value from a link)
  const fits = (o) => words.every((w) => o.textContent.toLowerCase().includes(w));
  const value = sel.value;  // rebuilding the list must not change the choice (a browser may select another option)
  sel.replaceChildren(...sel._all.filter((o) => !o.value || o.value === value || fits(o)));
  sel.value = value;
  // Enter's choice: the option whose value is what was typed, else one that ends with it ("SR.60", not SR.603), else the first
  const q = words.join(" "), left = sel._all.filter((o) => o.value && fits(o));
  return left.find((o) => o.value.toLowerCase() === q) || left.find((o) => o.value.toLowerCase().endsWith(q)) || left[0];
}
function clearNarrow() {
  for (const id of NARROWED) {
    document.querySelector(`[data-narrow="${id}"]`).value = "";
    narrow(id);
  }
}
async function loadFacets() {
  // the three answers the page needs before it can show anything, asked at once
  const [f, titlesByInstrument, symbols] = await Promise.all([getJSON("/api/facets"), getJSON("/api/article-titles"), getJSON("/api/symbols")]);
  exportCap = f.export_cap || 0;
  const t = Object.fromEntries(f.totals.map((x) => [x.v, x.n]));
  if (f.translations && f.translations.n) {
    $("translations-block").hidden = false;
    $("translations-note").textContent = `${f.translations.n} documents exist only in French; they are machine-translated (${modelLabel(f.translations.model)}) and marked.`;
  }
  for (const r of f.records) option($("symbol"), r.v, `${r.v} — ${dateLabel(r.meeting_date) || r.session} (${r.n})`);
  const shortB = (b) => (b || "").replace("Commission on Human Rights", "CHR").replace("CHR Drafting Committee", "Drafting Cttee")
    .replace("General Assembly Third Committee", "Third Committee").replace("Economic and Social Council", "ECOSOC");
  for (const s of f.sessions || []) option($("session"), s.v, `${shortB(s.body)} — ${s.session} (${s.n})`);
  for (const d of f.delegations) option($("delegation"), d.v, `${d.v} (${d.n})`);
  delegationNames = f.delegations.map((d) => d.v).sort((a, b) => a.localeCompare(b));
  for (const s of f.speakers) option($("speaker"), s.v, `${nameCase(s.v)} — ${s.d} (${s.n})`);
  for (const t of f.topics || []) option($("topic"), t.v, `${t.label} (${t.n})`);
  topicLabels = Object.fromEntries((f.topics || []).map((t) => [t.v, t.label]));
  allTitles = titlesByInstrument;
  articleFacets = f.articles;
  articleOptions();
  const c = Object.fromEntries(f.corpora.map((x) => [x.v, x]));
  const totalVotes = f.decisions_total || t.vote || 0;
  $("mast-folio").textContent = ["Travaux préparatoires", CFG.label,
    `UDHR ${c.UDHR?.records || 0} records, ${c.UDHR?.speeches || 0} speeches`,
    `Covenants ${c.Covenants?.records || 0} records, ${c.Covenants?.speeches || 0} speeches`, `${totalVotes} votes`].filter(Boolean).join(" · ");
  const totalRecs = (c.UDHR?.records || 0) + (c.Covenants?.records || 0);
  const totalSpeeches = (c.UDHR?.speeches || 0) + (c.Covenants?.speeches || 0);
  if ($("api-status")) {
    $("api-status").dataset.state = "ok";
    $("api-status").title = `Connected to Travaux DB server — ${totalRecs.toLocaleString("en-GB")} records · ${totalSpeeches.toLocaleString("en-GB")} speeches`;
    $("api-status-label").textContent = `${totalRecs.toLocaleString("en-GB")} records`;
  }
  corpusSymbols = new Set(symbols);
}

// "all results" of an export stops at the cap the server sets: the menu says so
let exportCap = 0;
function exportNote(total) {
  const cut = exportCap && total > exportCap;
  for (const a of document.querySelectorAll(".export-pop a")) {
    if (!a.dataset.note) a.dataset.note = a.querySelector("span").textContent;
    a.querySelector("span").textContent = cut ? `the first ${exportCap.toLocaleString("en-GB")} of ${total.toLocaleString("en-GB")} results` : a.dataset.note;
  }
}

// The article list follows the instrument (UDHR by default): articles are numbered per instrument.
function articleOptions() {
  const inst = $("instrument").value || "UDHR";
  const keep = $("article").value;
  $("article").innerHTML = '<option value="">Any article</option>';
  for (const a of articleFacets.filter((x) => x.i === inst)) {
    option($("article"), String(a.v), `${inst} art. ${a.v} — ${(allTitles[inst] || {})[a.v] || ""} (${a.n})`);
  }
  $("article").value = [...$("article").options].some((o) => o.value === keep) ? keep : "";
}

function apiParams(extra = {}) {
  const p = new URLSearchParams();
  const st = searchState();
  if (st.q) p.set("q", st.q);
  if (st.sort) p.set("sort", st.sort);
  for (const id of ["symbol", "session", "delegation", "speaker", "kind", "instrument"]) if (st[id]) p.set(id, st[id]);
  if (st.article) p.set("article", st.article);
  if (st.topic) p.set("topic", st.topic);
  if (st.translations === "0") p.set("translations", "0");
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  return p;
}

// ---------- workspace (localStorage) ----------
const WS_KEY = "travaux_workspace_v1";
function wsLoad() {
  try { return JSON.parse(localStorage.getItem(WS_KEY) || "[]"); } catch (e) { return []; }
}
function wsSave(items) {
  try { localStorage.setItem(WS_KEY, JSON.stringify(items)); } catch (e) { /* private mode: not saved */ }
  wsBadge();
}
function wsHas(id) {
  return wsLoad().some((x) => x.id === id);
}
function wsToggle(item) {
  const items = wsLoad();
  const i = items.findIndex((x) => x.id === item.id);
  if (i >= 0) items.splice(i, 1);
  else items.push({ ...item, note: "", added: new Date().toISOString() });
  wsSave(items);
  return i < 0;
}
function wsBadge() {
  const n = wsLoad().length;
  $("ws-badge").hidden = !n;
  $("ws-badge").textContent = n;
}
function formatWorkspaceCitation(x, style = "un") {
  const base = x.citation || "";
  if (style === "un" || !base) return base;
  const ym = (x.meta || "").match(/\b(19[456]\d)\b/);
  const yr = ym ? ` (${ym[1]})` : "";
  if (style === "bluebook") {
    const bb = base
      .replace(/^([^,]+),\s*paras\.\s*([0-9–-]+)/, `U.N. Doc. $1, ¶¶ $2${yr}`)
      .replace(/^([^,]+),\s*para\.\s*([0-9]+)/, `U.N. Doc. $1, ¶ $2${yr}`)
      .replace(/^([^,]+),\s*pp?\.\s*([0-9–-]+)/, `U.N. Doc. $1, at $2${yr}`);
    return bb.startsWith("U.N. Doc.") ? bb : `U.N. Doc. ${base}${yr}`;
  }
  if (style === "oscola") {
    const osc = base
      .replace(/^([^,]+),\s*paras\.\s*([0-9–-]+)/, `UN Doc $1${yr} paras $2`)
      .replace(/^([^,]+),\s*para\.\s*([0-9]+)/, `UN Doc $1${yr} para $2`)
      .replace(/^([^,]+),\s*pp?\.\s*([0-9–-]+)/, `UN Doc $1${yr} $2`);
    return osc.startsWith("UN Doc ") ? osc : `UN Doc ${base}${yr}`;
  }
  return base;
}
function renderWorkspace() {
  const items = wsLoad();
  const style = $("ws-cite-style")?.value || "un";
  $("ws-list").innerHTML = items.length ? items.map((x) => {
    const formattedCite = formatWorkspaceCitation(x, style);
    return `
    <li class="ws-item" data-ws="${esc(x.id)}">
      <div class="cite">${esc(formattedCite)}</div>
      <div class="meta muted">${esc(x.meta || "")}</div>
      <blockquote>${esc(x.excerpt)}</blockquote>
      <textarea data-note="${esc(x.id)}" placeholder="Your note…" aria-label="Your note on ${esc(x.symbol || "this passage")}">${esc(x.note || "")}</textarea>
      <div class="result-actions">
        <button type="button" data-open="${esc(x.symbol)}" data-seg="${esc(x.id)}" data-goto="search">Read in record</button>
        <button type="button" data-copy="${esc(formattedCite)}">Copy citation</button>
        <button type="button" data-unsave="${esc(x.id)}">Remove</button>
      </div>
    </li>`;
  }).join("") : '<li class="results-empty">Nothing saved yet. Use ☆ on a result or in the record to keep a passage here.</li>';
}
function workspaceMarkdown() {
  const items = wsLoad();
  const style = $("ws-cite-style")?.value || "un";
  const lines = [`# Travaux préparatoires — workspace`, ``, `Exported ${new Date().toLocaleString("en-GB")}. ` +
    `Summary records paraphrase; check the UN document before quoting.`, ``];
  for (const x of items) {
    lines.push(`## ${formatWorkspaceCitation(x, style)}`, ``, `> ${x.excerpt}`, ``);
    if (x.note) lines.push(`**Note:** ${x.note}`, ``);
    lines.push(`Source: UN Doc ${x.symbol}, https://undocs.org/${x.symbol}`, ``);
  }
  return lines.join("\n");
}
function download(name, text, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ---------- search ----------
// a vote that failed is shown in red, one that passed in green (as yes and no in the Votes view); a segment that records
// decisions of both kinds ("the amendment was rejected … paragraph 3 was adopted") in neither
const FAILED = new Set(["rejected", "defeated"]);
const SAYS_FAILED = /\b(?:was|were)\s+(?:rejected|defeated)\b|\bnot\s+adopted\b/i;
const SAYS_PASSED = /\b(?:was|were)\s+(?:adopted|approved|accepted|carried)\b/i;
function voteClass(v, text) {
  let failed = false;
  try { failed = FAILED.has(JSON.parse(v || "null")?.outcome); } catch (_) { return ""; }
  if (SAYS_FAILED.test(text || "") && SAYS_PASSED.test(text || "")) return " mixed";
  return failed ? " failed" : "";
}
function hitHTML(h) {
  const vote = h.vote ? JSON.parse(h.vote) : null;
  const voteLine = vote ? `Vote: ${vote.outcome}${vote.yes != null ? ` ${vote.yes}–${vote.no}${vote.abstentions != null ? `, ${vote.abstentions} abst.` : ""}` : vote.unanimous ? " unanimously" : ""}` : "";
  const prov = h.kind === "speech" && h.speaker_raw && h.speaker_raw.toUpperCase() !== (h.speaker || "").toUpperCase()
    ? `<div class="result-prov">Text layer reads “${esc(h.speaker_raw)} (${esc(h.country_raw)})”; resolved by ${esc(h.speaker_method)}</div>` : "";
  const sb = scanBase(h);
  const scan = sb ? `<a href="${esc(sb)}#page=${h.page_start}" target="_blank" rel="noopener">${CFG.scans === "un" ? "UN copy" : "Scan"} p. ${h.page_start}</a>` : "";
  const who = h.kind === "chair" ? (h.speaker ? ` — <span class="who">${esc(nameCase(h.speaker))}</span> (${chairRole(h)})` : ` — ${chairRole(h)}`)
    : h.speaker ? ` — <span class="who">${esc(nameCase(h.speaker))}</span> (${esc(h.delegation)})` : h.kind === "paragraph" && h.delegation ? ` — <span class="who">${esc(h.delegation)}</span>` : "";
  const meta = [dateLabel(h.meeting_date), h.body ? h.body.replace("Commission on Human Rights", "CHR").replace("CHR Drafting Committee", "Drafting Cttee") : "",
    h.session, h.final_article ? `${h.article_instrument} art. ${h.final_article}` + (h.draft_article && h.draft_article !== String(h.final_article) ? ` · draft ${h.draft_article}` : "")
      + (h.article_mapping && h.article_mapping.includes("chair") ? " (from agenda)" : "")
      : h.article_heading ? `draft art. ${h.article_heading}` : "",
    h.topic ? `general debate: ${topicLabels[h.topic] || h.topic}` : ""].filter(Boolean).map(esc).join("<br>");
  const excerpt = (h.snippet || "").replace(/[\u0001\u0002]/g, "").slice(0, 400);
  const saved = wsHas(h.id);
  const citeStr = citation(h);
  const quoteStr = `${citeStr}: “${excerpt}”`;
  const saveData = esc(JSON.stringify({ id: h.id, symbol: h.symbol, citation: citeStr, excerpt, meta: [h.body, h.session, dateLabel(h.meeting_date)].filter(Boolean).join(" · ") }));
  return `<li class="result" id="hit-${esc(h.id)}" data-open="${esc(h.symbol)}" data-seg="${esc(h.id)}">
    <div class="result-margin"><span class="result-pn">${esc(pinpoint(h))}</span><span class="badge badge-${esc(h.kind)}${h.kind === "vote" ? voteClass(h.vote, h.text || h.snippet) : ""}">${esc(h.kind)}</span>${h.machine_translated ? `<span class="badge badge-mt" title="${esc(mtNote(h))}">machine translation</span>` : ""}</div>
    <div class="result-main">
      <div class="result-headline"><a class="result-open" href="#view=search&open=${encodeURIComponent(h.symbol)}&seg=${encodeURIComponent(h.id)}" data-open="${esc(h.symbol)}" data-seg="${esc(h.id)}">${esc(h.symbol)}</a>${who}</div>
      <p class="result-text">${marked(h.snippet)}${h.snippet && !h.snippet.includes("\u0001") && h.snippet.length >= 320 ? "…" : ""}</p>
      ${voteLine ? `<div class="result-prov">${esc(voteLine)}</div>` : ""}${prov}${h.machine_translated ? `<div class="result-prov mt-note">${esc(mtNote(h))}</div>` : ""}
      <div class="result-actions">${scan}<button type="button" data-copy="${esc(citeStr)}">Copy citation</button><button type="button" data-copy-quote="${esc(quoteStr)}" title="Copy citation with excerpt">Copy quote</button>${reportLink(h.id, h.symbol, citeStr)}
        <button type="button" class="star ${saved ? "on" : ""}" data-save="${saveData}" title="Save to workspace">${saved ? "★" : "☆"}</button></div>
    </div>
    <div class="result-meta">${meta}</div>
  </li>`;
}

let searchSeq = 0;  // only the latest search may write to the page: a slow answer to an earlier one is dropped
async function runSearch(append = false, push = false) {
  const mine = ++searchSeq;
  offset = append ? offset : 0;
  if (!append) writeHash({ view: "search", ...searchState(), open: "", seg: "" }, push);
  // no query and no filter: the welcome panel, not 70,000 passages in record order
  const st = searchState();
  filtersLabel();
  const empty = !st.q && FILTERS.every((id) => !st[id]) && st.translations === "";
  if ($("export-menu")) $("export-menu").hidden = empty;
  if (!append) {
    $("welcome").hidden = !empty;
    $("results").hidden = empty;
    if (empty) {
      $("result-count").textContent = "—";
      if ($("sort-toggle")) $("sort-toggle").hidden = true;
      $("results").innerHTML = "";
      $("more").hidden = true;
      return;
    }
  }
  let d;
  try {
    const r = await fetch(API + "/api/search?" + apiParams({ offset }));
    d = await r.json();
    if (!r.ok && !d.error) d = { error: `The server answered with an error (${r.status}). Try again in a moment.` };
  } catch (e) {
    d = { error: "The server did not answer. Check your connection and try again." };
  }
  if (mine !== searchSeq) return;
  if (d.error) {
    // (the parser's own message, "query not understood: fts5: syntax error near ...", is no help to a reader)
    $("result-count").textContent = /^query not understood/.test(d.error)
      ? "The search words were not understood: close any quotation marks, and put AND, OR or NOT between words." : d.error;
    if ($("sort-toggle")) $("sort-toggle").hidden = true;
    $("results").innerHTML = "";
    $("more").hidden = true;
    return;
  }
  exportNote(d.total);
  const hasQ = Boolean($("q").value.replace(/\b(?:speaker|sp|delegation|country|del|art|article|inst|instrument|doc|symbol|record|kind|topic):(?:"[^"]+"|\S+)/gi, "").trim());
  const orderLabel = d.sort === "date" ? (hasQ ? " · chronological" : " · record order") : " · by relevance";
  const resParts = [];
  if (d.resolved?.speaker) resParts.push(nameCase(d.resolved.speaker));
  if (d.resolved?.delegation) resParts.push(d.resolved.delegation);
  if (d.resolved?.article) resParts.push(`${d.resolved.instrument || $("instrument").value || "UDHR"} art. ${d.resolved.article}`);
  else if (d.resolved?.instrument) resParts.push(d.resolved.instrument);
  if (d.resolved?.symbol) resParts.push(d.resolved.symbol);
  if (d.resolved?.topic) resParts.push(topicLabels[d.resolved.topic] || d.resolved.topic);
  const resLabel = resParts.length ? ` · ${resParts.join(", ")}` : "";
  $("result-count").textContent = `${d.total} result${d.total === 1 ? "" : "s"}${orderLabel}${resLabel}`;
  if ($("sort-toggle")) {
    $("sort-toggle").hidden = !hasQ || d.total <= 1;
    $("sort-toggle").textContent = d.sort === "date" ? "↕ Relevance" : "↕ Chronological";
  }
  const html = d.results.length ? d.results.map(hitHTML).join("")
    : append ? "" : `<li class="results-empty">Nothing matches. Try fewer words, or OR between alternatives${$("kind").value ? "" : "; documents (reports, drafts, amendments) are searched under Kind: Everything"}.</li>`;
  if (append) $("results").insertAdjacentHTML("beforeend", html);
  else $("results").innerHTML = html;
  offset = d.offset + d.results.length;
  $("more").hidden = offset >= d.total;
}

// ---------- the record reader ----------
// Document symbols in the text ("E/CN.4/95", "A/C.3/L.874/Rev.2") link to the record when
// it is in the database, otherwise to the UN copy.
const SYMBOL_IN_TEXT = /\b((?:A|E)\/(?:[A-Z][A-Z0-9.]*\/)*(?:[A-Z]+\.)?[1-9]\d*(?:\/(?:Rev|Add|Corr)\.\d+)*)/g;
function linkSymbols(escapedText) {
  return escapedText.replace(SYMBOL_IN_TEXT, (m) => {
    const shown = m.replace(/\.$/, "");
    const tail = m.slice(shown.length);
    const sym = shown.replace(/^E\/C[NIl1][.,]\s?[4U^hA]\//, "E/CN.4/");  // OCR: "E/CN.U/", "E/CI.4/", "E/CN,4/"
    if (/^(?:A\/C\.\d|E\/CN\.\d)$/.test(sym)) return m;  // "A/C.3" names the committee, not a document
    return corpusSymbols.has(sym)
      ? `<a class="symref" data-open="${sym}" href="#">${shown}</a>${tail}`
      : `<a class="symref ext" href="https://undocs.org/${sym}" target="_blank" rel="noopener">${shown}</a>${tail}`;
  });
}

function readerTermsRegex() {
  const raw = ($("q")?.value || "")
    .replace(/\b(?:speaker|sp|delegation|country|del|art|article|inst|instrument|doc|symbol|record|kind|topic):(?:"[^"]+"|\S+)/gi, " ")
    .replace(/\bNOT\s+(?:"[^"]+"|\S+)/gi, " ");
  const out = [];
  for (const m of raw.matchAll(/"([^"]+)"|(\S+)/g)) {
    const t = (m[1] || m[2] || "").replace(/^["()*]+|["()*]+$/g, "").trim();
    if (t.length >= 2 && !/^(?:AND|OR|NOT)$/i.test(t)) {
      const escRe = t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\\\*/g, "\\w*");
      out.push(escRe);
    }
  }
  return out.length ? new RegExp(`(<[^>]+>)|(\\b(?:${out.join("|")}))`, "gi") : null;
}
function highlightReaderHTML(html, rx) {
  if (!rx) return html;
  return html.replace(rx, (m, tag, word) => (tag ? tag : `<mark class="hl">${word}</mark>`));
}

function segHTML(s, doc, rx) {
  const para = s.n ? `<span class="para">${esc(s.n)}.</span>` : "";
  if (s.kind === "masthead") return `<details class="masthead"><summary>Masthead and attendance</summary><pre>${esc(s.text)}</pre></details>`;
  if (s.kind === "heading") return `<div class="seg heading" id="seg-${esc(s.id)}">${esc(s.text)}</div>`;
  let who = "";
  if (s.kind === "speech" && s.speaker) {
    const votes = JSON.parse(s.votes || "[]");
    const tip = `OCR readings: ${votes.join("; ") || s.speaker_raw} · ${s.speaker_method}`;
    who = `<span class="who" title="${esc(tip)}">${esc(nameCase(s.speaker))} (${esc(s.delegation)})</span> — `;
  } else if (s.kind === "chair") {
    who = `<span class="who"${s.speaker ? ` title="${esc(s.speaker_method || "")}"` : ""}>${s.speaker ? `${esc(nameCase(s.speaker))} (${chairRole(s)})` : chairRole(s)}</span> — `;
  }
  const review = s.review ? `<div class="review">Review: ${esc(s.review)}</div>` : "";
  const full = { ...(doc || {}), ...s };
  const cite = citation(full);
  const excerpt = (s.text || "").slice(0, 400);
  const quoteStr = `${cite}: “${excerpt}”`;
  const metaStr = [full.body, full.session, dateLabel(full.meeting_date)].filter(Boolean).join(" · ");
  const saveData = esc(JSON.stringify({ id: s.id, symbol: s.symbol, citation: cite, excerpt, meta: metaStr }));
  const isInteractive = ["speech", "chair", "vote", "paragraph"].includes(s.kind);
  const artChip = isInteractive && s.final_article
    ? ` <a class="seg-tag" href="#view=article&i=${encodeURIComponent(s.article_instrument || "UDHR")}&n=${s.final_article}">${esc(s.article_instrument || "UDHR")} art. ${s.final_article}</a>`
    : isInteractive && s.topic ? ` <span class="seg-tag">${esc(topicLabels[s.topic] || s.topic)}</span>` : "";
  const citeBtns = isInteractive
    ? ` <button type="button" class="seg-btn" data-copy="${esc(cite)}" title="Copy citation">Cite</button> <button type="button" class="seg-btn" data-copy-quote="${esc(quoteStr)}" title="Copy citation with excerpt">Quote</button>`
    : "";
  const star = isInteractive
    ? ` <button type="button" class="star ${wsHas(s.id) ? "on" : ""}" data-save="${saveData}" title="Save to workspace">${wsHas(s.id) ? "★" : "☆"}</button>` : "";
  const report = isInteractive ? reportLink(s.id, s.symbol, cite, "report-seg") : "";
  const bodyHTML = highlightReaderHTML(linkSymbols(esc(s.text)), rx);
  return `<div class="seg ${esc(s.kind)}${s.kind === "vote" ? voteClass(s.vote, s.text) : ""}" id="seg-${esc(s.id)}">${para}${who}${bodyHTML}${artChip}${citeBtns}${star}${report}${review}</div>`;
}

async function openRecord(symbol, segId, push = false, focusReader = false) {
  // from another view (Ask, the workspace, the records list) the reader opens over Search as it is: running the search first
  // would rewrite the history entry of the view the reader came from, and Back would not return to it
  const fromSearch = !document.querySelector('.view[data-view="search"]').hidden;
  setView("search");
  if (fromSearch && !$("results").children.length && $("welcome").hidden) await runSearch(false, false);
  const d = await (await fetch(API + "/api/record?symbol=" + encodeURIComponent(symbol))).json();
  const doc = d.document;
  if (!doc) {
    writeHash({ view: "search", open: symbol, seg: "" }, push);
    $("reader").innerHTML = `
      <div class="dossier-head">
        <button type="button" class="btn btn-ghost dossier-back" data-close-reader>← Results</button>
        <div class="folio accent">Record</div>
        <h2>${esc(symbol)}</h2>
        <div class="meta">Not in corpus · <a href="https://undocs.org/${esc(symbol)}" target="_blank" rel="noopener">UN copy</a></div>
      </div>
      <div class="dossier-body"><p class="results-empty">The text of ${esc(symbol)} is not served by the UN Official Document System. Check the <a href="https://digitallibrary.un.org/search?ln=en&p=${encodeURIComponent(symbol)}" target="_blank" rel="noopener">UN Digital Library</a> or <a href="https://undocs.org/${esc(symbol)}" target="_blank" rel="noopener">undocs.org/${esc(symbol)}</a>.</p></div>`;
    setReaderOpen(true);
    return;
  }
  writeHash({ view: "search", open: symbol, seg: segId || "" }, push);
  const scanUrl = scanBase(doc);
  const rx = readerTermsRegex();
  let page = null;
  let body = "";
  const refs = new Set();
  for (const s of d.segments) {
    if (s.page_start !== page && s.kind !== "masthead") {
      page = s.page_start;
      body += `<div class="pagebreak">${scanUrl ? `<a href="${scanUrl}#page=${page}" target="_blank" rel="noopener">p. ${page}</a>` : `p. ${page}`}</div>`;
    }
    body += segHTML(s, doc, rx);
    if (s.kind !== "masthead") {
      for (const m of s.text.matchAll(SYMBOL_IN_TEXT)) {
        const r = m[1].replace(/\.$/, "").replace(/^E\/C[NIl1][.,]\s?[4U^hA]\//, "E/CN.4/");
        if (r !== symbol && !/^(?:A\/C\.\d|E\/CN\.\d)$/.test(r)) refs.add(r);
      }
    }
  }
  if (!d.segments.length) {
    body = `<p class="results-empty">The text of this document is not served by the UN Official Document System. Check the <a href="https://digitallibrary.un.org/search?ln=en&p=${encodeURIComponent(doc.symbol)}" target="_blank" rel="noopener">UN Digital Library</a>${scanUrl ? ` or the <a href="${esc(scanUrl)}" target="_blank" rel="noopener">UN link</a>` : ""}.</p>`;
  }
  const refList = [...refs].sort();
  const refsHTML = refList.length ? `<details class="dossier-refs"><summary class="folio">Documents referred to (${refList.length})</summary>${refList.map((r) =>
    corpusSymbols.has(r) ? `<a class="symref" data-open="${esc(r)}" href="#">${esc(r)}</a>` : `<a class="symref ext" href="https://undocs.org/${esc(r)}" target="_blank" rel="noopener">${esc(r)}</a>`).join(" · ")}</details>` : "";
  const adjHTML = d.prev_symbol || d.next_symbol ? `<div class="dossier-adj">
    ${d.prev_symbol ? `<a href="#view=search&open=${encodeURIComponent(d.prev_symbol)}" data-open="${esc(d.prev_symbol)}" data-prev title="Previous record in this session ([)">← ${esc(d.prev_symbol)}</a>` : "<span></span>"}
    ${d.next_symbol ? `<a href="#view=search&open=${encodeURIComponent(d.next_symbol)}" data-open="${esc(d.next_symbol)}" data-next title="Next record in this session (])">${esc(d.next_symbol)} →</a>` : "<span></span>"}
  </div>` : "";
  $("reader").innerHTML = `
    <div class="dossier-head">
      <button type="button" class="btn btn-ghost dossier-back" data-close-reader>← Results</button>
      ${adjHTML}
      <div class="folio accent">Record</div>
      <h2>${esc(doc.symbol)}</h2>
      <div class="meta">${esc([doc.body, doc.session, dateLabel(doc.meeting_date)].filter(Boolean).join(" · "))}
        · ${doc.n_pages ? `${doc.n_pages} pp.` : "not on ODS"}
        ${scanUrl ? ` · <a href="${scanUrl}" target="_blank" rel="noopener">${CFG.scans === "un" ? "UN copy" : "local scan"}</a>` : ""}
        ${doc.pdf_url && doc.pdf_url !== scanUrl ? ` · <a href="${esc(doc.pdf_url)}" target="_blank" rel="noopener">UN PDF</a>` : ""}</div>
      ${doc.machine_translated ? `<div class="mt-banner"><strong>${esc(mtNote(doc).split("; ")[0])}.</strong> ${esc(mtNote(doc).split("; ").slice(1).join("; "))}${scanUrl ? ` <a href="${scanUrl}" target="_blank" rel="noopener">Open the French scan</a>.` : ""}</div>` : ""}
      ${refsHTML}
    </div>
    <div class="dossier-body">${body}</div>`;
  document.querySelectorAll(".result.is-active").forEach((e) => e.classList.remove("is-active"));
  setReaderOpen(true);
  $("sr-status").textContent = `Opened ${doc.symbol}: ${doc.n_pages} pages.`;
  if (focusReader || NARROW.matches) {
    // a keyboard user, or a phone where the reader is a panel of its own: focus goes where the record is
    const head = $("reader").querySelector(".dossier-head");
    head.tabIndex = -1;
    head.focus({ preventScroll: true });
  }
  if (segId) {
    const hit = document.getElementById("hit-" + segId);
    if (hit) hit.classList.add("is-active");
    const el = document.getElementById("seg-" + segId);
    if (el) {
      el.classList.add("target");
      el.scrollIntoView({ block: "center" });
    }
  }
}

// ---------- records view ----------
let recordsCache = null;
async function renderRecords() {
  const recs = (recordsCache ||= await (await fetch(API + "/api/records")).json());
  const corpus = readHash().get("rc") === "Covenants" ? "Covenants" : "UDHR";
  const n = (c) => recs.filter((r) => r.instrument === c).length;
  $("records-tabs").innerHTML = ["UDHR", "Covenants"].map((c) =>
    `<a class="tab${c === corpus ? " on" : ""}" href="#view=records&rc=${c}">${c === "UDHR" ? "UDHR (1946–48)" : "Covenants (1949–66)"} <span class="muted">${n(c)}</span></a>`).join("");
  const rq = ($("records-filter")?.value || "").trim().toLowerCase();
  const inCorpus = recs.filter((r) => r.instrument === corpus)
    .sort((a, b) => (a.meeting_date || "9999").localeCompare(b.meeting_date || "9999") || a.symbol.localeCompare(b.symbol, undefined, { numeric: true }));
  const shown = rq ? inCorpus.filter((r) =>
    r.symbol.toLowerCase().includes(rq) || (r.body || "").toLowerCase().includes(rq) ||
    (r.session || "").toLowerCase().includes(rq) || (r.meeting_date || "").includes(rq) ||
    dateLabel(r.meeting_date).toLowerCase().includes(rq)
  ) : inCorpus;
  if ($("records-count")) {
    $("records-count").textContent = rq ? `${shown.length} of ${inCorpus.length} records` : `${inCorpus.length} records`;
  }
  const groups = {};
  for (const r of shown) (groups[`${r.body || "Other"} — ${r.session || "session not known"}`] ||= []).push(r);
  $("records-list").innerHTML = Object.entries(groups).map(([g, rs]) => `
    <section class="rec-group"><h3>${esc(g)}</h3>
      ${rs.map((r) => `<div class="rec-row" data-open="${esc(r.symbol)}" data-goto="search">
        <a class="sym" href="#view=search&open=${encodeURIComponent(r.symbol)}" data-open="${esc(r.symbol)}">${esc(r.symbol)}</a>
        <span>${esc(dateLabel(r.meeting_date) || r.doc_type.replace("_", " "))}</span>
        <span class="num">${r.speeches ? `${r.speeches} speeches` : `<span class="muted">${esc((r.doc_type || "document").replace("_", " "))}</span>`}</span>
        <span class="num">${r.n_pages ? `${r.n_pages} pp.` : '<span class="muted" title="Not served by the UN Official Document System">not on ODS</span>'}</span></div>`).join("")}
    </section>`).join("");
}

// ---------- views ----------
function setView(view) {
  document.querySelectorAll(".view").forEach((v) => (v.hidden = v.dataset.view !== view));
  const nav = { article: "articles", delegation: "delegations" }[view] || view;
  document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === nav));
  if (view === "records") renderRecords();
  if (view === "workspace") renderWorkspace();
  if (view === "ask" && typeof renderAsk === "function") renderAsk(readHash());
  if (view === "check") setTimeout(() => $("check-text")?.focus(), 0);
  if (view !== "search" && typeof renderExplore === "function") {
    renderExplore(view, readHash());
    const box = document.querySelector(`.view[data-view="${view}"]`);
    if (box) box.scrollTop = 0;
  }
}

async function applyHash() {
  const h = readHash();
  let view = h.get("view") || "search";
  if (!document.querySelector(`.view[data-view="${CSS.escape(view)}"]`)) {  // a view that does not exist: Search, and the address says so
    view = "search";
    writeHash({ view });
  }
  setView(view);
  if (view !== "search") return;
  $("q").value = h.get("q") || "";
  searchSort = h.get("sort") === "date" ? "date" : "";
  $("instrument").value = h.get("instrument") || "";
  articleOptions();
  clearNarrow();
  // a record, session, delegation or speaker the facet lists leave out (a link from another page) is still a valid filter
  for (const id of ["symbol", "session", "delegation", "speaker"]) {
    const v = h.get(id);
    if (v && ![...$(id).options].some((o) => o.value === v)) option($(id), v, v);
  }
  for (const id of FILTERS) $(id).value = h.get(id) || "";
  $("translations").checked = h.get("translations") !== "0";
  const open = h.get("open");
  const seg = h.get("seg");
  if (!open) closeReader(false);
  await runSearch();
  if (open) await openRecord(open, seg);
}

// The box only gains the cursor, which alone looks like nothing happened: it also lights up for a moment
function callSearch() {
  const bar = document.querySelector(".searchbar");
  bar.classList.remove("is-called");
  void bar.offsetWidth;  // restarts the animation on a second click
  bar.classList.add("is-called");
  $("q").focus();
}

// ---------- events ----------
document.addEventListener("click", async (e) => {
  if (e.target.closest(".result-actions a, .symref.ext, .pagebreak a, .dossier-head .meta a")) return;
  const nav = e.target.closest("[data-nav]");
  if (nav) {
    e.preventDefault();
    const targetView = nav.dataset.nav;
    if (targetView === "search") {
      writeHash({ view: "search" }, true);
      if (!$("results").children.length && $("welcome").hidden) runSearch(false, false);
    } else {
      history.pushState(null, "", `#view=${encodeURIComponent(targetView)}`);
      appliedHash = location.hash;
    }
    return setView(targetView);
  }
  if (e.target.closest("[data-focus-search]")) {  // the welcome's and the tour's "Search what delegates said"
    e.preventDefault();
    if (document.querySelector('.view[data-view="search"]').hidden) {
      writeHash({ view: "search" }, true);
      if (!$("results").children.length && $("welcome").hidden) runSearch(false, false);
      setView("search");
    }
    return callSearch();
  }
  if (e.target.closest("[data-skip]")) {  // (the link's own address, #results, would wipe the search)
    e.preventDefault();
    const box = document.querySelector(".view:not([hidden])");
    const first = box.querySelector(".result-open, .rec-row a.sym, .art-card, h2");
    const target = first || box;
    if (!target.hasAttribute("tabindex") && !/^(A|BUTTON|SELECT|INPUT)$/.test(target.tagName)) target.tabIndex = -1;
    target.focus();
    return target.scrollIntoView({ block: "start" });
  }
  if (e.target.closest("[data-close-reader]")) {
    closeReader();
    return writeHash({ open: "", seg: "" }, true);
  }
  if (e.target.closest("#filters-toggle")) return setFilters($("filters").classList.contains("collapsed"));
  const retry = e.target.closest("[data-retry]");
  if (retry) {
    e.preventDefault();
    if (retry.closest("#app-error")) return location.reload();
    return applyHash();
  }
  const suggest = e.target.closest(".suggest");
  if (suggest) {
    $("q").value = suggest.dataset.q;
    return runSearch(false, true);
  }
  const exp = e.target.closest(".export-pop a");
  if (exp) {
    e.preventDefault();
    location.href = API + "/api/export?" + apiParams({ format: exp.dataset.format });
    return;
  }
  const save = e.target.closest("[data-save]");
  if (save) {
    e.stopPropagation();
    const on = wsToggle(JSON.parse(save.dataset.save));
    document.querySelectorAll(`[data-save]`).forEach((b) => {
      if (JSON.parse(b.dataset.save).id === JSON.parse(save.dataset.save).id) {
        b.classList.toggle("on", on);
        b.textContent = on ? "★" : "☆";
      }
    });
    return;
  }
  const unsave = e.target.closest("[data-unsave]");
  if (unsave) {
    wsSave(wsLoad().filter((x) => x.id !== unsave.dataset.unsave));
    return renderWorkspace();
  }
  const copy = e.target.closest("[data-copy]");
  if (copy) {
    const orig = copy.dataset.origLabel || (copy.dataset.origLabel = copy.textContent);
    try {
      await navigator.clipboard.writeText(copy.dataset.copy);
      copy.textContent = "Copied";
    } catch {
      copy.textContent = copy.dataset.copy;
    }
    setTimeout(() => (copy.textContent = orig), 1500);
    return;
  }
  const copyCite = e.target.closest("[data-copy-cite]");
  if (copyCite) {
    const kind = copyCite.dataset.copyCite === "bibtex" ? "bibtex" : "apa";
    const text = SITE_CITATION[kind];
    const orig = copyCite.dataset.origLabel || (copyCite.dataset.origLabel = copyCite.textContent);
    try {
      await navigator.clipboard.writeText(text);
      copyCite.textContent = kind === "bibtex" ? "BibTeX copied" : "Citation copied";
    } catch {
      copyCite.textContent = "Copied";
    }
    setTimeout(() => (copyCite.textContent = orig), 1800);
    return;
  }
  const copyQuote = e.target.closest("[data-copy-quote]");
  if (copyQuote) {
    const orig = copyQuote.dataset.origLabel || (copyQuote.dataset.origLabel = copyQuote.textContent);
    try {
      await navigator.clipboard.writeText(copyQuote.dataset.copyQuote);
      copyQuote.textContent = "Copied";
    } catch {
      copyQuote.textContent = "Copied";
    }
    setTimeout(() => (copyQuote.textContent = orig), 1500);
    return;
  }
  const open = e.target.closest("[data-open]");
  if (open) {
    e.preventDefault();
    return openRecord(open.dataset.open, open.dataset.seg, true, e.detail === 0 && open.tagName === "A");  // (detail 0: from the keyboard)
  }
});

document.addEventListener("input", (e) => {
  const note = e.target.closest("[data-note]");
  if (note) {
    const items = wsLoad();
    const it = items.find((x) => x.id === note.dataset.note);
    if (it) {
      it.note = note.value;
      wsSave(items);
    }
  }
});

$("search").addEventListener("submit", (e) => {
  e.preventDefault();
  runSearch(false, true);
});
if ($("sort-toggle")) {
  $("sort-toggle").addEventListener("click", () => {
    searchSort = searchSort === "date" ? "" : "date";
    runSearch(false, true);
  });
}
for (const id of FILTERS) $(id).addEventListener("change", () => {
  if (id === "instrument") articleOptions();
  runSearch(false, true);
});
$("translations").addEventListener("change", () => runSearch(false, true));
for (const id of NARROWED) {
  const box = document.querySelector(`[data-narrow="${id}"]`);
  box.addEventListener("input", () => narrow(id));
  box.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && box.value) {
      e.preventDefault();
      box.value = "";
      narrow(id);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const first = narrow(id);
      if (first && $(id).value !== first.value) {
        $(id).value = first.value;
        $(id).dispatchEvent(new Event("change"));
      }
    }
  });
}
$("more").addEventListener("click", () => runSearch(true));
$("reset").addEventListener("click", () => {
  $("q").value = "";
  searchSort = "";
  clearNarrow();
  for (const id of FILTERS) $(id).value = "";
  $("translations").checked = true;
  articleOptions();
  runSearch(false, true);
});
$("copy-link").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(location.href);
    $("copy-link").textContent = "✓ Link copied";
  } catch {
    $("copy-link").textContent = "Copy from the address bar";
  }
  setTimeout(() => ($("copy-link").textContent = "⌥ Copy link"), 1500);
});
if ($("records-filter")) {
  $("records-filter").addEventListener("input", () => renderRecords());
}
if ($("ws-cite-style")) {
  $("ws-cite-style").addEventListener("change", () => renderWorkspace());
}
$("ws-export").addEventListener("click", () => download(`travaux-workspace-${new Date().toISOString().slice(0, 10)}.md`, workspaceMarkdown(), "text/markdown"));
if ($("ws-export-json")) {
  $("ws-export-json").addEventListener("click", () => download(`travaux-workspace-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(wsLoad(), null, 2), "application/json;charset=utf-8"));
}
if ($("ws-import-json")) {
  $("ws-import-json").addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text());
      if (Array.isArray(parsed)) {
        const cur = wsLoad();
        const byId = new Map(cur.map((x) => [x.id, x]));
        for (const item of parsed) {
          if (item && item.id && item.symbol) byId.set(item.id, item);
        }
        wsSave([...byId.values()]);
        renderWorkspace();
      }
    } catch {
      /* ignore invalid file */
    }
    e.target.value = "";
  });
}
$("ws-clear").addEventListener("click", () => {
  if (confirm("Remove all saved passages?")) {
    wsSave([]);
    renderWorkspace();
  }
});
function toggleTheme() {
  const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  try { localStorage.setItem("travaux_theme", next); } catch (e) { /* private mode */ }
}
$("theme-toggle").addEventListener("click", toggleTheme);
// Keyboard (UNHRDB shortcuts): "/" focuses search, Esc clears it, "[" / "]" step to previous/next record in reader
document.addEventListener("keydown", (e) => {
  const typing = /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName);
  if (e.key === "/" && !typing) {
    e.preventDefault();
    setView("search");
    writeHash({ view: "search" }, false);
    $("q").focus();
    $("q").select();
  } else if ((e.key === "[" || e.key === "]") && !typing && $("reader").classList.contains("is-open")) {
    const link = $("reader").querySelector(e.key === "[" ? ".dossier-adj a[data-prev]" : ".dossier-adj a[data-next]");
    if (link) {
      e.preventDefault();
      link.click();
    }
  } else if (e.key === "Escape" && NARROW.matches && $("reader").classList.contains("is-open")) {
    closeReader();
    writeHash({ open: "", seg: "" }, true);
  } else if (e.key === "Escape" && document.activeElement === $("q") && $("q").value) {
    $("q").value = "";
    runSearch(false, true);
  }
});

// our own writes set appliedHash; this catches pasted links, links in the pages (#view=...) and Back/Forward
window.addEventListener("hashchange", syncFromAddress);
window.addEventListener("popstate", syncFromAddress);

// the footer: organized like HUDOC Researcher (.sf-left and .sf-right)
// "Report an error": a message to the contact address, filled with the passage, its citation and a link back to it (only when the
// contact is an email address: with a web address there is nothing to fill)
function reportHref(id, symbol, cite) {
  const c = CFG.contact || "";
  if (!/@/.test(c) || /^https?:/.test(c)) return "";
  const back = `${location.origin}${location.pathname}#view=search&open=${encodeURIComponent(symbol)}&seg=${encodeURIComponent(id)}`;
  const body = `Passage: ${cite}\nLink: ${back}\nId: ${id}\n\nWhat is wrong (speaker, delegation, article tag, split or merged speech, text, date, link to the scan):\n\n\nWhat it should be, if you know:\n`;
  return `mailto:${c}?subject=${encodeURIComponent(`Travaux DB: error in ${symbol}`)}&body=${encodeURIComponent(body)}`;
}
function reportLink(id, symbol, cite, cls = "") {
  const href = reportHref(id, symbol, cite);
  return href ? `<a class="report ${cls}" href="${esc(href)}" title="Report an error in this passage">Report an error</a>` : "";
}

function contactLink(c) {
  if (!c) return "";
  return /@/.test(c) && !/^https?:/.test(c) ? `<a href="mailto:${esc(c)}">${esc(c)}</a>` : `<a href="${esc(c)}" rel="noopener">${esc(c.replace(/^https?:\/\//, ""))}</a>`;
}
const authorName = esc(CFG.author || "Łukasz Szoszkiewicz");
const affilName = esc(CFG.affiliation || "Adam Mickiewicz University");
$("site-foot").innerHTML = `
  <div class="sf-left">
    <span class="sf-name">UN Travaux Préparatoires</span>
    <span class="sf-sep">·</span>
    <span>by <a href="https://lszoszk.github.io/" target="_blank" rel="noopener"><b>${authorName}</b></a></span>
    <span class="sf-sep">·</span>
    <span class="sf-label">Supported by</span>
    <span class="sf-sup" title="${affilName}, Poznań — research host">${affilName}</span>
    <span class="sf-sep">·</span>
    <span>Data: <a href="https://digitallibrary.un.org/" target="_blank" rel="noopener">UN Docs</a></span>
    <span class="sf-sep">·</span>
    <span class="sf-fine">Not an official UN product</span>
  </div>
  <div class="sf-right">
    <span class="api-status" id="api-status" data-state="checking" role="status" title="Connecting to the Travaux DB server…">
      <span class="api-dot" aria-hidden="true"></span>
      <span class="api-label" id="api-status-label">Connecting</span>
    </span>
    <button class="sf-btn" id="footer-theme-toggle" type="button" title="Switch between light and dark" aria-label="Toggle dark mode">
      <span class="theme-icon-light">Theme: light</span>
      <span class="theme-icon-dark">Theme: dark</span>
    </button>
    <button class="sf-btn" id="tour-btn" type="button" title="A one-minute tour of the database">✦ Tour</button>
    <a class="sf-btn" href="#view=about&part=mcp">MCP &amp; Skill</a>
    <a class="sf-btn" href="#view=about">About</a>
    <button class="sf-btn" id="cite-site-btn" type="button" data-copy-cite="apa" title="Copy a citation for UN Travaux Préparatoires (APA); BibTeX on the About page">Cite</button>
  </div>`;
if ($("footer-theme-toggle")) {
  $("footer-theme-toggle").addEventListener("click", toggleTheme);
}

wsBadge();
setFilters(!NARROW.matches);  // folded on a phone, so the first result is not under six filters
loadFacets().then(() => {
  appliedHash = location.hash;
  applyHash();
}).catch(() => {
  if ($("api-status")) {
    $("api-status").dataset.state = "err";
    $("api-status").title = "Travaux DB server unreachable";
    $("api-status-label").textContent = "Offline";
  }
  $("app-error").innerHTML = 'The server did not answer, so nothing can be shown yet. <button type="button" class="btn btn-ghost" data-retry>Try again</button>';
  $("app-error").hidden = false;
});
