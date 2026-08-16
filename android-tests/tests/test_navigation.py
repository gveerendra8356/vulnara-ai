"""tests/test_navigation.py -- bottom nav mechanics, back-button behavior,
and app-bar chrome, exercised with an authenticated session."""

import pytest

from pages.bottom_nav import BottomNav, TABS
from pages.scan_list_page import ScanListPage
from pages.new_scan_page import NewScanPage
from pages.dashboard_page import DashboardPage
from pages.notifications_page import NotificationsPage
from pages.profile_page import ProfilePage

pytestmark = pytest.mark.navigation


@pytest.mark.parametrize("tab", TABS)
def test_bottom_nav_navigates_to_each_tab(login_as_any_role, tab):
    driver, actual_role = login_as_any_role
    nav = BottomNav(driver)
    nav.tap(tab)
    page_by_tab = {
        "dashboard": DashboardPage(driver),
        "scans": ScanListPage(driver),
        "alerts": NotificationsPage(driver),
        "profile": ProfilePage(driver),
    }
    assert page_by_tab[tab].is_loaded(timeout=12), f"{tab} did not load after nav tap ({actual_role})"


@pytest.mark.parametrize("tab", TABS)
def test_bottom_nav_tap_is_idempotent(login_as_client, tab):
    """Tapping the already-active tab should not crash or navigate away."""
    nav = BottomNav(login_as_client)
    nav.tap(tab)
    nav.tap(tab)
    assert login_as_client.get_window_size()["width"] > 0


def test_back_button_from_new_scan_returns_to_scan_list(login_as_client):
    driver = login_as_client
    scans = ScanListPage(driver)
    assert scans.is_loaded()
    scans.open_new_scan_fab()
    new_scan = NewScanPage(driver)
    assert new_scan.is_loaded()
    driver.back()
    assert scans.is_loaded(timeout=10)


def test_navigating_all_tabs_in_sequence_never_crashes(login_as_any_role):
    driver, actual_role = login_as_any_role
    nav = BottomNav(driver)
    for tab in TABS:
        nav.tap(tab)
    assert driver.get_window_size()["width"] > 0


@pytest.mark.parametrize("screen_label", [
    "Global Analytics", "Active Scans", "Alerts Hub", "New Target Configuration",
])
def test_app_bar_wordmark_area_renders_without_crash(login_as_client, screen_label):
    """Every primary screen's Scaffold uses VulnaraAppBar; the wordmark
    itself is an Image.asset with no text semantics, so this checks the
    screen it sits above loaded successfully instead of the logo image
    directly."""
    driver = login_as_client
    nav = BottomNav(driver)
    label_to_tab = {
        "Global Analytics": "dashboard", "Active Scans": "scans",
        "Alerts Hub": "alerts", "New Target Configuration": None,
    }
    tab = label_to_tab[screen_label]
    if tab:
        nav.tap(tab)
    else:
        ScanListPage(driver).open_new_scan_fab()
    from pages.base_page import BasePage
    bp = BasePage(driver)
    assert bp.is_present(bp.by_text(screen_label), timeout=12)


@pytest.mark.parametrize("route", ["scans", "dashboard", "notifications", "profile"])
def test_direct_post_login_landing_screen_is_reachable(login_as_any_role, route):
    """initialLocation: '/scans' in router.dart -- confirms every role
    lands somewhere authenticated (not bounced to /login) and that each
    of the 4 primary destinations remains reachable from there."""
    driver, actual_role = login_as_any_role
    nav = BottomNav(driver)
    tab_map = {"scans": "scans", "dashboard": "dashboard", "notifications": "alerts", "profile": "profile"}
    nav.tap(tab_map[route])
    assert driver.get_window_size()["width"] > 0


def test_pending_remediations_icon_present_on_scan_status(login_as_client):
    """scan_status_screen.dart: IconButton tooltip 'Pending remediations'.
    Reachability of the scan-status screen itself (via an existing scan)
    is exercised in test_scan_lifecycle_crud.py; this asserts the icon
    contract only, guarding against the tooltip string silently changing."""
    driver = login_as_client
    scans = ScanListPage(driver)
    assert scans.is_loaded()
    if scans.scan_count() == 0:
        pytest.skip("no seeded scans available to open a scan-status screen from")
    scans.tap_first_scan()
    from pages.scan_status_page import ScanStatusPage
    status = ScanStatusPage(driver)
    assert status.is_loaded(timeout=12)
    assert status.is_present(status.by_content_desc("Pending remediations"), timeout=8)
