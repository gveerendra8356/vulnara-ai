"""
test_accessibility.py

Checks grounded in what's actually in the markup: aria-label on the
sidebar nav, alt text on logo images, presence of heading elements,
native-input labeling via placeholder/required (no <label for> elements
exist in this codebase -- verified by grep across src/pages and
src/components, so tests assert what IS there rather than assuming
<label> wiring that isn't).
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from config import ROUTES
from pages.login_page import LoginPage
from pages.register_page import RegisterPage
from pages.app_layout import AppLayout
from pages.base_page import BasePage

pytestmark = pytest.mark.accessibility


class TestImageAltText:
    def test_login_logo_has_alt_text(self, driver):
        page = LoginPage(driver).open()
        el = page.find(*page.LOGO)
        assert el.get_attribute("alt") not in (None, "")

    def test_sidebar_logo_has_alt_text(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        el = layout.find(*layout.LOGO)
        assert el.get_attribute("alt") not in (None, "")

    def test_no_image_on_login_page_has_empty_alt(self, driver):
        page = LoginPage(driver).open()
        imgs = page.driver.find_elements(By.TAG_NAME, "img")
        assert all((img.get_attribute("alt") or "").strip() != "" for img in imgs)


class TestHeadingStructure:
    @pytest.mark.parametrize("route_key", ["dashboard", "scans", "new_scan", "remediations"])
    def test_authenticated_page_has_at_least_one_heading_element(self, driver, login_as_analyst, route_key):
        page = BasePage(driver)
        page.goto(ROUTES[route_key])
        headings = page.driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3")
        assert len(headings) >= 1

    def test_login_page_has_an_h1(self, driver):
        page = LoginPage(driver).open()
        assert page.exists(By.TAG_NAME, "h1")

    def test_register_page_has_an_h1(self, driver):
        page = RegisterPage(driver).open()
        assert page.exists(By.TAG_NAME, "h1")


class TestFormFieldAccessibility:
    def test_login_email_field_has_a_placeholder_as_a_labeling_cue(self, driver):
        page = LoginPage(driver).open()
        el = page.find(*page.EMAIL_INPUT)
        assert (el.get_attribute("placeholder") or "") != ""

    def test_login_fields_are_reachable_via_tab_key(self, driver):
        page = LoginPage(driver).open()
        email = page.find(*page.EMAIL_INPUT)
        email.click()
        email.send_keys(Keys.TAB)
        active = page.driver.switch_to.active_element
        assert active.get_attribute("type") == "password"

    def test_register_role_select_is_a_native_select_element(self, driver):
        """Native <select> ships built-in keyboard and screen-reader support
        for free -- this asserts the app didn't replace it with an
        unlabeled custom <div> dropdown."""
        page = RegisterPage(driver).open()
        el = page.find(*page.ROLE_SELECT)
        assert el.tag_name == "select"

    def test_new_scan_authorized_checkbox_is_a_native_checkbox_input(self, driver, login_as_analyst):
        from pages.new_scan_page import NewScanPage
        page = NewScanPage(driver).open()
        el = page.find(*page.AUTHORIZED_CHECKBOX)
        assert el.get_attribute("type") == "checkbox"

    def test_submit_buttons_use_native_button_elements(self, driver):
        page = LoginPage(driver).open()
        el = page.find(*page.SUBMIT_BUTTON)
        assert el.tag_name == "button"


class TestKeyboardNavigation:
    def test_login_form_can_be_submitted_via_keyboard_only(self, driver):
        from config import CREDENTIALS
        page = LoginPage(driver).open()
        page.submit_via_enter(CREDENTIALS["analyst"]["email"], CREDENTIALS["analyst"]["password"])
        assert page.on_route("")

    def test_nav_links_are_real_anchor_or_button_elements(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        for key, (by, locator) in layout.NAV_ITEMS.items():
            if not layout.exists(by, locator, timeout=2):
                continue
            el = layout.find(by, locator)
            assert el.tag_name in ("a", "button")

    def test_logout_button_is_keyboard_focusable(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        el = layout.find(*layout.LOGOUT_BUTTON)
        assert el.get_attribute("tabindex") != "-1"


class TestAriaAttributes:
    def test_sidebar_nav_has_descriptive_aria_label(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        el = layout.find(*layout.SIDEBAR)
        assert el.get_attribute("aria-label") == "Sidebar"

    def test_page_html_lang_attribute_is_set(self, driver):
        page = LoginPage(driver).open()
        lang = page.driver.find_element(By.TAG_NAME, "html").get_attribute("lang")
        assert lang not in (None, "")


class TestColorAndTextContrastProxy:
    """Full contrast-ratio measurement is out of scope for Selenium; these
    are cheap proxy checks that error/status text isn't relying on color
    alone (icon or text label also present)."""

    def test_status_pills_carry_text_not_just_color(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["scans"])
        body = page.body_text().upper()
        assert any(s in body for s in ["COMPLETED", "PENDING", "FAILED", "IN PROGRESS", "CANCELLED"])

    def test_severity_labels_carry_text_not_just_color(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["vuln_detail"])
        body = page.body_text().upper()
        assert any(s in body for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])


class TestFocusVisibility:
    def test_email_field_receives_focus_on_click(self, driver):
        page = LoginPage(driver).open()
        el = page.find(*page.EMAIL_INPUT)
        el.click()
        active = page.driver.switch_to.active_element
        assert active.get_attribute("type") == "email"

    def test_register_name_field_receives_focus_on_click(self, driver):
        page = RegisterPage(driver).open()
        el = page.find(*page.NAME_INPUT)
        el.click()
        active = page.driver.switch_to.active_element
        assert active == el

    def test_new_scan_target_field_receives_focus_on_click(self, driver, login_as_analyst):
        from pages.new_scan_page import NewScanPage
        page = NewScanPage(driver).open()
        el = page.find(*page.TARGET_INPUT)
        el.click()
        active = page.driver.switch_to.active_element
        assert active == el


class TestButtonAndLinkLabeling:
    def test_new_scan_submit_button_has_readable_text_content(self, driver, login_as_analyst):
        from pages.new_scan_page import NewScanPage
        page = NewScanPage(driver).open()
        el = page.find(*page.SUBMIT_BUTTON)
        assert el.text.strip() != ""

    def test_dashboard_new_scan_button_has_readable_text_content(self, driver, login_as_analyst):
        page = BasePage(driver).goto(ROUTES["dashboard"])
        el = page.find((By.XPATH, "//button[.//span[text()='New Scan']]"))
        assert el.text.strip() != ""

    def test_not_found_home_link_has_readable_text_content(self, driver, login_as_analyst):
        from pages.not_found_page import NotFoundPage
        page = NotFoundPage(driver)
        page.goto(ROUTES["unknown"])
        el = page.find(*page.HOME_LINK)
        assert el.text.strip() != ""
