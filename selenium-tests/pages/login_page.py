"""
Login page object.
Source: vulnara-web/src/pages/LoginPage.jsx
No data-testid/name/id attributes exist in this component -- selectors below
are the most stable available: input[type=email], input[type=password],
button[type=submit], and exact visible copy ("INITIALIZE LINK" / "Register").
"""

from selenium.webdriver.common.by import By

from .base_page import BasePage


class LoginPage(BasePage):
    EMAIL_INPUT = (By.CSS_SELECTOR, "input[type='email']")
    PASSWORD_INPUT = (By.CSS_SELECTOR, "input[type='password']")
    SUBMIT_BUTTON = (By.CSS_SELECTOR, "form button[type='submit']")
    REGISTER_TAB = (By.XPATH, "//button[normalize-space()='Register']")
    ERROR_BANNER = (By.XPATH, "//*[contains(@class,'text-error')]")
    HEADING = (By.XPATH, "//h1[contains(text(),'Terminal Access')]")
    LOGO = (By.CSS_SELECTOR, "img[alt='Vulnara Logo']")
    MOCK_MODE_HINT = (By.XPATH, "//*[contains(text(),'Mock Mode is on')]")

    def open(self):
        self.goto("login")
        return self

    def is_loaded(self) -> bool:
        return self.exists(*self.EMAIL_INPUT) and self.exists(*self.PASSWORD_INPUT)

    def login(self, email: str, password: str, submit: bool = True):
        if email is not None:
            self.type_into(*self.EMAIL_INPUT, email)
        if password is not None:
            self.type_into(*self.PASSWORD_INPUT, password)
        if submit:
            self.click(*self.SUBMIT_BUTTON)
        return self

    def submit_via_enter(self, email: str, password: str):
        pw_el = self.type_into(*self.PASSWORD_INPUT, password)
        self.type_into(*self.EMAIL_INPUT, email)
        from selenium.webdriver.common.keys import Keys
        pw_el.send_keys(Keys.RETURN)
        return self

    def go_to_register(self):
        self.click(*self.REGISTER_TAB)
        return self

    def error_message(self) -> str:
        return self.find(*self.ERROR_BANNER).text if self.exists(*self.ERROR_BANNER) else ""

    def email_validation_message(self) -> str:
        """Native HTML5 constraint-validation message (e.g. invalid email format)."""
        el = self.find(*self.EMAIL_INPUT)
        return self.driver.execute_script("return arguments[0].validationMessage;", el)

    def email_is_valid(self) -> bool:
        el = self.find(*self.EMAIL_INPUT)
        return self.driver.execute_script("return arguments[0].checkValidity();", el)
