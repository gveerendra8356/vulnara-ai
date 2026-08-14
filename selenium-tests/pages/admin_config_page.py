"""
Admin config page object.
Source: vulnara-web/src/pages/AdminConfigPage.jsx
"""

from selenium.webdriver.common.by import By

from .base_page import BasePage


class AdminConfigPage(BasePage):
    HEADING = (By.XPATH, "//h2[contains(.,'Configuration')]")
    TABLE_ROWS = (By.CSS_SELECTOR, "table tbody tr")

    def open(self):
        self.goto("admin/config")
        return self

    def is_loaded(self) -> bool:
        return self.exists(*self.HEADING)

    def edit_button_for_key(self, key: str):
        return (By.XPATH, f"//tr[td[contains(text(),'{key}')]]//button[contains(.,'Edit')]")

    def click_edit(self, key: str):
        self.click(*self.edit_button_for_key(key))
        return self

    def save_button(self):
        return (By.XPATH, "//button[normalize-space()='Save']")

    def cancel_button(self):
        return (By.XPATH, "//button[normalize-space()='Cancel']")

    def value_input(self):
        return (By.CSS_SELECTOR, "table input")

    def set_value(self, value: str):
        self.type_into(*self.value_input(), value)
        return self

    def click_save(self):
        self.click(*self.save_button())
        return self

    def click_cancel(self):
        self.click(*self.cancel_button())
        return self

    def value_for_key(self, key: str) -> str:
        el = self.find((By.XPATH, f"//tr[td[contains(text(),'{key}')]]//td[2]"))
        return el.text
