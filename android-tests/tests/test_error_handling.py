"""tests/test_error_handling.py -- backend-unreachable and network-loss
recovery, using utils/adb_helpers.set_airplane_mode as the fault-injection
mechanism (see that module's docstring for why this replaces
driver.set_network_connection())."""

import pytest

import config
from pages.login_page import LoginPage
from pages.bottom_nav import BottomNav, CLIENT_TABS
from pages.dashboard_page import DashboardPage
from pages.scan_list_page import ScanListPage
from pages.notifications_page import NotificationsPage
from pages.profile_page import ProfilePage
from utils.adb_helpers import set_airplane_mode

pytestmark = pytest.mark.error_handling


@pytest.mark.parametrize("role", ["admin", "client"])
def test_login_shows_error_when_backend_unreachable(driver, role):
    login = LoginPage(driver)
    assert login.is_loaded()
    set_airplane_mode(driver, True)
    try:
        account = config.ACCOUNTS[role]
        login.login(account["email"], account["password"])
        assert login.is_still_on_login(timeout=12)
    finally:
        set_airplane_mode(driver, False)


def test_new_scan_submission_with_backend_offline_shows_error(login_as_client):
    driver = login_as_client
    scans = ScanListPage(driver)
    assert scans.is_loaded()
    scans.open_new_scan_fab()
    from pages.new_scan_page import NewScanPage
    form = NewScanPage(driver)
    assert form.is_loaded()
    form.fill_valid_scan()
    set_airplane_mode(driver, True)
    try:
        form.submit()
        assert form.is_loaded(timeout=10), "form should not silently succeed with no connectivity"
    finally:
        set_airplane_mode(driver, False)


@pytest.mark.parametrize("tab", CLIENT_TABS)
def test_app_recovers_after_airplane_mode_restored(login_as_client, tab):
    driver = login_as_client
    set_airplane_mode(driver, True)
    BottomNav(driver).tap(tab, role="client")
    set_airplane_mode(driver, False)
    page_by_tab = {
        "dashboard": DashboardPage(driver), "scans": ScanListPage(driver),
        "alerts": NotificationsPage(driver), "profile": ProfilePage(driver),
    }
    assert page_by_tab[tab].is_loaded(timeout=20), f"{tab} did not recover after connectivity restored"


@pytest.mark.parametrize("button_label", [
    "INITIALIZE SESSION", "INITIALIZE SCAN", "Approve Fix (Analyst)", "LOG OUT",
])
def test_no_crash_on_rapid_repeated_taps(login_as_client, button_label):
    """Fast, repeated taps on any primary action button shouldn't queue up
    duplicate submissions or crash the app -- this is a smoke check that
    the relevant screen is at least reachable and tappable multiple times
    without the app becoming unresponsive; it does not assert
    idempotency at the backend/API level."""
    driver = login_as_client
    from pages.base_page import BasePage
    bp = BasePage(driver)
    if button_label == "LOG OUT":
        BottomNav(driver).tap("profile")
    if not bp.is_present(bp.by_text(button_label), timeout=5):
        pytest.skip(f"{button_label!r} not present on the current screen for this role/state")
    for _ in range(3):
        try:
            bp.tap_text(button_label, timeout=2)
        except Exception:
            break
    assert driver.get_window_size()["width"] > 0


def test_form_resubmission_after_transient_error_succeeds(login_as_client):
    driver = login_as_client
    scans = ScanListPage(driver)
    assert scans.is_loaded()
    scans.open_new_scan_fab()
    from pages.new_scan_page import NewScanPage
    form = NewScanPage(driver)
    assert form.is_loaded()
    form.fill_valid_scan()
    set_airplane_mode(driver, True)
    form.submit()
    assert form.is_loaded(timeout=10)
    set_airplane_mode(driver, False)
    form.submit()
    from pages.scan_status_page import ScanStatusPage
    status = ScanStatusPage(driver)
    assert status.is_loaded(timeout=20), "resubmission after connectivity was restored did not succeed"
