"""
New Scan page object.
Source: vulnara-web/src/pages/NewScanPage.jsx
Client-side gate: canSubmit = target non-empty AND authorized checkbox AND
justification.trim().length >= 10. Enforced again server-side (mock throws
422 if authorization_confirmed is false or justification is blank).
"""

from selenium.webdriver.common.by import By

from .base_page import BasePage


class NewScanPage(BasePage):
    HEADING = (By.XPATH, "//h2[contains(text(),'New Scan Configurator')]")
    TARGET_INPUT = (By.CSS_SELECTOR, "input[placeholder*='staging.example.com']")
    ACTIVE_TESTING_TOGGLE = (By.CSS_SELECTOR, "input[type='checkbox'].sr-only")
    JUSTIFICATION_TEXTAREA = (By.CSS_SELECTOR, "textarea")
    AUTHORIZED_CHECKBOX = (By.CSS_SELECTOR, "input[type='checkbox']:not(.sr-only)")
    SUBMIT_BUTTON = (By.XPATH, "//button[@type='submit']")
    CANCEL_BUTTON = (By.XPATH, "//button[normalize-space()='Cancel']")
    BACK_BUTTON = (By.XPATH, "//button[.//span[text()='Back to Scans']]")
    ERROR_BANNER = (By.CSS_SELECTOR, ".bg-error-container\\/10, [class*='error']")

    def open(self):
        self.goto("scans/new")
        return self

    def is_loaded(self) -> bool:
        return self.exists(*self.HEADING) and self.exists(*self.TARGET_INPUT)

    def set_target(self, value: str):
        self.type_into(*self.TARGET_INPUT, value)
        return self

    def set_justification(self, value: str):
        self.type_into(*self.JUSTIFICATION_TEXTAREA, value)
        return self

    def set_authorized(self, checked: bool):
        el = self.find(*self.AUTHORIZED_CHECKBOX)
        if el.is_selected() != checked:
            el.click()
        return self

    def set_active_testing(self, checked: bool):
        el = self.find(*self.ACTIVE_TESTING_TOGGLE)
        if el.is_selected() != checked:
            el.click()
        return self

    def submit_button_enabled(self) -> bool:
        return self.find(*self.SUBMIT_BUTTON).is_enabled()

    def submit(self):
        self.click(*self.SUBMIT_BUTTON)
        return self

    def fill_and_submit(self, target: str, justification: str, authorized: bool = True,
                         active_testing: bool = False):
        self.set_target(target)
        self.set_justification(justification)
        self.set_authorized(authorized)
        self.set_active_testing(active_testing)
        self.submit()
        return self

    def error_text(self) -> str:
        return self.body_text()
