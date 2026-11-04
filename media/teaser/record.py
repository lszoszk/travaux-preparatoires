#!/usr/bin/env python3
"""Record the teaser's screen scenes from the running app (api/server.py on localhost:8430), headless, 1920x1080.

  python3 media/teaser/record.py [--base http://localhost:8430]

One browser context per scene, each recorded to its own WebM in dist/teaser/clips/; the moment the scene is ready (after
the page has loaded) is written to dist/teaser/clips/offsets.json so that build.sh trims the loading away. The header label
is set to "Working edition" by serving a different config.js to the browser; the app itself is not changed. A small dot
follows the mouse so that the viewer sees where the clicks go.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dist" / "teaser" / "clips"
W, H = 1920, 1080
CONFIG = 'window.TRAVAUX = { api: "", scans: "local", label: "Working edition", title: "UN Travaux Préparatoires" };'
CURSOR = """
window.addEventListener('DOMContentLoaded', () => {
  const d = document.createElement('div');
  d.id = '__cursor';
  Object.assign(d.style, {position: 'fixed', left: '-40px', top: '-40px', width: '22px', height: '22px', borderRadius: '50%',
    background: 'rgba(140, 30, 40, 0.55)', border: '2px solid rgba(255,255,255,0.95)', boxShadow: '0 1px 6px rgba(0,0,0,.35)',
    zIndex: 2147483647, pointerEvents: 'none', transform: 'translate(-50%, -50%)', transition: 'width .12s, height .12s'});
  document.body.appendChild(d);
  addEventListener('mousemove', (e) => { d.style.left = e.clientX + 'px'; d.style.top = e.clientY + 'px'; }, true);
  addEventListener('mousedown', () => { d.style.width = '16px'; d.style.height = '16px'; }, true);
  addEventListener('mouseup', () => { d.style.width = '22px'; d.style.height = '22px'; }, true);
});
"""


def glide(page, x0, y0, x1, y1, ms=600, steps=30):
    page.mouse.move(x0, y0)
    for i in range(1, steps + 1):
        page.mouse.move(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)
        page.wait_for_timeout(ms / steps)


def scroll(page, total, ms, steps=60):
    for _ in range(steps):
        page.mouse.wheel(0, total / steps)
        page.wait_for_timeout(ms / steps)


def scene(browser, name, base, act, offsets):
    ctx = browser.new_context(viewport={"width": W, "height": H}, record_video_dir=str(OUT / "_tmp"),
                              record_video_size={"width": W, "height": H}, device_scale_factor=1)
    ctx.route("**/config.js", lambda r: r.fulfill(status=200, content_type="text/javascript", body=CONFIG))
    ctx.add_init_script(CURSOR)
    t0 = time.monotonic()
    page = ctx.new_page()
    info = act(page, base) or {}
    offsets[name] = {"start": round(info.pop("_start") - t0, 2), **info}
    page.wait_for_timeout(300)
    video = page.video
    ctx.close()
    shutil.move(video.path(), OUT / f"{name}.webm")


def s2_search(page, base):
    page.goto(base + "/#view=search&kind=speech")
    page.wait_for_selector("#q")
    page.wait_for_timeout(1200)
    glide(page, 1500, 600, 640, 140, ms=500)
    start = time.monotonic()
    page.click("#q")
    page.keyboard.type('"change his religion"', delay=55)
    page.keyboard.press("Enter")
    page.wait_for_selector(".result")
    page.wait_for_timeout(900)
    glide(page, 640, 140, 760, 330, ms=700)
    scroll(page, 520, 2600)
    glide(page, 760, 330, 900, 420, ms=600)
    page.wait_for_timeout(2600)
    return {"_start": start}


def s3_record(page, base):
    page.goto(base + '/#view=search&kind=speech&q=%22change+his+religion%22')
    page.wait_for_selector(".result")
    page.wait_for_timeout(1200)
    first = page.locator(".result").first
    sym = first.get_attribute("data-open")
    box = first.locator(".result-headline").bounding_box()
    start = time.monotonic()
    glide(page, 900, 700, box["x"] + 60, box["y"] + box["height"] / 2, ms=700)
    first.locator(".result-headline").click()
    page.wait_for_selector(".dossier-body")
    page.wait_for_timeout(2600)
    seg = page.locator(".seg.target").first
    page_no = None
    if seg.count():
        hit = page.evaluate("() => { const t = document.querySelector('.seg.target'); let e = t; while (e && !(e.classList && e.classList.contains('pagebreak'))) e = e.previousElementSibling; return e ? e.textContent : null; }")
        if hit:
            import re
            m = re.search(r"(\d+)", hit)
            page_no = int(m.group(1)) if m else None
    page.wait_for_timeout(1500)
    return {"_start": start, "symbol": sym, "page": page_no}


def s4_article(page, base):
    page.goto(base + "/#view=article&i=UDHR&n=18")
    page.wait_for_selector("text=How the text changed")
    page.wait_for_timeout(1200)
    page.mouse.move(1500, 700)
    start = time.monotonic()
    page.wait_for_timeout(500)
    scroll(page, 900, 4200)
    page.wait_for_timeout(1500)
    return {"_start": start}


def s5_amendments(page, base):
    page.goto(base + "/#view=amendments&ai=UDHR&aa=18")
    page.wait_for_selector("text=A/C.3/232")
    page.wait_for_timeout(1200)
    page.mouse.move(1500, 800)
    start = time.monotonic()
    glide(page, 1500, 800, 700, 462, ms=900)
    glide(page, 700, 462, 1200, 470, ms=1200)
    glide(page, 1200, 470, 1260, 600, ms=900)
    page.wait_for_timeout(2000)
    return {"_start": start}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8430")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    offsets: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, act in (("s2", s2_search), ("s3", s3_record), ("s4", s4_article), ("s5", s5_amendments)):
            scene(browser, name, args.base, act, offsets)
            print(name, offsets[name])
        browser.close()
    shutil.rmtree(OUT / "_tmp", ignore_errors=True)
    (OUT / "offsets.json").write_text(json.dumps(offsets, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
