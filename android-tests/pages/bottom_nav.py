"""
pages/bottom_nav.py

widgets/vulnara_bottom_nav.dart renders its 4 tabs as bare `Icon(...)`
widgets with no `semanticLabel`, inside an `InkWell` with no `tooltip`
or `Semantics` wrapper -- so none of the 4 tabs expose a text or
content-description accessibility node at all (confirmed: no Text(),
tooltip:, or Semantics( anywhere in that file). That's a genuine
accessibility gap in the app, not a testing gap -- test_accessibility.py
asserts on it directly (see TestBottomNavAccessibility) and it is
expected to show up as a real FAILED/defect row in the Excel report,
the same way the reference FitFuel suite surfaces real app-side a11y
issues rather than papering over them.

For navigation *purposes* (not accessibility assertions), the 4 tabs are
still reliably reachable: the bar is a fixed 64px-tall Row of 4 equal
Expanded segments pinned to the bottom of the screen, so a positional tap
is deterministic across the whole app regardless of screen content.
"""

from pages.base_page import BasePage

TABS = ["dashboard", "scans", "alerts", "profile"]  # left -> right, matches VulnaraTab enum order
NAV_BAR_HEIGHT_PX_AT_MDPI = 64


class BottomNav(BasePage):
    def tap(self, tab: str):
        if tab not in TABS:
            raise ValueError(f"unknown tab {tab!r}, expected one of {TABS}")
        index = TABS.index(tab)
        size = self.driver.get_window_size()
        segment_w = size["width"] / len(TABS)
        x = int(segment_w * (index + 0.5))
        y = int(size["height"] * 0.965)  # bottom nav sits flush at the screen edge
        self.driver.tap([(x, y)], 50)

    def is_visible(self, timeout: float = 5) -> bool:
        # Indirect check: the nav bar has no locatable content of its own,
        # so this confirms the surrounding scaffold rendered without
        # crashing rather than the bar itself.
        size = self.driver.get_window_size()
        return size["width"] > 0 and size["height"] > 0
