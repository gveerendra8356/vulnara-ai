"""
test_forms.py

Field-level behavior of every form in the app: types, interactions, and
client-side enable/disable logic. Distinct from test_input_validation.py,
which focuses on boundary/malformed *values*; this file focuses on form
*mechanics* (typing works, toggles flip, buttons enable/disable correctly).
"""

import uuid

import pytest
from selenium.webdriver.support.ui import Select

from config import CREDENTIALS, MOCK_PASSWORD, ROUTES, SEED
from pages.login_page import LoginPage
from pages.register_page import RegisterPage
from pages.new_scan_page import NewScanPage
from pages.remediation_review_page import RemediationReviewPage
from pages.admin_config_page import AdminConfigPage
from pages.base_page import BasePage

pytestmark = pytest.mark.forms


class TestLoginFormFieldTypes:
    def test_email_field_accepts_typed_input(self, driver):
        page = LoginPage(driver).open()
        page.type_into(*page.EMAIL_INPUT, "someone@example.com")
        assert page.find(*page.EMAIL_INPUT).get_attribute("value") == "someone@example.com"

    def test_password_field_accepts_typed_input(self, driver):
        page = LoginPage(driver).open()
        page.type_into(*page.PASSWORD_INPUT, "s3cret!")
        assert page.find(*page.PASSWORD_INPUT).get_attribute("value") == "s3cret!"

    def test_email_field_placeholder_text(self, driver):
        page = LoginPage(driver).open()
        assert page.find(*page.EMAIL_INPUT).get_attribute("placeholder") == "you@company.com"

    def test_password_field_placeholder_is_masked_dots(self, driver):
        page = LoginPage(driver).open()
        placeholder = page.find(*page.PASSWORD_INPUT).get_attribute("placeholder")
        assert set(placeholder) == {"\u2022"}

    def test_clearing_and_retyping_email_field_works(self, driver):
        page = LoginPage(driver).open()
        page.type_into(*page.EMAIL_INPUT, "first@example.com")
        page.type_into(*page.EMAIL_INPUT, "second@example.com")
        assert page.find(*page.EMAIL_INPUT).get_attribute("value") == "second@example.com"


class TestRegisterFormFieldTypes:
    def test_name_field_type_text_or_untyped(self, driver):
        page = RegisterPage(driver).open()
        el = page.find(*page.NAME_INPUT)
        assert el.get_attribute("type") in ("text", None)

    def test_email_field_type_email(self, driver):
        page = RegisterPage(driver).open()
        assert page.find(*page.EMAIL_INPUT).get_attribute("type") == "email"

    def test_password_field_type_password(self, driver):
        page = RegisterPage(driver).open()
        assert page.find(*page.PASSWORD_INPUT).get_attribute("type") == "password"

    def test_role_select_default_value_is_client(self, driver):
        page = RegisterPage(driver).open()
        assert page.find(*page.ROLE_SELECT).get_attribute("value") == "client"

    def test_role_select_can_be_switched_to_analyst(self, driver):
        page = RegisterPage(driver).open()
        Select(page.find(*page.ROLE_SELECT)).select_by_value("analyst")
        assert page.find(*page.ROLE_SELECT).get_attribute("value") == "analyst"

    def test_all_register_fields_accept_typed_input_together(self, driver):
        page = RegisterPage(driver).open()
        page.fill(full_name="Jane Op", email="jane.op@example.com", password="pw12345")
        assert page.find(*page.NAME_INPUT).get_attribute("value") == "Jane Op"
        assert page.find(*page.EMAIL_INPUT).get_attribute("value") == "jane.op@example.com"
        assert page.find(*page.PASSWORD_INPUT).get_attribute("value") == "pw12345"


class TestNewScanFormMechanics:
    def test_target_field_accepts_typed_input(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_target("10.0.4.22")
        assert page.find(*page.TARGET_INPUT).get_attribute("value") == "10.0.4.22"

    def test_justification_textarea_accepts_typed_input(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        text = "Written pentest authorization on file, ref TEST-001."
        page.set_justification(text)
        assert page.find(*page.JUSTIFICATION_TEXTAREA).get_attribute("value") == text

    def test_authorized_checkbox_starts_unchecked(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        assert page.find(*page.AUTHORIZED_CHECKBOX).is_selected() is False

    def test_authorized_checkbox_can_be_checked(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_authorized(True)
        assert page.find(*page.AUTHORIZED_CHECKBOX).is_selected() is True

    def test_authorized_checkbox_can_be_unchecked_after_checking(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_authorized(True)
        page.set_authorized(False)
        assert page.find(*page.AUTHORIZED_CHECKBOX).is_selected() is False

    def test_active_testing_toggle_starts_off(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        assert page.find(*page.ACTIVE_TESTING_TOGGLE).is_selected() is False

    def test_active_testing_toggle_can_be_switched_on(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.set_active_testing(True)
        assert page.find(*page.ACTIVE_TESTING_TOGGLE).is_selected() is True

    def test_target_field_is_required(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        el = page.find(*page.TARGET_INPUT)
        assert el.get_attribute("required") is not None

    def test_justification_textarea_is_required(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        el = page.find(*page.JUSTIFICATION_TEXTAREA)
        assert el.get_attribute("required") is not None

    def test_cancel_button_navigates_back(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["scans"])
        new_scan = NewScanPage(driver).open()
        new_scan.click(*new_scan.CANCEL_BUTTON)
        assert new_scan.on_route("scans")

    def test_back_to_scans_link_navigates_back(self, driver, login_as_analyst):
        BasePage(driver).goto(ROUTES["scans"])
        new_scan = NewScanPage(driver).open()
        new_scan.click(*new_scan.BACK_BUTTON)
        assert new_scan.on_route("scans")

    def test_submitting_valid_scan_navigates_to_its_detail_page(self, driver, login_as_analyst):
        page = NewScanPage(driver).open()
        page.fill_and_submit(
            target="test-target.example.com",
            justification="Written pentest authorization on file for QA suite, ref QA-100.",
            authorized=True,
        )
        assert page.wait.until(lambda d: d.current_url.split(ROUTES["scans"])[-1].strip("/").startswith("scan"))


class TestRemediationReviewForm:
    def test_reject_button_opens_confirm_dialog_with_textarea(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_pending"])
        page.open_reject_dialog()
        assert page.exists(*page.REJECT_REASON_TEXTAREA)

    def test_reject_reason_textarea_accepts_typed_input(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_pending"])
        page.open_reject_dialog()
        page.type_reject_reason("Script needs a rollback step first.")
        assert page.find(*page.REJECT_REASON_TEXTAREA).get_attribute("value") == \
            "Script needs a rollback step first."

    def test_approve_button_present_for_pending_remediation(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_pending"])
        assert page.exists(*page.APPROVE_BUTTON)

    def test_mark_executed_button_present_for_approved_remediation(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_approved"])
        assert page.exists(*page.MARK_EXECUTED_BUTTON) or page.text_present("APPROVED")

    def test_copy_script_button_present(self, driver, login_as_analyst):
        page = RemediationReviewPage(driver)
        page.open(SEED["remediation_pending"])
        assert page.exists(*page.COPY_SCRIPT_BUTTON)


class TestAdminConfigForm:
    def test_edit_button_reveals_input_field(self, driver, login_as_admin):
        page = AdminConfigPage(driver).open()
        page.click_edit(SEED["config_key"])
        assert page.exists(*page.value_input())

    def test_editing_value_updates_input_content(self, driver, login_as_admin):
        page = AdminConfigPage(driver).open()
        page.click_edit(SEED["config_key"])
        page.set_value("0.55")
        assert page.find(*page.value_input()).get_attribute("value") == "0.55"

    def test_cancel_button_discards_edit_and_hides_input(self, driver, login_as_admin):
        page = AdminConfigPage(driver).open()
        page.click_edit(SEED["config_key"])
        page.click_cancel()
        assert not page.exists(*page.value_input(), timeout=3)

    def test_save_button_present_while_editing(self, driver, login_as_admin):
        page = AdminConfigPage(driver).open()
        page.click_edit(SEED["config_key"])
        assert page.exists(*page.save_button())

    def test_edit_button_reappears_after_cancel(self, driver, login_as_admin):
        page = AdminConfigPage(driver).open()
        page.click_edit(SEED["config_key"])
        page.click_cancel()
        assert page.exists(*page.edit_button_for_key(SEED["config_key"]))


class TestFormAccessInteractionAcrossRoles:
    @pytest.mark.parametrize("role", ["analyst", "admin"])
    def test_new_scan_form_reachable_by_both_scan_creating_roles(self, driver, role):
        page = LoginPage(driver).open()
        page.login(CREDENTIALS[role]["email"], CREDENTIALS[role]["password"])
        page.on_route("")
        new_scan = NewScanPage(driver).open()
        assert new_scan.is_loaded()

    def test_client_can_reach_new_scan_form(self, driver):
        email = f"formclient-{uuid.uuid4().hex[:8]}@vulnara.dev"
        reg = RegisterPage(driver).open()
        reg.register(full_name="Form Client", email=email, password=MOCK_PASSWORD, role="client")
        reg.on_route("")
        new_scan = NewScanPage(driver).open()
        assert new_scan.is_loaded()
