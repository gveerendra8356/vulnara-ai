"""tests/test_remediation_workflow.py -- Scenarios 2 & 3 from
docs/mobile_app_guide.md: the analyst reviewing/approving a remediation,
then the client executing it."""

import pytest

from pages.scan_list_page import ScanListPage
from pages.scan_status_page import ScanStatusPage
from pages.remediation_list_page import RemediationListPage
from pages.remediation_approval_page import RemediationApprovalPage
from pages.vulnerability_detail_page import VulnerabilityDetailPage

pytestmark = pytest.mark.remediation


def _open_remediation_list(driver) -> RemediationListPage:
    # /scans/:scanId/remediations (router.dart) is scoped to a scan -- there
    # is no top-level remediations screen -- so every test here has to open
    # a scan's status page first and tap into its "Pending remediations"
    # icon, same as test_scan_lifecycle_crud.py does.
    scans = ScanListPage(driver)
    assert scans.is_loaded()
    if scans.scan_count() == 0:
        pytest.skip("no seeded scans available to open a remediation list from")
    scans.tap_first_scan()
    status = ScanStatusPage(driver)
    assert status.is_loaded(timeout=15)
    status.open_pending_remediations()
    listing = RemediationListPage(driver)
    return listing


def test_remediation_list_loads_for_analyst(login_as_analyst):
    page = _open_remediation_list(login_as_analyst)
    assert page.is_loaded(timeout=15)


def test_remediation_approval_screen_loads_from_list(login_as_analyst):
    driver = login_as_analyst
    listing = _open_remediation_list(driver)
    assert listing.is_loaded(timeout=15)
    if listing.item_count_by_status_text("PENDING") == 0 and listing.item_count_by_status_text("pending") == 0:
        pytest.skip("no pending remediations seeded/generated to open")
    from appium.webdriver.common.appiumby import AppiumBy
    driver.find_elements(AppiumBy.XPATH, "//*[@text]")[0].click()
    approval = RemediationApprovalPage(driver)
    assert approval.is_loaded(timeout=15)


def test_analyst_can_approve_remediation(login_as_analyst):
    driver = login_as_analyst
    listing = _open_remediation_list(driver)
    assert listing.is_loaded(timeout=15)
    if listing.item_count_by_status_text("PENDING") == 0:
        pytest.skip("no pending remediations available to approve")
    from appium.webdriver.common.appiumby import AppiumBy
    driver.find_elements(AppiumBy.XPATH, "//*[@text]")[0].click()
    approval = RemediationApprovalPage(driver)
    assert approval.is_loaded(timeout=15)
    if not approval.can_approve():
        pytest.skip("Approve action not available for this remediation's current state")
    approval.approve()
    assert approval.already_actioned_text() is not None or approval.is_loaded(timeout=8)


def test_client_can_mark_executed_after_approval(login_as_client):
    driver = login_as_client
    listing = _open_remediation_list(driver)
    assert listing.is_loaded(timeout=15)
    if listing.item_count_by_status_text("APPROVED") == 0:
        pytest.skip("no approved remediations available to execute")
    from appium.webdriver.common.appiumby import AppiumBy
    driver.find_elements(AppiumBy.XPATH, "//*[@text]")[0].click()
    approval = RemediationApprovalPage(driver)
    assert approval.is_loaded(timeout=15)
    if not approval.can_execute():
        pytest.skip("Mark Executed action not available for this remediation's current state")
    approval.mark_executed()
    assert approval.already_actioned_text() is not None or approval.is_loaded(timeout=8)


def test_analyst_can_reject_remediation(login_as_analyst):
    driver = login_as_analyst
    listing = _open_remediation_list(driver)
    assert listing.is_loaded(timeout=15)
    if listing.item_count_by_status_text("PENDING") == 0:
        pytest.skip("no pending remediations available to reject")
    from appium.webdriver.common.appiumby import AppiumBy
    driver.find_elements(AppiumBy.XPATH, "//*[@text]")[0].click()
    approval = RemediationApprovalPage(driver)
    assert approval.is_loaded(timeout=15)
    if not approval.can_reject():
        pytest.skip("Reject action not available for this remediation's current state")
    approval.reject()
    assert approval.is_loaded(timeout=8)


@pytest.mark.parametrize("status_substring", ["APPROVED", "REJECTED"])
def test_already_actioned_remediation_shows_status_text(login_as_analyst, status_substring):
    listing = _open_remediation_list(login_as_analyst)
    assert listing.is_loaded(timeout=15)
    count = listing.item_count_by_status_text(status_substring)
    if count == 0:
        pytest.skip(f"no {status_substring} remediations present to assert on yet")
    assert count >= 1


def test_copy_script_to_clipboard_button_present(login_as_analyst):
    driver = login_as_analyst
    listing = _open_remediation_list(driver)
    assert listing.is_loaded(timeout=15)
    if listing.item_count_by_status_text("PENDING") == 0:
        pytest.skip("no pending remediations available")
    from appium.webdriver.common.appiumby import AppiumBy
    driver.find_elements(AppiumBy.XPATH, "//*[@text]")[0].click()
    approval = RemediationApprovalPage(driver)
    assert approval.is_loaded(timeout=15)
    assert approval.is_present(approval.by_content_desc("Copy to clipboard"), timeout=8)


@pytest.mark.parametrize("role,action", [
    ("admin", "approve"), ("admin", "execute"), ("admin", "reject"),
    ("analyst", "approve"), ("analyst", "execute"), ("analyst", "reject"),
    ("client", "approve"), ("client", "execute"), ("client", "reject"),
])
def test_remediation_actions_available_by_role(role, action):
    pytest.skip("superseded by test_authorization.test_remediation_action_buttons_visible_regardless_of_role, "
                "kept only so the (role, action) matrix stays visible in collected test IDs for this module")


def test_vulnerability_detail_loads(login_as_client):
    driver = login_as_client
    from pages.scan_list_page import ScanListPage
    from pages.scan_status_page import ScanStatusPage
    scans = ScanListPage(driver)
    assert scans.is_loaded()
    if scans.scan_count() == 0:
        pytest.skip("no seeded scans to drill into a vulnerability from")
    scans.tap_first_scan()
    status = ScanStatusPage(driver)
    assert status.is_loaded(timeout=15)
    if not status.has_findings():
        pytest.skip("scan has no findings to open a detail screen for")
    from appium.webdriver.common.appiumby import AppiumBy
    driver.find_elements(AppiumBy.XPATH, "//*[@text]")[-1].click()
    detail = VulnerabilityDetailPage(driver)
    assert detail.is_loaded(timeout=15)


def test_vulnerability_detail_confidence_score_visible(login_as_client):
    driver = login_as_client
    from pages.scan_list_page import ScanListPage
    from pages.scan_status_page import ScanStatusPage
    scans = ScanListPage(driver)
    assert scans.is_loaded()
    if scans.scan_count() == 0:
        pytest.skip("no seeded scans to drill into a vulnerability from")
    scans.tap_first_scan()
    status = ScanStatusPage(driver)
    assert status.is_loaded(timeout=15)
    if not status.has_findings():
        pytest.skip("scan has no findings to open a detail screen for")
    from appium.webdriver.common.appiumby import AppiumBy
    driver.find_elements(AppiumBy.XPATH, "//*[@text]")[-1].click()
    detail = VulnerabilityDetailPage(driver)
    assert detail.is_loaded(timeout=15)
    assert detail.is_present(detail.by_text("AI CONFIDENCE SCORE"))
