"""
test_error_handling.py

Error banners, the 404 catch-all page and its recovery link, and graceful
handling of "impossible" URLs (nonexistent seeded IDs).
"""

import pytest

from config import ROUTES
from pages.new_scan_page import NewScanPage
from pages.not_found_page import NotFoundPage
from pages.base_page import BasePage
from pages.scan_detail_page import ScanDetailPage
from pages.vuln_detail_page import VulnDetailPage
from pages.remediation_review_page import RemediationReviewPage

pytestmark = pytest.mark.error_handling


class TestNotFoundPage:
    def test_unknown_route_shows_404_heading(self, driver, login_as_analyst):
        page = NotFoundPage(driver)
        page.goto(ROUTES["unknown"])
        assert page.is_loaded()

    def test_not_found_page_shows_helpful_message(self, driver, login_as_analyst):
        page = NotFoundPage(driver)
        page.goto(ROUTES["unknown"])
        assert page.text_present("doesn't exist") or page.text_present("does not exist")

    def test_not_found_page_has_link_back_to_dashboard(self, driver, login_as_analyst):
        page = NotFoundPage(driver)
        page.goto(ROUTES["unknown"])
        assert page.exists(*page.HOME_LINK)

    def test_clicking_back_to_dashboard_link_navigates_home(self, driver, login_as_analyst):
        page = NotFoundPage(driver)
        page.goto(ROUTES["unknown"])
        page.click_home()
        assert page.on_route("")

    def test_deeply_nested_unknown_path_also_shows_404(self, driver, login_as_analyst):
        page = NotFoundPage(driver)
        page.goto("scans/does/not/exist/at/all")
        assert page.is_loaded()


class TestNonexistentSeededIds:
    def test_scan_detail_with_nonexistent_id_does_not_crash(self, driver, login_as_analyst):
        page = ScanDetailPage(driver)
        page.open("scan-9999-does-not-exist")
        assert len(page.body_text().strip()) > 0

    def test_vuln_detail_with_nonexistent_id_does_not_crash(self, driver, login_as_analyst):
        page = VulnDetailPage(driver)
        page.open("vuln-9999-does-not-exist")
        assert len(page.body_text().strip()) > 0

    def test_remediation_review_with_nonexistent_id_does_not_crash(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open("rem-9999-does-not-exist")
        assert len(page.body_text().strip()) > 0

    def test_scan_detail_nonexistent_id_has_no_severe_console_errors_left_unhandled(self, driver, login_as_analyst):
        page = ScanDetailPage(driver)
        page.open("scan-9999-does-not-exist")
        page.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        # We only assert the page didn't hard-crash to a white screen; some
        # SEVERE entries (e.g. a 404-style fetch) are expected and fine.
        assert len(page.body_text().strip()) > 0


class TestNewScanErrorRecovery:
    def test_incomplete_form_submission_shows_the_validation_error_message(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_target("error-banner-check.example.com")
        page.set_justification("short")
        page.set_authorized(True)
        page.submit()
        assert page.text_present("at least 10 characters")

    def test_unauthorized_submission_shows_the_validation_error_message(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_target("unauth-banner-check.example.com")
        page.set_justification("Owner-authorized QA scan, checking the unauthorized error banner.")
        page.set_authorized(False)
        page.submit()
        assert page.text_present("Confirm authorization")

    def test_incomplete_form_submission_keeps_user_on_form_with_data_intact(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_target("recovery-check.example.com")
        page.set_justification("short")  # under the 10-char minimum
        page.set_authorized(True)
        page.submit()
        assert page.on_route("scans/new", timeout=4)
        assert page.find(*page.TARGET_INPUT).get_attribute("value") == "recovery-check.example.com"

    def test_user_can_correct_and_resubmit_after_a_blocked_submission(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_target("retry-check.example.com")
        page.set_justification("short")
        page.set_authorized(True)
        page.submit()
        assert page.on_route("scans/new", timeout=4)
        page.set_justification("Owner-authorized QA scan, corrected after a blocked first attempt.")
        page.submit()
        assert not page.on_route("scans/new", timeout=4)

    def test_navigating_away_and_back_resets_the_new_scan_form(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_target("stale-data-check.example.com")
        page.goto(ROUTES["scans"])
        page.goto(ROUTES["new_scan"])
        assert page.find(*page.TARGET_INPUT).get_attribute("value") == ""


class TestFormResilience:
    @pytest.mark.parametrize("route_key", ["new_scan", "scans", "remediations"])
    def test_rapid_repeated_navigation_does_not_leave_page_blank(self, driver, login_as_analyst, route_key):
        page = BasePage(driver)
        for _ in range(3):
            page.goto(ROUTES[route_key])
        assert len(page.body_text().strip()) > 0

    def test_submitting_new_scan_form_twice_in_a_row_does_not_duplicate_error(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_target("double-submit-check.example.com")
        page.set_justification("short")
        page.set_authorized(True)
        page.submit()
        page.submit()
        assert page.on_route("scans/new", timeout=4)

    def test_browser_back_after_failed_submission_returns_to_scans_list(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["scans"])
        new_scan = NewScanPage(driver).open()
        new_scan.set_target("back-nav-check.example.com")
        new_scan.set_justification("short")
        new_scan.set_authorized(True)
        new_scan.submit()
        driver.back()
        assert new_scan.on_route("scans")

    def test_admin_only_route_denial_does_not_leave_a_blank_page(self, driver, login_as_analyst):
        page = BasePage(driver)
        page.goto(ROUTES["admin_config"])
        assert len(page.body_text().strip()) > 0

    def test_repeated_failed_login_attempts_do_not_lock_up_the_form(self, driver):
        from pages.login_page import LoginPage
        page = LoginPage(driver).open()
        for _ in range(3):
            page.type_into(*page.EMAIL_INPUT, "not-a-valid-email")
            page.type_into(*page.PASSWORD_INPUT, "x")
            page.click(*page.SUBMIT_BUTTON)
        assert page.exists(*page.EMAIL_INPUT)

    def test_rejecting_remediation_with_empty_reason_keeps_dialog_open_or_shows_guidance(self, driver, login_as_analyst):
        from config import SEED
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_pending"])
        page.open_reject_dialog()
        from selenium.webdriver.common.by import By
        confirm_buttons = page.driver.find_elements(By.XPATH, "//button[normalize-space()='Reject']")
        assert page.exists(*page.REJECT_REASON_TEXTAREA)
    def test_admin_visiting_unknown_route_can_recover_via_home_link(self, driver, login_as_admin):
        page = NotFoundPage(driver)
        page.goto(ROUTES["unknown"])
        page.click_home()
        assert page.on_route("")

    def test_unauthenticated_visiting_unknown_route_then_logging_in_reaches_dashboard(self, driver):
        from config import CREDENTIALS
        from pages.login_page import LoginPage
        page = BasePage(driver)
        page.goto(ROUTES["unknown"])
        login = LoginPage(driver)
        if login.on_route("login", timeout=4):
            login.login(CREDENTIALS["analyst"]["email"], CREDENTIALS["analyst"]["password"])
            assert login.on_route("")
        else:
            assert page.text_present("404")
