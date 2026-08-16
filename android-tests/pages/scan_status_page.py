from pages.base_page import BasePage

OVERVIEW_LABEL = "OVERVIEW"
TOP_FINDINGS_LABEL = "TOP FINDINGS"
VIEW_ALL_LABEL = "VIEW ALL"
NO_FINDINGS_LABEL = "No findings yet."
RECON_PHASE_LABEL = "Reconnaissance Phase"
ESTIMATING_LABEL = "Estimating completion..."


class ScanStatusPage(BasePage):
    def is_loaded(self, timeout: float = 15) -> bool:
        return self.is_present(self.by_text(OVERVIEW_LABEL), timeout=timeout)

    def has_findings(self) -> bool:
        return not self.is_present(self.by_text(NO_FINDINGS_LABEL), timeout=3)

    def is_in_progress(self) -> bool:
        return self.is_present(self.by_text(RECON_PHASE_LABEL), timeout=3) or \
            self.is_present(self.by_text(ESTIMATING_LABEL), timeout=3)

    def open_pending_remediations(self):
        # IconButton tooltip: 'Pending remediations' from scan_status_screen.dart
        self.driver.find_element(*self.by_content_desc("Pending remediations")).click()

    def open_view_all_findings(self):
        self.tap_text(VIEW_ALL_LABEL)

    def target_label_text(self) -> str | None:
        for t in self.all_texts():
            if t.startswith("Target: scan"):
                return t
        return None
