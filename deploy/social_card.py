"""The picture a link to the site shows when it is shared (og:image, 1200 x 630), after HUDOC Researcher's social card:
the title, one line on what it is, the speeches of each year 1946-66 from the database, and the views.

  python3 deploy/social_card.py        # writes site/assets/social-card.png
"""
import sqlite3
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "assets" / "social-card.png"


def main():
    con = sqlite3.connect(ROOT / "data" / "travaux.sqlite3")
    per_year = dict(con.execute("SELECT substr(d.meeting_date, 1, 4), COUNT(*) FROM segments s JOIN documents d ON d.symbol = s.symbol "
                                "WHERE s.kind = 'speech' AND d.meeting_date >= '1946' GROUP BY 1"))
    years = [str(y) for y in range(1946, 1967)]
    top = max(per_year.get(y, 0) for y in years)
    bars = "".join(f'<i style="height:{max(2, round(100 * per_year.get(y, 0) / top))}%"></i>' for y in years)
    speeches = con.execute("SELECT COUNT(*) FROM segments WHERE kind = 'speech'").fetchone()[0]
    docs = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{(ROOT / 'site' / 'assets' / 'fonts.css').as_uri()}">
<style>
  body{{margin:0;width:1200px;height:630px;background:#faf8f3;color:#24232a;font-family:'Source Serif 4',Georgia,serif;
    border-left:16px solid #8d2f2f;box-sizing:border-box;padding:70px 90px 0 75px;position:relative}}
  h1{{font-family:'Spectral',Georgia,serif;font-weight:500;font-size:76px;margin:0 0 22px;letter-spacing:-.5px}}
  hr{{border:0;border-top:2px solid #ddd5c6;margin:0 0 26px}}
  p{{font-style:italic;font-size:38px;line-height:1.35;margin:0 0 26px;color:#2b2e35}}
  .bars{{display:flex;align-items:flex-end;gap:6px;height:110px;border-bottom:2px solid #ddd5c6}}
  .bars i{{flex:1;background:#8d2f2f;opacity:.78}}
  .cap,.views,.url{{font-family:'JetBrains Mono',monospace;font-size:19px;font-weight:600;letter-spacing:.3px}}
  .cap{{color:#60636a;margin-top:12px}}
  .views{{color:#8d2f2f;margin-top:30px;text-transform:uppercase;letter-spacing:1.2px}}
  .url{{color:#60636a;position:absolute;bottom:34px}}
</style></head><body>
<h1>UN Travaux Préparatoires</h1><hr>
<p>How the Universal Declaration and the two Covenants were drafted, speech by speech.</p>
<div class="bars">{bars}</div>
<div class="cap">{speeches:,} speeches · {docs:,} UN documents · 1946–1966</div>
<div class="views">Search · Ask · Articles · Delegations · Votes</div>
<div class="url">Adam Mickiewicz University · not an official UN product</div>
</body></html>"""
    with sync_playwright() as p:
        b = p.webkit.launch()  # (the WebKit that Playwright already has here)
        page = b.new_page(viewport={"width": 1200, "height": 630})
        page.set_content(html, wait_until="networkidle")
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT))
        b.close()
    print(f"{OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
