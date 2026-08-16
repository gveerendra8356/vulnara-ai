"""tests/test_responsive_orientation.py -- portrait/landscape rendering.
Uses utils/adb_helpers.rotate_device (a thin wrapper over
driver.orientation, which UiAutomator2 supports natively -- unlike
background_app/set_network_connection, this one capability did NOT need a
workaround)."""

import pytest

from pages.bottom_nav import BottomNav, TABS
from pages.base_page import BasePage
from pages.login_page import LoginPage
from utils.adb_helpers import rotate_device

pytestmark = pytest.mark.responsive


@pytest.mark.parametrize("screen_and_tab", [
    ("Global Analytics", "dashboard"), ("Active Scans", "scans"),
    ("Alerts Hub", "alerts"), ("Account Settings", "profile"),
])
def test_screen_renders_in_portrait(login_as_client, screen_and_tab):
    heading, tab = screen_and_tab
    driver = login_as_client
    rotate_device(driver, "PORTRAIT")
    BottomNav(driver).tap(tab)
    bp = BasePage(driver)
    assert bp.is_present(bp.by_text(heading), timeout=15)


@pytest.mark.parametrize("screen_and_tab", [
    ("Global Analytics", "dashboard"), ("Active Scans", "scans"),
    ("Alerts Hub", "alerts"), ("Account Settings", "profile"),
])
def test_screen_renders_in_landscape(login_as_client, screen_and_tab):
    heading, tab = screen_and_tab
    driver = login_as_client
    rotate_device(driver, "LANDSCAPE")
    try:
        BottomNav(driver).tap(tab)
        bp = BasePage(driver)
        assert bp.is_present(bp.by_text(heading), timeout=15)
    finally:
        rotate_device(driver, "PORTRAIT")


def test_rotation_preserves_login_state(login_as_any_role):
    driver, actual_role = login_as_any_role
    rotate_device(driver, "LANDSCAPE")
    try:
        login = LoginPage(driver)
        assert not login.is_still_on_login(timeout=8), \
            f"session for {actual_role} was lost after rotating to landscape"
    finally:
        rotate_device(driver, "PORTRAIT")


def test_rotation_does_not_crash_new_scan_form(login_as_client):
    driver = login_as_client
    from pages.scan_list_page import ScanListPage
    from pages.new_scan_page import NewScanPage
    scans = ScanListPage(driver)
    assert scans.is_loaded()
    scans.open_new_scan_fab()
    form = NewScanPage(driver)
    assert form.is_loaded()
    form.enter_target("testphp.vulnweb.com")
    rotate_device(driver, "LANDSCAPE")
    try:
        assert form.is_loaded(timeout=10)
    finally:
        rotate_device(driver, "PORTRAIT")


@pytest.mark.parametrize("screen_and_tab", [
    ("Global Analytics", "dashboard"), ("Active Scans", "scans"), ("Alerts Hub", "alerts"),
])
def test_rotation_back_to_portrait_restores_layout(login_as_client, screen_and_tab):
    heading, tab = screen_and_tab
    driver = login_as_client
    BottomNav(driver).tap(tab)
    rotate_device(driver, "LANDSCAPE")
    rotate_device(driver, "PORTRAIT")
    bp = BasePage(driver)
    assert bp.is_present(bp.by_text(heading), timeout=15)


@pytest.mark.parametrize("tab", TABS)
def test_bottom_nav_tap_works_in_landscape(login_as_client, tab):
    driver = login_as_client
    rotate_device(driver, "LANDSCAPE")
    try:
        BottomNav(driver).tap(tab)
        assert driver.get_window_size()["width"] > 0
    finally:
        rotate_device(driver, "PORTRAIT")
