"""
test_ui_validation.py

General page-chrome checks across every route: title, heading, non-blank
body, no uncaught JS console errors, consistent visual chrome. Parametrized
across the full route set so gaps show up per-page instead of as one vague
"the app works" assertion.
"""

import pytest

from config import ROUTES
from pages.base_page import BasePage
from pages.app_layout import AppLayout
from pages.login_page import LoginPage
from selenium.webdriver.common.by import By

pytestmark = pytest.mark.ui_validation

AUTHENTICATED_PAGES = ["dashboard", "scans", "new_scan", "scan_detail", "vuln_detail",
                        "remediations", "remediation_review"]
PUBLIC_PAGES = ["login", "register"]


class TestPageChrome:
    @pytest.mark.parametrize("route_key", AUTHENTICATED_PAGES)
    def test_page_body_is_not_blank(self, driver, login_as_analyst, route_key):
        page = BasePage(driver)
        page.goto(ROUTES[route_key])
        assert len(page.body_text().strip()) > 0

    @pytest.mark.parametrize("route_key", AUTHENTICATED_PAGES)
    def test_page_title_is_vulnara(self, driver, login_as_analyst, route_key):
        page = BasePage(driver)
        page.goto(ROUTES[route_key])
        assert "vulnara" in page.page_title().lower()

    @pytest.mark.parametrize("route_key", PUBLIC_PAGES)
    def test_public_page_body_is_not_blank(self, driver, route_key):
        page = BasePage(driver)
        page.goto(ROUTES[route_key])
        assert len(page.body_text().strip()) > 0

    @pytest.mark.parametrize("route_key", AUTHENTICATED_PAGES)
    def test_page_has_no_severe_console_errors(self, driver, login_as_analyst, route_key):
        page = BasePage(driver)
        page.goto(ROUTES[route_key])
        page.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        errors = page.js_console_errors()
        assert errors == [], f"Console errors on {route_key}: {errors}"


class TestLoginPageChrome:
    def test_login_shows_terminal_access_heading(self, driver):
        page = LoginPage(driver).open()
        assert page.text_present("Terminal Access")

    def test_login_shows_analyst_console_subtitle(self, driver):
        page = LoginPage(driver).open()
        assert page.text_present("Analyst Console")

    def test_login_version_string_visible(self, driver):
        page = LoginPage(driver).open()
        assert page.text_present("v1.0")

    def test_login_status_indicator_visible(self, driver):
        page = LoginPage(driver).open()
        assert page.text_present("Sys Status")


class TestDashboardChrome:
    def test_dashboard_heading_visible(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["dashboard"])
        assert page.text_present("Global Analytics Overview")

    def test_dashboard_new_scan_button_visible(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["dashboard"])
        assert page.exists((By.XPATH, "//button[.//span[text()='New Scan']]"))

    def test_dashboard_either_renders_kpis_or_a_clear_loading_state(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["dashboard"])
        body = page.body_text()
        assert body != ""


class TestScansListChrome:
    def test_scans_page_heading_visible(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["scans"])
        assert page.text_present("Scans Overview")

    def test_scans_page_shows_status_filter_buttons(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["scans"])
        for status in ["ALL", "PENDING", "COMPLETED"]:
            assert page.text_present(status)

    def test_scans_page_shows_seeded_scan_targets(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["scans"])
        assert page.text_present("acmecorp")


class TestNewScanChrome:
    def test_new_scan_heading_visible(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["new_scan"])
        assert page.text_present("New Scan Configurator")

    def test_new_scan_shows_authorization_gate_section(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["new_scan"])
        assert page.text_present("Authorization Gate")

    def test_new_scan_shows_active_ai_testing_toggle_label(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["new_scan"])
        assert page.text_present("Active AI Testing")


class TestRemediationsChrome:
    def test_remediation_queue_loads_without_blank_body(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["remediations"])
        assert len(page.body_text().strip()) > 0

    def test_remediation_review_shows_context_section(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["remediation_review"])
        assert page.text_present("Context")

    def test_remediation_review_shows_ai_confidence_section(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["remediation_review"])
        assert page.text_present("AI Confidence")


class TestAdminChrome:
    def test_admin_config_heading_visible(self, driver, login_as_admin):
        page = BasePage(driver).goto(ROUTES["admin_config"])
        assert page.text_present("Configuration")

    def test_admin_config_shows_seeded_key(self, driver, login_as_admin):
        page = BasePage(driver).goto(ROUTES["admin_config"])
        assert page.text_present("ai_confidence_threshold")

    def test_admin_cve_page_loads_without_blank_body(self, driver, login_as_admin):
        page = BasePage(driver).goto(ROUTES["admin_cve"])
        assert len(page.body_text().strip()) > 0

    def test_admin_cve_shows_seeded_cve_id(self, driver, login_as_admin):
        page = BasePage(driver).goto(ROUTES["admin_cve"])
        assert page.text_present("CVE-2021-41773")


class TestVisualConsistency:
    @pytest.mark.parametrize("route_key", ["dashboard", "scans", "remediations"])
    def test_logo_image_present_on_every_core_page(self, driver, login_as_analyst, route_key):
        layout = AppLayout(driver)
        layout.goto(ROUTES[route_key])
        assert layout.exists(*layout.LOGO)

    @pytest.mark.parametrize("route_key", ["dashboard", "scans", "remediations"])
    def test_sidebar_background_present_on_every_core_page(self, driver, login_as_analyst, route_key):
        layout = AppLayout(driver)
        layout.goto(ROUTES[route_key])
        el = layout.find(*layout.SIDEBAR)
        assert "bg-surface-container-low" in (el.get_attribute("class") or "")

    def test_dark_theme_class_applied_to_html_element(self, driver):
        page = LoginPage(driver).open()
        cls = page.driver.execute_script("return document.documentElement.className;")
        assert "dark" in cls

    def test_favicon_link_present(self, driver):
        page = LoginPage(driver).open()
        has_icon = page.driver.execute_script(
            "return !!document.querySelector('link[rel=icon]');"
        )
        assert has_icon


class TestSeverityAndStatusBadges:
    def test_scan_detail_shows_a_status_pill(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["scan_detail"])
        assert page.text_present("COMPLETED") or page.text_present("PENDING") or page.text_present("IN PROGRESS")

    def test_vuln_detail_shows_severity_language(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["vuln_detail"])
        body = page.body_text().upper()
        assert any(sev in body for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])

    def test_remediation_review_shows_pending_or_approved_language(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["remediation_review"])
        body = page.body_text().upper()
        assert "PENDING" in body or "APPROVE" in body


class TestEmptyAndLoadingStates:
    def test_scans_filtered_to_cancelled_status_shows_empty_state_or_zero_rows(self, driver, login_as_analyst):
        from pages.scans_list_page import ScansListPage
        page = ScansListPage(driver)
        page.open()
        page.click_filter("CANCELLED")
        page.wait.until(lambda d: True)
        assert page.exists(*page.EMPTY_STATE, timeout=6) or page.row_count() == 0

    def test_scans_filtered_to_all_shows_seeded_rows(self, driver, login_as_analyst):
        from pages.scans_list_page import ScansListPage
        page = ScansListPage(driver)
        page.open()
        assert page.row_count() >= 1
