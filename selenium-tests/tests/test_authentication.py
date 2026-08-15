"""
test_authentication.py

Covers: LoginPage + RegisterPage structure, login/register flows, native
HTML5 email validation, logout, and Mock-Mode-specific token behavior.

IMPORTANT (verified from source, not assumed): mockApi.login()
(src/lib/mockApi.js) keeps the session in an in-memory `state.currentUser`
only -- it never calls localStorage.setItem. Only realApi.js (the
VITE_USE_MOCK=false path) writes vulnara_access_token to localStorage. So in
this suite (Mock Mode ON), asserting the token key is ABSENT after a
successful login is the correct assertion, not a bug in the test.
"""

import pytest
from selenium.webdriver.common.by import By

from config import BASE_URL, CREDENTIALS, MOCK_PASSWORD, UNSEEDED_EMAIL, TOKEN_KEY
from pages.login_page import LoginPage
from pages.register_page import RegisterPage
from pages.app_layout import AppLayout

pytestmark = pytest.mark.authentication


# --------------------------------------------------------------- structure

class TestLoginPageStructure:
    def test_login_page_loads(self, driver):
        page = LoginPage(driver).open()
        assert page.is_loaded()

    def test_login_page_has_email_field(self, driver):
        page = LoginPage(driver).open()
        assert page.exists(*page.EMAIL_INPUT)

    def test_login_page_has_password_field(self, driver):
        page = LoginPage(driver).open()
        assert page.exists(*page.PASSWORD_INPUT)

    def test_password_field_has_password_type(self, driver):
        page = LoginPage(driver).open()
        el = page.find(*page.PASSWORD_INPUT)
        assert el.get_attribute("type") == "password"

    def test_email_field_has_email_type(self, driver):
        page = LoginPage(driver).open()
        el = page.find(*page.EMAIL_INPUT)
        assert el.get_attribute("type") == "email"

    def test_login_page_has_submit_button(self, driver):
        page = LoginPage(driver).open()
        assert page.exists(*page.SUBMIT_BUTTON)

    def test_login_page_has_heading(self, driver):
        page = LoginPage(driver).open()
        assert page.exists(*page.HEADING)

    def test_login_page_has_logo(self, driver):
        page = LoginPage(driver).open()
        assert page.exists(*page.LOGO)

    def test_login_page_shows_mock_mode_hint(self, driver):
        page = LoginPage(driver).open()
        assert page.exists(*page.MOCK_MODE_HINT)

    def test_email_and_password_fields_are_required(self, driver):
        page = LoginPage(driver).open()
        email = page.find(*page.EMAIL_INPUT)
        password = page.find(*page.PASSWORD_INPUT)
        assert email.get_attribute("required") is not None
        assert password.get_attribute("required") is not None

    def test_login_page_has_register_tab(self, driver):
        page = LoginPage(driver).open()
        assert page.exists(*page.REGISTER_TAB)


class TestRegisterPageStructure:
    def test_register_page_loads(self, driver):
        page = RegisterPage(driver).open()
        assert page.is_loaded()

    def test_register_has_name_field(self, driver):
        page = RegisterPage(driver).open()
        assert page.exists(*page.NAME_INPUT)

    def test_register_has_email_field(self, driver):
        page = RegisterPage(driver).open()
        assert page.exists(*page.EMAIL_INPUT)

    def test_register_has_password_field(self, driver):
        page = RegisterPage(driver).open()
        assert page.exists(*page.PASSWORD_INPUT)

    def test_register_has_role_select(self, driver):
        page = RegisterPage(driver).open()
        assert page.exists(*page.ROLE_SELECT)

    def test_register_role_select_has_two_options(self, driver):
        page = RegisterPage(driver).open()
        assert page.role_options() == ["client", "analyst"]

    def test_register_has_heading(self, driver):
        page = RegisterPage(driver).open()
        assert page.exists(*page.HEADING)

    def test_register_shows_admin_self_signup_hint(self, driver):
        page = RegisterPage(driver).open()
        assert page.exists(*page.ADMIN_HINT)

    def test_register_has_login_tab(self, driver):
        page = RegisterPage(driver).open()
        assert page.exists(*page.LOGIN_TAB)

    def test_register_name_field_is_required(self, driver):
        page = RegisterPage(driver).open()
        el = page.find(*page.NAME_INPUT)
        assert el.get_attribute("required") is not None

    def test_register_email_field_is_required(self, driver):
        page = RegisterPage(driver).open()
        el = page.find(*page.EMAIL_INPUT)
        assert el.get_attribute("required") is not None


# -------------------------------------------------------------- navigation

class TestLoginRegisterTabNavigation:
    def test_clicking_register_tab_navigates_to_register(self, driver):
        page = LoginPage(driver).open()
        page.go_to_register()
        assert page.on_route("register")

    def test_clicking_login_tab_from_register_navigates_to_login(self, driver):
        page = RegisterPage(driver).open()
        page.go_to_login()
        assert page.on_route("login")


# ------------------------------------------------------------------ login

class TestSuccessfulLogin:
    @pytest.mark.parametrize("role", ["analyst", "admin"])
    def test_login_with_seeded_account_redirects_to_dashboard(self, driver, role):
        page = LoginPage(driver).open()
        page.login(CREDENTIALS[role]["email"], CREDENTIALS[role]["password"])
        assert page.on_route("")

    def test_login_via_enter_key_submits_form(self, driver):
        page = LoginPage(driver).open()
        page.submit_via_enter(CREDENTIALS["analyst"]["email"], CREDENTIALS["analyst"]["password"])
        assert page.on_route("")

    def test_login_shows_correct_full_name_in_sidebar(self, driver):
        page = LoginPage(driver).open()
        page.login(CREDENTIALS["admin"]["email"], CREDENTIALS["admin"]["password"])
        page.on_route("")
        layout = AppLayout(driver)
        assert layout.text_present(CREDENTIALS["admin"]["full_name"])

    def test_login_button_shows_busy_state_while_submitting(self, driver):
        page = LoginPage(driver).open()
        page.type_into(*page.EMAIL_INPUT, CREDENTIALS["analyst"]["email"])
        page.type_into(*page.PASSWORD_INPUT, CREDENTIALS["analyst"]["password"])
        btn = page.find(*page.SUBMIT_BUTTON)
        btn.click()
        # Busy or already-navigated -- either is a valid outcome of a fast mock
        # login; what must NOT happen is staying on /login with an idle button.
        assert page.on_route("") or "SIGNING IN" in btn.text.upper()

    def test_unseeded_email_falls_back_to_default_mock_user(self, driver):
        """Verified behavior: mockApi login() does `find(u => u.email===email)
        || mockUser` -- an email with no matching seeded user still logs in,
        as the default analyst account, rather than failing."""
        page = LoginPage(driver).open()
        page.login(UNSEEDED_EMAIL, MOCK_PASSWORD)
        assert page.on_route("")

    def test_mock_mode_accepts_any_password_for_seeded_email(self, driver):
        page = LoginPage(driver).open()
        page.login(CREDENTIALS["analyst"]["email"], "literally-anything-123")
        assert page.on_route("")


class TestTokenBehaviorInMockMode:
    def test_no_access_token_written_to_localstorage_after_mock_login(self, driver):
        """Mock Mode keeps the session in-memory only (state.currentUser) --
        it never calls localStorage.setItem, unlike the real API transport."""
        page = LoginPage(driver).open()
        page.login(CREDENTIALS["analyst"]["email"], CREDENTIALS["analyst"]["password"])
        page.on_route("")
        assert page.get_token() is None

    def test_no_refresh_token_written_to_localstorage_after_mock_login(self, driver):
        page = LoginPage(driver).open()
        page.login(CREDENTIALS["admin"]["email"], CREDENTIALS["admin"]["password"])
        page.on_route("")
        assert page.get_local_storage_item("vulnara_refresh_token") is None


# --------------------------------------------------------- email validation

MALFORMED_EMAILS = [
    "plainaddress",
    "missing-at-sign.com",
    "user@",
    "@no-local-part.com",
    "user name@example.com",
    "user@@example.com",
    "user@.com",
    "user@exa mple.com",
]

# These look malformed to a human but are genuinely VALID per the WHATWG
# HTML5 living-standard email regex that browsers actually implement for
# input[type=email] constraint validation -- confirmed against the spec
# regex directly (not just observed in CI): the regex doesn't require a TLD
# (so "user@example" with no dot in the domain passes), and its local-part
# character class allows "." anywhere, including a leading position (so
# ".leadingdot@example.com" also passes). A real CI run caught both of
# these as test bugs, not app bugs -- they were originally miscategorized
# as MALFORMED_EMAILS above.
VALID_BUT_SURPRISING_EMAILS = [
    "user@example",
    ".leadingdot@example.com",
]

VALID_LOOKING_EMAILS = [
    "user@example.com",
    "first.last@example.co.in",
    "u@e.io",
    "user+tag@example.com",
]


class TestEmailFormatHandling:
    @pytest.mark.parametrize("bad_email", MALFORMED_EMAILS)
    def test_malformed_emails_fail_native_validation(self, driver, bad_email):
        page = LoginPage(driver).open()
        page.type_into(*page.EMAIL_INPUT, bad_email)
        page.type_into(*page.PASSWORD_INPUT, MOCK_PASSWORD)
        assert page.email_is_valid() is False

    @pytest.mark.parametrize("surprising_email", VALID_BUT_SURPRISING_EMAILS)
    def test_html5_email_validation_is_more_permissive_than_it_looks(self, driver, surprising_email):
        """Documents real, spec-correct browser behavior rather than
        asserting what a human would intuitively expect: the native
        email regex requires no TLD and doesn't restrict dot position in
        the local part, so both of these pass constraint validation."""
        page = LoginPage(driver).open()
        page.type_into(*page.EMAIL_INPUT, surprising_email)
        page.type_into(*page.PASSWORD_INPUT, MOCK_PASSWORD)
        assert page.email_is_valid() is True

    @pytest.mark.parametrize("good_email", VALID_LOOKING_EMAILS)
    def test_valid_looking_emails_pass_native_validation(self, driver, good_email):
        page = LoginPage(driver).open()
        page.type_into(*page.EMAIL_INPUT, good_email)
        page.type_into(*page.PASSWORD_INPUT, MOCK_PASSWORD)
        assert page.email_is_valid() is True

    def test_malformed_email_blocks_form_submission(self, driver):
        page = LoginPage(driver).open()
        page.login("not-an-email", MOCK_PASSWORD)
        # Native validation should prevent navigation away from /login
        assert page.on_route("login", timeout=4)

    def test_register_malformed_email_fails_native_validation(self, driver):
        page = RegisterPage(driver).open()
        page.type_into(*page.EMAIL_INPUT, "bad-email-format")
        el = page.find(*page.EMAIL_INPUT)
        assert driver.execute_script("return arguments[0].checkValidity();", el) is False


# ---------------------------------------------------------------- register

class TestRegisterFlow:
    @pytest.mark.parametrize("role", ["client", "analyst"])
    def test_register_new_account_auto_logs_in_and_redirects(self, driver, role):
        import uuid
        email = f"newuser-{uuid.uuid4().hex[:8]}@vulnara.dev"
        page = RegisterPage(driver).open()
        page.register(full_name="QA New User", email=email, password=MOCK_PASSWORD, role=role)
        assert page.on_route("")

    def test_registered_client_sees_client_role_in_sidebar(self, driver):
        import uuid
        email = f"newclient-{uuid.uuid4().hex[:8]}@vulnara.dev"
        page = RegisterPage(driver).open()
        page.register(full_name="Fresh Client", email=email, password=MOCK_PASSWORD, role="client")
        assert page.on_route(""), "registration did not land on the dashboard within the wait window"
        layout = AppLayout(driver)
        assert layout.text_present("client")

    def test_register_default_role_is_client(self, driver):
        page = RegisterPage(driver).open()
        select_value = page.find(*page.ROLE_SELECT).get_attribute("value")
        assert select_value == "client"


# ------------------------------------------------------------------ logout

class TestLogout:
    def test_logout_button_visible_when_authenticated(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        assert layout.exists(*layout.LOGOUT_BUTTON)

    def test_logout_redirects_to_login(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.logout()
        assert layout.on_route("login")

    def test_logout_then_protected_route_redirects_to_login_again(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.logout()
        layout.on_route("login")
        layout.goto("scans")
        assert layout.on_route("login")
