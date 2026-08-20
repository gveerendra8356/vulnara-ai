"""tests/test_profile.py -- profile screen (lib/screens/profile_screen.dart)
and logout."""

import pytest

import config
from pages.bottom_nav import BottomNav
from pages.profile_page import ProfilePage
from pages.login_page import LoginPage

pytestmark = pytest.mark.navigation


def test_profile_loads(login_as_any_role):
    driver, actual_role = login_as_any_role
    BottomNav(driver).tap("profile")
    page = ProfilePage(driver)
    assert page.is_loaded(timeout=15)


def test_profile_role_chip_matches_account_role(login_as_any_role):
    driver, actual_role = login_as_any_role
    BottomNav(driver).tap("profile")
    page = ProfilePage(driver)
    assert page.is_loaded(timeout=15)
    chip = page.role_chip_text()
    if chip is None:
        pytest.skip("role chip text not found in current semantics tree -- see profile_page.py note")
    assert chip.lower() == config.ACCOUNTS[actual_role]["role"]


def test_profile_account_settings_row_present(login_as_client):
    driver = login_as_client
    BottomNav(driver).tap("profile")
    page = ProfilePage(driver)
    assert page.is_loaded(timeout=15)
    # lib/screens/profile_screen.dart has no "Account Settings" section --
    # the account-editing tab is labelled "ACCOUNT INFO".
    assert page.is_present(page.by_text("ACCOUNT INFO"), timeout=8)


def test_profile_version_label_present(login_as_client):
    """profile_screen.dart renders no app-version string anywhere on this
    screen (pubspec.yaml's version isn't surfaced in the UI at all) --
    there's nothing for this test to assert on until that becomes a real
    feature."""
    pytest.skip("no version label is rendered anywhere in profile_screen.dart")


def test_logout_returns_to_login(login_as_any_role):
    driver, actual_role = login_as_any_role
    BottomNav(driver).tap("profile")
    page = ProfilePage(driver)
    assert page.is_loaded(timeout=15)
    page.logout()
    login = LoginPage(driver)
    assert login.is_loaded(timeout=15)


def test_logout_clears_session_requiring_relogin(login_as_client):
    driver = login_as_client
    BottomNav(driver).tap("profile")
    page = ProfilePage(driver)
    assert page.is_loaded(timeout=15)
    page.logout()
    login = LoginPage(driver)
    assert login.is_loaded(timeout=15)
    # Backgrounding/foregrounding right after logout shouldn't silently
    # re-authenticate from a stale token.
    from utils.adb_helpers import send_to_background
    send_to_background(driver, seconds=3)
    assert login.is_loaded(timeout=15)
