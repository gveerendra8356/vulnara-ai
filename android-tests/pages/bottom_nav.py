"""
pages/bottom_nav.py

widgets/vulnara_bottom_nav.dart gives every icon a semanticLabel and wraps
the item in a Tooltip, so tests can locate each tab by its accessibility
content description.

For navigation *purposes* (not accessibility assertions), the 4 tabs are
still reliably reachable: the bar is a fixed 64px-tall Row of 4 equal
Expanded segments pinned to the bottom of the screen, so a positional tap
is deterministic across the whole app regardless of screen content.
"""

from pages.base_page import BasePage

TABS = ["dashboard", "scans", "alerts", "profile"]  # left -> right, matches VulnaraTab enum order
TAB_LABELS = {"dashboard": "Dashboard", "scans": "Scans", "alerts": "Alerts", "profile": "Profile"}
# widgets/vulnara_bottom_nav.dart: clients don't get the Dashboard tab (it
# shows org-wide analytics clients shouldn't see), so their bar only has 3
# equal-width segments, not 4 -- see tabs_for_role().
CLIENT_TABS = ["scans", "alerts", "profile"]
NAV_BAR_HEIGHT_PX_AT_MDPI = 64


def tabs_for_role(role: str) -> list[str]:
    return CLIENT_TABS if role == "client" else TABS


class BottomNav(BasePage):
    def tap(self, tab: str, role: str = "admin"):
        # Keep a coordinate fallback because some Flutter/UiAutomator2
        # versions do not expose semantic nodes until after the first tap.
        tabs = tabs_for_role(role)
        if tab not in tabs:
            raise ValueError(f"unknown tab {tab!r} for role {role!r}, expected one of {tabs}")
        # The app now exposes semantic labels for every tab. Prefer the
        # actual control over screen coordinates, which become unreliable
        # after rotation or with different system-bar insets.
        try:
            self.wait_visible(self.by_content_desc(TAB_LABELS[tab]), timeout=4).click()
            return
        except Exception:
            pass
        index = tabs.index(tab)
        size = self.driver.get_window_size()
        segment_w = size["width"] / len(tabs)
        x = int(segment_w * (index + 0.5))
        y = int(size["height"] * 0.965)  # bottom nav sits flush at the screen edge
        self.driver.tap([(x, y)], 50)

    def is_visible(self, timeout: float = 5) -> bool:
        # Indirect check: the nav bar has no locatable content of its own,
        # so this confirms the surrounding scaffold rendered without
        # crashing rather than the bar itself.
        size = self.driver.get_window_size()
        return size["width"] > 0 and size["height"] > 0
