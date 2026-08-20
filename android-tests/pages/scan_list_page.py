from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage

HEADER = "Active Scans"
RETRY_LABEL = "Retry"


class ScanListPage(BasePage):
    def is_loaded(self, timeout: float = 15) -> bool:
        return self.is_present(self.by_text(HEADER), timeout=timeout)

    def open_new_scan_fab(self):
        # FloatingActionButton has no explicit label in the source; it's
        # the single android.widget.Button-role FAB rendered by Scaffold
        # (every other tappable control on this screen -- avatar, scan
        # cards, bottom nav items -- is a bare GestureDetector/InkWell,
        # which surfaces as android.view.View, not android.widget.Button).
        fab = self.driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().clickable(true).className("android.widget.Button").instance(0)',
        )
        fab.click()

    def scan_count(self) -> int:
        vuln_badges = self.driver.find_elements(self.by_text_contains("Vulns")[0], self.by_text_contains("Vulns")[1])
        return len(vuln_badges)

    def tap_first_scan(self):
        self.driver.find_elements(AppiumBy.XPATH, "//*[contains(@text, 'Vulns')]")[0].click()

    def is_retry_visible(self) -> bool:
        return self.is_present(self.by_text(RETRY_LABEL), timeout=3)

    def tap_retry(self):
        self.tap_text(RETRY_LABEL)
