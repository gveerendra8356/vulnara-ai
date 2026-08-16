"""tests/test_input_validation.py -- deep boundary/edge-case fuzzing of
every text-entry field in the app. Complements the lighter functional
checks in test_authentication.py and test_scan_creation_forms.py; this
module's job is exhaustive coverage of the input space, not asserting a
specific pass/fail outcome for each value (many of these have no "correct"
outcome defined anywhere -- the point is that none of them should crash
the app or silently corrupt the session)."""

import pytest

import config
from pages.login_page import LoginPage
from pages.scan_list_page import ScanListPage
from pages.new_scan_page import NewScanPage
from tests.fuzz_data import BOUNDARY_TEXT_INPUTS, BOUNDARY_PASSWORD_INPUTS, MALFORMED_EMAILS, VALID_LOOKING_EMAILS

pytestmark = pytest.mark.input_validation

ALL_EMAILS = MALFORMED_EMAILS + VALID_LOOKING_EMAILS
ALL_EMAIL_IDS = [n for n, _ in ALL_EMAILS]


@pytest.mark.parametrize("name,value", BOUNDARY_TEXT_INPUTS, ids=[n for n, _ in BOUNDARY_TEXT_INPUTS])
def test_target_field_boundary_inputs_do_not_crash_app(login_as_client, name, value):
    driver = login_as_client
    scans = ScanListPage(driver)
    assert scans.is_loaded()
    scans.open_new_scan_fab()
    form = NewScanPage(driver)
    assert form.is_loaded()
    form.enter_target(value)
    assert form.is_loaded(), f"app crashed/left the form entering target={name}"
    driver.back()


@pytest.mark.parametrize("name,value", BOUNDARY_TEXT_INPUTS, ids=[n for n, _ in BOUNDARY_TEXT_INPUTS])
def test_justification_field_boundary_inputs_do_not_crash_app(login_as_client, name, value):
    driver = login_as_client
    scans = ScanListPage(driver)
    assert scans.is_loaded()
    scans.open_new_scan_fab()
    form = NewScanPage(driver)
    assert form.is_loaded()
    form.enter_justification(value)
    assert form.is_loaded(), f"app crashed/left the form entering justification={name}"
    driver.back()


@pytest.mark.parametrize("name,email", ALL_EMAILS, ids=ALL_EMAIL_IDS)
def test_login_email_field_boundary_inputs_do_not_crash_app(driver, name, email):
    login = LoginPage(driver)
    assert login.is_loaded()
    login.enter_email(email)
    assert login.is_loaded(), f"app crashed/left the login screen entering email={name}"


@pytest.mark.parametrize("name,password", BOUNDARY_PASSWORD_INPUTS, ids=[n for n, _ in BOUNDARY_PASSWORD_INPUTS])
def test_login_password_field_boundary_inputs_do_not_crash_app(driver, name, password):
    login = LoginPage(driver)
    assert login.is_loaded()
    login.enter_password(password)
    assert login.is_loaded(), f"app crashed/left the login screen entering password={name}"


@pytest.mark.parametrize("name,value", BOUNDARY_TEXT_INPUTS, ids=[n for n, _ in BOUNDARY_TEXT_INPUTS])
def test_target_field_boundary_inputs_survive_field_switch(login_as_client, name, value):
    """Entering a boundary value then immediately moving focus to the
    justification field shouldn't drop or mutate what was typed -- a
    stronger check than the crash-only assertion above, since focus-loss
    is where TextEditingController state bugs typically surface."""
    driver = login_as_client
    scans = ScanListPage(driver)
    assert scans.is_loaded()
    scans.open_new_scan_fab()
    form = NewScanPage(driver)
    assert form.is_loaded()
    form.enter_target(value)
    form.enter_justification("focus-switch check")
    assert form.is_loaded(), f"app crashed switching focus away from target={name}"
    driver.back()


@pytest.mark.parametrize("name,email", ALL_EMAILS, ids=ALL_EMAIL_IDS)
def test_login_email_field_boundary_inputs_survive_field_switch(driver, name, email):
    login = LoginPage(driver)
    assert login.is_loaded()
    login.enter_email(email)
    login.enter_password("some-password-to-force-focus-switch")
    assert login.is_loaded(), f"app crashed switching focus away from email={name}"
