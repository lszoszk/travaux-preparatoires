// Check: the citations of the travaux in a reader's own text, held against the records (api/server.py check_text()).
// The text goes to the server by POST, is checked there and kept nowhere; the page keeps it only while it is open.
const CHECK_SAMPLE = `Malik opposed the Egyptian limitation, arguing that the article "dealt with the rights and freedoms that were above the law and, as it were, outside it" (E/CN.4/SR.60, p. 7 (Malik, Lebanon)). In the Third Committee, Saudi Arabia regretted that the draft covenant "still contained a phrase which he had constantly criticized" (A/C.3/SR.289, para. 40 (Baroody, Saudi Arabia)). Cassin took the same line (E/CN.4/SR.60, p. 12 (Cassin, France)), and Czechoslovakia went further (A/C.3/SR.290, paras. 7–15 (Hoffmeister, Czechoslovakia)). On social security, see A/C.3/SR.729 (14 January 1957), 242.`;
const CHECK_STATUS = {
  ok: ["✓", "checks out"], check: ["?", "look again"], problem: ["✗", "does not match"], not_held: ["–", "not in the database"],
};
const CHECK_ICON = (ok) => (ok === true ? "✓" : ok === false ? "✗" : "?");
let checkSeq = 0;

function checkCiteLink(c, label) {
  const h = new URLSearchParams({ view: "search", open: c.symbol });
  if (c.open) h.set("seg", c.open);
  return `<a class="symref" href="#${h}" data-open="${esc(c.symbol)}"${c.open ? ` data-seg="${esc(c.open)}"` : ""}>${esc(label || c.symbol)}</a>`;
}

function checkRender(text, d) {
  // the text, with each citation (and the quotation it supports) marked and numbered
  const marks = [];
  d.citations.forEach((c, i) => {
    if (c.quote_span) marks.push({ s: c.quote_span[0], e: c.quote_span[1], cls: `ck-quote st-${c.status}`, n: null });
    marks.push({ s: c.start, e: c.end, cls: `ck-cite st-${c.status}`, n: i + 1 });
  });
  marks.sort((a, b) => a.s - b.s);
  let html = "", at = 0;
  for (const m of marks) {
    if (m.s < at) continue;
    html += esc(text.slice(at, m.s));
    const inner = esc(text.slice(m.s, m.e));
    html += m.n ? `<a class="${m.cls}" href="#ck-${m.n}" data-ck="${m.n}">${inner}<sup>${m.n}</sup></a>` : `<span class="${m.cls}">${inner}</span>`;
    at = m.e;
  }
  html += esc(text.slice(at));
  $("check-annotated").innerHTML = html.replace(/\n/g, "<br>");
  $("check-list").innerHTML = d.citations.map((c, i) => {
    const [icon, label] = CHECK_STATUS[c.status];
    const pin = c.pin ? ` · ${c.pin.type === "para" ? "para" : "p"}${c.pin.to !== c.pin.from ? `s. ${c.pin.from}–${c.pin.to}` : `. ${c.pin.from}`}` : "";
    const who = c.who ? ` · ${esc(c.who)}` : "";
    const doc = c.doc ? [dateLabel(c.doc.meeting_date), c.doc.body].filter(Boolean).map(esc).join(" · ") : "";
    return `<li class="ck-card st-${c.status}" id="ck-${i + 1}">
      <div class="ck-head"><span class="ck-n">${String(i + 1).padStart(2, "0")}</span>
        <span class="ck-badge st-${c.status}">${icon} ${label}</span>
        <span class="ck-sym">${c.status === "not_held" ? `<a href="https://undocs.org/${esc(c.symbol)}" target="_blank" rel="noopener">${esc(c.symbol)}</a>` : checkCiteLink(c)}${pin}${who}</span></div>
      ${doc ? `<div class="ck-doc muted">${doc}</div>` : ""}
      ${c.quote ? `<blockquote class="ck-q">“${esc(c.quote)}”</blockquote>` : ""}
      <ul class="ck-checks">${c.checks.map((k) => `<li class="ok-${k.ok}"><span class="ck-i">${CHECK_ICON(k.ok)}</span>${esc(k.note)}${k.segment && k.what !== "document"
        ? ` ${checkCiteLink({ symbol: c.symbol, open: k.segment }, "open")}` : ""}</li>`).join("")}</ul>
      ${c.status !== "not_held" ? `<div class="ck-actions"><a href="https://undocs.org/${esc(c.symbol)}" target="_blank" rel="noopener">UN copy</a></div>` : ""}
    </li>`;
  }).join("") || `<li class="results-empty">No UN symbol found in the text (they look like E/CN.4/SR.60 or A/C.3/SR.290).</li>`;
  $("check-out").hidden = false;
}

async function runCheck() {
  const text = $("check-text").value;
  if (!text.trim()) return;
  const mine = ++checkSeq;
  $("check-status").textContent = "Checking…";
  $("check-status").classList.remove("is-error");
  $("check-submit").disabled = true;
  let d;
  try {
    const r = await fetch(API + "/api/check", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
    d = await r.json();
    if (!r.ok && !d.error) d = { error: `The server answered with an error (${r.status}).` };
  } catch (e) {
    d = { error: "The server did not answer. Check your connection and try again." };
  }
  if (mine !== checkSeq) return;
  $("check-submit").disabled = false;
  if (d.error) {
    $("check-status").textContent = d.error;
    $("check-status").classList.add("is-error");
    $("check-out").hidden = true;
    return;
  }
  const k = d.counts;
  $("check-status").textContent = `${d.citations.length} citation${d.citations.length === 1 ? "" : "s"} · ${k.ok} check out · ${k.check} to look at · ${k.problem} do not match · ${k.not_held} not held`;
  checkRender(text, d);
}

$("check-form").addEventListener("submit", (e) => { e.preventDefault(); runCheck(); });
$("check-text").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); runCheck(); }
});
$("check-sample").addEventListener("click", () => { $("check-text").value = CHECK_SAMPLE; runCheck(); });
document.addEventListener("click", (e) => {
  const a = e.target.closest("[data-ck]");
  if (!a) return;
  e.preventDefault();
  document.getElementById("ck-" + a.dataset.ck)?.scrollIntoView({ behavior: "smooth", block: "center" });
});
