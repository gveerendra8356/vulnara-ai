from pages.base_page import BasePage

HEADER = "Alerts Hub"
EMPTY_LABEL = "No alerts."


class NotificationsPage(BasePage):
    def is_loaded(self, timeout: float = 15) -> bool:
        return self.is_present(self.by_text(HEADER), timeout=timeout)

    def is_empty_state(self) -> bool:
        return self.is_present(self.by_text(EMPTY_LABEL), timeout=3)
