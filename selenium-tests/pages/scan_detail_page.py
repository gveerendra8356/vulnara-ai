"""
Scan detail page object.
Source: vulnara-web/src/pages/ScanDetailPage.jsx
"""

from selenium.webdriver.common.by import By

from .base_page import BasePage


class ScanDetailPage(BasePage):
    STATUS_PILL = (By.CSS_SELECTOR, "[class*='rounded'][class*='uppercase']")
    VULN_TABLE = (By.CSS_SELECTOR, "table")
    VULN_ROWS = (By.CSS_SELECTOR, "table tbody tr")
    BACK_BUTTON = (By.XPATH, "//button[contains(.,'Back')]")

    def open(self, scan_id: str):
        self.goto(f"scans/{scan_id}")
        return self

    def is_loaded(self) -> bool:
        return self.exists(By.TAG_NAME, "h2") or self.exists(By.TAG_NAME, "h1")

    def click_first_vuln_row(self):
        rows = self.find_all(*self.VULN_ROWS)
        rows[0].click()
        return self

    def vuln_row_count(self) -> int:
        try:
            return len(self.driver.find_elements(*self.VULN_ROWS))
        except Exception:
            return 0
