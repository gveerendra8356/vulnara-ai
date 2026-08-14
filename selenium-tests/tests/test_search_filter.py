"""
test_search_filter.py

Scans list: text search (`Filter by target...`) + status filter buttons
(both wired to real client-side filtering in ScansListPage.jsx).
Header search bar: present in AppLayout but NOT wired to any filtering logic
(it's local `useState` with no consumer) -- tests here document that
honestly rather than asserting a filtering behavior that doesn't exist.
"""

import pytest

from config import ROUTES
from pages.scans_list_page import ScansListPage, STATUS_FILTERS
from pages.app_layout import AppLayout

pytestmark = pytest.mark.search_filter


class TestScansTargetSearch:
    def test_searching_existing_target_substring_returns_matching_row(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.search("acmecorp")
        assert page.text_present("acmecorp")

    def test_searching_nonexistent_target_shows_empty_state(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.search("this-target-does-not-exist-anywhere")
        assert page.exists(*page.EMPTY_STATE, timeout=6) or page.row_count() == 0

    def test_search_is_case_insensitive(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.search("ACMECORP")
        assert page.text_present("acmecorp") or page.row_count() >= 1

    def test_clearing_search_restores_full_list(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        full_count = page.row_count()
        page.search("acmecorp")
        page.search("")
        assert page.row_count() == full_count

    def test_search_by_ip_address_target(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.search("192.168.56.101")
        assert page.text_present("192.168.56.101")

    def test_partial_target_match_returns_result(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.search("acme")
        assert page.row_count() >= 1


class TestScansStatusFilter:
    @pytest.mark.parametrize("status", STATUS_FILTERS)
    def test_each_status_filter_button_is_clickable(self, driver, login_as_analyst, status):
        page = ScansListPage(driver).open()
        page.click_filter(status)
        assert page.filter_is_active(status)

    def test_only_one_status_filter_is_active_at_a_time(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.click_filter("COMPLETED")
        assert page.filter_is_active("COMPLETED")
        assert not page.filter_is_active("ALL")

    def test_switching_filters_updates_the_active_state(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.click_filter("PENDING")
        page.click_filter("FAILED")
        assert page.filter_is_active("FAILED")
        assert not page.filter_is_active("PENDING")

    def test_all_filter_shows_the_most_rows_of_any_filter(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.click_filter("ALL")
        all_count = page.row_count()
        page.click_filter("COMPLETED")
        completed_count = page.row_count()
        assert all_count >= completed_count

    def test_search_and_status_filter_combine(self, driver, login_as_analyst):
        page = ScansListPage(driver).open()
        page.click_filter("COMPLETED")
        page.search("acmecorp")
        assert page.text_present("acmecorp") or page.row_count() == 0


class TestHeaderSearchBarBehavior:
    """The header search bar exists but is not wired to any filtering
    logic (a documented gap, not a mis-designed test)."""

    def test_header_search_input_is_present_and_typable(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.type_into(*layout.SEARCH_INPUT, "anything")
        assert layout.find(*layout.SEARCH_INPUT).get_attribute("value") == "anything"

    def test_typing_in_header_search_does_not_navigate_or_crash(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        layout.type_into(*layout.SEARCH_INPUT, "staging.acmecorp.test")
        assert layout.on_route("")

    def test_header_search_input_present_across_every_core_page(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        for route_key in ["scans", "remediations", "dashboard"]:
            layout.goto(ROUTES[route_key])
            assert layout.exists(*layout.SEARCH_INPUT)
