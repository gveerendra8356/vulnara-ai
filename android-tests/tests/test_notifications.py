"""tests/test_notifications.py -- Alerts Hub screen (lib/screens/notifications_screen.dart)."""

import pytest

from pages.bottom_nav import BottomNav
from pages.notifications_page import NotificationsPage

pytestmark = pytest.mark.navigation


def test_notifications_screen_loads(login_as_any_role):
    driver, actual_role = login_as_any_role
    BottomNav(driver).tap("alerts")
    page = NotificationsPage(driver)
    assert page.is_loaded(timeout=15)


def test_notifications_empty_or_list_state_renders(login_as_client):
    driver = login_as_client
    BottomNav(driver).tap("alerts")
    page = NotificationsPage(driver)
    assert page.is_loaded(timeout=15)
    # Either the empty-state label is present, or it isn't because there
    # are real notification rows -- both are valid; the invalid case is
    # neither being true (a blank/frozen screen).
    empty = page.is_empty_state()
    has_any_text = len(page.all_texts()) > 1  # more than just the header
    assert empty or has_any_text


def test_notifications_reachable_from_bottom_nav(login_as_client):
    driver = login_as_client
    BottomNav(driver).tap("alerts")
    page = NotificationsPage(driver)
    assert page.is_loaded(timeout=15)


def test_notifications_header_present(login_as_client):
    driver = login_as_client
    BottomNav(driver).tap("alerts")
    page = NotificationsPage(driver)
    assert page.is_present(page.by_text("Alerts Hub"), timeout=10)


@pytest.mark.parametrize("visit", [1, 2, 3])
def test_notifications_no_crash_on_repeat_visits(login_as_client, visit):
    driver = login_as_client
    nav = BottomNav(driver)
    nav.tap("alerts")
    nav.tap("dashboard")
    nav.tap("alerts")
    page = NotificationsPage(driver)
    assert page.is_loaded(timeout=15)
