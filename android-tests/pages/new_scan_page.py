"""
pages/new_scan_page.py

Field order from lib/screens/new_scan_screen.dart:
  - EditText instance 0: TARGET ADDRESS / IP RANGE
  - EditText instance 1: AUTHORIZATION JUSTIFICATION
  - "Explicit Permission Confirmation" is a custom tappable Container
    (GestureDetector on the checkbox row), NOT a native Checkbox widget --
    toggled by tapping its text, same as the Switch row below it.
  - Switch: "Enable AI Active Testing" -- native Switch widget.
  - Submit button label: "INITIALIZE SCAN"
"""

from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage

TARGET_FIELD = 0
JUSTIFICATION_FIELD = 1
HEADER = "New Target Configuration"
CONFIRMATION_LABEL = "Explicit Permission Confirmation"
ACTIVE_TESTING_LABEL = "Enable AI Active Testing"
SUBMIT_LABEL = "INITIALIZE SCAN"


class NewScanPage(BasePage):
    def is_loaded(self, timeout: float = 10) -> bool:
        return self.is_present(self.by_text(HEADER), timeout=timeout)

    def enter_target(self, value: str):
        self.enter_text(TARGET_FIELD, value)

    def enter_justification(self, value: str):
        self.enter_text(JUSTIFICATION_FIELD, value)

    def toggle_authorization_confirmation(self):
        self.tap_text(CONFIRMATION_LABEL)

    def toggle_active_testing_switch(self):
        switch = self.driver.find_element(AppiumBy.CLASS_NAME, "android.widget.Switch")
        switch.click()

    def is_active_testing_enabled(self) -> bool:
        switch = self.driver.find_element(AppiumBy.CLASS_NAME, "android.widget.Switch")
        return switch.get_attribute("checked") == "true"

    def submit(self):
        self.tap_text(SUBMIT_LABEL)

    def error_text(self) -> str | None:
        known = {HEADER, CONFIRMATION_LABEL, ACTIVE_TESTING_LABEL, SUBMIT_LABEL,
                 "TARGET ADDRESS / IP RANGE", "AUTHORIZATION JUSTIFICATION"}
        for t in self.all_texts():
            if t not in known and t.strip() and "Utilize" not in t and "I confirm" not in t:
                return t
        return None

    def fill_valid_scan(self, target: str = "testphp.vulnweb.com",
                         justification: str = "Authorized by security team for Q3 compliance testing."):
        self.enter_target(target)
        self.enter_justification(justification)
        self.toggle_authorization_confirmation()
