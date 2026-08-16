"""
pages/login_page.py

Field order/labels taken verbatim from lib/screens/login_screen.dart:
  - EditText instance 0: email (_VulnaraField, hint "sysadmin@vulnara.io")
  - EditText instance 1: password (obscured, hint bullets)
  - Button label: "INITIALIZE SESSION"
  - Error text (when present): rendered as a plain Text widget above the
    email field, from AuthLoggedOut.error
"""

from pages.base_page import BasePage

EMAIL_FIELD = 0
PASSWORD_FIELD = 1
SUBMIT_LABEL = "INITIALIZE SESSION"
TITLE_LABEL = "VULNARA"
SUBTITLE_LABEL = "SECURE TERMINAL ACCESS"
EMAIL_SECTION_LABEL = "OPERATOR ID / EMAIL"
PASSWORD_SECTION_LABEL = "ACCESS KEY"
FORGOT_LABEL = "FORGOT CREDENTIALS?"


class LoginPage(BasePage):
    def is_loaded(self, timeout: float = 15) -> bool:
        return self.is_present(self.by_text(TITLE_LABEL), timeout=timeout)

    def enter_email(self, email: str):
        self.enter_text(EMAIL_FIELD, email)

    def enter_password(self, password: str):
        self.enter_text(PASSWORD_FIELD, password)

    def submit(self):
        self.tap_text(SUBMIT_LABEL)

    def login(self, email: str, password: str):
        self.enter_email(email)
        self.enter_password(password)
        self.submit()

    def error_text(self) -> str | None:
        # The error Text widget, when present, sits directly above the
        # email section label in document order; simplest robust check is
        # "any text present that isn't one of the known static labels".
        known = {
            TITLE_LABEL, SUBTITLE_LABEL, EMAIL_SECTION_LABEL, PASSWORD_SECTION_LABEL,
            SUBMIT_LABEL, FORGOT_LABEL, "SYSTEM STATUS: OPTIMAL", "NODE: V-77X",
        }
        for t in self.all_texts():
            if t not in known and t.strip():
                return t
        return None

    def is_still_on_login(self, timeout: float = 3) -> bool:
        return self.is_present(self.by_text(TITLE_LABEL), timeout=timeout)
