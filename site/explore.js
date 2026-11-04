// Research views over the database's structure: each article's drafting history, the
// delegations, the vote table and the amendments. Uses the helpers in app.js ($, esc,
// nameCase, dateLabel, corpusSymbols). Every view is a URL (#view=article&n=18).
const STAGE_SHORT = {
  secretariat_outline: "Secretariat outline", cassin_rev1: "Cassin draft (Rev.1)", cassin_draft: "Cassin draft", drafting_committee_1: "Drafting Cttee I", geneva_draft: "Geneva draft",
  drafting_committee_2: "Drafting Cttee II", chr_3: "CHR 3rd session", a777: "Third Committee (A/777)", final: "Adopted text",
  uk_draft_1947: "UK draft bill (1947)", e_cn4_21_g: "Drafting Cttee I: convention articles",
  e_cn4_57: "Geneva working group", e_cn4_56: "Geneva working group (Convention)", e600: "Geneva draft Covenant",
  chr5: "E/800 (1948)", chr6: "E/1371 (1949)", e1681: "E/1681 (1950)", e1992: "E/1992 (1951)", e2256: "E/2256 (1952)", e2447: "E/2447 (1953)",
  e2573: "CHR draft 1954 (E/2573)", a4625: "Third Committee 1960 (A/4625)", a5000: "Third Committee 1961 (A/5000)",
};
const GOOD = ["adopted", "accepted", "approved", "carried"];
// Only the latest view that was asked for may write to the page: a slow answer to an earlier request is dropped.
let viewToken = 0;
let articleTitles = null;  // {UDHR: {n: title}, ICCPR: ..., ICESCR: ...}
async function titles() {
  return (articleTitles ||= await getJSON("/api/article-titles"));
}
const INSTR = {
  UDHR: { name: "Universal Declaration", count: 30, span: "1946–48" },
  ICCPR: { name: "International Covenant on Civil and Political Rights", count: 53, span: "1949–66" },
  ICESCR: { name: "International Covenant on Economic, Social and Cultural Rights", count: 31, span: "1949–66" },
};
const artTitle = (inst, n) => ((articleTitles || {})[inst] || {})[n] || "";
function instrumentSelect(id, value, allLabel = "All instruments") {
  return `<select id="${id}" aria-label="Instrument"><option value="">${allLabel}</option>${Object.keys(INSTR).map((i) =>
    `<option value="${i}"${i === value ? " selected" : ""}>${i}</option>`).join("")}</select>`;
}
function articleSelect(id, inst, value) {
  const i = inst || "UDHR";
  return `<select id="${id}" aria-label="Article"><option value="">Any ${inst ? i + " " : ""}article</option>${Array.from({ length: INSTR[i].count }, (_, k) =>
    `<option value="${k + 1}"${String(k + 1) === String(value) ? " selected" : ""}>${i} art. ${k + 1} — ${esc(artTitle(i, k + 1))}</option>`).join("")}</select>`;
}

// ---------- small pieces ----------
function recLink(symbol, segId, label, extra = {}) {
  const h = new URLSearchParams({ view: "search", ...extra, open: symbol });
  if (segId) h.set("seg", segId);
  return `<a class="symref" href="#${h}">${esc(label || symbol)}</a>`;
}
function docLink(sym) {
  return corpusSymbols.has(sym) ? recLink(sym)
    : `<a class="symref ext" href="https://undocs.org/${esc(sym)}" target="_blank" rel="noopener">${esc(sym)}</a>`;
}
const delegLink = (d) => `<a class="chip" href="#view=delegation&d=${encodeURIComponent(d)}">${esc(d)}</a>`;
const artLink = (n, inst = "UDHR") => `<a class="chip" href="#view=article&i=${inst}&n=${n}" title="${esc(artTitle(inst, n))}">${inst === "UDHR" ? "" : inst + " "}Art. ${n}</a>`;
const shortBody = (b) => (b || "").replace("Commission on Human Rights", "CHR").replace("CHR Drafting Committee", "Drafting Cttee")
  .replace("General Assembly Third Committee", "Third Committee").replace("Economic and Social Council", "ECOSOC");
function figures(d) {
  if (d.yes != null) return `${d.yes}–${d.no ?? "?"}${d.abstentions != null ? `–${d.abstentions}` : ""}`;
  if (d.unanimous) return "unanimous";
  if (d.without_vote) return "no vote";
  return "—";
}
function outcome(o) {
  if (!o) return '<span class="badge">roll-call</span>';
  return `<span class="badge ${GOOD.includes(o) ? "badge-vote" : "badge-failed"}">${esc(o)}</span>`;
}
function subject(s) {
  const t = (s || "").replace(/^The CHA\S*\s+(?:then\s+)?put\s+to\s+the\s+vote\s+/i, "Put to the vote: ");
  return t.length > 260 ? "…" + t.slice(-260) : t;
}
function rollHTML(r, who = "") {
  const link = (x) => `<a href="#view=delegation&d=${encodeURIComponent(x)}">${x === who ? `<mark>${esc(x)}</mark>` : esc(x)}</a>`;
  const row = (label, xs) => `<div><b>${label} (${xs.length}):</b> ${xs.map(link).join(", ") || "—"}</div>`;
  return `<details class="roll"${who ? " open" : ""}><summary>Roll-call${r.complete ? "" : " · list incomplete in the OCR, check the scan"}</summary>
    ${row("For", r.yes)}${row("Against", r.no)}${row("Abstaining", r.abstentions)}</details>`;
}
const HOW = { for: "For", against: "Against", abstained: "Abstained" };
function decisionsTable(ds, withArticle = true, who = "") {
  if (!ds.length) return '<p class="muted">No votes found.</p>';
  return `<table class="data"><thead><tr><th>Date</th><th>Record</th><th>What was put to the vote</th><th>Outcome</th>
    <th class="num">For–ag.–abst.</th>${who ? `<th>${esc(who)}</th>` : ""}${withArticle ? "<th>Art.</th>" : ""}</tr></thead><tbody>${ds.map((d) => `
    <tr><td class="num nowrap">${esc(d.meeting_date || "")}</td>
      <td class="nowrap">${recLink(d.symbol, d.segment_id, `${d.symbol}, ${d.para ? `para. ${d.para}` : `p. ${d.page_start}`}`)}</td>
      <td class="subj">${esc(subject(d.subject))}${d.context ? `<div class="xnote">After: “…${esc(d.context)}”</div>` : ""}${d.proposers.length ? `<div class="chips">${d.proposers.map(delegLink).join("")}</div>` : ""}
        ${d.roll_call ? rollHTML(d.roll_call, who) : ""}</td>
      <td>${outcome(d.outcome)}</td><td class="num nowrap">${figures(d)}</td>
      ${who ? `<td class="nowrap"><b>${HOW[d.delegation_vote] || "—"}</b></td>` : ""}
      ${withArticle ? `<td>${d.final_article ? artLink(d.final_article, d.article_instrument) : ""}</td>` : ""}</tr>`).join("")}</tbody></table>`;
}
function amendmentsTable(as) {
  if (!as.length) return '<p class="muted">No amendments cited by symbol.</p>';
  return `<table class="data"><thead><tr><th>Document</th><th>Proposed by</th><th>Articles</th><th>Cited</th><th>Decision</th></tr></thead>
    <tbody>${as.map((a) => `<tr>
      <td class="nowrap">${docLink(a.symbol)}</td>
      <td>${a.proposers.length ? `<div class="chips">${a.proposers.map(delegLink).join("")}</div>` : '<span class="muted">not named</span>'}</td>
      <td><div class="chips">${a.articles.slice(0, 4).map(([i, n]) => artLink(n, i)).join("")}</div></td>
      <td class="num">${a.mentions}× · ${a.records.length} rec.<br><span class="muted">${esc(a.first || "")}${a.last && a.last !== a.first ? ` – ${esc(a.last)}` : ""}</span></td>
      <td>${a.decisions.map((d) => `<div>${outcome(d.outcome)} ${figures(d)} <span class="muted">${recLink(d.symbol, d.segment_id)}</span></div>`).join("") || '<span class="muted">—</span>'}</td>
    </tr>`).join("")}</tbody></table>`;
}
function diffHTML(ops) {
  return ops.map(([op, t]) => (op === "eq" ? esc(t) : op === "del" ? `<del>${esc(t)}</del>` : `<ins>${esc(t)}</ins>`)).join(" ");
}
function bars(items, label, value, href) {
  const max = Math.max(1, ...items.map(value));
  return `<div class="bars">${items.map((x) => `<a class="bar-row" href="${href(x)}"><span class="bar-label">${esc(label(x))}</span>
    <span class="bar"><span style="width:${(100 * value(x)) / max}%"></span></span><span class="num">${value(x)}</span></a>`).join("")}</div>`;
}
function section(title, body, note = "", id = "") {
  return `<section class="xsection"${id ? ` id="${esc(id)}"` : ""}><h3 class="serif">${title}</h3>${note ? `<p class="xnote">${note}</p>` : ""}${body}</section>`;
}

// ---------- articles ----------
async function renderArticles(h) {
  const my = ++viewToken;
  const inst = INSTR[h.get("i")] ? h.get("i") : "UDHR";
  const arts = await getJSON("/api/articles?instrument=" + inst);
  if (my !== viewToken) return;
  const tabs = Object.keys(INSTR).map((i) => `<a class="tab${i === inst ? " on" : ""}" href="#view=articles&i=${i}">${i}</a>`).join("");
  $("articles-page").innerHTML = `
    <div class="folio accent">Articles</div>
    <h2 class="serif page-title">${inst === "UDHR" ? "The Declaration" : "The " + inst}, article by article</h2>
    <div class="tabs">${tabs}</div>
    <p class="page-lede">For each article: its text at each drafting stage, the meetings that debated it, who spoke, the votes and the amendments.</p>
    <div class="art-grid">${arts.map((a) => `
      <a class="art-card" href="#view=article&i=${inst}&n=${a.n}">
        <span class="art-n">${a.n}</span>
        <span class="art-title serif">${esc(a.title)}</span>
        <span class="art-stats">${a.speeches} speeches · ${a.records} records · ${a.decisions} votes</span>
        <span class="art-drafts">${a.drafts.map((d) => { const [st, k] = d.split(":"); return `${STAGE_SHORT[st]} ${k}`; }).join(" → ") || "no draft text matched yet"}</span>
      </a>`).join("")}</div>
    ${inst === "UDHR" ? "" : `<p class="xnote">The drafts shown are the Commission's texts from its Geneva session (December 1947:
      its working group's, E/CN.4/56, and its own, E/600) to 1954 (E/2573, as the Secretary-General's annotations, A/2929, reprint
      them), each as its session's report prints it. Speeches are tagged from the Drafting Committee's debate on the Geneva draft (May 1948), the Commission's sessions of
      1949–54 (by the numbering of the draft each worked from and its report's lists of meetings) and the Third Committee's of
      1954–66, where the record or the chair names the covenant and the article.</p>`}
    <p class="xnote">Each stage numbered the articles differently. Drafts are matched to the final articles by comparing
      their texts (UN documents only), directly or through the next stage's version; the 1947 texts are matched by hand. A
      draft without a clear match is left out rather than guessed. A speech is tagged with an article when the record's
      heading, or the chair, names it. The 1947–48 meetings moved from one text to the next and took up the draft Covenant
      too: for them the text each meeting worked from is read from its record.</p>`;
}

async function renderArticle(inst, n) {
  const my = ++viewToken;
  $("article-page").innerHTML = '<p class="muted">Loading…</p>';
  const [a] = await Promise.all([getJSON(`/api/article?instrument=${inst}&n=${n}`), titles()]);
  if (my !== viewToken) return;
  const meetings = a.meetings.filter((m) => m.speeches > 0);
  const docs = a.meetings.filter((m) => !(m.speeches > 0));
  const base = `#view=article&i=${inst}&n=`;
  const evo = a.evolution.map((e) => `
    <li class="evo-step${e.stage === "final" ? " final" : ""}">
      <div class="evo-head"><span class="folio">${esc(e.date || "")}</span>
        <span class="evo-stage">${esc(e.label || STAGE_SHORT[e.stage])}</span>
        <span class="muted">${e.stage === "final" ? "article" : "draft article"} ${esc(e.draft_article)} · ${docLink(e.symbol)}${e.page ? `, p. ${e.page}` : ""}</span>
        ${e.also && e.also.length ? `<span class="muted evo-also">· also holds ${e.also.map((x) => `<a href="${base}${x}">art. ${x}</a>`).join(", ")}</span>` : ""}</div>
      <div class="evo-text">${e.diff ? diffHTML(e.diff) : esc(e.text)}</div>
    </li>`).join("");
  const prevNext = `<div class="art-nav">${n > 1 ? `<a href="${base}${n - 1}">← Art. ${n - 1}</a>` : "<span></span>"}
    <a href="#view=articles&i=${inst}">All ${inst} articles</a>${n < INSTR[inst].count ? `<a href="${base}${n + 1}">Art. ${n + 1} →</a>` : "<span></span>"}</div>`;
  $("article-page").innerHTML = `
    ${prevNext}
    <div class="folio accent">${esc(INSTR[inst].name)} · Article ${n}</div>
    <h2 class="serif page-title">${esc(a.title)}</h2>
    <blockquote class="final-text serif">${esc(a.final_text)}</blockquote>
    <p class="page-lede"><a class="btn btn-ghost" href="#view=search&instrument=${inst}&article=${n}&kind=speech">Search the ${a.delegations.reduce((s, d) => s + d.speeches, 0)} speeches on this article →</a></p>
    ${section("How the text changed", `<label class="xtoggle"><input type="checkbox" id="evo-changes" checked> Mark changes from the previous stage</label>
      <ol class="evo" id="evo">${evo}</ol>`,
      "Draft texts are the OCR of the UN documents; a marked change can be an OCR error. Stages with no matched draft are not shown.")}
    ${section(`Where it was debated <span class="muted">(${meetings.length} meetings)</span>`, meetings.length ? `<ol class="timeline">${meetings.map((m) => `
      <li><span class="tl-date num">${esc(dateLabel(m.meeting_date) || "undated")}</span>
        <div class="tl-body">${recLink(m.symbol, m.first_id, m.symbol, { instrument: inst, article: String(n), symbol: m.symbol })}
          <span class="muted">· ${esc(shortBody(m.body))}${m.draft_numbers ? ` · as draft art. ${esc(m.draft_numbers)}` : ""} · ${m.speeches} speeches</span>
          <div class="chips">${m.delegations.slice(0, 14).map(delegLink).join("")}</div></div></li>`).join("")}</ol>` : '<p class="muted">No meeting tagged with this article yet.</p>')}
    ${a.topics && a.topics.length ? section("General debate on its question", `<ul class="plain-list">${a.topics.map((t) => `
      <li><a href="#view=search&topic=${encodeURIComponent(t.topic)}&kind=speech">${esc(t.label)}</a>
        <span class="muted">· ${t.speeches} speeches in ${t.records} records</span></li>`).join("")}</ul>`,
      "Speeches in general debates on the question this article settled, which no article tag holds: chosen by a classifier and checked on a sample. They may range beyond the article.") : ""}
    ${docs.length ? section(`Documents on this article <span class="muted">(${docs.length})</span>`, `<ol class="timeline">${docs.map((d) => `
      <li><span class="tl-date num">${esc(dateLabel(d.meeting_date) || "undated")}</span>
        <div class="tl-body">${recLink(d.symbol, d.first_id, d.symbol, { instrument: inst, article: String(n) })}
          <span class="muted">${[d.body ? shortBody(d.body) : "", d.doc_type && d.doc_type !== "document" ? d.doc_type.replace(/_/g, " ") : "",
            d.draft_numbers ? `as draft art. ${d.draft_numbers.replace(/,/g, ", ")}` : ""].filter(Boolean).map((x) => `· ${esc(x)}`).join(" ")}</span></div></li>`).join("")}</ol>`) : ""}
    ${section(`Votes <span class="muted">(${a.decisions.length})</span>`, decisionsTable(a.decisions, false),
      "Read from the records: the clause before “was adopted/rejected”, with the figures. Summary records paraphrase; check the record.")}
    ${section(`Amendments cited <span class="muted">(${a.amendments.length})</span>`, amendmentsTable(a.amendments),
      "Documents the debate on this article cites as an amendment or proposal. The proposer is the delegation the record names with it.")}
    ${section("Who spoke", bars(a.delegations.slice(0, 30), (d) => d.delegation, (d) => d.speeches,
      (d) => `#view=search&instrument=${inst}&article=${n}&delegation=${encodeURIComponent(d.delegation)}&kind=speech`),
      "Select a delegation to read its speeches on this article.")}
    ${prevNext}`;
  $("evo-changes").addEventListener("change", (e) => $("evo").classList.toggle("plain", !e.target.checked));
}

// ---------- delegations ----------
async function renderDelegations() {
  const my = ++viewToken;
  const ds = await getJSON("/api/actors");
  if (my !== viewToken) return;
  $("delegations-page").innerHTML = `
    <div class="folio accent">Delegations</div>
    <h2 class="serif page-title">Who spoke, and how they voted</h2>
    <p class="page-lede">States and organisations with speeches in the records. Open one for its delegates, the articles it spoke on,
      the amendments it proposed and its roll-call votes.</p>
    <input type="search" id="deleg-filter" class="xfilter" placeholder="Filter…" aria-label="Filter delegations">
    <table class="data" id="deleg-table"><thead><tr><th>Delegation</th><th class="num">Speeches</th><th class="num">Delegates</th>
      <th class="num">Records</th><th class="num">Roll-calls</th></tr></thead><tbody>${ds.map((d) => `
      <tr data-name="${esc(d.delegation.toLowerCase())}"><td><a href="#view=delegation&d=${encodeURIComponent(d.delegation)}">${esc(d.delegation)}</a></td>
        <td class="num">${d.speeches}</td><td class="num">${d.speakers}</td><td class="num">${d.records}</td><td class="num">${d.roll_calls}</td></tr>`).join("")}
    </tbody></table>`;
  $("deleg-filter").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll("#deleg-table tbody tr").forEach((tr) => (tr.hidden = q && !tr.dataset.name.includes(q)));
  });
}

async function renderDelegation(d, sp) {
  const my = ++viewToken;
  $("delegation-page").innerHTML = '<p class="muted">Loading…</p>';
  const [a] = await Promise.all([getJSON(`/api/actor?delegation=${encodeURIComponent(d)}${sp ? `&speaker=${encodeURIComponent(sp)}` : ""}`), titles()]);
  if (my !== viewToken) return;
  const base = `#view=delegation&d=${encodeURIComponent(d)}`;
  const searchHref = `#view=search&delegation=${encodeURIComponent(d)}${sp ? `&speaker=${encodeURIComponent(sp)}` : ""}`;
  const voted = a.roll_calls || [];
  const tally = { yes: 0, no: 0, abstained: 0 };
  voted.forEach((v) => tally[v.voted]++);
  $("delegation-page").innerHTML = `
    <div class="art-nav"><a href="#view=delegations">← All delegations</a>${sp ? `<a href="${base}">${esc(d)}</a>` : ""}<span></span></div>
    <div class="folio accent">${sp ? `Delegate of ${esc(d)}` : "Delegation"}</div>
    <h2 class="serif page-title">${esc(sp ? nameCase(sp) : d)}</h2>
    <p class="page-lede"><a class="btn btn-ghost" href="${searchHref}">Read the ${a.speakers.reduce((s, x) => s + x.speeches, 0)} speeches →</a></p>
    ${sp ? "" : section("Delegates", `<table class="data"><thead><tr><th>Name (as the records print it)</th><th class="num">Speeches</th><th class="num">Records</th><th>First – last</th></tr></thead>
      <tbody>${a.speakers.map((s) => `<tr><td><a href="${base}&sp=${encodeURIComponent(s.speaker)}">${esc(nameCase(s.speaker))}</a></td>
        <td class="num">${s.speeches}</td><td class="num">${s.records}</td><td class="num nowrap">${esc(s.first || "")} – ${esc(s.last || "")}</td></tr>`).join("")}</tbody></table>`,
      "Names come from the attendance lists and the speeches; one person can appear under two spellings the OCR could not reconcile.")}
    ${section("Sessions", bars(a.sessions, (s) => `${shortBody(s.body)} — ${s.session || ""}`, (s) => s.speeches,
      (s) => `${searchHref}&session=${encodeURIComponent(`${s.body} / ${s.session}`)}`))}
    ${section("Articles spoken on", a.articles.length ? bars(a.articles, (x) => `${x.instrument} art. ${x.n} — ${x.title}`, (x) => x.speeches,
      (x) => `#view=search&instrument=${x.instrument}&article=${x.n}&delegation=${encodeURIComponent(d)}${sp ? `&speaker=${encodeURIComponent(sp)}` : ""}`) : '<p class="muted">No speech tagged with an article.</p>')}
    ${sp ? "" : section(`Amendments proposed <span class="muted">(${a.amendments.length})</span>`, amendmentsTable(a.amendments))}
    ${sp ? "" : section(`Votes on its proposals <span class="muted">(${a.proposed.length})</span>`, decisionsTable(a.proposed),
      "Decisions whose subject names this delegation's amendment or proposal.")}
    ${sp ? "" : section(`Roll-call votes <span class="muted">(${voted.length}: ${tally.yes} for, ${tally.no} against, ${tally.abstained} abstaining)</span>`,
      voted.length ? `<table class="data"><thead><tr><th>Date</th><th>Record</th><th>What was put to the vote</th><th>Its vote</th><th>Outcome</th><th class="num">For–ag.–abst.</th></tr></thead><tbody>${voted.map((v) => `
        <tr><td class="num nowrap">${esc(v.meeting_date || "")}</td><td class="nowrap">${recLink(v.symbol, v.segment_id)}</td><td class="subj">${esc(subject(v.subject))}</td>
          <td><span class="vote-${v.voted}">${v.voted === "yes" ? "for" : v.voted === "no" ? "against" : "abstained"}</span></td>
          <td>${outcome(v.outcome)}</td><td class="num">${figures(v)}</td></tr>`).join("")}</tbody></table>` : '<p class="muted">Not found in any roll-call.</p>')}`;
}

// ---------- the vote table ----------
const csvCell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
let votesOffset = 0;
async function renderVotes(h, append = false) {
  const my = ++viewToken;
  await titles();
  const p = new URLSearchParams();
  let vi = INSTR[h.get("vi")] ? h.get("vi") : "";  // (an unknown instrument or article number in the address is left out)
  const va = /^\d{1,2}$/.test(h.get("va") || "") && +h.get("va") >= 1 && +h.get("va") <= INSTR[vi || "UDHR"].count ? h.get("va") : "";
  if (va && !vi) vi = "UDHR";
  const f = { instrument: vi, article: va, outcome: h.get("vo") || "", roll: h.get("vr") || "", figures: h.get("vf") || "", delegation: h.get("vd") || "" };
  for (const [k, v] of Object.entries(f)) if (v) p.set(k, v);
  votesOffset = append ? votesOffset : 0;
  p.set("offset", votesOffset);
  const d = await getJSON("/api/decisions?" + p);
  if (my !== viewToken) return;
  if (!append) {
    $("votes-page").innerHTML = `
      <div class="folio accent">Votes</div>
      <h2 class="serif page-title">Every vote in the records</h2>
      <p class="page-lede">What was put to the vote, the outcome and the figures, as the records report them; roll-calls with each delegation's vote.</p>
      <div class="xfilters">
        ${instrumentSelect("vf-instrument", f.instrument)}
        ${articleSelect("vf-article", f.instrument, f.article)}
        <select id="vf-delegation" aria-label="Delegation"><option value="">Any delegation</option>${delegationNames.map((n) =>
          `<option value="${esc(n)}"${n === f.delegation ? " selected" : ""}>${esc(n)}</option>`).join("")}</select>
        <select id="vf-outcome" aria-label="Outcome"><option value="">Any outcome</option><option value="adopted">adopted</option><option value="failed">rejected or defeated</option>
          <option value="accepted">accepted</option><option value="approved">approved</option></select>
        <label><input type="checkbox" id="vf-roll"> roll-calls only</label>
        <label><input type="checkbox" id="vf-figures"> with figures</label>
        <span class="folio" id="votes-count"></span>
        <button type="button" class="btn btn-ghost" id="votes-export-csv" title="Export filtered votes as CSV">↓ CSV</button>
        <button type="button" class="btn btn-ghost" id="votes-export-json" title="Export filtered votes as JSON">↓ JSON</button>
      </div>
      ${f.delegation ? `<p class="xnote">The records print how each delegation voted only in roll-calls, so these are the roll-calls that name ${esc(f.delegation)}.</p>` : ""}
      <div id="votes-table"></div><button id="votes-more" class="btn btn-ghost more" type="button" hidden>More votes</button>`;
    $("vf-outcome").value = f.outcome;
    $("vf-roll").checked = !!f.roll;
    $("vf-figures").checked = !!f.figures;
    const upd = () => {
      if ($("vf-article").value && !$("vf-instrument").value) $("vf-instrument").value = "UDHR";
      location.hash = new URLSearchParams({ view: "votes", ...Object.fromEntries(Object.entries({
        vi: $("vf-instrument").value, va: $("vf-article").value, vd: $("vf-delegation").value, vo: $("vf-outcome").value, vr: $("vf-roll").checked ? "1" : "", vf: $("vf-figures").checked ? "1" : "",
      }).filter(([, v]) => v)) }).toString();
    };
    ["vf-article", "vf-delegation", "vf-outcome", "vf-roll", "vf-figures"].forEach((id) => $(id).addEventListener("change", upd));
    $("vf-instrument").addEventListener("change", () => { $("vf-article").value = ""; upd(); });
    $("votes-more").addEventListener("click", () => renderVotes(readHash(), true));
    const exportVotes = async (fmt) => {
      const ep = new URLSearchParams(p);
      ep.set("offset", "0");
      ep.set("limit", "2000");
      const all = await getJSON("/api/decisions?" + ep);
      if (fmt === "json") {
        return download("travaux-votes.json", JSON.stringify(all, null, 2), "application/json;charset=utf-8");
      }
      const hdr = ["meeting_date", "symbol", "segment_id", "article_instrument", "final_article", "outcome", "yes", "no", "abstentions", "unanimous", "delegation_vote", "proposers", "subject"];
      const lines = [hdr.join(","), ...all.results.map((r) => [
        r.meeting_date, r.symbol, r.segment_id, r.article_instrument, r.final_article, r.outcome,
        r.yes, r.no, r.abstentions, r.unanimous ? 1 : "", r.delegation_vote || "", (r.proposers || []).join("|"), r.subject,
      ].map(csvCell).join(","))];
      download("travaux-votes.csv", "\ufeff" + lines.join("\n") + "\n", "text/csv;charset=utf-8");
    };
    $("votes-export-csv").addEventListener("click", () => exportVotes("csv"));
    $("votes-export-json").addEventListener("click", () => exportVotes("json"));
    $("votes-table").innerHTML = decisionsTable(d.results, true, f.delegation);
  } else {
    const tmp = document.createElement("div");
    tmp.innerHTML = decisionsTable(d.results, true, f.delegation);
    $("votes-table").querySelector("tbody").append(...tmp.querySelectorAll("tbody tr"));
  }
  votesOffset = d.offset + d.results.length;
  $("votes-count").textContent = `${d.total} vote${d.total === 1 ? "" : "s"}`;
  $("votes-more").hidden = votesOffset >= d.total;
}

// ---------- amendments ----------
async function renderAmendments(h) {
  const my = ++viewToken;
  await titles();
  let inst = INSTR[h.get("ai")] ? h.get("ai") : "";
  const art = /^\d{1,2}$/.test(h.get("aa") || "") && +h.get("aa") >= 1 && +h.get("aa") <= INSTR[inst || "UDHR"].count ? h.get("aa") : "";
  if (art && !inst) inst = "UDHR";
  const proposer = h.get("ap") || "";
  const aq = h.get("aq") || "";
  const q = new URLSearchParams(Object.entries({ instrument: inst, article: art, proposer, q: aq }).filter(([, v]) => v));
  // 100 at a time: all 2,500 at once were 740 KB and some 40,000 elements
  const pageQuery = (offset) => new URLSearchParams([...q, ["limit", "100"], ["offset", String(offset)]]);
  const first = await getJSON("/api/amendments?" + pageQuery(0));
  if (my !== viewToken) return;
  const as = first.results;
  $("amendments-page").innerHTML = `
    <div class="folio accent">Amendments</div>
    <h2 class="serif page-title">Amendments and proposals</h2>
    <p class="page-lede">Documents the records cite as an amendment or proposal, with the delegation named with them, the articles
      they were debated under and the votes that name them.</p>
    <div class="xfilters">${instrumentSelect("af-instrument", inst)}${articleSelect("af-article", inst, art)}
      <select id="af-proposer" aria-label="Proposed by"><option value="">Any proposer</option>${delegationNames.map((n) =>
        `<option value="${esc(n)}"${n === proposer ? " selected" : ""}>${esc(n)}</option>`).join("")}</select>
      <input type="search" id="af-q" class="xfilter-inline" value="${esc(aq)}" placeholder="Symbol or state (e.g. L.93)…" aria-label="Filter amendments">
      <span class="folio" id="am-count"></span>
      <button type="button" class="btn btn-ghost" id="am-export-csv" title="Export filtered amendments as CSV">↓ CSV</button>
      <button type="button" class="btn btn-ghost" id="am-export-json" title="Export filtered amendments as JSON">↓ JSON</button>
    </div>
    <div id="am-table">${amendmentsTable(as)}</div>
    <button id="am-more" class="btn btn-ghost more" type="button" hidden>More amendments</button>
    <p class="xnote">Only amendments cited by symbol are listed. Many are named only by their author (“the Cuban amendment”);
      those appear in the vote table, under the delegation.</p>`;
  let shown = as.length;
  const count = () => { $("am-count").textContent = `${shown < first.total ? `${shown} of ` : ""}${first.total} documents`; $("am-more").hidden = shown >= first.total; };
  count();
  $("am-more").addEventListener("click", async () => {
    try {
      const more = await getJSON("/api/amendments?" + pageQuery(shown));
      if (my !== viewToken) return;
      const tmp = document.createElement("div");
      tmp.innerHTML = amendmentsTable(more.results);
      $("am-table").querySelector("tbody").append(...tmp.querySelectorAll("tbody tr"));
      shown += more.results.length;
      count();
    } catch (e) {
      $("am-count").textContent = e.message;
    }
  });
  const exportAmendments = async (fmt) => {
    const all = await getJSON("/api/amendments?" + q);
    if (fmt === "json") {
      return download("travaux-amendments.json", JSON.stringify(all, null, 2), "application/json;charset=utf-8");
    }
    const hdr = ["symbol", "proposers", "articles", "mentions", "records_count", "first_date", "last_date", "decisions"];
    const lines = [hdr.join(","), ...all.map((a) => [
      a.symbol, (a.proposers || []).join("|"), (a.articles || []).map(([i, n]) => `${i} ${n}`).join("|"),
      a.mentions, (a.records || []).length, a.first || "", a.last || "",
      (a.decisions || []).map((d) => `${d.outcome || "roll-call"} (${d.symbol})`).join("|"),
    ].map(csvCell).join(","))];
    download("travaux-amendments.csv", "\ufeff" + lines.join("\n") + "\n", "text/csv;charset=utf-8");
  };
  $("am-export-csv").addEventListener("click", () => exportAmendments("csv"));
  $("am-export-json").addEventListener("click", () => exportAmendments("json"));
  const upd = (keepArticle) => {
    if (keepArticle && $("af-article").value && !$("af-instrument").value) $("af-instrument").value = "UDHR";
    const p = new URLSearchParams({ view: "amendments", ...Object.fromEntries(Object.entries({
      ai: $("af-instrument").value,
      aa: keepArticle ? $("af-article").value : "",
      ap: $("af-proposer").value,
      aq: $("af-q").value.trim(),
    }).filter(([, v]) => v)) });
    location.hash = p.toString();
  };
  $("af-instrument").addEventListener("change", () => upd(false));
  $("af-article").addEventListener("change", () => upd(true));
  $("af-proposer").addEventListener("change", () => upd(true));
  $("af-q").addEventListener("change", () => upd(true));
  $("af-q").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); upd(true); } });
}

// ---------- about ----------
// The models on the same fixed items (eval/model_bench_build.py, run.js, model_bench_score.py)
function benchHTML(runs) {
  if (!runs || !runs.length) return "";
  const latest = {};
  for (const r of runs) latest[r.model] = r;
  const models = Object.values(latest);
  const benchName = (m) => ({ opus: "Claude Opus 5.5", sonnet: "Claude Sonnet 5.5", haiku: "Claude Haiku 4.5", fable: "Claude Fable 5.1", "gemini-4-argon": "Gemini 4 Argon" }[m] || m);
  const dates = [...new Set(models.map((r) => r.date))];
  const p = (x) => (x == null ? "–" : `${Math.round(100 * x)}%`);
  const s = models[0].scores;
  const cols = [["speaker", "Speaker on the page image", (t) => p(t.speaker)], ["vote", "Vote: outcome / figures", (t) => `${p(t.outcome)} / ${p(t.figures)}`],
    ["sponsor", "Who proposed it", (t) => p(t.exact)], ["tag", "Speech about its article", (t) => p(t.accuracy)]];
  return `<h3 class="sub">The same items put to each model</h3>
    <p>To follow a model's progress apart from the work done so far, a fixed set of ${cols.map(([k]) => s[k].n).reduce((a, b) => a + b, 0)} items from the project's checked sets is put to each model.
      Scores are shares of items right. The samples are small (${cols.map(([k, l]) => `${s[k].n} ${l.toLowerCase()}`).join(", ")}), so differences of ten points or less are within chance;
      the answers come from checked rounds, in which two blind model judges and the researcher's samples settled each item.</p>
    <table class="data"><thead><tr><th>Model</th>${cols.map(([, l]) => `<th class="num">${esc(l)}</th>`).join("")}</tr></thead><tbody>
      ${models.map((r) => `<tr><td>${esc(benchName(r.model))}</td>${cols.map(([k, , f]) => `<td class="num">${f(r.scores[k])}</td>`).join("")}</tr>`).join("")}
    </tbody></table><p class="note">Run ${dates.map(esc).join(" and ")}, default settings, items version 2.</p>`;
}
// The AI work behind the database (eval/ledger.py): totals from the project's Claude Code and Antigravity transcripts
function ledgerHTML(L) {
  const M = (n) => (n >= 1e9 ? `${(n / 1e9).toFixed(2)} billion` : n >= 1e6 ? `${(n / 1e6).toFixed(1)} million` : n.toLocaleString("en-GB"));
  const short = (m) => m === "gemini-4-argon" ? "Gemini 4 Argon"
    : m.replace(/^claude-/, "Claude ").replace(/-\d{8}$/, "").replace(/-(\d)-(\d)$/, " $1.$2")
        .replace(/\b([a-z])/g, (c) => c.toUpperCase());
  const out = L.tokens.output;
  const bar = (v, max) => `<span class="ledger-bar" style="width:${Math.max(1, Math.round((80 * v) / max))}%"></span>`;
  const kinds = Object.entries(L.by_kind);
  const kmax = Math.max(...kinds.map(([, v]) => v.output));
  const days = Object.entries(L.days);
  const dmax = Math.max(...days.map(([, d]) => d.output));
  const models = Object.keys(L.by_model);
  return `<p>The database was built in ${L.period.active_days} days (${esc(L.period.first)} to ${esc(L.period.last)}) by one
      researcher directing Claude and Gemini models in Claude Code and Google Antigravity: ${L.prompts} prompts, ${L.model_turns.toLocaleString("en-GB")} model
      responses, ${L.agents.toLocaleString("en-GB")} agents in ${L.workflows} multi-agent workflows. The models wrote the pipeline,
      read reports by hand, audited the interface in a live browser, and checked each other blind; the researcher set the method, took the decisions and checked samples.</p>
    <p>In the first phase (22 September – 31 October 2026, Claude Code), <b>Claude Opus 5.5</b>, <b>Claude Sonnet 5.5</b>, <b>Claude Haiku 4.5</b>
      and <b>Claude Fable 5.1</b> built the OCR voting pipeline, segmented speeches and votes, translated the French-only records, built the
      draft-to-final concordances, merged the vision reader's text and ran the audit and repair rounds up to round 120 (the audit of round 109
      measured the tag precision and coverage given under "How good it is"). In the second phase (31 October – 2 November 2026, Google Antigravity),
      <b>Gemini 4 Argon</b> ran rounds 121–127 (the last article tags carried over from a previous debate, judged blind; the chair named in
      more turns; a speaker and a delegation on every speech; the documents' dates and sessions completed), verified 20 user scenarios in a
      live browser, and added the sorting, the citation styles, the CSV/JSON exports, the MCP server over HTTP and the
      <code>travaux-research</code> skill. Claude then reviewed that work and checked its speaker changes blind (round 128).</p>
    <div class="ledger-figures">
      <div><b>${M(out)}</b><span>tokens generated</span></div>
      <div><b>${M(L.tokens.processed)}</b><span>tokens processed (mostly the same context re-read)</span></div>
      <div><b>${L.local.pages.toLocaleString("en-GB")}</b><span>scanned pages OCR'd locally</span></div>
      <div><b>${L.local.jev_answers.toLocaleString("en-GB")}</b><span>classifier answers (Jev)</span></div>
      <div><b>${L.local.commits}</b><span>commits, ${L.local.tests} tests</span></div>
    </div>
    <table class="data"><thead><tr><th>Model</th><th class="num">Responses</th><th class="num">Tokens generated</th></tr></thead><tbody>
      ${Object.entries(L.by_model).map(([m, v]) => `<tr><td>${esc(short(m))}</td><td class="num">${v.turns.toLocaleString("en-GB")}</td><td class="num">${M(v.output)}</td></tr>`).join("")}
    </tbody></table>
    <table class="data"><thead><tr><th>Kind of work</th><th class="num">Responses</th><th>Share of the tokens generated</th></tr></thead><tbody>
      ${kinds.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num">${v.turns.toLocaleString("en-GB")}</td><td>${bar(v.output, kmax)} ${Math.round((100 * v.output) / out)}%</td></tr>`).join("")}
    </tbody></table>
    <div class="ledger-days" aria-label="Tokens generated per day, by model">
      ${days.map(([d, x]) => `<div class="ledger-day" title="${esc(d)}: ${M(x.output)} generated, ${x.prompts} prompts">
        ${models.map((m, i) => `<span class="ledger-seg m${i}" style="height:${(100 * (x.output_by_model[m] || 0)) / dmax}%"></span>`).join("")}
        <em>${esc(d.slice(5))}</em></div>`).join("")}
    </div>
    <p class="ledger-legend">${models.map((m, i) => `<span class="ledger-key m${i}"></span>${esc(short(m))}`).join(" ")}</p>
    <p class="note">${L.notes.map(esc).join(" ")} Counted ${esc(L.generated)} by <code>eval/ledger.py</code>.</p>`;
}
// What is new, for readers (the full record of every change is the build log, docs/devlog.md): newest first.
const NEWS = [
  ["4 November 2026", `A 90-second <b>film</b> on what the database is and how far to trust it, here on the About page and at the start of
    the tour. The site also has its own mark, square brackets (text not yet agreed), and its own colour, ink blue.`],
  ["4 November 2026", `<b>Check</b>: paste a text that cites the drafting records, and every UN symbol in it is held against the record
    it names (the document, the page or paragraph, the delegate named, and the quotation before it). The article pages list the
    documents on an article by date.`],
  ["4 November 2026", `<b>Ask</b>, a search by meaning (experimental): put a question in a sentence and get the passages closest to it,
    even in other words. Tested before it was built on 579 claims from two commentaries on the Covenants (the cited record among the
    first ten passages for 82% of them). Also new: a one-minute tour (✦ Tour in the footer), and usage counts without cookies, with
    Google Analytics only if you allow it (About, Privacy). <code>E/CN.4/SR.98/Corr.1</code> corrected: it held the text of
    <code>A/C.3/SR.289</code>, from a mislabelled copy; it is now the corrigendum itself.`],
  ["3 November 2026", "The About page rewritten: a short main page, with the detail in Methods and build log and the instructions for AI assistants on a page of their own."],
  ["2 November 2026", "A fresh audit of the whole database by blind judges: article tags 95% right, speakers on the page images 98%; nine wrong tags removed."],
  ["31 October 2026", "Doubtful article tags removed from procedural lines (157) and from chair turns (612), each change checked blind before it was kept; the chair's turns now carry the chair's name (98.6%)."],
  ["30 October 2026", "Article tags that a passing mention of another article had moved were judged one by one: 139 removed, 18 corrected."],
  ["28 October 2026", "The text of 10,348 pages read again by a vision model, on the Athena GPUs of PLGrid; the French column of bilingual pages kept out of the English text."],
  ["21 October 2026", "<code>A/C.3/L.1355</code> (the Netherlands' amendments to part IV of the draft ICCPR, 1966; cited 56 times in the debates) added from the French original: machine-translated and marked as such."],
];

async function renderAbout() {
  const my = ++viewToken;
  const q = await getJSON("/api/quality");
  if (my !== viewToken) return;
  const c = Object.fromEntries(q.counts.map((x) => [x.corpus, x]));
  const pct = (a, b) => (b ? `${((100 * a) / b).toFixed(1)}%` : "—");
  const g = q.gold_speeches || {};
  const ocr = q.ocr || {};
  const lSeries = q.coverage ? q.coverage.cited.families.filter((f) => /amendments/.test(f.family))
    .reduce((a, f) => ({ distinct: a.distinct + f.distinct, held: a.held + f.held }), { distinct: 0, held: 0 }) : { distinct: 0, held: 0 };
  const mcpUrl = "https://150.254.115.204/travaux-api/mcp";
  const h = readHash();
  // (the instructions for AI assistants and the methods have pages of their own; old links to #view=about&sec=mcp still land there)
  const part = h.get("part") || (h.get("sec") === "mcp" ? "mcp" : "");
  const back = `<p class="about-back"><a href="#view=about">← About</a></p>`;
  if (part === "news") {
    $("about-page").innerHTML = `<div class="folio accent">About</div>${back}
    <h2 class="serif page-title">What is new</h2>
    <p class="page-lede">The changes a reader will notice, newest first. Every change to the data, with how it was measured, is in the
      <a href="#view=about&part=methods">build log</a>.</p>
    <dl class="news">${NEWS.map(([d, t]) => `<dt>${esc(d)}</dt><dd>${t}</dd>`).join("")}</dl>`;
    return;
  }
  if (part === "mcp") {
    $("about-page").innerHTML = `<div class="folio accent">About</div>${back}
    ${section("Use it from your AI assistant (MCP &amp; Claude Skill)", `<p>The database is also exposed as a
      <a href="https://modelcontextprotocol.io/" target="_blank" rel="noopener">Model Context Protocol</a> (MCP) server, so Claude (or any MCP-capable assistant)
      can search speeches, read full meeting records, trace how an article's draft text evolved, inspect a delegation's speeches and roll-call votes, and verify citations directly against the 2,160 UN records instead of relying on memory. Programs and AI agents should use
      this server: the site's own data addresses are for people reading the site, and refuse crawlers and requests from cloud
      servers.</p>
      <p>Six read-only tools are provided: <code>search_travaux</code> (full-text and filter search over speeches, chair turns, votes and paragraphs),
      <code>lookup_travaux</code> (read a meeting record or document in sequence by symbol, e.g. <code>A/C.3/SR.127</code>),
      <code>article_history_travaux</code> (draft evolution, meetings, votes, amendments and top speakers for any UDHR, ICCPR or ICESCR article),
      <code>delegation_travaux</code> (a state or organisation's delegates, articles, amendments and roll-call votes),
      <code>decisions_travaux</code> (votes and roll-calls) and <code>amendments_travaux</code> (cited L-series amendments and proposals).</p>
      <ol class="mcp-steps">
        <li><b>Add the connector (nothing to install).</b> The MCP server is hosted alongside the database API at:
          <div class="cite-box">
            <p class="cite-text"><code>${esc(mcpUrl)}</code></p>
            <div class="cite-actions">
              <button class="cite-copy" type="button" data-copy="${esc(mcpUrl)}">Copy address</button>
            </div>
          </div>
          In <b>Claude (web or desktop)</b>, open <b>Settings → Connectors → Add custom connector</b> and paste the address above.<br>
          In <b>Claude Code</b>, run:
          <pre class="mcp-code">claude mcp add --transport http travaux ${esc(mcpUrl)}</pre>
        </li>
        <li><b>Add the research skill (optional, for Claude).</b> For multi-step drafting-history questions, download
          <a href="skills/travaux-research.zip" download><b>travaux-research.zip</b></a> (or view the plain
          <a href="skills/travaux-research/SKILL.md" target="_blank" rel="noopener"><code>SKILL.md</code></a>). It teaches Claude the database's
          final-numbering concordance (UDHR 1–30, ICCPR 1–53, ICESCR 1–31), the questions of general debate (<code>self_determination</code>, <code>two_covenants</code>, <code>implementation</code>, <code>petitions</code>, <code>federal_clause</code>, <code>territorial_clause</code>, <code>reservations</code>, <code>form_of_bill</code>, <code>general</code>),
          how to distinguish third-person summary records from verbatim plenary records, and how to cite every speech by UN symbol and paragraph/page pinpoint.<br>
          In <b>Claude Desktop or claude.ai</b>: open <b>Settings → Capabilities → Skills → Upload skill</b> and choose <code>travaux-research.zip</code>.<br>
          In <b>Claude Code</b>: place <a href="skills/travaux-research/SKILL.md" target="_blank" rel="noopener"><code>SKILL.md</code></a> in <code>.claude/skills/travaux-research/SKILL.md</code> (project) or <code>~/.claude/skills/travaux-research/SKILL.md</code> (personal).
        </li>
        <li><b>Ask.</b> Once connected, ask in plain language — for example:
          <ul>
            <li><i>“Trace how the right to change one's religion in Article 18 of the UDHR was debated in 1948, which amendments were put to the vote, and how the roll-call went.”</i></li>
            <li><i>“Compare the arguments of France (Cassin) and Lebanon (Malik) on Article 1 of the UDHR, with exact UN document symbols and page or paragraph pinpoints.”</i></li>
            <li><i>“How did draft Article 19 of the ICCPR (freedom of expression) evolve from the 1947 Geneva working group to the Third Committee's adoption in 1961?”</i></li>
          </ul>
        </li>
      </ol>
      <p><b>Run it yourself (local stdio).</b> If you have a local copy of this repository and <code>data/travaux.sqlite3</code>, you can also run the zero-dependency Python MCP server locally over stdio in Claude Desktop's <code>claude_desktop_config.json</code>:</p>
      <pre class="mcp-code">{\n  "mcpServers": {\n    "travaux": {\n      "command": "python3",\n      "args": ["/ABSOLUTE/PATH/TO/travaux/mcp/travaux_mcp.py"]\n    }\n  }\n}</pre>`, "", "about-mcp")}
`;
    return;
  }
  if (part === "methods") {
    $("about-page").innerHTML = `<div class="folio accent">About</div>${back}
    <h2 class="serif page-title">Methods and build log</h2>
    <p class="page-lede">The full account behind the short version on the About page: every quality figure, how each layer is made,
      the AI work that built the database, and the mistakes found on the way.</p>
    ${section("Quality, in detail", `<ul>
      <li><b>OCR</b>: ${ocr.all ?? "—"}% of characters wrong overall, measured on ${q.ocr_docs || "—"} documents against a
        retyped edition (typed summary records ${ocr["1947-48 typed summary records"] ?? "—"}%, typed documents
        ${ocr["1947-48 typed documents/reports"] ?? "—"}%, printed records ${ocr["1948 printed (GAOR, EN/FR columns)"] ?? "—"}%).</li>
      <li><b>Completeness</b>: ${q.completeness ?? "—"}% of the retyped edition's sentences are found in this text (UDHR).</li>
      ${q.tag_precision && Object.keys(q.tag_precision).length ? `<li><b>Article tags</b>: checked on samples by blind judges (two language models, a third on their splits), ${Object.entries(q.tag_precision)
        .map(([k, v]) => `${v.correct} of ${v.checked} ${{UDHR: "UDHR tags of 1948", "UDHR 1947-48": "UDHR tags of 1947–48 (Drafting Committee, Geneva working group)",
          "Covenant 1948": "ICCPR tags of the Drafting Committee's debate on the Geneva draft Covenant (May 1948)",
          "Geneva plenary 1947": "UDHR and ICCPR tags of the Commission's Geneva debate on both texts (December 1947)",
          Covenants: `Covenant tags of the Third Committee (1954–66${v.covers && v.covers.length ? `; the latest check: ${v.covers.join(", ")}` : ""})`,
          "Covenants CHR": `Covenant tags of the Commission (1949–54${v.covers && v.covers.length ? `; the latest check: ${v.covers.join(", ").replace(/-/g, "–")}` : ""})`}[k] || k}`).join(", ")} are about the article they are tagged with.</li>` : ""}
      ${q.audit ? `<li><b>Overall audit</b> (${q.audit.checked}): on a fresh sample from every kind of record, ${q.audit.precision.correct} of
        ${q.audit.precision.checked} tags were right (${Math.round(q.audit.precision.weighted * 100)}% ± ${Math.round(q.audit.precision.half_interval * 100)} weighted by
        each kind's share of the tags). Coverage${q.audit.coverage.round && q.audit.coverage.round !== q.audit.round ? ` (measured again on ${q.audit.coverage.checked})` : ""}: about ${Math.round(q.audit.coverage.overall * 100)}% of the speeches about one article are tagged
        (${Math.round(q.audit.coverage.within_tagged_records * 100)}% in the meetings that have tags); the rest have no heading or chair naming
        the article, a number the concordance does not map, or a tag the classifier dropped.${q.audit.coverage.pooled ? ` Pooled over the
        last ${q.audit.coverage.pooled.rounds.length} measurements, which vary with their small samples: ${Math.round(q.audit.coverage.pooled.overall * 100)}%
        (${Math.round(q.audit.coverage.pooled.within_tagged_records * 100)}% in the meetings that have tags).` : ""}${q.audit.previous ? ` The previous audit
        (${q.audit.previous.checked}, before the fixes it led to) found ${Math.round(q.audit.previous.precision.weighted * 100)}% and
        ${Math.round(q.audit.previous.coverage.overall * 100)}%.` : ""}${q.audit.reports ? ` The reports' paragraphs, tagged by
        section as read by hand: ${q.audit.reports.correct} of ${q.audit.reports.checked} right.` : ""}</li>` : ""}
      <li><b>Speakers</b>: no errors in the reference sets: ${Object.entries(g).map(([k, v]) => `${v} speeches (${k === "images" ? "checked on the page images" : "checked against the text"})`).join(", ")}.
        On a fresh sample of 150 speeches from every kind of record, read from the page images by two readers (2 November 2026),
        147 had the right speaker and delegation; the 3 wrong were in the 1946–48 plenary records (two names misread by the OCR,
        one line of a list of members taken for a speech).</li>
      <li><b>Division into speeches</b>: on 117 random pages compared with their images (2 November 2026), 82 (70%) had no
        error at all; 14 of the 517 turns that start on them were left inside the speech before, and the commonest other
        errors were a decision, heading or footnote left inside a speech, and a passage in no segment.</li></ul>`, "", "about-quality-detail")}
    ${section("How it is made, in detail", `<ul>
      <li><b>Text.</b> A vision model (Chandra OCR 2, run on the PLGrid grant's GPUs) read every page; its text is used on the pages
        where it agrees in length with the OCR engines' reading and the page is in one column (10,348 pages). Elsewhere four OCR
        engines (the UN's own text layer, Tesseract, Apple Vision) read the page, the best reading is corrected word by word by the
        majority of the engines, and misreadings every engine shares are corrected from the corpus's own word frequencies. In the
        1948 bilingual printed records the French column is set aside. Speakers' names at the opening of a turn are checked against
        the OCR engines' readings and the session's attendance lists.</li>
      <li><b>Speakers.</b> Each speech opening ("Mr. CASSIN (France) said…") is read by every engine and matched against the
        attendance lists of the whole session. Delegates of organisations and officials of the Secretariat are taken as printed.</li>
      <li><b>Articles.</b> Each drafting stage numbered the articles differently. Draft numbers are mapped to the final articles
        by comparing the texts of the drafts with the adopted texts. A passage is tagged only where the numbering is certainly
        that instrument's; where it is not (the early meetings discussed the draft Declaration and draft Covenant together),
        the draft number is kept but no final article is given. The 1947–48 meetings moved from one text to the next (the
        Secretariat's outline, Cassin's drafts, the Drafting Committee's articles, the Geneva text) and, in May 1948, took up the
        Geneva draft Covenant first: the text each meeting worked from is read from its record, and those texts' articles are
        matched to the final ones by hand (the draft Covenant's to the ICCPR's). In Geneva (December 1947) the Commission took
        up a Declaration article together with the corresponding Convention article: each passage is numbered by the text
        the record names for it, and a pair by its Declaration article unless a speech names only the Convention's.</li>
      <li><b>Votes.</b> Decisions are read from the records: what was put to the vote, the outcome, the figures ("rejected by
        28 votes to 17" is 17 for, 28 against) and roll-calls, matched to the delegations.</li>
      <li><b>Tools.</b> Language models (Anthropic's Claude and Google's Gemini 4 Argon) read the records, audited the interface and checked one another's work, as "How it was built" below describes. Jev (TypeSafe's System One) is a classification service: it answers yes/no and choice questions about a passage, and its
        probability is stored with the passage. Voyage AI's models (voyage-3-large, rerank-2.5) turn the passages and the questions put to
        Ask into vectors and order Ask's results.</li></ul>`, "", "about-how-made-detail")}
    ${section("Ask: search by meaning", `<p><a href="#view=ask">Ask</a> takes a question or a description in a sentence and returns the
      passages whose meaning is closest to it, even in other words. Every speech, chair turn, vote and document paragraph (69,193 of them) was
      turned into a vector by Voyage AI's voyage-3-large model. A question is turned into a vector by the same model; the 100 closest passages
      are merged with the 100 that an ordinary word search finds for the question's words (reciprocal rank fusion), and Voyage's rerank-2.5
      model orders the merged list by how well each passage answers the question. A text repeated in a draft, its amendments and the adopted
      resolution is shown once. Ask writes no answer: it only orders the UN's own passages.</p>
      <p>How well it works was measured before it was built, on the claims that two commentaries on the Covenants (Nowak on the ICCPR; Saul,
      Kinley and Mowbray on the ICESCR) support with a meeting record: 579 claims, each restated by a language model as a question, with the
      cited record as the answer to find. Written as a sentence, the cited record was among the first ten passages for 82% of the claims (the
      word search, its words joined by OR, 49%; Search as it is, which needs every word, 1%), and the first passage for 55%. Written as two
      to five keywords, it was the other way round: Search found the cited record among the first ten for 45%, Ask for 26%. So Ask is for
      questions, Search for words; and neither finds every passage on a subject. The cited record is only one of the places where a claim
      can be checked, so these figures are lower bounds.</p>`, "", "about-ask")}
    ${section("Sources", `<p>Only UN documents: the meeting records, reports, drafts and amendments of the Commission on Human Rights (with its Drafting
      Committee and working groups), the Economic and Social Council, and the General Assembly and its Third Committee, 1946–66. They were fetched
      from the UN Official Document System by symbol, one request at a time and at least six seconds apart, in September 2026. A few came another way,
      and the harvest logs record each: 22 were saved by hand in a browser from the UN Digital Library; 22 that the Official Document System does not
      serve were taken from the University of Virginia School of Law's public copy of its travaux collection of the Covenants
      (hr-travaux.law.virginia.edu), whose item list also served as a finding aid for what exists; and 11 documents that exist only in French were
      machine-translated (Claude Fable 5.1, each translation compared with the scan by Claude Sonnet 5.5). Translated passages are marked wherever they
      appear, can be left out of any search, and are not UN text: check the French original before quoting.</p>
      <p>Every passage carries its UN symbol and a page or paragraph pinpoint and links to the UN copy. Printed compilations of the travaux (Schabas,
      Saul, Bossuyt) are not used as sources; one of them serves, privately, to measure the OCR (below).</p>`, "", "about-sources")}
    ${q.ledger ? section("How it was built", ledgerHTML(q.ledger) + benchHTML(q.model_bench), "", "about-built") : ""}
    ${q.what_went_wrong ? section("What went wrong", `<p>${esc(q.what_went_wrong.intro)}</p><ul>${q.what_went_wrong.items.map((i) =>
      `<li><b>${esc(i.date)}.</b> ${esc(i.text)}</li>`).join("")}</ul><p>${esc(q.what_went_wrong.outro)}</p>`, "", "about-wrong") : ""}
`;
    const sec = h.get("sec");
    const target = sec && document.getElementById("about-" + sec);
    if (target) setTimeout(() => target.scrollIntoView({ behavior: "smooth", block: "start" }), 30);
    return;
  }
  const a = q.audit;
  $("about-page").innerHTML = `
    <div class="folio accent">About</div>
    <h2 class="serif page-title">What this is, and how far to trust it</h2>
    <p class="page-lede">A speech-level companion to the drafting records of the Universal Declaration of Human Rights
      (1946–48) and the two International Covenants (1949–66), built from the UN's own documents: who spoke, for which
      delegation, on which article, with the page of the UN record beside it.</p>
    <p class="about-tour">New here? <button type="button" class="linklike" data-tour-open>Take the one-minute tour</button> (it is also
      in the footer, ✦ Tour). <a href="#view=about&part=news">What is new</a>: ${esc(NEWS[0][0])}.</p>
    <figure class="about-film" id="about-film">
      <video controls preload="none" playsinline poster="${FILM.poster}" src="${FILM.src}"></video>
      <figcaption>The database in 90 seconds (English subtitles; the narration is voiced with AI, ElevenLabs). The film shows the counts of
        4 November 2026. <details><summary>Transcript</summary><p>The Universal Declaration of Human Rights and the two Covenants were drafted at the United Nations between 1946 and 1966, and the drafting records run to more than eighteen thousand pages. To find who said what, and why a provision reads as it does, one reads them page by page. UN Travaux Préparatoires, an independent resource built from the UN's own documents, divides them into speeches, each with its speaker, delegation, date, article and page.</p><p>Search opens every result in its record, at its page, with a ready citation and a link to the UN copy. Each article can be followed through the drafting: its text at every stage, the meetings that debated it, and every vote, by name where the record gives one. Ask takes a question in plain words and returns the passages closest to it in meaning, even when the delegates used other words.</p><p>Summary records paraphrase the speakers, the text is machine-read, and about one article tag in twenty is wrong: the About page gives every figure, and every passage links to the scan. AI brings new risks, such as invented quotations, and two tools answer them.</p><p>Check holds every citation and quotation in your draft against the record it names. Through the MCP server and the Claude skill, your AI assistant cites the records by symbol and page, instead of from memory. The UN document remains the authority, one click away from every speech.</p></details></figcaption>
    </figure>
    <p class="disclaimer"><b>Not an official United Nations product.</b> This is an independent research resource. It is not produced, endorsed or
      maintained by the United Nations or its Dag Hammarskjöld Library. The documents are the UN's; the passages here are machine-read text of
      them, and the UN copy linked on every passage is the authority.</p>
    ${section("Read with care", `<ul>
      <li><b>Summary records paraphrase</b> what delegates said; they are not verbatim. Plenary records (A/PV, E/PV) are verbatim.</li>
      <li><b>The text is read by machine</b> from scans of the 1940s–60s. Check the scan (linked on every passage) before quoting.</li>
      <li><b>Articles are given in their final numbering</b>, mapped from each session's draft numbering. A speaker can range beyond the
        article a speech is tagged with; about one tag in twenty is wrong, and some speeches about an article carry no tag.</li>
      <li><b>Where one speech ends and the next begins</b> is right for about 97 turns in 100; now and then a footnote, a heading or the
        record's decision sits inside a speech. Where it matters, check the scan.</li>
      <li><b>Most amendments are not here as texts.</b> The UN's document server holds few of the L-series; their sponsors and the votes on
        them are read from the records.</li>
      <li><b>Eleven documents exist only in French</b>; their machine translations are marked wherever they appear and are not UN text.</li>
      <li><b>Ask orders passages by closeness of meaning.</b> It writes no answer and does not find every passage on a subject; for every
        passage with a word, use Search.</li></ul>`, "", "about-care")}
    ${section("How reliable it is", `<table class="data"><thead><tr><th>What</th><th>Checked on</th><th class="num">Right</th></tr></thead><tbody>
      <tr><td>Speaker and delegation</td><td>150 random speeches, read from the page images</td><td class="num">98%</td></tr>
      <tr><td>Division into speeches</td><td>117 random pages: turns that start a segment of their own</td><td class="num">97%</td></tr>
      ${a ? `<tr><td>Article tags</td><td>${a.precision.checked} random tagged passages</td><td class="num">${Math.round(a.precision.weighted * 100)}% ± ${Math.round(a.precision.half_interval * 100)}</td></tr>
      <tr><td>Speeches about one article that carry its tag</td><td>110 random untagged speeches</td><td class="num">about ${Math.round(a.coverage.overall * 100)}%</td></tr>` : ""}
      <tr><td>Questions of general debate</td><td>60 random speeches</td><td class="num">92%</td></tr>
      <tr><td>Ask: the record a commentary cites among the first ten passages</td><td>579 claims from two commentaries on the Covenants,
        put as questions (as a few keywords: 26%)</td><td class="num">82%</td></tr>
      ${ocr.all != null ? `<tr><td>Text</td><td>${q.ocr_docs || "—"} documents of 1947–48 against a retyped edition: characters wrong</td><td class="num">${ocr.all}%</td></tr>` : ""}
      </tbody></table>
      <p class="note">Measured in November 2026 on random samples, by judges who did not see the database's answer: two language models per
        item, reading the records and the page images, and a third where they disagreed. A check by people is under way. Every figure
        in detail: <a href="#view=about&part=methods">Methods and build log</a>.</p>`, "", "about-quality")}
    ${section("What is in it", `<table class="data"><thead><tr><th>Corpus</th><th class="num">Documents</th><th class="num">Speeches</th>
      <th class="num">Tagged with an article</th></tr></thead><tbody>
      ${["UDHR", "Covenants"].filter((k) => c[k]).map((k) => `<tr><td>${k === "UDHR" ? "UDHR, 1946–48" : "ICCPR and ICESCR, 1949–66"}</td>
        <td class="num">${c[k].documents}</td><td class="num">${c[k].speeches}</td><td class="num">${pct(c[k].tagged, c[k].speeches)}</td></tr>`).join("")}</tbody></table>
      <p>Plus ${q.decisions.n.toLocaleString("en-GB")} decisions and votes read from the records (${q.decisions.roll_calls} roll-calls).
        ${q.coverage ? `The database holds ${q.coverage.records.pct}% of the meeting records the UN's guides list. What the speeches cite is less
        complete: ${q.coverage.cited.pct}% of the documents they cite are here, and ${lSeries.distinct ? Math.round((100 * lSeries.held) / lSeries.distinct) : 0}%
        of the amendments.` : ""}</p>`, "", "about-records")}
    ${section("How it is made", `<p>The UN's records of 1946–66 were downloaded once, in September 2026, read from their scans by a vision model
      and OCR engines, divided into speeches, matched to the delegates of each session and to the article under discussion, and their
      votes read. The work was done by one researcher with AI models (Anthropic's Claude and Google's Gemini) writing the code and checking
      the data under his direction; every change to the data was measured on a blind sample before it was kept, and the mistakes found are
      listed. A classification service (Jev, by TypeSafe) checks each article tag; Ask, the search by meaning, uses Voyage AI's embedding
      and re-ranking models. Printed compilations of the travaux are not used as sources. The full account: <a href="#view=about&part=methods">Methods and build log</a>.</p>`, "", "about-how-made")}
    ${section("Use it from your AI assistant", `<p>Claude, or any assistant that speaks the Model Context Protocol, can search the speeches,
      read whole records, trace an article's drafts and check its citations against the UN records directly.
      <a href="#view=about&part=mcp">How to connect it</a>.</p>`, "", "about-mcp-short")}
    ${section("Acknowledgements", `<p>We gratefully acknowledge Polish high-performance computing infrastructure PLGrid (HPC Centers:
      ACK Cyfronet AGH) for providing computer facilities and support within computational grant no. PLG/2026/020181. The
      grant's GPUs (the Athena cluster) read the scans of the records with the vision model whose text the database uses.</p>`, "", "about-acknowledgements")}
    ${section("Licence and privacy", `<p><b>Licence.</b> What this database adds to the documents (the division into speeches, speakers and delegations, the
      article tags and the concordance of drafts, the decisions and votes, the machine translations) is released under
      <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noopener">CC BY-NC-SA 4.0</a>; the code is under the
      <a href="https://polyformproject.org/licenses/noncommercial/1.0.0/" target="_blank" rel="noopener">PolyForm Noncommercial License 1.0.0</a>. The text of the UN documents is
      the UN's and stays under the UN's own terms: each passage links to the UN copy.</p>
      <p><b>Privacy.</b> No accounts and no cookies. The passages you save with ☆ stay in this browser. To see how the site is
      used and where it needs work, it keeps counts, never a profile of anyone. A cookie-free counter (GoatCounter) records which
      view is opened (Search, Ask, Articles and so on), the site a visit came from and the screen size; it never receives the words
      of a search, a question, a filter or the records you open, and it sends nothing when your browser asks not to be tracked (Do
      Not Track, Global Privacy Control). The film on this page plays from the author's site on GitHub Pages (lszoszk.github.io),
      and only once you press play. ${(CFG.analytics || {}).ga4 ? `Google Analytics runs only if you allow it in the banner,
      and receives the same view names. ` : ""}After some minutes of use the site may ask, once, who you are (researcher, student,
      practitioner and so on): one optional, anonymous click. The web server keeps an ordinary access log, in which the words of a
      search appear as part of the address; it is read only as counts (how many people a day). A question put to
      <a href="#view=ask">Ask</a> is sent to Voyage AI, a commercial service, to be matched with the passages; it is not kept in this
      site's logs. A text put to <a href="#view=check">Check</a> is checked on this server and kept nowhere. Nothing is passed on to
      anyone else.</p>
      <div data-consent-ui></div>`, "", "about-licence")}
    ${section("How to cite", `<p><b>Citing a speech or record.</b> Always cite the primary UN document by symbol and paragraph or page pinpoint, as the
      “Copy citation” buttons and the <a href="#view=workspace">Workspace</a> style selector do:</p>
      <ul>
        <li><b>UN standard:</b> <code>E/CN.4/SR.60, p. 10 (Malik, Lebanon)</code> · <code>A/C.3/SR.290, paras. 7–15 (Hoffmeister, Czechoslovakia)</code></li>
        <li><b>Bluebook:</b> <code>U.N. Doc. A/C.3/SR.290, ¶¶ 7–15 (1950) (Hoffmeister, Czechoslovakia)</code></li>
        <li><b>OSCOLA:</b> <code>UN Doc A/C.3/SR.290 (1950) paras 7–15 (Hoffmeister, Czechoslovakia)</code></li>
      </ul>
      <p><b>Citing this database.</b> If UN Travaux Préparatoires helped your research, please also cite the database:</p>
      <div class="cite-box">
        <p class="cite-text" id="cite-apa-text">${esc(SITE_CITATION.apa)}</p>
        <div class="cite-actions">
          <button class="cite-copy" type="button" data-copy-cite="apa">Copy citation</button>
          <button class="cite-copy cite-copy-sub" type="button" data-copy-cite="bibtex">Copy BibTeX</button>
        </div>
      </div>
      ${CFG.contact ? `<p><b>Corrections and feedback:</b> ${contactLink(CFG.contact)}${CFG.author || CFG.affiliation ? `. ${esc([CFG.author, CFG.affiliation].filter(Boolean).join(", "))}.` : ""}</p>` : ""}`, "", "about-cite")}
`;
  window.TravauxAnalytics?.mountPrivacyUi(document.querySelector("#about-page [data-consent-ui]"));
  const sec = h.get("sec");
  if (sec) {
    const target = document.getElementById("about-" + sec);
    if (target) setTimeout(() => target.scrollIntoView({ behavior: "smooth", block: "start" }), 30);
  }
}

// called by setView in app.js
const VIEW_BOX = { articles: "articles-page", article: "article-page", delegations: "delegations-page", delegation: "delegation-page",
  votes: "votes-page", amendments: "amendments-page", about: "about-page" };
function viewError(view, e) {
  $(VIEW_BOX[view]).innerHTML = `<div class="view-error" role="alert"><p>${esc(e.message)}</p>
    <p>${/^The server/.test(e.message) ? '<button class="btn btn-ghost" type="button" data-retry>Try again</button> ' : ""}
    ${view === "article" ? '<a href="#view=articles">All articles</a>' : ""}</p></div>`;
}
function renderExplore(view, h) {
  const run = () => {
    if (view === "articles") return renderArticles(h);
    if (view === "article") return renderArticle(INSTR[h.get("i")] ? h.get("i") : "UDHR", parseInt(h.get("n") || "1", 10));
    if (view === "delegations") return renderDelegations();
    if (view === "delegation") return renderDelegation(h.get("d") || "", h.get("sp") || "");
    if (view === "votes") return renderVotes(h);
    if (view === "amendments") return renderAmendments(h);
    if (view === "about") return renderAbout();
  };
  const result = run();
  const mine = viewToken;  // (each render takes its token before its first await)
  if (result && VIEW_BOX[view]) return result.catch((e) => { if (mine === viewToken) viewError(view, e); });
  return result;
}
