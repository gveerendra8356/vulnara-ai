from pages.base_page import BasePage

HEADER = "Global Analytics"
OPEN_CRIT_VULNS_LABEL = "OPEN CRITICAL VULNERABILITIES"
REMEDIATIONS_PENDING_LABEL = "REMEDIATIONS PENDING"
INTEGRITY_LABEL = "SYSTEM INTEGRITY"
THREATS_OVER_TIME_LABEL = "Threats Over Time"


class DashboardPage(BasePage):
    def is_loaded(self, timeout: float = 15) -> bool:
        return self.is_present(self.by_text(HEADER), timeout=timeout)

    def has_metric_cards(self) -> bool:
        return self.is_present(self.by_text(OPEN_CRIT_VULNS_LABEL)) and \
            self.is_present(self.by_text(REMEDIATIONS_PENDING_LABEL))

    def has_error_banner(self) -> bool:
        # dashboard_screen.dart renders error: (err, _) => Text(err.toString())
        # on a riverpod AsyncError -- any unexpected long text block combined
        # with the header still present is treated as an error state.
        return not self.has_metric_cards() and self.is_loaded(timeout=3)
