"""
404 / catch-all page object.
Source: vulnara-web/src/pages/NotFoundPage.jsx
"""

from selenium.webdriver.common.by import By

from .base_page import BasePage


class NotFoundPage(BasePage):
    HEADING = (By.XPATH, "//div[normalize-space()='404']")
    MESSAGE = (By.XPATH, "//*[contains(text(),\"That page doesn't exist\")]")
    HOME_LINK = (By.XPATH, "//a[contains(.,'Back to dashboard')]")

    def is_loaded(self) -> bool:
        return self.exists(*self.HEADING, timeout=6)

    def click_home(self):
        self.click(*self.HOME_LINK)
        return self
