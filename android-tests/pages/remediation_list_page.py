from pages.base_page import BasePage

HEADER = "Pending Remediations"


class RemediationListPage(BasePage):
    def is_loaded(self, timeout: float = 15) -> bool:
        return self.is_present(self.by_text(HEADER), timeout=timeout)

    def item_count_by_status_text(self, status_substring: str) -> int:
        locator = self.by_text_contains(status_substring)
        return len(self.driver.find_elements(*locator))
