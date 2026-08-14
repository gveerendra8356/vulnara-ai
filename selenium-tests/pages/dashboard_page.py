"""
Dashboard page object.
Source: vulnara-web/src/pages/DashboardPage.jsx
"""

from selenium.webdriver.common.by import By

from .base_page import BasePage


class DashboardPage(BasePage):
    HEADING = (By.XPATH, "//h2[contains(text(),'Global Analytics Overview')]")
    NEW_SCAN_BUTTON = (By.XPATH, "//button[.//span[text()='New Scan']]")
    KPI_CARDS = (By.CSS_SELECTOR, "[class*='col-span']")

    def open(self):
        self.goto("")
        return self

    def is_loaded(self) -> bool:
        return self.exists(*self.HEADING)

    def click_new_scan(self):
        self.click(*self.NEW_SCAN_BUTTON)
        return self
