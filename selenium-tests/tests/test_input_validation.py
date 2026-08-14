"""
test_input_validation.py

Boundary and malformed-value handling, distinct from test_forms.py (which
tests form mechanics) and test_authentication.py (which owns email-format
validation specifically). This file focuses on: the New Scan justification
10-character minimum (verified in NewScanPage.jsx: `justification.trim()
.length >= 10`), XSS/SQLi-shaped strings not breaking rendering, and
whitespace/length edge cases across register and new-scan forms.
"""

import uuid

import pytest

from config import MOCK_PASSWORD
from pages.register_page import RegisterPage
from pages.new_scan_page import NewScanPage

pytestmark = pytest.mark.input_validation


# ---------------------------------------------------- new scan: target field

TARGET_EDGE_CASES = [
    "",
    "   ",
    "a",
    "x" * 500,
    "<script>alert(1)</script>",
    "'; DROP TABLE scans; --",
    "target with spaces.example.com",
    "target\twith\ttabs.com",
    "target\nwith\nnewlines.com",
    "😀emoji-target.example.com",
    "目标.example.com",
    "../../etc/passwd",
]


class TestNewScanTargetBoundaries:
    @pytest.mark.parametrize("target", TARGET_EDGE_CASES)
    def test_target_edge_case_does_not_crash_the_form(self, driver, login_as_analyst, target):
        page = NewScanPage(driver).open()
        page.set_target(target)
        # The app must still be responsive -- heading still present, no
        # blank/crashed page -- regardless of whether submission is allowed.
        assert page.exists(*page.HEADING)

    def test_empty_target_blocks_submission(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_justification("Owner-authorized QA scan, empty-target boundary check.")
        page.set_authorized(True)
        page.submit()
        assert page.on_route("scans/new", timeout=4)

    def test_whitespace_only_target_blocks_submission(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_target("   ")
        page.set_justification("Owner-authorized QA scan, whitespace-target boundary check.")
        page.set_authorized(True)
        page.submit()
        assert page.on_route("scans/new", timeout=4)

    def test_xss_shaped_target_is_not_executed_as_script(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_target("<img src=x onerror=alert(1)>")
        page.set_justification("Owner-authorized QA scan, XSS-shaped target boundary check.")
        page.set_authorized(True)
        page.submit()
        # If the payload had actually executed as script, a JS alert would
        # be blocking the page and this call would raise
        # UnexpectedAlertPresentException instead of returning normally.
        assert page.driver.execute_script("return document.readyState") == "complete"

    def test_very_long_target_is_accepted_or_gracefully_rejected(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_target("x" * 500 + ".example.com")
        page.set_justification("Owner-authorized QA scan, long-target boundary check.")
        page.set_authorized(True)
        page.submit()
        # Either it created a scan (long value accepted) or it stayed on the
        # form (rejected) -- both are acceptable outcomes as long as the
        # page itself is still intact.
        assert page.on_route("scans/new", timeout=4) or "scans/scan-" in page.current_path()


# ------------------------------------------------------ new scan: justification

JUSTIFICATION_EDGE_CASES = [
    ("", False),
    ("short", False),
    ("123456789", False),           # 9 chars, one under the 10-char minimum
    ("1234567890", True),           # exactly 10 chars
    ("Owner-authorized QA scan for boundary testing purposes.", True),
    ("   spaced out but long enough to pass   ", True),
]


class TestNewScanJustificationBoundary:
    @pytest.mark.parametrize("justification,should_allow_submit", JUSTIFICATION_EDGE_CASES)
    def test_justification_length_boundary(self, driver, login_as_analyst, justification, should_allow_submit):
        page = NewScanPage(driver).open()
        page.set_target(f"boundary-{uuid.uuid4().hex[:6]}.example.com")
        page.set_justification(justification)
        page.set_authorized(True)
        page.submit()
        if should_allow_submit:
            assert not page.on_route("scans/new", timeout=4)
        else:
            assert page.on_route("scans/new", timeout=4)

    def test_unauthorized_checkbox_blocks_submission_even_with_valid_fields(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_target(f"unauth-{uuid.uuid4().hex[:6]}.example.com")
        page.set_justification("Owner-authorized QA scan, but the checkbox itself stays unchecked.")
        page.set_authorized(False)
        page.submit()
        assert page.on_route("scans/new", timeout=4)


# ------------------------------------------------------------ register fields

NAME_EDGE_CASES = [
    "O'Brien",
    "Jean-Luc Picard",
    "李雷",
    "'; DROP TABLE users; --",
    "<script>alert(1)</script>",
    "a" * 200,
    "   Leading Space Name",
    "Name With\tTab",
]


class TestRegisterNameFieldEdgeCases:
    @pytest.mark.parametrize("name", NAME_EDGE_CASES)
    def test_unusual_name_values_do_not_crash_registration(self, driver, name):
        email = f"nameedge-{uuid.uuid4().hex[:8]}@vulnara.dev"
        page = RegisterPage(driver).open()
        page.fill(full_name=name, email=email, password=MOCK_PASSWORD, role="client")
        page.submit()
        # App must not be left on a broken/blank state -- either it
        # registered (redirected home) or stayed on register with the page
        # intact; a truly blank/crashed body would fail both checks.
        assert page.on_route("") or page.exists(*page.HEADING, timeout=3)


PASSWORD_EDGE_CASES = ["", "a", "1234567", "12345678", "x" * 300, "🔑🔑🔑🔑🔑🔑🔑🔑"]


class TestRegisterPasswordFieldEdgeCases:
    @pytest.mark.parametrize("password", PASSWORD_EDGE_CASES)
    def test_password_edge_case_does_not_crash_registration_form(self, driver, password):
        email = f"pwedge-{uuid.uuid4().hex[:8]}@vulnara.dev"
        page = RegisterPage(driver).open()
        page.fill(full_name="Edge Case Tester", email=email, password=password, role="client")
        page.submit()
        assert page.exists(*page.HEADING, timeout=3) or page.on_route("")

    def test_duplicate_email_registration_shows_error_or_handles_gracefully(self, driver):
        from config import CREDENTIALS
        page = RegisterPage(driver).open()
        page.fill(full_name="Duplicate Tester", email=CREDENTIALS["analyst"]["email"],
                   password=MOCK_PASSWORD, role="client")
        page.submit()
        # Should not silently corrupt state -- either an error banner shows,
        # or (if mock allows re-registration) it still lands somewhere sane.
        assert page.exists(*page.HEADING, timeout=3) or page.on_route("")


# --------------------------------------------------------------- remediation

class TestRejectReasonBoundaries:
    def test_empty_reject_reason_does_not_crash_dialog(self, driver, login_as_analyst):
        from pages.remediation_review_page import RemediationReviewPage
        from config import SEED
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_pending"])
        page.open_reject_dialog()
        assert page.exists(*page.REJECT_REASON_TEXTAREA)

    def test_very_long_reject_reason_is_accepted_by_the_textarea(self, driver, login_as_analyst):
        from pages.remediation_review_page import RemediationReviewPage
        from config import SEED
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_pending"])
        page.open_reject_dialog()
        long_reason = "This script needs revision. " * 50
        page.type_reject_reason(long_reason)
        assert page.find(*page.REJECT_REASON_TEXTAREA).get_attribute("value") == long_reason
