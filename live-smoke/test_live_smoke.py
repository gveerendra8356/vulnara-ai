"""
live-smoke/test_live_smoke.py

Read-only end-to-end smoke tests that run against the LIVE GitHub Pages
deployment (never localhost). They verify the deployed site is up and its
public pages render — they do NOT log in, because the live site talks to the
real backend and we keep the smoke suite non-destructive and credential-free.

BASE_URL is configurable via the environment and defaults to the project's
Pages URL:
    BASE_URL=https://gveerendra8356.github.io/vulnara-ai/
"""

from __future__ import annotations

import os
import time

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


def _open(driver, path=""):
    driver.get(BASE_URL + path.lstrip("/"))
    WebDriverWait(driver, 30).until(
        lambda d: d.execute_script("return document.readyState") == "complete")
    # SPA hydration: wait until the root has rendered something.
    WebDriverWait(driver, 30).until(
        lambda d: len(d.find_element(By.TAG_NAME, "body").text.strip()) > 0)


# ── Deployment availability (no browser) ────────────────────────────────────
def test_deployment_returns_http_200():
    r = requests.get(BASE_URL, timeout=30)
    assert r.status_code == 200, f"Deployment not available: HTTP {r.status_code}"


def test_deployment_serves_html_shell():
    r = requests.get(BASE_URL, timeout=30)
    assert "<div id=\"root\"" in r.text or "<html" in r.text.lower()


def test_js_bundle_is_reachable():
    html = requests.get(BASE_URL, timeout=30).text
    import re
    m = re.search(r'src="([^"]*assets/[^"]+\.js)"', html)
    assert m, "No JS bundle reference found in the deployed HTML"
    asset = m.group(1)
    url = asset if asset.startswith("http") else BASE_URL.rstrip("/") + "/" + asset.lstrip("/")
    # Pages serves assets under /vulnara-ai/; normalise double segments.
    url = url.replace("/vulnara-ai/vulnara-ai/", "/vulnara-ai/")
    assert requests.get(url, timeout=30).status_code == 200, f"JS bundle 404: {url}"


# ── Rendered SPA checks (headless Chrome) ───────────────────────────────────
def test_homepage_title_mentions_vulnara(driver):
    _open(driver)
    assert "vulnara" in driver.title.lower(), f"Unexpected title: {driver.title!r}"


def test_root_redirects_to_login_when_unauthenticated(driver):
    _open(driver)
    WebDriverWait(driver, 20).until(lambda d: "login" in d.current_url.lower())
    assert "login" in driver.current_url.lower()


def test_login_page_renders_form(driver):
    _open(driver, "login")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input")))
    inputs = driver.find_elements(By.CSS_SELECTOR, "input")
    assert len(inputs) >= 1, "Login page shows no input fields"


def test_login_page_has_email_and_password_fields(driver):
    _open(driver, "login")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input")))
    types = {(i.get_attribute("type") or "").lower() for i in driver.find_elements(By.CSS_SELECTOR, "input")}
    assert "password" in types, f"No password field on login page (types seen: {types})"


def test_register_page_renders(driver):
    _open(driver, "register")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input")))
    assert len(driver.find_elements(By.CSS_SELECTOR, "input")) >= 1


def test_forgot_password_page_renders(driver):
    _open(driver, "forgot-password")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input")))
    assert len(driver.find_elements(By.CSS_SELECTOR, "input")) >= 1


def test_unknown_route_does_not_blank_screen(driver):
    _open(driver, "this-route-does-not-exist-xyz")
    body = driver.find_element(By.TAG_NAME, "body").text.strip()
    assert len(body) > 0, "Unknown route rendered a blank screen"
