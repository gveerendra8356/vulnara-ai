"""
Base Page Object.

Everything here uses WebDriverWait + expected_conditions. No time.sleep()
anywhere in this framework -- final_year.md's audit of the sibling
KrishiIQ/FitFuel/NutriScan suites specifically flags time.sleep() drift and
`assert x or True` as the two anti-patterns that quietly rot a suite's
signal. Both are avoided by construction here, not by policy alone.
"""

from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config import BASE_URL, DEFAULT_WAIT, SHORT_WAIT, TOKEN_KEY


class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, DEFAULT_WAIT)
        self.short_wait = WebDriverWait(driver, SHORT_WAIT)

    # ------------------------------------------------------------------ nav
    def goto(self, route: str, hard: bool = False):
        """Navigate to BASE_URL + route.

        Uses client-side navigation (History API pushState + a synthetic
        popstate event) whenever the app is already loaded in this tab, so
        an authenticated Mock Mode session survives the hop -- the same way
        it would for a real user clicking a link, rather than typing a URL
        and hitting Enter.

        This matters because Mock Mode's session lives ONLY in an in-memory
        JS variable (verified directly in src/lib/mockApi.js:
        `state.currentUser`, never written to localStorage -- see
        test_authentication.py::TestTokenBehaviorInMockMode and
        test_session_management.py for the confirmed behavior this
        produces). A real browser navigation -- driver.get(), same as
        typing a URL and hitting Enter, or a hard reload -- tears down and
        reloads the whole JS module tree, which resets that variable to
        null and bounces to /login. That's the CORRECT thing to test
        deliberately (see driver.refresh() in
        test_session_management.py's TestMockModeSessionDoesNotSurviveReload),
        but goto() using driver.get() unconditionally meant nearly every
        OTHER test that just wanted to move from one authenticated page to
        another was accidentally logging itself out first -- the actual
        root cause behind a real CI run reporting 199 failures across
        exactly the modules that navigate between pages after logging in
        (crud_operations, forms, ui_validation, search_filter, navigation,
        authorization, input_validation), while modules that either don't
        navigate post-login or deliberately test the reload-drops-session
        behavior (authentication, session_management) stayed mostly green.

        Pass hard=True to force a real full navigation when a fresh/
        bookmarked/unauthenticated visit is genuinely the point of the
        test. The very first navigation in a brand-new browser tab always
        uses a real navigation regardless of `hard`, since there's no JS
        context loaded yet for pushState to act on.
        """
        target_url = BASE_URL + route
        is_first_navigation = self.driver.current_url.startswith(("data:", "about:"))

        if hard or is_first_navigation:
            self.driver.get(target_url)
        else:
            self.driver.execute_script(
                "window.history.pushState({}, '', arguments[0]);"
                "window.dispatchEvent(new PopStateEvent('popstate'));",
                target_url,
            )
        return self

    def current_path(self) -> str:
        """The path portion after BASE_URL, e.g. 'scans/new'."""
        url = self.driver.current_url
        return url.split(BASE_URL, 1)[-1] if BASE_URL in url else url

    def on_route(self, route: str, timeout: int = DEFAULT_WAIT) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: self.current_path().rstrip("/") == route.rstrip("/")
            )
            return True
        except TimeoutException:
            return False

    # -------------------------------------------------------------- finders
    def find(self, by, locator, timeout: int = DEFAULT_WAIT):
        return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, locator)))

    def find_clickable(self, by, locator, timeout: int = DEFAULT_WAIT):
        return WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((by, locator)))

    def find_all(self, by, locator, timeout: int = DEFAULT_WAIT):
        WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, locator)))
        return self.driver.find_elements(by, locator)

    def exists(self, by, locator, timeout: int = SHORT_WAIT) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, locator)))
            return True
        except TimeoutException:
            return False

    def visible(self, by, locator, timeout: int = SHORT_WAIT) -> bool:
        try:
            el = WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((by, locator)))
            return el.is_displayed()
        except (TimeoutException, NoSuchElementException):
            return False

    def text_present(self, text: str, timeout: int = DEFAULT_WAIT) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: text.lower() in d.find_element(By.TAG_NAME, "body").text.lower()
            )
            return True
        except TimeoutException:
            return False

    # ------------------------------------------------------------- actions
    def type_into(self, by, locator, value: str, clear_first: bool = True):
        el = self.find_clickable(by, locator)
        if clear_first:
            el.clear()
        if value:
            el.send_keys(value)
        return el

    def click(self, by, locator):
        el = self.find_clickable(by, locator)
        el.click()
        return el

    # ------------------------------------------------------- auth / storage
    def get_token(self):
        return self.driver.execute_script(f"return window.localStorage.getItem('{TOKEN_KEY}');")

    def set_token(self, value: str):
        self.driver.execute_script(f"window.localStorage.setItem('{TOKEN_KEY}', arguments[0]);", value)

    def clear_local_storage(self):
        self.driver.execute_script("window.localStorage.clear();")

    def set_local_storage_item(self, key: str, value: str):
        self.driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", key, value)

    def get_local_storage_item(self, key: str):
        return self.driver.execute_script("return window.localStorage.getItem(arguments[0]);", key)

    # -------------------------------------------------------------- errors
    def js_console_errors(self):
        """Severe-level console entries since the last call (log gets drained)."""
        try:
            logs = self.driver.get_log("browser")
        except Exception:
            return []
        return [entry for entry in logs if entry.get("level") == "SEVERE"]

    def body_text(self) -> str:
        return self.find(By.TAG_NAME, "body").text

    def page_title(self) -> str:
        return self.driver.title
