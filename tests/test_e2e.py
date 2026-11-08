"""The site in a real browser (Playwright, WebKit): the paths a reader takes, which the API tests cannot see.

Skipped when Playwright or its WebKit is not installed. The server runs from the repository without a Voyage key, so Ask
answers that it is not available; the analytics stay off (no production host on localhost, and an automated browser).

  python3 -m pytest -q tests/test_e2e.py
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sync_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def base():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {"PATH": os.environ["PATH"], "HOST": "127.0.0.1", "PORT": str(port)}
    proc = subprocess.Popen([sys.executable, str(ROOT / "api" / "server.py")], env=env, cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}/"
    for _ in range(100):
        try:
            urllib.request.urlopen(url + "health", timeout=1)
            break
        except OSError:
            time.sleep(0.2)
    yield url
    proc.terminate()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.webkit.launch()
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"no WebKit for Playwright: {exc}")
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    yield pg
    ctx.close()


def test_search_open_a_record_and_come_back(page, base):
    page.goto(base + '#view=search&q=%22freedom%20of%20thought%22')
    page.wait_for_selector("#results .result")
    assert page.locator("#results .result").count() > 3
    page.locator("#results .result-open").first.click()
    page.wait_for_selector("#reader.is-open .dossier-head h2")
    assert "open=" in page.url
    page.go_back()
    page.wait_for_function("!location.hash.includes('open=')")
    assert "freedom" in page.url and page.locator("#results .result").count() > 3
    assert not page.errors


def test_the_box_above_a_long_list_narrows_it_and_enter_chooses(page, base):
    page.goto(base + "#view=search")
    page.wait_for_function("document.getElementById('symbol').options.length > 100")
    box = page.locator('[data-narrow="symbol"]')
    box.fill("sr.60")
    left = page.eval_on_selector("#symbol", "s => [...s.options].map(o => o.value)")
    assert "A/C.3/SR.603" in left and len(left) < 20  # every record that contains it is left, and only those
    box.press("Enter")
    page.wait_for_function("location.hash.includes('symbol=E%2FCN.4%2FSR.60&') || location.hash.endsWith('symbol=E%2FCN.4%2FSR.60')")
    assert page.locator("#symbol").input_value() == "E/CN.4/SR.60"  # the exact symbol, not SR.603
    box.press("Escape")
    assert page.locator("#symbol option").count() > 100 and page.locator("#symbol").input_value() == "E/CN.4/SR.60"
    assert not page.errors


def test_a_record_opened_from_another_view_returns_to_it(page, base):
    # (fixed on 4 Nov: the search behind the reader rewrote the history entry of the view the reader was opened from)
    page.goto(base + "#view=records")
    page.wait_for_selector(".rec-row[data-open]")
    page.locator(".rec-row[data-open]").first.click()
    page.wait_for_selector("#reader.is-open")
    page.go_back()
    page.wait_for_function("location.hash.includes('view=records')")
    assert page.locator('.view[data-view="records"]').is_visible()
    assert not page.errors


def test_ask_shows_six_examples_and_says_when_it_is_off(page, base):
    page.goto(base + "#view=ask")
    page.wait_for_selector("#ask-examples .ask-example")
    assert page.locator("#ask-examples .ask-example").count() == 6
    page.locator("#ask-examples .ask-example").first.click()
    page.wait_for_function("document.getElementById('ask-status').textContent.length > 0 && !document.getElementById('ask-submit').disabled")
    assert "not available" in page.locator("#ask-status.is-error").text_content()
    assert "qa=" in page.url
    page.goto(base + "#view=ask&qa=right%20to%20strike")
    page.wait_for_selector("#ask-hint:not([hidden])")  # a few words: the hint toward Search
    assert not page.errors


def test_check_marks_the_citations_of_a_text(page, base):
    page.goto(base + "#view=check")
    page.click("#check-sample")
    page.wait_for_selector(".ck-card")
    assert page.locator(".ck-card").count() == 5
    assert page.locator(".ck-card.st-ok").count() == 3 and page.locator(".ck-card.st-problem").count() == 1
    assert page.locator("#check-annotated .ck-cite").count() == 5
    assert not page.errors


def test_the_tour_opens_from_the_footer_not_by_itself_for_a_robot(page, base):
    page.goto(base)
    page.wait_for_selector("#tour-btn")
    page.wait_for_timeout(1200)
    assert page.locator(".tourwrap.open").count() == 0  # never for an automated browser
    page.click("#tour-btn")
    page.wait_for_selector(".tourwrap.open .tslide.on")
    for _ in range(4):
        page.click("#tour-next")
    assert page.locator("#tour-next").text_content() == "Start exploring"
    page.keyboard.press("Escape")
    assert page.locator(".tourwrap.open").count() == 0
    assert not page.errors


def test_about_privacy_choice_and_what_is_new(page, base):
    page.goto(base + "#view=about")
    page.wait_for_selector("#about-page [data-consent-ui] p")
    assert "cookie-free counter" in page.locator("#about-licence").inner_text()
    page.goto(base + "#view=about&part=news")
    page.wait_for_selector(".news dt")
    assert page.locator(".news dt").count() >= 5
    assert not page.errors


def test_no_counting_off_the_production_host(page, base):
    sent = []
    page.on("request", lambda r: sent.append(r.url) if "goatcounter" in r.url or "googletagmanager" in r.url else None)
    page.goto(base + "#view=search")
    page.goto(base + "#view=ask")
    page.wait_for_timeout(500)
    assert not sent and page.locator("#tx-consent").count() == 0
