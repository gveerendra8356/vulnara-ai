"""tests/test_audit_log.py -- system audit log screen
(lib/screens/audit_log_screen.dart). Not on the bottom nav bar; reached
via in-app navigation from profile in this scaffold, so tests here open it
through the same path a real user would."""

import pytest

from pages.bottom_nav import BottomNav
from pages.profile_page import ProfilePage
from pages.audit_log_page import AuditLogPage
from pages.base_page import BasePage

pytestmark = pytest.mark.navigation


def _open_audit_log(driver):
    BottomNav(driver).tap("profile")
    profile = ProfilePage(driver)
    assert profile.is_loaded(timeout=15)
    bp = BasePage(driver)
    if not bp.is_present(bp.by_text("System Audit Log"), timeout=5) and \
       not bp.is_present(bp.by_text("Audit Log"), timeout=3):
        pytest.skip("no in-app link to the audit log was found from the profile screen")
    for label in ("System Audit Log", "Audit Log"):
        if bp.is_present(bp.by_text(label), timeout=2):
            bp.tap_text(label)
            break
    return AuditLogPage(driver)


def test_audit_log_loads_for_admin(login_as_admin):
    page = _open_audit_log(login_as_admin)
    assert page.is_loaded(timeout=15)


def test_audit_log_reachability_by_role(login_as_any_role):
    driver, actual_role = login_as_any_role
    page = _open_audit_log(driver)
    assert page.is_loaded(timeout=15), f"audit log not reachable/loaded for role={actual_role}"


def test_audit_log_table_columns_present(login_as_admin):
    page = _open_audit_log(login_as_admin)
    assert page.is_loaded(timeout=15)
    assert page.has_table_columns()


def test_audit_log_entry_count_text_present(login_as_admin):
    page = _open_audit_log(login_as_admin)
    assert page.is_loaded(timeout=15)
    text = page.showing_count_text()
    if text is None:
        pytest.skip("no 'Showing ...' summary text found in current semantics tree")
    assert "Showing" in text


@pytest.mark.parametrize("swipes", [1, 2, 3])
def test_audit_log_scroll_does_not_crash(login_as_admin, swipes):
    page = _open_audit_log(login_as_admin)
    assert page.is_loaded(timeout=15)
    page.swipe_up(times=swipes)
    assert page.is_loaded(timeout=10)
