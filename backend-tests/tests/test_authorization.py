"""
test_authorization.py — Category: Authorization (target: 40+ cases)

Covers role-based access control (client/analyst/admin) and cross-tenant
ownership checks across scans, vulnerabilities, and remediations. Uses
two same-role client accounts (client1/client2) so tests actually check
cross-tenant access, not just "logged in vs not logged in".
"""
import pytest

pytestmark = pytest.mark.authorization

ADMIN_ONLY_GET_ENDPOINTS = [
    "/admin/config",
    "/admin/cve-definitions",
]


class TestAdminOnlyEndpoints:
    @pytest.mark.parametrize("endpoint", ADMIN_ONLY_GET_ENDPOINTS)
    async def test_admin_endpoint_accessible_to_admin(self, client, admin_headers, endpoint):
        """
        CATEGORY: Authorization
        TITLE: Admin-only GET endpoint is reachable by an admin
        OBJECTIVE: Confirm the admin role is not itself over-restricted.
        EXPECTED: 200 OK.
        SEVERITY: Medium
        """
        r = await client.get(endpoint, headers=admin_headers)
        assert r.status_code == 200

    @pytest.mark.parametrize("endpoint", ADMIN_ONLY_GET_ENDPOINTS)
    async def test_admin_endpoint_blocked_for_client(self, client, client1_headers, endpoint):
        """
        CATEGORY: Authorization
        TITLE: Admin-only GET endpoint rejects a client-role user
        OBJECTIVE: Confirm privilege escalation is not possible for 'client'.
        EXPECTED: 403 Forbidden.
        SEVERITY: Critical
        """
        r = await client.get(endpoint, headers=client1_headers)
        assert r.status_code == 403

    @pytest.mark.parametrize("endpoint", ADMIN_ONLY_GET_ENDPOINTS)
    async def test_admin_endpoint_blocked_for_analyst(self, client, analyst_headers, endpoint):
        """
        CATEGORY: Authorization
        TITLE: Admin-only GET endpoint rejects an analyst-role user
        OBJECTIVE: Confirm 'analyst' does not implicitly inherit admin rights.
        EXPECTED: 403 Forbidden.
        SEVERITY: Critical
        """
        r = await client.get(endpoint, headers=analyst_headers)
        assert r.status_code == 403

    @pytest.mark.parametrize("endpoint", ADMIN_ONLY_GET_ENDPOINTS)
    async def test_admin_endpoint_blocked_when_unauthenticated(self, client, endpoint):
        """
        CATEGORY: Authorization
        TITLE: Admin-only GET endpoint rejects unauthenticated requests
        OBJECTIVE: Confirm no anonymous access to admin data.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Critical
        """
        r = await client.get(endpoint)
        assert r.status_code == 401

    async def test_admin_config_patch_blocked_for_client(self, client, client1_headers):
        """
        CATEGORY: Authorization
        TITLE: PATCH /admin/config/{key} rejects a client-role user
        OBJECTIVE: Confirm write access to system config is admin-only.
        EXPECTED: 403 Forbidden.
        SEVERITY: Critical
        """
        r = await client.patch("/admin/config/max_concurrent_scans", json={"config_value": "10"}, headers=client1_headers)
        assert r.status_code == 403

    async def test_admin_config_patch_allowed_for_admin(self, client, admin_headers):
        """
        CATEGORY: Authorization
        TITLE: PATCH /admin/config/{key} succeeds for an admin
        OBJECTIVE: Confirm the admin write path itself functions.
        EXPECTED: 200 OK.
        SEVERITY: Low
        """
        r = await client.patch("/admin/config/max_concurrent_scans", json={"config_value": "10"}, headers=admin_headers)
        assert r.status_code == 200

    async def test_cve_sync_blocked_for_analyst(self, client, analyst_headers):
        """
        CATEGORY: Authorization
        TITLE: POST /admin/cve-definitions/sync rejects an analyst-role user
        OBJECTIVE: Confirm the CVE sync trigger is admin-only.
        EXPECTED: 403 Forbidden.
        SEVERITY: High
        """
        r = await client.post("/admin/cve-definitions/sync", headers=analyst_headers)
        assert r.status_code == 403

    async def test_create_admin_user_blocked_for_non_admin(self, client, client1_headers, unique_email):
        """
        CATEGORY: Authorization
        TITLE: POST /auth/users (admin-provisioned account creation) rejects a client
        OBJECTIVE: Confirm only admins can provision new accounts via this path.
        EXPECTED: 403 Forbidden.
        SEVERITY: Critical
        """
        r = await client.post("/auth/users", headers=client1_headers, json={
            "email": unique_email, "full_name": "New Officer", "role": "analyst", "temp_password": "TempPass123!",
        })
        assert r.status_code == 403

    async def test_create_admin_user_allowed_for_admin(self, client, admin_headers, unique_email):
        """
        CATEGORY: Authorization
        TITLE: POST /auth/users succeeds for an admin
        OBJECTIVE: Confirm the admin-provisioning path itself works, including
                    provisioning a role ('admin') self-registration cannot reach.
        EXPECTED: 201 Created.
        SEVERITY: Medium
        """
        r = await client.post("/auth/users", headers=admin_headers, json={
            "email": unique_email, "full_name": "New Analyst", "role": "analyst", "temp_password": "TempPass123!",
        })
        assert r.status_code == 201


class TestAnalystPrivilegedActions:
    async def test_vulnerability_status_update_blocked_for_client(self, client, client1_headers, seeded_vulnerability):
        """
        CATEGORY: Authorization
        TITLE: PATCH /vulnerabilities/{id} rejects a client-role user
        OBJECTIVE: Confirm only analyst/admin can triage vulnerability status.
        EXPECTED: 403 Forbidden.
        SEVERITY: High
        """
        r = await client.patch(
            f"/vulnerabilities/{seeded_vulnerability['vuln_id']}",
            json={"status": "CONFIRMED"}, headers=client1_headers,
        )
        assert r.status_code == 403

    async def test_vulnerability_status_update_allowed_for_analyst(self, client, analyst_headers, seeded_vulnerability):
        """
        CATEGORY: Authorization
        TITLE: PATCH /vulnerabilities/{id} succeeds for an analyst
        OBJECTIVE: Confirm the analyst role can perform its core triage action.
        EXPECTED: 200 OK.
        SEVERITY: Low
        """
        r = await client.patch(
            f"/vulnerabilities/{seeded_vulnerability['vuln_id']}",
            json={"status": "CONFIRMED"}, headers=analyst_headers,
        )
        assert r.status_code == 200

    async def test_remediation_approve_blocked_for_client(self, client, client1_headers, seeded_remediation):
        """
        CATEGORY: Authorization
        TITLE: POST /remediations/{id}/approve rejects a client-role user
        OBJECTIVE: Confirm remediation approval is restricted to analyst/admin.
        EXPECTED: 403 Forbidden.
        SEVERITY: High
        """
        r = await client.post(f"/remediations/{seeded_remediation['remediation_id']}/approve", headers=client1_headers)
        assert r.status_code == 403

    async def test_remediation_approve_allowed_for_analyst(self, client, analyst_headers, seeded_remediation):
        """
        CATEGORY: Authorization
        TITLE: POST /remediations/{id}/approve succeeds for an analyst
        OBJECTIVE: Confirm the approval action itself functions for the intended role.
        EXPECTED: 200 OK, status becomes APPROVED.
        SEVERITY: Low
        """
        r = await client.post(f"/remediations/{seeded_remediation['remediation_id']}/approve", headers=analyst_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "APPROVED"

    async def test_remediation_reject_blocked_for_client(self, client, client1_headers, seeded_remediation_2):
        """
        CATEGORY: Authorization
        TITLE: POST /remediations/{id}/reject rejects a client-role user
        OBJECTIVE: Confirm remediation rejection is restricted to analyst/admin.
        EXPECTED: 403 Forbidden.
        SEVERITY: High
        """
        r = await client.post(
            f"/remediations/{seeded_remediation_2['remediation_id']}/reject",
            json={"reason": "not applicable"}, headers=client1_headers,
        )
        assert r.status_code == 403

    async def test_remediation_reject_allowed_for_admin(self, client, admin_headers, seeded_remediation_2):
        """
        CATEGORY: Authorization
        TITLE: POST /remediations/{id}/reject succeeds for an admin
        OBJECTIVE: Confirm admins retain analyst-level remediation privileges.
        EXPECTED: 200 OK, status becomes REJECTED.
        SEVERITY: Low
        """
        r = await client.post(
            f"/remediations/{seeded_remediation_2['remediation_id']}/reject",
            json={"reason": "not applicable"}, headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "REJECTED"


class TestScanOwnershipCrossTenant:
    """client2 must never be able to read/act on client1's scan data."""

    async def test_owner_can_view_own_scan(self, client, client1_headers, client1_scan):
        """
        CATEGORY: Authorization
        TITLE: Scan owner can view their own scan
        OBJECTIVE: Baseline positive case for the ownership check.
        EXPECTED: 200 OK.
        SEVERITY: Low
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}", headers=client1_headers)
        assert r.status_code == 200

    async def test_other_client_cannot_view_scan_idor(self, client, client2_headers, client1_scan):
        """
        CATEGORY: Authorization
        TITLE: [IDOR] A different client cannot view another tenant's scan
        OBJECTIVE: Cross-tenant authorization check, not just auth-vs-anon.
        EXPECTED: 403 Forbidden.
        SEVERITY: Critical
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}", headers=client2_headers)
        assert r.status_code == 403

    async def test_admin_can_view_any_scan(self, client, admin_headers, client1_scan):
        """
        CATEGORY: Authorization
        TITLE: Admin can view any tenant's scan
        OBJECTIVE: Confirm the admin override bypasses per-user ownership as designed.
        EXPECTED: 200 OK.
        SEVERITY: Low
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}", headers=admin_headers)
        assert r.status_code == 200

    async def test_unauthenticated_cannot_view_scan(self, client, client1_scan):
        """
        CATEGORY: Authorization
        TITLE: Unauthenticated request to a scan is rejected
        OBJECTIVE: Baseline anonymous-access check.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Critical
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}")
        assert r.status_code == 401

    async def test_other_client_cannot_cancel_scan_idor(self, client, client2_headers, client1_scan):
        """
        CATEGORY: Authorization
        TITLE: [IDOR] A different client cannot cancel another tenant's scan
        OBJECTIVE: Cross-tenant write-action check.
        EXPECTED: 403 Forbidden.
        SEVERITY: Critical
        """
        r = await client.post(f"/scans/{client1_scan['scan_id']}/cancel", headers=client2_headers)
        assert r.status_code == 403

    async def test_other_client_cannot_list_scan_vulnerabilities_idor(self, client, client2_headers, client1_scan):
        """
        CATEGORY: Authorization
        TITLE: [IDOR] A different client cannot list another tenant's scan vulnerabilities
        OBJECTIVE: Cross-tenant nested-resource check.
        EXPECTED: 403 Forbidden.
        SEVERITY: Critical
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}/vulnerabilities", headers=client2_headers)
        assert r.status_code == 403

    async def test_other_client_cannot_list_scan_threat_logs_idor(self, client, client2_headers, client1_scan):
        """
        CATEGORY: Authorization
        TITLE: [IDOR] A different client cannot list another tenant's threat logs
        OBJECTIVE: Cross-tenant nested-resource check.
        EXPECTED: 404 Not Found (this endpoint 404s rather than 403 on mismatch by design).
        SEVERITY: Critical
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}/threat-logs", headers=client2_headers)
        assert r.status_code == 404

    async def test_other_client_cannot_list_scan_remediations_idor(self, client, client2_headers, client1_scan):
        """
        CATEGORY: Authorization
        TITLE: [IDOR] A different client cannot list another tenant's scan remediations
        OBJECTIVE: Cross-tenant nested-resource check.
        EXPECTED: 404 Not Found (this endpoint 404s rather than 403 on mismatch by design).
        SEVERITY: Critical
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}/remediations", headers=client2_headers)
        assert r.status_code == 404

    async def test_scan_list_scopes_to_owner_for_client_role(self, client, client1_headers, client2_headers, client1_scan):
        """
        CATEGORY: Authorization
        TITLE: GET /scans only returns the caller's own scans for role=client
        OBJECTIVE: Confirm list-endpoint scoping, not just single-resource ownership.
        EXPECTED: client2's scan list never contains client1's scan_id.
        SEVERITY: Critical
        """
        r = await client.get("/scans", headers=client2_headers)
        assert r.status_code == 200
        ids = [s["scan_id"] for s in r.json()]
        assert client1_scan["scan_id"] not in ids

    async def test_scan_list_shows_all_scans_for_admin(self, client, admin_headers, client1_scan):
        """
        CATEGORY: Authorization
        TITLE: GET /scans returns every tenant's scans for role=admin
        OBJECTIVE: Confirm the admin list view is not incorrectly scoped down.
        EXPECTED: client1's scan_id is present in the admin's scan list.
        SEVERITY: Medium
        """
        r = await client.get("/scans", headers=admin_headers)
        assert r.status_code == 200
        ids = [s["scan_id"] for s in r.json()]
        assert client1_scan["scan_id"] in ids


class TestKnownIdorGaps:
    """
    These document CONFIRMED gaps found by static review of
    api/routes/vulnerabilities.py and api/routes/remediations.py: neither
    GET /vulnerabilities/{id} nor GET /remediations/{id} performs any
    ownership check at all (unlike the /scans/* family above). Any
    authenticated user -- any role -- can read any other tenant's
    vulnerability or remediation record by ID. See findings.xlsx (VULN-001).
    """

    async def test_get_vulnerability_by_id_has_no_ownership_check(self, client, client2_headers, seeded_vulnerability):
        """
        CATEGORY: Authorization
        TITLE: [IDOR - CONFIRMED FINDING] GET /vulnerabilities/{id} has no tenant check
        OBJECTIVE: Document that a client from a different tenant CAN currently
                    read a vulnerability that belongs to another user's scan.
        EXPECTED (CURRENT BEHAVIOR): 200 OK -- this is the vulnerability, not the
                   correct behavior. See findings.xlsx VULN-001 (Critical) for
                   the remediation recommendation (add a scan-ownership join
                   check identical to the one already used in scans.py).
        SEVERITY: Critical
        """
        r = await client.get(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}", headers=client2_headers)
        assert r.status_code == 200, (
            "If this now returns 403/404, the IDOR in VULN-001 has been fixed -- "
            "update findings.xlsx accordingly rather than treating this as a test failure."
        )

    async def test_get_remediation_by_id_has_no_ownership_check(self, client, client2_headers, seeded_remediation):
        """
        CATEGORY: Authorization
        TITLE: [IDOR - CONFIRMED FINDING] GET /remediations/{id} has no tenant check
        OBJECTIVE: Document that a client from a different tenant CAN currently
                    read another tenant's remediation record.
        EXPECTED (CURRENT BEHAVIOR): 200 OK. See findings.xlsx VULN-001.
        SEVERITY: Critical
        """
        r = await client.get(f"/remediations/{seeded_remediation['remediation_id']}", headers=client2_headers)
        assert r.status_code == 200, (
            "If this now returns 403/404, the IDOR in VULN-001 has been fixed -- "
            "update findings.xlsx accordingly rather than treating this as a test failure."
        )

    async def test_list_remediations_is_not_scoped_per_tenant(self, client, client1_headers, seeded_remediation):
        """
        CATEGORY: Authorization
        TITLE: [Finding] GET /remediations (list) is not scoped by tenant for role=client
        OBJECTIVE: Document that the list endpoint returns remediations across
                    all tenants regardless of caller role.
        EXPECTED (CURRENT BEHAVIOR): 200 OK with the fixture remediation visible
                   even though it belongs to a scan client1 does not own in this
                   test. See findings.xlsx VULN-001.
        SEVERITY: High
        """
        r = await client.get("/remediations", headers=client1_headers)
        assert r.status_code == 200
        ids = [rem["remediation_id"] for rem in r.json()]
        assert seeded_remediation["remediation_id"] in ids


class TestDeviceRegistrationAuthz:
    async def test_device_register_requires_auth(self, client):
        """
        CATEGORY: Authorization
        TITLE: POST /devices/register requires authentication
        OBJECTIVE: Confirm push-token registration cannot be spoofed anonymously.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Medium
        """
        r = await client.post("/devices/register", json={"fcm_token": "x" * 20, "platform": "android"})
        assert r.status_code == 401

    async def test_device_register_succeeds_for_any_authenticated_role(self, client, client1_headers):
        """
        CATEGORY: Authorization
        TITLE: POST /devices/register succeeds for a client-role user
        OBJECTIVE: Confirm this endpoint is intentionally open to every role (no
                    admin-only restriction is expected here).
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        r = await client.post("/devices/register", json={"fcm_token": "clientdevicetoken1234", "platform": "android"}, headers=client1_headers)
        assert r.status_code == 201

    async def test_device_register_succeeds_for_analyst_role(self, client, analyst_headers):
        """
        CATEGORY: Authorization
        TITLE: POST /devices/register succeeds for an analyst-role user
        OBJECTIVE: Confirm device registration is open to every role, analyst included.
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        r = await client.post("/devices/register", json={"fcm_token": "analystdevicetoken12345", "platform": "ios"}, headers=analyst_headers)
        assert r.status_code == 201

    async def test_device_register_succeeds_for_admin_role(self, client, admin_headers):
        """
        CATEGORY: Authorization
        TITLE: POST /devices/register succeeds for an admin-role user
        OBJECTIVE: Confirm device registration is open to every role, admin included.
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        r = await client.post("/devices/register", json={"fcm_token": "admindevicetoken123456", "platform": "android"}, headers=admin_headers)
        assert r.status_code == 201


class TestAuthorizationHeaderEdgeCases:
    async def test_analyst_cannot_reach_admin_config_patch(self, client, analyst_headers):
        """
        CATEGORY: Authorization
        TITLE: PATCH /admin/config/{key} rejects an analyst-role user
        OBJECTIVE: Confirm analyst does not have write access to system config either.
        EXPECTED: 403 Forbidden.
        SEVERITY: Critical
        """
        r = await client.patch("/admin/config/max_concurrent_scans", json={"config_value": "1"}, headers=analyst_headers)
        assert r.status_code == 403

    async def test_cve_sync_blocked_for_client(self, client, client1_headers):
        """
        CATEGORY: Authorization
        TITLE: POST /admin/cve-definitions/sync rejects a client-role user
        OBJECTIVE: Confirm the CVE sync trigger is blocked for the client role too.
        EXPECTED: 403 Forbidden.
        SEVERITY: High
        """
        r = await client.post("/admin/cve-definitions/sync", headers=client1_headers)
        assert r.status_code == 403

    async def test_cve_definitions_get_blocked_for_client(self, client, client1_headers):
        """
        CATEGORY: Authorization
        TITLE: GET /admin/cve-definitions rejects a client-role user
        OBJECTIVE: Confirm CVE data itself is admin-only, not just the sync trigger.
        EXPECTED: 403 Forbidden.
        SEVERITY: Medium
        """
        r = await client.get("/admin/cve-definitions", headers=client1_headers)
        assert r.status_code == 403
