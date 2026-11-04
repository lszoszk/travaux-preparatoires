// Ask: a question in a sentence, answered with the passages that match its meaning (api/server.py ask(); rounds 131-132).
// The question lives in the address (#view=ask&qa=...&qi=...), which the browser keeps and the server never sees.
const ASK_EXAMPLES = [
  { title: "Changing one's religion", tag: "UDHR art. 18",
    q: "Which delegations objected to the freedom to change one's religion or belief?" },
  { title: "God or nature in the Declaration", tag: "UDHR art. 1",
    q: "Should the first article of the Declaration name God or nature as the source of human rights?" },
  { title: "Natural disasters as emergencies", tag: "ICCPR art. 4",
    q: "Can a natural disaster be a public emergency that allows a State to suspend rights?" },
  { title: "Maximum of available resources", tag: "ICESCR art. 2",
    q: "What did delegates mean by the maximum of available resources?" },
  { title: "Colonies and trust territories", tag: "Covenants",
    q: "Arguments for applying the Covenants to colonies and trust territories" },
  { title: "The right to property", tag: "Covenants",
    q: "Why was the right to property left out of the Covenants?" },
];
let askShown = null;  // the question and instrument on the page, so that coming back to Ask does not ask again
let askSeq = 0;

function renderAsk(h) {
  if (!$("ask-examples").children.length) {
    $("ask-examples").innerHTML = ASK_EXAMPLES.map((x, i) => `<li><button type="button" class="ask-example" data-ask-example="${i}">
      <span class="ask-ex-n">${String(i + 1).padStart(2, "0")}</span>
      <span class="ask-ex-body"><span class="ask-ex-title">${esc(x.title)} <span class="chip garnet">${esc(x.tag)}</span></span>
        <span class="ask-ex-q">${esc(x.q)}</span></span></button></li>`).join("");
  }
  const q = h.get("qa") || "";
  const inst = h.get("qi") || "";
  $("ask-q").value = q;
  $("ask-instrument").value = inst;
  if (q && askShown !== q + "\u0000" + inst) runAsk(false);
  if (!q) {
    askShown = null;
    $("ask-results").innerHTML = "";
    $("ask-status").textContent = "";
    $("ask-hint").hidden = true;
  }
}

// Round 132: on two to five keywords Ask finds less than Search; a reader who types a few words is told so.
function askHint(q) {
  const words = q.trim().split(/\s+/).filter(Boolean);
  if (words.length > 4 || /[?]/.test(q)) return ($("ask-hint").hidden = true);
  $("ask-hint").innerHTML = `<strong>Ask works best on a sentence.</strong> For a few words, <a href="#view=search&q=${encodeURIComponent(q)}">Search</a>
    finds more; here, say what you are looking for, e.g. “Who argued for or against ${esc(q)}, and why?”`;
  $("ask-hint").hidden = false;
}

async function runAsk(push = true) {
  const q = $("ask-q").value.trim();
  const inst = $("ask-instrument").value;
  if (!q) return;
  if (push) writeHash({ view: "ask", qa: q, qi: inst }, true);
  const mine = ++askSeq;
  askShown = q + "\u0000" + inst;
  askHint(q);
  $("ask-status").textContent = "Searching…";
  $("ask-status").classList.remove("is-error");
  $("ask-submit").disabled = true;
  let d;
  try {
    const r = await fetch(API + "/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ q, instrument: inst }) });
    d = await r.json();
    if (!r.ok && !d.error) d = { error: `The server answered with an error (${r.status}).` };
  } catch (e) {
    d = { error: "The server did not answer. Check your connection and try again." };
  }
  if (mine !== askSeq) return;
  $("ask-submit").disabled = false;
  if (d.error) {
    askShown = null;
    $("ask-status").textContent = d.error;
    $("ask-status").classList.add("is-error");
    $("ask-results").innerHTML = "";
    return;
  }
  $("ask-status").textContent = `${d.results.length} passages · by closeness to your question`;
  $("ask-results").innerHTML = d.results.length ? d.results.map((x) => {
    const li = hitHTML(x);
    const also = x.also && x.also.length
      ? `<div class="result-prov">The same text also in ${x.also.slice(0, 6).map(esc).join(", ")}${x.also.length > 6 ? ` and ${x.also.length - 6} more` : ""}</div>` : "";
    return also ? li.replace('<div class="result-actions">', `${also}<div class="result-actions">`) : li;
  }).join("") : `<li class="results-empty">Nothing found. Try saying it another way.</li>`;
}

$("ask-form").addEventListener("submit", (e) => { e.preventDefault(); runAsk(); });
$("ask-q").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); runAsk(); }
});
document.addEventListener("click", (e) => {
  const ex = e.target.closest("[data-ask-example]");
  if (!ex) return;
  const x = ASK_EXAMPLES[+ex.dataset.askExample];
  $("ask-q").value = x.q;
  $("ask-instrument").value = "";
  runAsk();
});
