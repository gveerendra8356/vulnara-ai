"""
Register page object.
Source: vulnara-web/src/pages/RegisterPage.jsx
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from .base_page import BasePage


class RegisterPage(BasePage):
    NAME_INPUT = (By.CSS_SELECTOR, "form input[type='text'], form input:not([type])")
    EMAIL_INPUT = (By.CSS_SELECTOR, "input[type='email']")
    PASSWORD_INPUT = (By.CSS_SELECTOR, "input[type='password']")
    ROLE_SELECT = (By.CSS_SELECTOR, "form select")
    SUBMIT_BUTTON = (By.CSS_SELECTOR, "form button[type='submit']")
    LOGIN_TAB = (By.XPATH, "//button[normalize-space()='Login']")
    ERROR_BANNER = (By.XPATH, "//*[contains(@class,'text-error')]")
    HEADING = (By.XPATH, "//h1[contains(text(),'New Operator')]")
    ADMIN_HINT = (By.XPATH, "//*[contains(text(),'Admin accounts are created by an existing admin')]")

    def open(self):
        self.goto("register")
        return self

    def is_loaded(self) -> bool:
        return self.exists(*self.EMAIL_INPUT) and self.exists(*self.ROLE_SELECT)

    def fill(self, full_name: str = None, email: str = None, password: str = None, role: str = None):
        if full_name is not None:
            self.type_into(*self.NAME_INPUT, full_name)
        if email is not None:
            self.type_into(*self.EMAIL_INPUT, email)
        if password is not None:
            self.type_into(*self.PASSWORD_INPUT, password)
        if role is not None:
            Select(self.find(*self.ROLE_SELECT)).select_by_value(role)
        return self

    def submit(self):
        self.click(*self.SUBMIT_BUTTON)
        return self

    def register(self, full_name: str, email: str, password: str, role: str = "client"):
        self.fill(full_name, email, password, role)
        self.submit()
        return self

    def role_options(self):
        select = Select(self.find(*self.ROLE_SELECT))
        return [o.get_attribute("value") for o in select.options]

    def go_to_login(self):
        self.click(*self.LOGIN_TAB)
        return self

    def error_message(self) -> str:
        return self.find(*self.ERROR_BANNER).text if self.exists(*self.ERROR_BANNER) else ""

    def name_validation_message(self) -> str:
        el = self.find(*self.NAME_INPUT)
        return self.driver.execute_script("return arguments[0].validationMessage;", el)
