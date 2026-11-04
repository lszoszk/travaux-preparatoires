/* A one-minute tour of UN Travaux Préparatoires (five slides), after HUDOC Researcher's and UNHRDB's.
   Opens by itself on the first visit, when the page opens on Search with nothing asked yet; the "✦ Tour" button of the
   footer (#tour-btn) reopens it from any view. Its figures come from the API (/api/quality), with fixed fallbacks. */
(function () {
  "use strict";
  const DONE_KEY = "travaux-tour-done";
  const fmt = (n) => Number(n).toLocaleString("en-GB");
  const EXAMPLES = ['"freedom of thought"', "religion AND change", "speaker:cassin art:18"];

  const CSS = `
  .tourwrap{position:fixed;inset:0;z-index:400;display:none;align-items:center;justify-content:center;padding:16px;
    background:color-mix(in srgb,var(--ink) 38%,transparent)}
  .tourwrap.open{display:flex}
  .tour-box{width:min(720px,100%);max-height:calc(100vh - 32px);display:flex;flex-direction:column;overflow:hidden;
    background:var(--paper);color:var(--ink);border:1px solid var(--ink);box-shadow:0 3px 0 rgba(36,35,40,.18)}
  .tour-box:focus{outline:none}
  .tour-slides{position:relative;flex:1;overflow:auto;padding:28px 30px 18px}
  .tslide{display:none}.tslide.on{display:block}
  .tour-kicker{font-family:var(--mono);font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin-bottom:10px}
  .tour-h{margin:0 0 12px;font-family:var(--display);font-weight:500;font-size:1.7rem;line-height:1.2}
  .tour-lead{font-family:var(--body);font-size:1rem;line-height:1.6;color:var(--ink-2);max-width:600px}
  .tour-lead code,.tour-list code{font-family:var(--mono);font-size:.85em;background:var(--paper-3);padding:0 3px}
  .tour-stats{display:flex;flex-wrap:wrap;gap:12px 30px;margin:18px 0 10px}
  .tour-stats b{display:block;font-family:var(--display);font-weight:500;font-size:1.5rem}
  .tour-stats span{font-family:var(--mono);font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}
  .tour-cap{margin-top:6px;font-family:var(--mono);font-size:.64rem;color:var(--ink-3)}
  .tour-list{list-style:none;margin:14px 0 0;padding:0}
  .tour-list li{display:grid;grid-template-columns:34px 1fr;gap:2px 10px;padding:8px 0;border-top:1px solid var(--rule)}
  .tour-list li:first-child{border-top:0}
  .tour-list .n{font-family:var(--mono);font-size:.7rem;color:var(--ink-3);padding-top:3px}
  .tour-list b{font-family:var(--body);font-weight:600}
  .tour-list span{font-family:var(--body);color:var(--ink-2)}
  .tour-list .x{font-family:var(--mono);font-size:.6rem;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
  .tour-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
  .tour-chips button,.tour-go a{cursor:pointer;font-family:var(--mono);font-size:.76rem;color:var(--ink-2);
    background:var(--paper-3);border:1px solid var(--rule);padding:4px 9px;text-decoration:none}
  .tour-chips button:hover,.tour-go a:hover{color:var(--accent);border-color:var(--accent)}
  .tour-go{display:flex;flex-direction:column;align-items:flex-start;gap:10px;margin-top:18px}
  .tour-go a{font-size:.86rem;padding:7px 12px}
  .tour-nav{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 30px;border-top:1px solid var(--rule);
    background:var(--paper-2)}
  .tour-nav button{cursor:pointer;background:none;border:0;font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;
    text-transform:uppercase;color:var(--ink-2)}
  .tour-nav #tour-next{color:var(--accent);font-weight:600}
  .tour-dots{display:flex;gap:8px}
  .tour-dots .tdot{width:7px;height:7px;padding:0;border-radius:50%;background:var(--rule)}
  .tour-dots .tdot.on{background:var(--accent)}
  .tour-views .s{display:none}
  @media (max-width:860px){.tour-nav button:not(.tdot){min-height:36px;padding:0 4px}
    .tour-dots{gap:0}.tour-dots .tdot{width:28px;height:32px;padding:12px 10px;background-clip:content-box}}
  @media (max-width:600px){
    .tourwrap{padding:10px}
    .tour-box{max-height:calc(100vh - 20px);max-height:calc(100dvh - 20px)}
    .tour-slides{padding:16px 16px 12px}
    .tour-kicker{font-size:.6rem;margin-bottom:6px}
    .tour-h{font-size:1.2rem;margin-bottom:8px}
    .tour-lead{font-size:.88rem;line-height:1.45}
    .tour-stats{display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;margin:12px 0 4px}
    .tour-stats b{font-size:1.15rem}
    .tour-list{margin-top:8px}
    .tour-list li{grid-template-columns:22px 1fr;padding:6px 0;font-size:.88rem;line-height:1.4}
    .tour-views .d{display:none}.tour-views .s{display:inline}
    .tour-chips{margin-top:10px;gap:6px}
    .tour-chips button{padding:6px 8px;font-size:.7rem}
    .tour-go{gap:8px;margin-top:12px}
    .tour-nav{padding:8px 12px}}
  @media print{.tourwrap{display:none!important}}`;

  function slides(q) {
    const sum = (k) => (q && q.counts ? q.counts.reduce((a, c) => a + (c[k] || 0), 0) : 0);
    const records = sum("documents") || 2160;
    const speeches = sum("speeches") || 29694;
    const votes = (q && q.decisions && q.decisions.n) || 6768;
    return [
      `<div class="tour-kicker">First time here · a one-minute tour</div>
       <h2 class="tour-h">How the Declaration and the Covenants were drafted, speech by speech.</h2>
       <div class="tour-lead">The UN's own records of the drafting of the Universal Declaration of Human Rights (1946–48) and the two
         International Covenants (1949–66), split into speeches: who spoke, for which delegation, on which article, with the page
         of the UN record beside it and a link to the UN's copy.</div>
       <div class="tour-stats">
         <div><b>${fmt(records)}</b><span>UN documents</span></div>
         <div><b>${fmt(speeches)}</b><span>speeches</span></div>
         <div><b>${fmt(votes)}</b><span>decisions and votes</span></div>
         <div><b>1946–66</b><span>years covered</span></div>
       </div>`,
      `<div class="tour-kicker">The views</div>
       <h2 class="tour-h">Seven ways in.</h2>
       <ul class="tour-list tour-views">
         <li><span class="n">01</span><div><b>Search</b> <span class="s">— every speech, by word</span> <span class="d">— every speech, chair turn and vote, by word, phrase, speaker,
           delegation, article or session; a result opens in its record, at its page.</span></div></li>
         <li><span class="n">02</span><div><b>Ask and Check</b> <span class="x">experimental</span> <span class="s">— a question; your citations</span> <span class="d">— put a question in a sentence and get the
           passages closest to it in meaning; or paste your own text and have its citations of the records checked.</span></div></li>
         <li><span class="n">03</span><div><b>Articles</b> <span class="s">— one article through the drafting</span> <span class="d">— one article through the drafting: its drafts at every
           stage, the meetings that debated it, its amendments and votes.</span></div></li>
         <li><span class="n">04</span><div><b>Delegations</b> <span class="s">— who said what</span> <span class="d">— each delegation and delegate: their speeches, by article and over time.</span></div></li>
         <li><span class="n">05</span><div><b>Votes and Amendments</b> <span class="s">— what was decided</span> <span class="d">— every recorded decision with its figures and
           roll-calls, and the amendments with their sponsors and fate.</span></div></li>
         <li><span class="n">06</span><div><b>Records and Workspace</b> <span class="s">— the documents, your notes</span> <span class="d">— the list of every document held, and the passages you
           save (☆) with your notes, kept in your browser only and exportable.</span></div></li>
         <li><span class="n">07</span><div><b>AI assistant</b> <span class="s">— the same data from Claude</span> <span class="d">— a connector (MCP) and a skill for Claude or another
           assistant: it searches these records and cites them by UN symbol and page.</span></div></li>
       </ul>`,
      `<div class="tour-kicker">Search</div>
       <h2 class="tour-h">From a phrase to the speech.</h2>
       <div class="tour-lead">Type words or a <code>"phrase"</code>, combine them with <code>AND</code>, <code>OR</code> and
         <code>NOT</code>, and end a word with <code>*</code> for every word that begins so (<code>propert*</code>). Narrow by
         speaker, delegation or article in the box itself (<code>speaker:cassin art:18</code>) or with the filters at the left.
         Every result shows its UN symbol and page, opens in its record, and copies as a citation. Try one:</div>
       <div class="tour-chips">${EXAMPLES.map((x) => `<button type="button" data-tour-q="${x.replace(/"/g, "&quot;")}">${x.replace(/</g, "&lt;")}</button>`).join("")}</div>`,
      `<div class="tour-kicker">Read with care</div>
       <h2 class="tour-h">Honest about what it holds.</h2>
       <ul class="tour-list">
         <li><span class="n">·</span><div><span><b>Summary records paraphrase.</b> Most meetings were recorded in the third person by the
           Secretariat; only the plenary records and the draft texts are verbatim.</span></div></li>
         <li><span class="n">·</span><div><span><b>Machine-read text.</b> The text is OCR of 1946–66 scans: check the page of the UN copy,
           one click from every passage, before you quote.</span></div></li>
         <li><span class="n">·</span><div><span><b>Final article numbers.</b> Each stage numbered the articles differently; passages carry
           the final number, mapped from the draft's. The tags are made by machine and checked on samples (about 95% right).</span></div></li>
         <li><span class="n">·</span><div><span><b>Not an official UN product.</b> The UN's documents remain the authoritative source;
           About says how this edition was made and how far to trust it.</span></div></li>
       </ul>`,
      `<div class="tour-kicker">Start anywhere</div>
       <h2 class="tour-h">Where to first?</h2>
       <div class="tour-go">
         <a href="#view=search" data-tour-go="search">→ Search what delegates said</a>
         <a href="#view=ask">→ Ask a question in plain words</a>
         <a href="#view=article&i=UDHR&n=18">→ Follow an article: the freedom of religion (UDHR 18)</a>
         <a href="#view=votes">→ Check a vote</a>
         <a href="#view=about&part=mcp">→ Use it from Claude or another AI assistant</a>
       </div>
       <div class="tour-cap" style="margin-top:18px">Reopen this tour any time: footer → ✦ Tour.</div>`,
    ];
  }

  let wrap = null, index = 0, lastFocus = null;

  function build(q) {
    if (!document.getElementById("tour-style")) {
      const st = document.createElement("style");
      st.id = "tour-style";
      st.textContent = CSS;
      document.head.appendChild(st);
    }
    wrap?.remove();
    const html = slides(q);
    wrap = document.createElement("div");
    wrap.className = "tourwrap";
    wrap.id = "tour-wrap";
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-modal", "true");
    wrap.setAttribute("aria-label", "Introduction tour");
    wrap.innerHTML = `<div class="tour-box" tabindex="-1">
      <div class="tour-slides">${html.map((h, i) => `<div class="tslide" data-i="${i}">${h}</div>`).join("")}</div>
      <div class="tour-nav"><button type="button" id="tour-skip">Skip tour</button>
        <div class="tour-dots">${html.map((_, i) => `<button type="button" class="tdot" data-i="${i}" aria-label="Slide ${i + 1}"></button>`).join("")}</div>
        <button type="button" id="tour-next">Next →</button></div></div>`;
    document.body.appendChild(wrap);
    wrap.addEventListener("click", (e) => {
      if (e.target === wrap) return close();
      const dot = e.target.closest(".tdot");
      if (dot) return go(Number(dot.dataset.i));
      if (e.target.id === "tour-skip") return close();
      if (e.target.id === "tour-next") return index >= html.length - 1 ? close() : go(index + 1);
      const ex = e.target.closest("[data-tour-q]");
      if (ex) {
        close();
        location.hash = "view=search&q=" + encodeURIComponent(ex.dataset.tourQ);
        return;
      }
      if (e.target.closest(".tour-go a")) {
        close();
        if (e.target.closest('[data-tour-go="search"]')) setTimeout(() => document.getElementById("q")?.focus(), 50);
      }
    });
  }

  function go(i) {
    const n = wrap.querySelectorAll(".tslide").length;
    index = Math.max(0, Math.min(n - 1, i));
    wrap.querySelectorAll(".tslide").forEach((s, k) => s.classList.toggle("on", k === index));
    wrap.querySelectorAll(".tdot").forEach((d, k) => d.classList.toggle("on", k === index));
    wrap.querySelector("#tour-next").textContent = index === n - 1 ? "Start exploring" : "Next →";
  }

  async function open() {
    lastFocus = document.activeElement;
    const api = (window.TRAVAUX && window.TRAVAUX.api) || "";
    const q = await fetch(api + "/api/quality", { signal: AbortSignal.timeout(4000) }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
    build(q);
    go(0);
    wrap.classList.add("open");
    document.documentElement.style.overflow = "hidden";
    wrap.querySelector(".tour-box").focus();
  }

  function close() {
    if (!wrap) return;
    wrap.classList.remove("open");
    document.documentElement.style.overflow = "";
    try { localStorage.setItem(DONE_KEY, "1"); } catch (_) { /* private mode: it may open again next time */ }
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener("keydown", (e) => {
    if (!wrap || !wrap.classList.contains("open")) return;
    if (e.key === "Escape") close();
    else if (e.key === "ArrowRight") go(index + 1);
    else if (e.key === "ArrowLeft") go(index - 1);
    else if (e.key === "Tab") {  // keep the focus inside the dialog
      const f = [...wrap.querySelectorAll("button, a[href]")].filter((x) => x.offsetParent);
      if (!f.length) return;
      if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
    }
  });
  document.addEventListener("click", (e) => {
    if (e.target.closest("#tour-btn, [data-tour-open]")) open();
  });

  window.TravauxTour = { open, close };

  // The first visit: only when the page opens on Search with nothing asked (a shared link to a record or a question opens
  // straight on what was shared), and never for automated browsers.
  let seen = false;
  try { seen = !!localStorage.getItem(DONE_KEY); } catch (_) { seen = true; }
  const h = new URLSearchParams(location.hash.replace(/^#/, ""));
  const plain = (h.get("view") || "search") === "search" && !h.get("q") && !h.get("open");
  if (!seen && plain && !navigator.webdriver) setTimeout(open, 700);
})();
