"""
test_session_management.py

Verified source behavior (src/context/AuthContext.jsx):
    const hasToken = USE_MOCK ? true : !!localStorage.getItem(TOKEN_KEY);
    ...
    useEffect(() => { if (hasToken) { api.me().then(setUser).catch(() => setUser(null)) ... } }, [])

and mockApi.me() (src/lib/mockApi.js) does `requireAuth()` which throws
unless `state.currentUser` is already set in memory. `state.currentUser` is
set only by a successful mockApi.login() call in the CURRENT tab's JS
context -- so on an actual full page reload, `state.currentUser` resets to
null and `api.me()` throws, regardless of `hasToken`. This is a genuine,
verifiable Mock Mode limitation ("Mock Mode is a demo sandbox, not a real
session store" per the code comment) and the tests below assert that real
behavior rather than assuming persistence like a normal backend would give.
"""

import pytest

from config import CREDENTIALS, ROUTES, TOKEN_KEY
from pages.login_page import LoginPage
from pages.app_layout import AppLayout
from pages.base_page import BasePage

pytestmark = pytest.mark.session_management


class TestMockModeSessionDoesNotSurviveReload:
    @pytest.mark.parametrize("route_key", ["dashboard", "scans", "remediations"])
    def test_reloading_a_protected_page_redirects_to_login(self, driver, login_as_analyst, route_key):
        page = BasePage(driver)
        page.goto(ROUTES[route_key])
        page.driver.refresh()
        assert page.on_route("login")

    def test_reloading_the_login_page_itself_stays_on_login(self, driver):
        page = LoginPage(driver).open()
        page.driver.refresh()
        assert page.on_route("login")

    def test_after_reload_user_must_log_in_again_to_reach_dashboard(self, driver, login_as_analyst):
        page = BasePage(driver)
        page.driver.refresh()
        page.on_route("login")
        login = LoginPage(driver)
        login.login(CREDENTIALS["analyst"]["email"], CREDENTIALS["analyst"]["password"])
        assert login.on_route("")


class TestLocalStorageTokenHandling:
    def test_manually_setting_a_fake_token_does_not_grant_access_without_login(self, driver):
        page = BasePage(driver)
        page.goto("login")
        page.set_token("totally-fake-token-value")
        page.goto(ROUTES["dashboard"])
        # hasToken is always true in Mock Mode regardless of the token value,
        # but api.me() still requires an in-memory currentUser -- so a fake
        # token alone must NOT be sufficient to reach the dashboard.
        assert page.on_route("login")

    def test_clearing_local_storage_after_login_does_not_immediately_log_out_current_tab(self, driver, login_as_analyst):
        """currentUser lives in a JS module variable, not localStorage, so
        clearing localStorage alone shouldn't kick out an already-hydrated
        session within the same tab (no reload triggered)."""
        page = BasePage(driver)
        page.clear_local_storage()
        page.goto(ROUTES["scans"])
        assert not page.on_route("login", timeout=4)

    def test_token_key_absent_before_any_login_attempt(self, driver):
        page = BasePage(driver)
        page.goto("login")
        assert page.get_token() is None


class TestMultiTabIsolation:
    def test_new_driver_session_starts_unauthenticated_regardless_of_prior_test(self, driver):
        """Each test gets a fresh Chrome session (see conftest.py `driver`
        fixture) -- this asserts that isolation actually holds."""
        page = BasePage(driver)
        page.goto(ROUTES["dashboard"])
        assert page.on_route("login")


class TestSessionAcrossNavigation:
    def test_session_persists_across_in_app_navigation_without_reload(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.click_nav("scans")
        layout.click_nav("remediations")
        layout.click_nav("dashboard")
        assert not layout.on_route("login", timeout=3)

    def test_session_persists_when_opening_a_detail_page_via_ui_click(self, driver, login_as_analyst):
        from pages.scans_list_page import ScansListPage
        page = ScansListPage(driver).open()
        page.click_row_with_target("acmecorp")
        assert not page.on_route("login", timeout=3)

    def test_logging_out_ends_the_session_for_subsequent_in_app_navigation(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.logout()
        layout.on_route("login")
        layout.goto(ROUTES["dashboard"])
        assert layout.on_route("login")


class TestRoleSessionConsistency:
    @pytest.mark.parametrize("role", ["analyst", "admin"])
    def test_role_stays_consistent_across_multiple_page_visits_in_one_session(self, driver, role):
        page = LoginPage(driver).open()
        page.login(CREDENTIALS[role]["email"], CREDENTIALS[role]["password"])
        page.on_route("")
        layout = AppLayout(driver)
        for route_key in ["scans", "remediations", "dashboard"]:
            layout.goto(ROUTES[route_key])
            assert layout.text_present(role)


class TestSessionExpiryEdgeCases:
    def test_navigating_to_admin_route_after_logout_redirects_to_login_not_dashboard(self, driver, login_as_admin):
        layout = AppLayout(driver)
        layout.logout()
        layout.on_route("login")
        layout.goto(ROUTES["admin_config"])
        assert layout.on_route("login")

    def test_two_sequential_logins_in_the_same_tab_do_not_mix_roles(self, driver):
        page = LoginPage(driver).open()
        page.login(CREDENTIALS["analyst"]["email"], CREDENTIALS["analyst"]["password"])
        page.on_route("")
        layout = AppLayout(driver)
        layout.logout()
        layout.on_route("login")
        login2 = LoginPage(driver)
        login2.login(CREDENTIALS["admin"]["email"], CREDENTIALS["admin"]["password"])
        login2.on_route("")
        assert layout.text_present(CREDENTIALS["admin"]["full_name"])
        assert not layout.text_present(CREDENTIALS["analyst"]["full_name"])

    def test_login_then_immediate_logout_then_login_again_succeeds(self, driver):
        page = LoginPage(driver).open()
        page.login(CREDENTIALS["analyst"]["email"], CREDENTIALS["analyst"]["password"])
        page.on_route("")
        layout = AppLayout(driver)
        layout.logout()
        layout.on_route("login")
        login2 = LoginPage(driver)
        login2.login(CREDENTIALS["analyst"]["email"], CREDENTIALS["analyst"]["password"])
        assert login2.on_route("")

    def test_session_survives_opening_a_deeply_nested_detail_route_directly(self, driver, login_as_analyst):
        page = BasePage(driver)
        page.goto(ROUTES["remediation_review"])
        assert not page.on_route("login", timeout=4)

    def test_admin_session_can_reach_every_admin_route_without_relogin(self, driver, login_as_admin):
        layout = AppLayout(driver)
        for route_key in ["admin_config", "admin_cve"]:
            layout.goto(ROUTES[route_key])
            assert not layout.on_route("login", timeout=3)
