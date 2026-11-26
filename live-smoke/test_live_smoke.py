"""
live-smoke/test_live_smoke.py

Read-only end-to-end smoke tests against the LIVE GitHub Pages deployment
(never localhost). They verify the deployed site is up and the single-page app
boots and renders its public login UI.

IMPORTANT (GitHub Pages + SPA): Pages has no server-side SPA fallback, so a
direct request to a client-side route like `/login` returns HTTP 404. The app's
router (BrowserRouter) only creates those routes in the browser. So every check
here loads the ROOT URL and lets the SPA route client-side — it never navigates
straight to a deep route.

BASE_URL is configurable and defaults to the project's Pages URL:
    BASE_URL=https://gveerendra8356.github.io/vulnara-ai/
"""

from __future__ import annotations

import os
import re

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.environ.get("BASE_URL", "https://gveerendra8356.github.io/vulnara-ai/").rstrip("/") + "/"


@pytest.fixture(scope="session")
def driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1366,900")
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(45)
    yield d
    d.quit()


def _open_root(driver):
    """Load the ROOT URL and wait for the SPA to hydrate."""
    driver.get(BASE_URL)
    WebDriverWait(driver, 30).until(
        lambda d: d.execute_script("return document.readyState") == "complete")
    WebDriverWait(driver, 30).until(
        lambda d: len(d.find_element(By.TAG_NAME, "body").text.strip()) > 0)


def _body_text(driver) -> str:
    return driver.find_element(By.TAG_NAME, "body").text


# ── Deployment availability (no browser) ────────────────────────────────────
def test_deployment_returns_http_200():
    r = requests.get(BASE_URL, timeout=30)
    assert r.status_code == 200, f"Deployment not available: HTTP {r.status_code}"


def test_deployment_serves_spa_shell():
    html = requests.get(BASE_URL, timeout=30).text
    assert 'id="root"' in html, "SPA root container not found in deployed HTML"


def test_js_bundle_is_reachable():
    html = requests.get(BASE_URL, timeout=30).text
    m = re.search(r'src="([^"]*assets/[^"]+\.js)"', html)
    assert m, "No JS bundle reference found in the deployed HTML"
    asset = m.group(1)
    url = asset if asset.startswith("http") else BASE_URL.rstrip("/") + "/" + asset.lstrip("/")
    url = url.replace("/vulnara-ai/vulnara-ai/", "/vulnara-ai/")
    assert requests.get(url, timeout=30).status_code == 200, f"JS bundle not reachable: {url}"


# ── Rendered SPA checks (headless Chrome, all via the root URL) ──────────────
def test_homepage_title_mentions_vulnara(driver):
    _open_root(driver)
    assert "vulnara" in driver.title.lower(), f"Unexpected title: {driver.title!r}"


def test_root_is_not_a_blank_screen(driver):
    _open_root(driver)
    assert len(_body_text(driver).strip()) > 0, "App rendered a blank screen at the root URL"


def test_unauthenticated_root_routes_to_login(driver):
    _open_root(driver)
    # BrowserRouter redirects an unauthenticated visitor to /login client-side.
    WebDriverWait(driver, 20).until(lambda d: "login" in d.current_url.lower())
    assert "login" in driver.current_url.lower()


def test_login_form_renders(driver):
    _open_root(driver)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input")))
    assert len(driver.find_elements(By.CSS_SELECTOR, "input")) >= 1, "Login form shows no inputs"


def test_login_has_a_password_field(driver):
    _open_root(driver)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input")))
    types = {(i.get_attribute("type") or "").lower() for i in driver.find_elements(By.CSS_SELECTOR, "input")}
    assert "password" in types, f"No password field on the login screen (input types: {types})"


def test_login_screen_offers_registration(driver):
    # The register path exists only client-side; verify the login screen exposes
    # the affordance to reach it (a tab/link), without navigating to /register
    # directly (which 404s on Pages).
    _open_root(driver)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input")))
    assert re.search(r"register|sign up", _body_text(driver), re.I), \
        "Login screen does not expose a registration affordance"


def test_login_screen_offers_password_recovery(driver):
    _open_root(driver)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input")))
    assert re.search(r"forgot", _body_text(driver), re.I), \
        "Login screen does not expose a forgot-password affordance"
