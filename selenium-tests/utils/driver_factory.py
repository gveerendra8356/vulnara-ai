"""
Chrome WebDriver factory.

- Uses Selenium 4.6+'s built-in Selenium Manager: no separate chromedriver
  package/download step needed.
- Reads CHROME_PATH if set (browser-actions/setup-chrome@v1 exports this in
  CI) so Selenium binds to the exact Chrome the workflow installed instead of
  whatever happens to be on PATH.
- Every flag below exists because CI (not local) Chrome needs it: no /dev/shm
  size limit in containers, no sandbox as a non-root CI user, deterministic
  window size for consistent screenshots.
"""

import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from config import HEADLESS


def build_chrome_options() -> Options:
    opts = Options()

    if HEADLESS:
        opts.add_argument("--headless=new")

    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--log-level=3")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    # Deterministic locale/timezone so date-formatted assertions don't drift
    # between CI runners.
    opts.add_argument("--lang=en-US")

    opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    chrome_path = os.environ.get("CHROME_PATH")
    if chrome_path:
        opts.binary_location = chrome_path

    return opts


def new_driver(mobile: bool = False) -> webdriver.Chrome:
    opts = build_chrome_options()
    if mobile:
        opts.add_experimental_option(
            "mobileEmulation", {"deviceMetrics": {"width": 390, "height": 844, "pixelRatio": 3},
                                 "userAgent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                                               "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                                               "Version/17.0 Mobile/15E148 Safari/604.1")},
        )
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(0)  # we always use explicit waits
    return driver
