"""
test_responsive.py

Verified from source (src/components/AppLayout.jsx): the sidebar `<nav>` is
`className="hidden md:flex ..."` with NO mobile hamburger/drawer alternative
anywhere in the component tree. That means below Tailwind's `md` breakpoint
(768px) the primary navigation is genuinely inaccessible -- not a test bug.
These tests document that real gap explicitly rather than silently passing
or hiding it behind a loose assertion, alongside checks that content itself
still renders (doesn't hard-crash) at small widths.
"""

import pytest

from config import ROUTES
from pages.base_page import BasePage
from pages.app_layout import AppLayout
from pages.login_page import LoginPage

pytestmark = pytest.mark.responsive

DESKTOP = (1440, 900)
TABLET = (820, 1180)
MOBILE = (390, 844)


class TestDesktopViewport:
    def test_sidebar_visible_at_desktop_width(self, driver, login_as_analyst):
        driver.set_window_size(*DESKTOP)
        layout = AppLayout(driver)
        layout.goto(ROUTES["dashboard"])
        assert layout.sidebar_visible()

    def test_dashboard_content_renders_at_desktop_width(self, driver, login_as_analyst):
        driver.set_window_size(*DESKTOP)
        page = BasePage(driver).goto(ROUTES["dashboard"])
        assert len(page.body_text().strip()) > 0


class TestTabletViewport:
    def test_sidebar_visible_at_tablet_width(self, driver, login_as_analyst):
        """768px is exactly Tailwind's `md` breakpoint; 820px is above it,
        so the sidebar should still be visible here."""
        driver.set_window_size(*TABLET)
        layout = AppLayout(driver)
        layout.goto(ROUTES["dashboard"])
        assert layout.sidebar_visible()

    def test_scans_table_still_renders_at_tablet_width(self, driver, login_as_analyst):
        driver.set_window_size(*TABLET)
        page = BasePage(driver).goto(ROUTES["scans"])
        assert page.text_present("Scans Overview")


class TestMobileViewportKnownGap:
    def test_sidebar_is_not_displayed_below_md_breakpoint(self, driver, login_as_analyst):
        """Documents the real, current behavior: `hidden md:flex` removes
        the nav from layout entirely at mobile widths, with no alternative
        entry point provided."""
        driver.set_window_size(*MOBILE)
        layout = AppLayout(driver)
        layout.goto(ROUTES["dashboard"])
        assert not layout.visible(*layout.SIDEBAR, timeout=3)

    def test_no_mobile_menu_button_exists_as_an_alternative(self, driver, login_as_analyst):
        driver.set_window_size(*MOBILE)
        layout = AppLayout(driver)
        layout.goto(ROUTES["dashboard"])
        from selenium.webdriver.common.by import By
        hamburgers = layout.driver.find_elements(
            By.XPATH, "//button[contains(@aria-label,'menu') or contains(@aria-label,'Menu')]"
        )
        assert len(hamburgers) == 0

    def test_main_content_area_still_renders_at_mobile_width_despite_missing_nav(self, driver, login_as_analyst):
        driver.set_window_size(*MOBILE)
        page = BasePage(driver).goto(ROUTES["dashboard"])
        assert len(page.body_text().strip()) > 0

    def test_login_page_is_usable_at_mobile_width(self, driver):
        driver.set_window_size(*MOBILE)
        page = LoginPage(driver).open()
        assert page.is_loaded()

    def test_register_page_is_usable_at_mobile_width(self, driver):
        driver.set_window_size(*MOBILE)
        from pages.register_page import RegisterPage
        page = RegisterPage(driver).open()
        assert page.is_loaded()

    def test_login_form_can_still_be_submitted_at_mobile_width(self, driver):
        from config import CREDENTIALS
        driver.set_window_size(*MOBILE)
        page = LoginPage(driver).open()
        page.login(CREDENTIALS["analyst"]["email"], CREDENTIALS["analyst"]["password"])
        assert page.on_route("")


class TestViewportResizeMidSession:
    def test_resizing_from_desktop_to_mobile_does_not_crash_the_app(self, driver, login_as_analyst):
        driver.set_window_size(*DESKTOP)
        page = BasePage(driver).goto(ROUTES["dashboard"])
        driver.set_window_size(*MOBILE)
        assert len(page.body_text().strip()) > 0

    def test_resizing_from_mobile_to_desktop_restores_sidebar_visibility(self, driver, login_as_analyst):
        driver.set_window_size(*MOBILE)
        layout = AppLayout(driver)
        layout.goto(ROUTES["dashboard"])
        driver.set_window_size(*DESKTOP)
        assert layout.sidebar_visible()

    def test_new_scan_form_remains_usable_across_a_resize(self, driver, login_as_analyst):
        from pages.new_scan_page import NewScanPage
        driver.set_window_size(*DESKTOP)
        page = NewScanPage(driver).open()
        driver.set_window_size(*TABLET)
        page.set_target("resize-check.example.com")
        assert page.find(*page.TARGET_INPUT).get_attribute("value") == "resize-check.example.com"


class TestResponsiveAcrossRoutes:
    @pytest.mark.parametrize("route_key", ["scans", "new_scan", "remediations"])
    def test_route_renders_without_blank_body_at_tablet_width(self, driver, login_as_analyst, route_key):
        driver.set_window_size(*TABLET)
        page = BasePage(driver)
        page.goto(ROUTES[route_key])
        assert len(page.body_text().strip()) > 0

    @pytest.mark.parametrize("route_key", ["scans", "new_scan", "remediations"])
    def test_route_renders_without_blank_body_at_mobile_width(self, driver, login_as_analyst, route_key):
        driver.set_window_size(*MOBILE)
        page = BasePage(driver)
        page.goto(ROUTES[route_key])
        assert len(page.body_text().strip()) > 0


class TestAdminResponsiveness:
    def test_admin_config_renders_at_tablet_width(self, driver, login_as_admin):
        driver.set_window_size(*TABLET)
        page = BasePage(driver).goto(ROUTES["admin_config"])
        assert page.text_present("Configuration")

    def test_admin_cve_renders_at_mobile_width(self, driver, login_as_admin):
        driver.set_window_size(*MOBILE)
        page = BasePage(driver).goto(ROUTES["admin_cve"])
        assert len(page.body_text().strip()) > 0

    def test_admin_nav_items_hidden_at_mobile_width_same_as_core_nav(self, driver, login_as_admin):
        driver.set_window_size(*MOBILE)
        layout = AppLayout(driver)
        layout.goto(ROUTES["admin_config"])
        assert not layout.visible(*layout.SIDEBAR, timeout=3)
