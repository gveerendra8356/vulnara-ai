from pages.base_page import BasePage

# lib/screens/profile_screen.dart: the "Account Info" tab label (there is no
# "Account Settings" section anywhere on this screen) and no version string
# rendered anywhere in the UI.
ACCOUNT_SETTINGS_LABEL = "ACCOUNT INFO"
LOGOUT_LABEL = "LOG OUT"
VERSION_LABEL = "v2.4.1"


class ProfilePage(BasePage):
    def is_loaded(self, timeout: float = 15) -> bool:
        return self.is_present(self.by_text(ACCOUNT_SETTINGS_LABEL), timeout=timeout) or \
            self.is_present(self.by_text(LOGOUT_LABEL), timeout=timeout)

    def display_name_text(self) -> str | None:
        # First non-empty text at the top of the card that isn't one of the
        # known static labels/role chip text -- see full_name in
        # profile_screen.dart ("Unknown Operator" fallback).
        known = {ACCOUNT_SETTINGS_LABEL, LOGOUT_LABEL, VERSION_LABEL}
        for t in self.all_texts():
            if t not in known and t.strip() and not t.isupper():
                return t
        return None

    def role_chip_text(self) -> str | None:
        for t in self.all_texts():
            if t.upper() == t and t.lower() in ("admin", "analyst", "client"):
                return t
        return None

    def logout(self):
        self.tap_text(LOGOUT_LABEL)
