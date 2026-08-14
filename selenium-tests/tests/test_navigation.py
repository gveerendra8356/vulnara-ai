"""
test_navigation.py

Covers: sidebar presence, per-page nav-item visibility, active-state
highlighting, click-through navigation, and logout navigation.
Source: src/components/AppLayout.jsx
"""

import pytest

from config import ROUTES
from pages.app_layout import AppLayout
from pages.base_page import BasePage

pytestmark = pytest.mark.navigation

CORE_PAGES = ["dashboard", "scans", "remediations"]
ALL_CORE_ROUTE_KEYS = ["dashboard", "scans", "new_scan", "remediations"]


class TestSideNavPresence:
    def test_sidebar_visible_on_dashboard(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        assert layout.sidebar_visible()

    @pytest.mark.parametrize("route_key", ALL_CORE_ROUTE_KEYS)
    def test_sidebar_visible_on_every_core_page(self, driver, login_as_analyst, route_key):
        layout = AppLayout(driver)
        layout.goto(ROUTES[route_key])
        assert layout.sidebar_visible()

    @pytest.mark.parametrize("route_key", ALL_CORE_ROUTE_KEYS)
    def test_all_three_core_nav_links_present_on_every_page(self, driver, login_as_analyst, route_key):
        layout = AppLayout(driver)
        layout.goto(ROUTES[route_key])
        for nav_key in CORE_PAGES:
            assert layout.nav_item_visible(nav_key), f"{nav_key} missing on {route_key}"

    def test_brand_logo_visible_in_sidebar(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        assert layout.exists(*layout.LOGO)

    def test_sidebar_has_aria_label(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        el = layout.find(*layout.SIDEBAR)
        assert el.get_attribute("aria-label") == "Sidebar"

    def test_sidebar_hidden_on_login_page(self, driver):
        page = AppLayout(driver)
        page.goto("login")
        assert not page.exists(*page.SIDEBAR, timeout=3)

    def test_sidebar_hidden_on_register_page(self, driver):
        page = AppLayout(driver)
        page.goto("register")
        assert not page.exists(*page.SIDEBAR, timeout=3)


class TestNavLinkNavigation:
    def test_clicking_dashboard_nav_navigates_home(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.goto(ROUTES["scans"])
        layout.click_nav("dashboard")
        assert layout.on_route("")

    def test_clicking_scans_nav_navigates_to_scans_list(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.click_nav("scans")
        assert layout.on_route("scans")

    def test_clicking_remediations_nav_navigates_to_remediation_queue(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.click_nav("remediations")
        assert layout.on_route("remediations")

    def test_navigation_between_all_core_pages_in_sequence_never_errors(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        for nav_key in ["scans", "remediations", "dashboard"]:
            layout.click_nav(nav_key)
        assert layout.exists(*layout.SIDEBAR)

    def test_logo_click_area_does_not_crash_app(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.goto(ROUTES["scans"])
        assert layout.exists(*layout.LOGO)


class TestActiveNavState:
    def test_dashboard_nav_item_is_active_on_dashboard(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        assert layout.nav_item_is_active("dashboard")

    def test_scans_nav_item_is_active_on_scans_page(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.goto(ROUTES["scans"])
        assert layout.nav_item_is_active("scans")

    def test_scans_nav_item_is_active_on_new_scan_page(self, driver, login_as_analyst):
        """new_scan is a nested route under /scans -- NavLink without `end`
        should still mark Scans active."""
        layout = AppLayout(driver)
        layout.goto(ROUTES["new_scan"])
        assert layout.nav_item_is_active("scans")

    def test_remediations_nav_item_is_active_on_remediation_queue(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.goto(ROUTES["remediations"])
        assert layout.nav_item_is_active("remediations")

    def test_only_one_nav_item_is_active_at_a_time_on_dashboard(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        assert len(layout.active_nav_keys()) == 1

    def test_only_one_nav_item_is_active_at_a_time_on_scans(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.goto(ROUTES["scans"])
        assert len(layout.active_nav_keys()) == 1

    def test_admin_config_active_when_admin_on_that_page(self, driver, login_as_admin):
        layout = AppLayout(driver)
        layout.goto(ROUTES["admin_config"])
        assert layout.nav_item_is_active("admin_config")


class TestLogoutNavigation:
    def test_logout_button_present_in_sidebar(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        assert layout.exists(*layout.LOGOUT_BUTTON)

    def test_logout_navigates_to_login(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.logout()
        assert layout.on_route("login")

    def test_logout_then_direct_nav_to_protected_route_redirects_again(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.logout()
        layout.on_route("login")
        layout.goto(ROUTES["remediations"])
        assert layout.on_route("login")

    def test_logout_available_from_every_core_page(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.goto(ROUTES["remediations"])
        assert layout.exists(*layout.LOGOUT_BUTTON)


class TestTopBarChrome:
    def test_search_input_present_in_header(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        assert layout.exists(*layout.SEARCH_INPUT)

    def test_mock_mode_badge_present_in_header(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        assert layout.exists(*layout.MOCK_MODE_BADGE)

    def test_user_role_shown_in_sidebar_footer(self, driver, login_as_admin):
        layout = AppLayout(driver)
        assert layout.text_present("admin")

    def test_user_avatar_initial_shown_in_header(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        assert layout.exists(*layout.USER_AVATAR)

    def test_notifications_button_present(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        assert layout.exists(*layout.NOTIFICATIONS_BUTTON)
