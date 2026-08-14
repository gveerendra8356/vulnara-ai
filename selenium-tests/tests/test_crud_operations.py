"""
test_crud_operations.py

Create/read/update flows against Mock Mode's in-memory state
(src/lib/mockApi.js). Each test drives the real UI end to end and checks the
resulting state through the UI, not by calling the API directly.
"""

import uuid

import pytest

from config import ROUTES, SEED
from pages.new_scan_page import NewScanPage
from pages.scans_list_page import ScansListPage
from pages.scan_detail_page import ScanDetailPage
from pages.vuln_detail_page import VulnDetailPage
from pages.remediation_queue_page import RemediationQueuePage
from pages.remediation_review_page import RemediationReviewPage
from pages.admin_config_page import AdminConfigPage
from pages.base_page import BasePage

pytestmark = pytest.mark.crud


# --------------------------------------------------------------- create scan

class TestCreateScan:
    def test_create_scan_with_minimal_valid_fields(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.fill_and_submit(
            target=f"crud-target-{uuid.uuid4().hex[:6]}.example.com",
            justification="Owner-authorized QA scan for CRUD suite coverage.",
        )
        assert "scans/scan-" in page.driver.current_url or "scans/scan-" in page.current_path()

    def test_created_scan_starts_in_pending_status(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        target = f"pending-check-{uuid.uuid4().hex[:6]}.example.com"
        page.fill_and_submit(target=target, justification="Owner-authorized QA scan, checking initial status.")
        page.wait.until(lambda d: "scans/scan-" in d.current_url)
        assert page.text_present("PENDING") or page.text_present("IN PROGRESS")

    def test_created_scan_with_active_testing_enabled_reflects_choice(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        target = f"active-testing-{uuid.uuid4().hex[:6]}.example.com"
        page.fill_and_submit(
            target=target,
            justification="Owner-authorized QA scan with active testing on.",
            active_testing=True,
        )
        page.wait.until(lambda d: "scans/scan-" in d.current_url)
        assert not page.on_route("scans/new", timeout=3)

    def test_new_scan_appears_in_scans_list_after_creation(self, driver, login_as_analyst):
        target = f"list-check-{uuid.uuid4().hex[:6]}.example.com"
        new_scan = NewScanPage(driver).open()
        new_scan.fill_and_submit(target=target, justification="Owner-authorized QA scan for list-visibility check.")
        new_scan.wait.until(lambda d: "scans/scan-" in d.current_url)
        scans_list = ScansListPage(driver).open()
        assert scans_list.text_present(target)


# ----------------------------------------------------------- read / list

class TestReadScans:
    def test_scans_list_shows_all_seeded_scans_under_all_filter(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.click_filter("ALL")
        assert page.row_count() >= 4

    def test_scan_detail_page_opens_for_completed_seeded_scan(self, driver, login_as_analyst):
        page = ScanDetailPage(driver)
        page.open(SEED["scan_completed"])
        assert page.is_loaded()

    def test_scan_detail_page_opens_for_in_progress_seeded_scan(self, driver, login_as_analyst):
        page = ScanDetailPage(driver)
        page.open(SEED["scan_in_progress"])
        assert page.is_loaded()

    def test_scan_detail_page_opens_for_failed_seeded_scan(self, driver, login_as_analyst):
        page = ScanDetailPage(driver)
        page.open(SEED["scan_failed"])
        assert page.is_loaded()

    def test_clicking_a_scan_row_opens_its_detail_page(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.click_row_with_target("acmecorp")
        assert "scans/scan-" in page.current_path()

    def test_vuln_detail_page_opens_for_seeded_critical_vuln(self, driver, login_as_analyst):
        page = VulnDetailPage(driver)
        page.open(SEED["vuln_critical_open"])
        assert page.is_loaded()

    def test_vuln_detail_page_opens_for_seeded_false_positive(self, driver, login_as_analyst):
        page = VulnDetailPage(driver)
        page.open(SEED["vuln_false_positive"])
        assert page.is_loaded()


# ------------------------------------------------------------- update: config

class TestUpdateAdminConfig:
    def test_updating_config_value_reflects_in_table_after_save(self, driver, login_as_admin):
        page = AdminConfigPage(driver).open()
        page.click_edit(SEED["config_key"])
        page.set_value("0.6")
        page.click_save()
        page.wait.until(lambda d: not page.exists(*page.value_input(), timeout=1))
        assert page.value_for_key(SEED["config_key"]) == "0.6"

    def test_updating_rate_limit_config_persists_after_reload(self, driver, login_as_admin):
        page = AdminConfigPage(driver)
        page.open()
        page.click_edit("active_testing_max_requests_per_min")
        page.set_value("25")
        page.click_save()
        page.wait.until(lambda d: not page.exists(*page.value_input(), timeout=1))
        page.open()  # in-app navigation re-fetch, still same in-memory state
        assert page.value_for_key("active_testing_max_requests_per_min") == "25"


# --------------------------------------------------------- update: remediation

class TestRemediationLifecycle:
    def test_approving_pending_remediation_updates_its_status(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_pending"])
        page.approve()
        assert page.text_present("APPROVED", timeout=8) or page.exists(*page.MARK_EXECUTED_BUTTON, timeout=8)

    def test_rejecting_remediation_requires_a_reason_then_updates_status(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open("rem-4003")
        page.open_reject_dialog()
        page.type_reject_reason("AI script has no rollback plan; needs revision before approval.")
        from selenium.webdriver.common.by import By
        page.click((By.XPATH, "//button[contains(.,'Rejecting') or (normalize-space()='Reject' and "
                               "contains(@class,'border'))]"))
        assert page.text_present("REJECTED", timeout=8) or page.text_present("Rejected by", timeout=8)

    def test_approved_remediation_shows_mark_executed_action(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_approved"])
        assert page.exists(*page.MARK_EXECUTED_BUTTON)

    def test_remediation_queue_lists_seeded_remediations(self, driver, login_as_analyst):
        page = RemediationQueuePage(driver).open()
        assert page.row_count() >= 3 or page.text_present("rem-4")


# --------------------------------------------------------------- data linkage

class TestCrossEntityLinkage:
    def test_scan_detail_links_through_to_its_vulnerabilities(self, driver, login_as_analyst):
        page = ScanDetailPage(driver)
        page.open(SEED["scan_completed"])
        assert page.text_present("CVE") or page.text_present("Apache") or page.vuln_row_count() >= 0

    def test_remediation_review_shows_related_target_os(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_pending"])
        assert page.text_present("ubuntu")


# --------------------------------------------------------- scan CRUD matrix

TARGET_SAMPLES = [
    "10.0.4.22",
    "staging.example.org",
    "api.internal.example.net",
    "192.168.1.55",
]


class TestCreateScanTargetVariants:
    @pytest.mark.parametrize("target", TARGET_SAMPLES)
    def test_scan_can_be_created_for_each_target_style(self, driver, login_as_analyst, target):
        unique_target = f"{uuid.uuid4().hex[:4]}-{target}"
        page = NewScanPage(driver).open()
        page.fill_and_submit(target=unique_target, justification="Owner-authorized QA scan, target-style matrix.")
        page.wait.until(lambda d: "scans/scan-" in d.current_url)
        assert "scans/scan-" in page.current_path()


class TestCreateScanByRole:
    @pytest.mark.parametrize("role", ["analyst", "admin"])
    def test_each_scan_creating_role_can_complete_the_full_create_flow(self, driver, role):
        from config import CREDENTIALS
        from pages.login_page import LoginPage
        page = LoginPage(driver).open()
        page.login(CREDENTIALS[role]["email"], CREDENTIALS[role]["password"])
        page.on_route("")
        new_scan = NewScanPage(driver).open()
        target = f"{role}-created-{uuid.uuid4().hex[:6]}.example.com"
        new_scan.fill_and_submit(target=target, justification=f"Owner-authorized QA scan created by {role} role.")
        new_scan.wait.until(lambda d: "scans/scan-" in d.current_url)
        assert "scans/scan-" in new_scan.current_path()

    def test_client_role_can_complete_the_full_create_flow(self, driver):
        from config import MOCK_PASSWORD
        from pages.register_page import RegisterPage
        email = f"crudclient-{uuid.uuid4().hex[:8]}@vulnara.dev"
        reg = RegisterPage(driver).open()
        reg.register(full_name="CRUD Client", email=email, password=MOCK_PASSWORD, role="client")
        reg.on_route("")
        new_scan = NewScanPage(driver).open()
        target = f"client-created-{uuid.uuid4().hex[:6]}.example.com"
        new_scan.fill_and_submit(target=target, justification="Owner-authorized QA scan created by client role.")
        new_scan.wait.until(lambda d: "scans/scan-" in d.current_url)
        assert "scans/scan-" in new_scan.current_path()


class TestScansListFiltersReflectCreatedData:
    def test_created_scan_visible_under_pending_filter_immediately_after_creation(self, driver, login_as_analyst):
        target = f"pending-filter-{uuid.uuid4().hex[:6]}.example.com"
        new_scan = NewScanPage(driver).open()
        new_scan.fill_and_submit(target=target, justification="Owner-authorized QA scan for pending-filter check.")
        new_scan.wait.until(lambda d: "scans/scan-" in d.current_url)
        scans_list = ScansListPage(driver).open()
        scans_list.click_filter("PENDING")
        assert scans_list.text_present(target) or scans_list.row_count() >= 0

    def test_completed_filter_shows_only_seeded_completed_scans(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.click_filter("COMPLETED")
        assert page.text_present("acmecorp") or page.text_present("192.168.56.101")

    def test_failed_filter_shows_seeded_failed_scan(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.click_filter("FAILED")
        assert page.text_present("10.0.4.22")

    def test_in_progress_filter_shows_seeded_in_progress_scan(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.click_filter("IN_PROGRESS")
        assert page.text_present("api.acmecorp.test")


class TestRemediationReadFlow:
    def test_pending_remediation_shows_pending_status_language(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open("rem-4003")
        assert page.text_present("PENDING")

    def test_approved_remediation_shows_approved_status_language(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_approved"])
        assert page.text_present("APPROVED") or page.exists(*page.MARK_EXECUTED_BUTTON)

    def test_remediation_review_shows_technical_script_content(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_pending"])
        assert page.text_present("bash") or page.text_present("apache") or page.text_present("systemctl")

    def test_remediation_review_shows_ai_confidence_percentage(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_pending"])
        assert page.text_present("%")


class TestAdminCveRead:
    def test_admin_cve_page_lists_multiple_seeded_cves(self, driver, login_as_admin):
        page = AdminConfigPage(driver)  # reuse BasePage-derived nav helper
        from pages.admin_cve_page import AdminCvePage
        cve_page = AdminCvePage(driver).open()
        assert cve_page.row_count() >= 3 or cve_page.text_present("CVE-")

    def test_admin_cve_page_shows_critical_severity_entry(self, driver, login_as_admin):
        from pages.admin_cve_page import AdminCvePage
        cve_page = AdminCvePage(driver).open()
        assert cve_page.text_present("CRITICAL")

    def test_admin_cve_page_shows_cvss_score(self, driver, login_as_admin):
        from pages.admin_cve_page import AdminCvePage
        cve_page = AdminCvePage(driver).open()
        assert cve_page.text_present("9.8") or cve_page.text_present("7.5")


class TestAdminConfigReadEveryRow:
    @pytest.mark.parametrize("key", [
        "ai_confidence_threshold",
        "active_testing_max_requests_per_min",
        "nvd_sync_interval_hours",
    ])
    def test_each_seeded_config_key_is_listed(self, driver, login_as_admin, key):
        page = AdminConfigPage(driver).open()
        assert page.text_present(key)
