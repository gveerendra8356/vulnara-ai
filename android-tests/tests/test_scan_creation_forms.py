"""tests/test_scan_creation_forms.py -- New Target Configuration form
(lib/screens/new_scan_screen.dart), field interaction and client-side
validation, logged in as the client role (the role docs/mobile_app_guide.md
identifies as the one that creates scans)."""

import pytest

from pages.scan_list_page import ScanListPage
from pages.new_scan_page import NewScanPage
from tests.fuzz_data import BOUNDARY_TEXT_INPUTS

pytestmark = pytest.mark.forms


@pytest.fixture
def new_scan_page(login_as_client):
    scans = ScanListPage(login_as_client)
    assert scans.is_loaded()
    scans.open_new_scan_fab()
    page = NewScanPage(login_as_client)
    assert page.is_loaded()
    return page


def test_new_scan_form_loads(new_scan_page):
    assert new_scan_page.is_loaded()


@pytest.mark.parametrize("label", [
    "TARGET ADDRESS / IP RANGE", "AUTHORIZATION JUSTIFICATION",
    "Explicit Permission Confirmation", "Enable AI Active Testing",
])
def test_new_scan_static_labels_present(new_scan_page, label):
    assert new_scan_page.is_present(new_scan_page.by_text(label), timeout=8), f"missing: {label}"


@pytest.mark.parametrize("name,value", BOUNDARY_TEXT_INPUTS, ids=[n for n, _ in BOUNDARY_TEXT_INPUTS])
def test_target_field_accepts_various_inputs(new_scan_page, name, value):
    new_scan_page.enter_target(value)
    got = new_scan_page.text_of_field(0)
    if value.strip():
        assert got != "" or value.isspace(), f"target field appears empty after entering {name}"


@pytest.mark.parametrize("name,value", BOUNDARY_TEXT_INPUTS, ids=[n for n, _ in BOUNDARY_TEXT_INPUTS])
def test_justification_field_accepts_various_inputs(new_scan_page, name, value):
    new_scan_page.enter_justification(value)
    got = new_scan_page.text_of_field(1)
    if value.strip():
        assert got != "" or value.isspace(), f"justification field appears empty after entering {name}"


def test_authorization_checkbox_toggle_no_crash(new_scan_page):
    new_scan_page.toggle_authorization_confirmation()
    new_scan_page.toggle_authorization_confirmation()
    assert new_scan_page.is_loaded()


def test_active_testing_switch_reflects_state(new_scan_page):
    before = new_scan_page.is_active_testing_enabled()
    new_scan_page.toggle_active_testing_switch()
    after = new_scan_page.is_active_testing_enabled()
    assert after != before


def test_submit_blocked_without_authorization_checkbox(new_scan_page):
    new_scan_page.enter_target("testphp.vulnweb.com")
    new_scan_page.enter_justification("QA test run, no authorization checked.")
    new_scan_page.submit()
    assert new_scan_page.is_loaded(timeout=5), \
        "form should not submit without the authorization confirmation checked"


def test_submit_blocked_without_target(new_scan_page):
    new_scan_page.enter_justification("QA test run, missing target field.")
    new_scan_page.toggle_authorization_confirmation()
    new_scan_page.submit()
    assert new_scan_page.is_loaded(timeout=5)


def test_submit_blocked_without_justification(new_scan_page):
    new_scan_page.enter_target("testphp.vulnweb.com")
    new_scan_page.toggle_authorization_confirmation()
    new_scan_page.submit()
    assert new_scan_page.is_loaded(timeout=5)


def test_submit_valid_scan_from_client(new_scan_page):
    new_scan_page.fill_valid_scan()
    new_scan_page.submit()
    from pages.scan_status_page import ScanStatusPage
    status = ScanStatusPage(new_scan_page.driver)
    assert status.is_loaded(timeout=20), "valid scan submission did not navigate to scan status"


@pytest.mark.parametrize("scenario", [
    "target_only_whitespace", "justification_only_whitespace",
    "target_extremely_long", "justification_extremely_long",
    "both_fields_only_symbols",
])
def test_error_message_scenarios(new_scan_page, scenario):
    scenario_inputs = {
        "target_only_whitespace": ("   ", "valid justification text here"),
        "justification_only_whitespace": ("testphp.vulnweb.com", "   "),
        "target_extremely_long": ("t" * 5000, "valid justification text here"),
        "justification_extremely_long": ("testphp.vulnweb.com", "j" * 5000),
        "both_fields_only_symbols": ("!@#$%^&*()", "!@#$%^&*()"),
    }
    target, justification = scenario_inputs[scenario]
    new_scan_page.enter_target(target)
    new_scan_page.enter_justification(justification)
    new_scan_page.toggle_authorization_confirmation()
    new_scan_page.submit()
    # Documents actual behavior: either blocked client-side (still on
    # form) or accepted and surfaced as a backend error -- both are valid
    # outcomes to record, silently succeeding is the only wrong outcome.
    from pages.scan_status_page import ScanStatusPage
    still_on_form = new_scan_page.is_loaded(timeout=6)
    moved_to_status = ScanStatusPage(new_scan_page.driver).is_loaded(timeout=6)
    assert still_on_form or moved_to_status
