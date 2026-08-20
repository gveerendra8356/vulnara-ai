"""tests/test_session_management.py -- token persistence, backgrounding,
logout, and cold-start behavior."""

import time

import pytest

import config
from pages.login_page import LoginPage
from pages.bottom_nav import BottomNav
from utils.adb_helpers import send_to_background, clear_app_data, force_stop_app

pytestmark = pytest.mark.session_management


def test_token_persists_across_background_foreground(login_as_any_role):
    driver, actual_role = login_as_any_role
    BottomNav(driver).tap("dashboard")
    send_to_background(driver, seconds=4)
    login = LoginPage(driver)
    assert not login.is_still_on_login(timeout=8), \
        f"session for {actual_role} was lost after a background/foreground cycle"


def test_pm_clear_removes_session_forcing_login(login_as_client):
    """clear_app_data() wipes the Flutter Secure Storage token (force-stop +
    rm -rf shared_prefs/files). After a relaunch the app has no stored JWT
    so the router's initial redirect sends the user to /login.
    Note: we replaced the original `pm clear` with a targeted rm -rf to avoid
    wiping the UiAutomator2 server state -- the auth-token removal behavior
    is identical from the test perspective."""
    driver = login_as_client
    clear_app_data(driver)
    force_stop_app(driver)
    from utils.adb_helpers import bring_to_foreground
    bring_to_foreground(driver)
    import time
    time.sleep(3)  # wait for cold-start + semantics tree after the relaunch
    login = LoginPage(driver)
    assert login.is_loaded(timeout=20), "expected login screen after data clear + relaunch"


def test_relogin_after_logout_requires_valid_credentials(login_as_client):
    driver = login_as_client
    from pages.profile_page import ProfilePage
    BottomNav(driver).tap("profile")
    profile = ProfilePage(driver)
    assert profile.is_loaded(timeout=15)
    profile.logout()
    login = LoginPage(driver)
    assert login.is_loaded(timeout=15)
    login.login(config.ACCOUNTS["client"]["email"], "wrong-password-after-logout")
    assert login.is_still_on_login(timeout=8)
    assert login.error_text() is not None


@pytest.mark.parametrize("first_role,second_role", [
    ("client", "analyst"), ("analyst", "admin"), ("admin", "client"),
])
def test_session_isolated_between_consecutive_different_role_logins(driver, first_role, second_role):
    login = LoginPage(driver)
    assert login.is_loaded()
    first = config.ACCOUNTS[first_role]
    login.login(first["email"], first["password"])
    assert login.wait_gone(login.by_text("INITIALIZE SESSION"), timeout=15)

    from pages.profile_page import ProfilePage
    BottomNav(driver).tap("profile")
    profile = ProfilePage(driver)
    assert profile.is_loaded(timeout=15)
    profile.logout()
    assert login.is_loaded(timeout=15)

    second = config.ACCOUNTS[second_role]
    login.login(second["email"], second["password"])
    assert login.wait_gone(login.by_text("INITIALIZE SESSION"), timeout=15)
    BottomNav(driver).tap("profile")
    assert profile.is_loaded(timeout=15)
    chip = profile.role_chip_text()
    if chip is not None:
        assert chip.lower() == second["role"], \
            f"profile still showed {first_role}'s role after switching to {second_role}"


def test_cold_start_without_token_shows_login(driver):
    login = LoginPage(driver)
    assert login.is_loaded(timeout=20)


@pytest.mark.parametrize("cycle", [1, 2, 3])
def test_multiple_background_foreground_cycles_preserve_session(login_as_client, cycle):
    driver = login_as_client
    send_to_background(driver, seconds=2)
    login = LoginPage(driver)
    assert not login.is_still_on_login(timeout=8), \
        f"session lost on background/foreground cycle #{cycle}"
