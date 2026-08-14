"""
Scans list page object.
Source: vulnara-web/src/pages/ScansListPage.jsx
"""

from selenium.webdriver.common.by import By

from .base_page import BasePage

STATUS_FILTERS = ["ALL", "PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "CANCELLED"]


class ScansListPage(BasePage):
    HEADING = (By.XPATH, "//h2[contains(text(),'Scans Overview')]")
    SEARCH_INPUT = (By.CSS_SELECTOR, "input[placeholder='Filter by target...']")
    NEW_SCAN_BUTTON = (By.XPATH, "//button[.//span[text()='New Scan']]")
    TABLE_ROWS = (By.CSS_SELECTOR, "table tbody tr")
    EMPTY_STATE = (By.XPATH, "//*[contains(text(),'No matching scans')]")

    def open(self):
        self.goto("scans")
        return self

    def is_loaded(self) -> bool:
        return self.exists(*self.HEADING)

    def filter_button(self, status: str):
        return (By.XPATH, f"//button[normalize-space()='{status}']")

    def click_filter(self, status: str):
        self.click(*self.filter_button(status))
        return self

    def filter_is_active(self, status: str) -> bool:
        el = self.find(*self.filter_button(status))
        return "border-primary" in (el.get_attribute("class") or "")

    def search(self, text: str):
        self.type_into(*self.SEARCH_INPUT, text)
        return self

    def row_count(self) -> int:
        try:
            return len(self.driver.find_elements(*self.TABLE_ROWS))
        except Exception:
            return 0

    def click_new_scan(self):
        self.click(*self.NEW_SCAN_BUTTON)
        return self

    def click_row_with_target(self, target_substring: str):
        self.click((By.XPATH, f"//table//td[contains(text(),'{target_substring}')]"))
        return self
