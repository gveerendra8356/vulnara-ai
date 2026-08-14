"""
test_authorization.py

Covers: ProtectedRoute redirect behavior (src/components/ProtectedRoute.jsx),
admin-only route gating, role-based sidebar visibility, and unknown-route
handling both authenticated and not.

Verified from source:
  if (loading) -> spinner
  if (!user) -> <Navigate to="/login" replace />
  if (requireAdmin && user.role !== "admin") -> <Navigate to="/" replace />
"""

import pytest

from config import CORE_PROTECTED_ROUTES, ADMIN_ROUTES, ALL_PROTECTED_ROUTES, CREDENTIALS, MOCK_PASSWORD, ROUTES
from pages.login_page import LoginPage
from pages.register_page import RegisterPage
from pages.app_layout import AppLayout
from pages.base_page import BasePage

pytestmark = pytest.mark.authorization


# ----------------------------------------------------- unauthenticated gate

class TestUnauthenticatedRedirects:
    @pytest.mark.parametrize("route", ALL_PROTECTED_ROUTES)
    def test_direct_navigation_to_protected_route_redirects_to_login(self, driver, route):
        page = BasePage(driver)
        page.goto(ROUTES[route])
        assert page.on_route("login")

    def test_unauthenticated_root_redirects_to_login(self, driver):
        page = BasePage(driver)
        page.goto("")
        assert page.on_route("login")


# -------------------------------------------------------------- admin gate

class TestAdminRouteGating:
    @pytest.mark.parametrize("route", ADMIN_ROUTES)
    def test_analyst_cannot_access_admin_routes(self, driver, login_as_analyst, route):
        page = BasePage(driver)
        page.goto(ROUTES[route])
        assert page.on_route("")

    @pytest.mark.parametrize("route", ADMIN_ROUTES)
    def test_client_cannot_access_admin_routes(self, driver, route):
        import uuid
        email = f"authz-client-{uuid.uuid4().hex[:8]}@vulnara.dev"
        reg = RegisterPage(driver).open()
        reg.register(full_name="Authz Client", email=email, password=MOCK_PASSWORD, role="client")
        page = BasePage(driver)
        page.on_route("")
        page.goto(ROUTES[route])
        assert page.on_route("")

    @pytest.mark.parametrize("route", ADMIN_ROUTES)
    def test_admin_can_access_admin_routes(self, driver, login_as_admin, route):
        page = BasePage(driver)
        page.goto(ROUTES[route])
        assert page.on_route(ROUTES[route])


# ----------------------------------------------------- core route access

class TestAuthorizedAccess:
    @pytest.mark.parametrize("route", CORE_PROTECTED_ROUTES)
    def test_protected_route_does_not_bounce_back_to_login(self, driver, login_as_analyst, route):
        page = BasePage(driver)
        page.goto(ROUTES[route])
        assert not page.on_route("login", timeout=4)

    @pytest.mark.parametrize("route", CORE_PROTECTED_ROUTES)
    def test_admin_can_access_every_core_route(self, driver, login_as_admin, route):
        page = BasePage(driver)
        page.goto(ROUTES[route])
        assert not page.on_route("login", timeout=4)


# ---------------------------------------------------- role-based nav items

class TestRoleBasedNavVisibility:
    def test_admin_nav_section_hidden_for_analyst(self, driver, login_as_analyst):
        layout = AppLayout(driver)
        assert not layout.nav_item_visible("admin_config")
        assert not layout.nav_item_visible("admin_cve")

    def test_admin_nav_section_visible_for_admin(self, driver, login_as_admin):
        layout = AppLayout(driver)
        assert layout.nav_item_visible("admin_config")
        assert layout.nav_item_visible("admin_cve")

    @pytest.mark.parametrize("nav_key", ["dashboard", "scans", "remediations"])
    def test_core_nav_items_visible_for_every_role(self, driver, login_as_any_role, nav_key):
        _, role = login_as_any_role
        layout = AppLayout(driver)
        assert layout.nav_item_visible(nav_key)

    def test_admin_config_link_navigates_to_admin_config_page(self, driver, login_as_admin):
        layout = AppLayout(driver)
        layout.click_nav("admin_config")
        assert layout.on_route("admin/config")

    def test_admin_cve_link_navigates_to_cve_database_page(self, driver, login_as_admin):
        layout = AppLayout(driver)
        layout.click_nav("admin_cve")
        assert layout.on_route("admin/cve")


# ------------------------------------------------------------- unknown route

class TestUnknownRoutes:
    def test_unknown_route_when_unauthenticated_shows_not_found_or_login(self, driver):
        page = BasePage(driver)
        page.goto(ROUTES["unknown"])
        # App has a top-level catch-all "*" -> NotFoundPage, independent of auth.
        assert page.text_present("404") or page.on_route("login")

    def test_unknown_route_when_authenticated_shows_not_found_page(self, driver, login_as_analyst):
        page = BasePage(driver)
        page.goto(ROUTES["unknown"])
        assert page.text_present("404")


# --------------------------------------------------------- cross-role reach

class TestCrossRoleDataVisibility:
    def test_client_can_reach_scan_detail_of_seeded_scan(self, driver):
        """Mock Mode has no per-user scoping (state.scans is a single shared
        in-memory array) -- any authenticated role can open any seeded
        scan/vuln detail URL. This documents real current behavior; it is
        not an endorsement of it as a security design for the real backend."""
        import uuid
        email = f"authz-cross-{uuid.uuid4().hex[:8]}@vulnara.dev"
        reg = RegisterPage(driver).open()
        reg.register(full_name="Cross Role", email=email, password=MOCK_PASSWORD, role="client")
        page = BasePage(driver)
        page.on_route("")
        page.goto(ROUTES["scan_detail"])
        assert not page.on_route("login", timeout=4)

    def test_analyst_can_reach_remediation_review_of_seeded_id(self, driver, login_as_analyst):
        page = BasePage(driver)
        page.goto(ROUTES["remediation_review"])
        assert not page.on_route("login", timeout=4)
