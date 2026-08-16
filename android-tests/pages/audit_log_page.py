from pages.base_page import BasePage

HEADER = "System Audit Log"
TIMESTAMP_COL_LABEL = "TIMESTAMP (UTC)"
EVENT_COL_LABEL = "EVENT DETAILS"
STATUS_COL_LABEL = "STATUS"


class AuditLogPage(BasePage):
    def is_loaded(self, timeout: float = 15) -> bool:
        return self.is_present(self.by_text(HEADER), timeout=timeout)

    def has_table_columns(self) -> bool:
        return self.is_present(self.by_text(TIMESTAMP_COL_LABEL)) and \
            self.is_present(self.by_text(EVENT_COL_LABEL)) and \
            self.is_present(self.by_text(STATUS_COL_LABEL))

    def showing_count_text(self) -> str | None:
        for t in self.all_texts():
            if t.startswith("Showing"):
                return t
        return None
