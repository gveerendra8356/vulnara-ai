"""
Remediation queue page object.
Source: vulnara-web/src/pages/RemediationQueuePage.jsx
"""

from selenium.webdriver.common.by import By

from .base_page import BasePage


class RemediationQueuePage(BasePage):
    HEADING = (By.TAG_NAME, "h2")
    TABLE_ROWS = (By.CSS_SELECTOR, "table tbody tr")
    EMPTY_STATE = (By.XPATH, "//*[contains(text(),'No') and contains(@class,'headline')]")

    def open(self):
        self.goto("remediations")
        return self

    def is_loaded(self) -> bool:
        return self.exists(*self.HEADING)

    def row_count(self) -> int:
        try:
            return len(self.driver.find_elements(*self.TABLE_ROWS))
        except Exception:
            return 0
