"""
AppLayout page object -- the sidebar/header chrome wrapping every
authenticated route (src/components/AppLayout.jsx). Login/Register pages do
NOT use this layout.
"""

from selenium.webdriver.common.by import By

from .base_page import BasePage


class AppLayout(BasePage):
    SIDEBAR = (By.CSS_SELECTOR, "nav[aria-label='Sidebar']")
    NAV_ITEMS = {
        "dashboard": (By.XPATH, "//nav[@aria-label='Sidebar']//a[.//span[text()='Dashboard']]"),
        "scans": (By.XPATH, "//nav[@aria-label='Sidebar']//a[.//span[text()='Scans']]"),
        "remediations": (By.XPATH, "//nav[@aria-label='Sidebar']//a[.//span[text()='Remediation Queue']]"),
        "admin_config": (By.XPATH, "//nav[@aria-label='Sidebar']//a[.//span[text()='Admin Config']]"),
        "admin_cve": (By.XPATH, "//nav[@aria-label='Sidebar']//a[.//span[text()='CVE Database']]"),
    }
    ADMIN_SECTION_LABEL = (By.XPATH, "//nav[@aria-label='Sidebar']//div[normalize-space()='Admin']")
    LOGO = (By.CSS_SELECTOR, "nav[aria-label='Sidebar'] img[alt='Vulnara']")
    LOGOUT_BUTTON = (By.XPATH, "//button[.//span[text()='Logout']]")
    USER_ROLE_BADGE = (By.CSS_SELECTOR, "nav[aria-label='Sidebar'] span.uppercase")
    SEARCH_INPUT = (By.CSS_SELECTOR, "header input[placeholder='Search scans, CVEs...']")
    MOCK_MODE_BADGE = (By.XPATH, "//*[normalize-space()='Mock Mode']")
    NOTIFICATIONS_BUTTON = (By.CSS_SELECTOR, "header button span.material-symbols-outlined")
    USER_AVATAR = (By.CSS_SELECTOR, "header div.rounded-full")

    def nav_item_visible(self, key: str) -> bool:
        by, locator = self.NAV_ITEMS[key]
        return self.visible(by, locator)

    def click_nav(self, key: str):
        by, locator = self.NAV_ITEMS[key]
        self.click(by, locator)
        return self

    def nav_item_is_active(self, key: str) -> bool:
        by, locator = self.NAV_ITEMS[key]
        el = self.find(by, locator)
        return "text-primary" in (el.get_attribute("class") or "")

    def active_nav_keys(self):
        return [k for k in self.NAV_ITEMS if self.exists(*self.NAV_ITEMS[k], timeout=2)
                and self.nav_item_is_active(k)]

    def logout(self):
        self.click(*self.LOGOUT_BUTTON)
        return self

    def sidebar_visible(self) -> bool:
        return self.visible(*self.SIDEBAR)
