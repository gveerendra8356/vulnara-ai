"""
pages/base_page.py

Locator strategy
-----------------
This app has no ValueKeys anywhere in lib/ (verified: `grep -rn "Key(" lib`
returns nothing), so key-based finders (the ones appium-flutter-driver
would use) aren't an option regardless of driver choice. Instead, every
Text/button label/hint is reached the same way a real Android accessibility
service would reach it, since that's exactly what UiAutomator2 is to
Flutter: Flutter auto-builds and exposes its semantics tree as native
Android accessibility nodes the moment an accessibility service attaches
(no debug flag, no app code change needed).

- by_text(): exact visible label text (Text widgets, ElevatedButton/
  TextButton labels) -> XPath //*[@text='...']
- by_text_contains(): partial match, for dynamic/interpolated labels
  (e.g. "Scan #<id>") -> XPath //*[contains(@text, '...')]
- edit_field(index): TextFormFields render as focusable native EditText
  nodes in document order -> UiSelector().className("android.widget.
  EditText").instance(N). This is why every *_page.py documents field
  order explicitly next to the screen's source layout, instead of hunting
  for a semantic label that doesn't exist on plain TextFormFields.
- by_content_desc(): IconButtons with a tooltip (Flutter derives a
  semantics content-description from Tooltip/tooltip: text) -> accessibility id.
"""

import time

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait


class BasePage:
    def __init__(self, driver, timeout: float = 12):
        self.driver = driver
        self.timeout = timeout

    # ---- locators -----------------------------------------------------
    def by_text(self, text: str):
        return (AppiumBy.XPATH, f"//*[@text='{text}']")

    def by_text_contains(self, text: str):
        return (AppiumBy.XPATH, f"//*[contains(@text, '{text}')]")

    def by_content_desc(self, desc: str):
        return (AppiumBy.ACCESSIBILITY_ID, desc)

    def edit_field(self, index: int):
        return (
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().className("android.widget.EditText").instance({index})',
        )

    # ---- actions --------------------------------------------------------
    def wait_visible(self, locator, timeout: float | None = None):
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            lambda d: d.find_element(*locator)
        )

    def is_present(self, locator, timeout: float = 3) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(lambda d: d.find_element(*locator))
            return True
        except (NoSuchElementException, TimeoutException):
            return False

    def tap_text(self, text: str, timeout: float | None = None):
        el = self.wait_visible(self.by_text(text), timeout)
        el.click()

    def enter_text(self, index: int, value: str, clear_first: bool = True):
        el = self.wait_visible(self.edit_field(index))
        if clear_first:
            el.clear()
        el.send_keys(value)

    def text_of_field(self, index: int) -> str:
        el = self.wait_visible(self.edit_field(index))
        return el.text or el.get_attribute("text") or ""

    def wait_gone(self, locator, timeout: float | None = None) -> bool:
        try:
            WebDriverWait(self.driver, timeout or self.timeout).until_not(
                lambda d: d.find_element(*locator)
            )
            return True
        except TimeoutException:
            return False
        except NoSuchElementException:
            return True

    def swipe_up(self, times: int = 1):
        size = self.driver.get_window_size()
        x = size["width"] // 2
        y_start = int(size["height"] * 0.8)
        y_end = int(size["height"] * 0.2)
        for _ in range(times):
            self.driver.swipe(x, y_start, x, y_end, 400)
            time.sleep(0.3)

    def back(self):
        self.driver.back()

    def all_texts(self) -> list[str]:
        """All @text values currently in the semantics tree -- used by
        page-chrome/accessibility tests that assert on general page
        content rather than one specific element."""
        elements = self.driver.find_elements(AppiumBy.XPATH, "//*[@text]")
        return [e.get_attribute("text") for e in elements if e.get_attribute("text")]
