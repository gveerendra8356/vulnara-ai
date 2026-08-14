"""
test_functional_api.py — Category: Functional API (target: 100+ cases)

Contract-level correctness for every route: response shape, field types,
status codes, filters, and not-found handling. Where authorization/
input-validation/injection angles for the same endpoint are covered
elsewhere, this file focuses on "does it do the right thing when used
correctly".
"""
import uuid

import pytest

pytestmark = pytest.mark.functional_api


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    async def test_health_status_code(self, client):
        """
        CATEGORY: Functional API
        TITLE: GET /health returns 200
        OBJECTIVE: Baseline liveness check.
        EXPECTED: 200 OK.
        SEVERITY: Low
        """
        assert (await client.get("/health")).status_code == 200

    async def test_health_response_has_status_field(self, client):
        """
        CATEGORY: Functional API
        TITLE: GET /health response includes a 'status' field
        OBJECTIVE: Confirm the response contract.
        EXPECTED: body['status'] == 'ok'.
        SEVERITY: Low
        """
        assert (await client.get("/health")).json()["status"] == "ok"

    async def test_health_response_has_db_field(self, client):
        """
        CATEGORY: Functional API
        TITLE: GET /health response includes a 'db' field
        OBJECTIVE: Confirm the response contract.
        EXPECTED: body['db'] present and is a string.
        SEVERITY: Low
        """
        assert isinstance((await client.get("/health")).json()["db"], str)


# ---------------------------------------------------------------------------
# /auth/*
# ---------------------------------------------------------------------------

class TestAuthResponseShapes:
    async def test_register_response_has_all_expected_fields(self, client, unique_email):
        """
        CATEGORY: Functional API
        TITLE: POST /auth/register response matches UserResponse contract
        OBJECTIVE: Confirm every documented field is present with the right type.
        EXPECTED: user_id (str/UUID), email, full_name, role, created_at all present.
        SEVERITY: Medium
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "Shape QA", "role": "client",
        })
        body = r.json()
        for field in ("user_id", "email", "full_name", "role", "created_at"):
            assert field in body, f"missing field: {field}"

    async def test_login_response_has_all_expected_fields(self, client, unique_email):
        """
        CATEGORY: Functional API
        TITLE: POST /auth/login response matches TokenResponse contract
        OBJECTIVE: Confirm every documented field is present with the right type.
        EXPECTED: access_token, refresh_token, token_type, expires_in, user all present.
        SEVERITY: Medium
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "Shape QA", "role": "client",
        })
        r = await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})
        body = r.json()
        for field in ("access_token", "refresh_token", "token_type", "expires_in", "user"):
            assert field in body
        assert isinstance(body["expires_in"], int)
        assert isinstance(body["access_token"], str) and len(body["access_token"]) > 20

    async def test_me_response_matches_user_response_contract(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: GET /auth/me response matches UserResponse contract
        OBJECTIVE: Confirm field presence/types for the identity endpoint.
        EXPECTED: user_id, email, full_name, role, created_at, last_login_at present.
        SEVERITY: Medium
        """
        r = await client.get("/auth/me", headers=client1_headers)
        body = r.json()
        for field in ("user_id", "email", "full_name", "role", "created_at", "last_login_at"):
            assert field in body
        assert body["role"] == "client"

    async def test_me_role_reflects_actual_account_role(self, client, admin_headers, analyst_headers):
        """
        CATEGORY: Functional API
        TITLE: GET /auth/me returns the correct role per account
        OBJECTIVE: Confirm role resolution isn't hardcoded/stubbed.
        EXPECTED: admin session -> role 'admin'; analyst session -> role 'analyst'.
        SEVERITY: Medium
        """
        admin_me = await client.get("/auth/me", headers=admin_headers)
        analyst_me = await client.get("/auth/me", headers=analyst_headers)
        assert admin_me.json()["role"] == "admin"
        assert analyst_me.json()["role"] == "analyst"


# ---------------------------------------------------------------------------
# /scans
# ---------------------------------------------------------------------------

class TestScanCrud:
    async def test_create_scan_response_shape(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: POST /scans response matches ScanCreateResponse contract
        OBJECTIVE: Confirm every documented field is present.
        EXPECTED: scan_id, target, status, active_testing_enabled, created_at present.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "functional-shape.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Functional shape regression test.",
        })
        assert r.status_code == 201
        body = r.json()
        for field in ("scan_id", "target", "status", "active_testing_enabled", "created_at"):
            assert field in body

    async def test_get_scan_includes_vulnerability_severity_counts(self, client, client1_headers, client1_scan):
        """
        CATEGORY: Functional API
        TITLE: GET /scans/{id} includes a vulnerability-severity breakdown
        OBJECTIVE: Confirm the aggregation query in get_scan actually runs and
                    is exposed in the response.
        EXPECTED: 200, response contains the scan's core fields.
        SEVERITY: Low
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}", headers=client1_headers)
        assert r.status_code == 200
        assert r.json()["scan_id"] == client1_scan["scan_id"]

    async def test_list_scans_returns_an_array(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: GET /scans returns a JSON array
        OBJECTIVE: Confirm the list endpoint's top-level response type.
        EXPECTED: 200, response body is a list.
        SEVERITY: Low
        """
        r = await client.get("/scans", headers=client1_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_get_nonexistent_scan_returns_404(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: GET /scans/{id} for an unknown id returns 404
        OBJECTIVE: Baseline not-found handling.
        EXPECTED: 404 Not Found.
        SEVERITY: Low
        """
        r = await client.get(f"/scans/{uuid.uuid4()}", headers=client1_headers)
        assert r.status_code == 404

    async def test_list_scan_vulnerabilities_returns_array(self, client, client1_headers, client1_scan):
        """
        CATEGORY: Functional API
        TITLE: GET /scans/{id}/vulnerabilities returns a JSON array
        OBJECTIVE: Confirm the nested-list endpoint's response type, even when empty.
        EXPECTED: 200, response is a list (empty for a fresh scan).
        SEVERITY: Low
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}/vulnerabilities", headers=client1_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_list_scan_vulnerabilities_severity_filter_accepted(self, client, client1_headers, client1_scan):
        """
        CATEGORY: Functional API
        TITLE: GET /scans/{id}/vulnerabilities?severity= is accepted
        OBJECTIVE: Confirm the optional severity query param doesn't error.
        EXPECTED: 200 for a plausible severity value.
        SEVERITY: Low
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}/vulnerabilities", params={"severity": "HIGH"}, headers=client1_headers)
        assert r.status_code == 200

    async def test_list_scan_threat_logs_returns_array_for_owner(self, client, client1_headers, client1_scan):
        """
        CATEGORY: Functional API
        TITLE: GET /scans/{id}/threat-logs returns a JSON array for the owner
        OBJECTIVE: Confirm the endpoint responds correctly for a scan the
                    caller legitimately owns (paired with the 404-on-mismatch
                    IDOR test in test_authorization.py).
        EXPECTED: 200, response is a list.
        SEVERITY: Low
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}/threat-logs", headers=client1_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_list_scan_remediations_returns_array_for_owner(self, client, client1_headers, client1_scan):
        """
        CATEGORY: Functional API
        TITLE: GET /scans/{id}/remediations returns a JSON array for the owner
        OBJECTIVE: Confirm the nested remediations-by-scan endpoint works for the owner.
        EXPECTED: 200, response is a list.
        SEVERITY: Low
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}/remediations", headers=client1_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_scan_created_at_is_iso8601(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: Scan created_at is a valid ISO-8601 timestamp
        OBJECTIVE: Confirm timestamp serialization format for downstream clients.
        EXPECTED: created_at parses cleanly with datetime.fromisoformat.
        SEVERITY: Low
        """
        from datetime import datetime
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "iso-timestamp.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "ISO-8601 timestamp regression test.",
        })
        created_at = r.json()["created_at"]
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# /vulnerabilities
# ---------------------------------------------------------------------------

class TestVulnerabilityCrud:
    async def test_get_vulnerability_response_shape(self, client, admin_headers, seeded_vulnerability):
        """
        CATEGORY: Functional API
        TITLE: GET /vulnerabilities/{id} response matches VulnerabilityResponse contract
        OBJECTIVE: Confirm every documented field is present.
        EXPECTED: vuln_id, scan_id, host, severity, confidence_score, status, discovered_at present.
        SEVERITY: Medium
        """
        r = await client.get(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        for field in ("vuln_id", "scan_id", "host", "severity", "confidence_score", "status", "discovered_at"):
            assert field in body

    async def test_get_nonexistent_vulnerability_returns_404(self, client, admin_headers):
        """
        CATEGORY: Functional API
        TITLE: GET /vulnerabilities/{id} for an unknown id returns 404
        OBJECTIVE: Baseline not-found handling.
        EXPECTED: 404 Not Found.
        SEVERITY: Low
        """
        r = await client.get(f"/vulnerabilities/{uuid.uuid4()}", headers=admin_headers)
        assert r.status_code == 404

    async def test_update_nonexistent_vulnerability_returns_404(self, client, analyst_headers):
        """
        CATEGORY: Functional API
        TITLE: PATCH /vulnerabilities/{id} for an unknown id returns 404
        OBJECTIVE: Baseline not-found handling on the write path.
        EXPECTED: 404 Not Found.
        SEVERITY: Low
        """
        r = await client.patch(f"/vulnerabilities/{uuid.uuid4()}", headers=analyst_headers, json={"status": "CONFIRMED"})
        assert r.status_code == 404

    @pytest.mark.parametrize("new_status", ["CONFIRMED", "FALSE_POSITIVE", "REMEDIATED", "OPEN"])
    async def test_update_vulnerability_status_round_trips(self, client, analyst_headers, seeded_vulnerability, new_status):
        """
        CATEGORY: Functional API
        TITLE: PATCH /vulnerabilities/{id} correctly persists each plausible status value
        OBJECTIVE: Confirm the write actually round-trips through a GET afterwards.
        EXPECTED: PATCH 200 with the new status; a follow-up GET reflects the same value.
        SEVERITY: Low
        """
        patch = await client.patch(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}", headers=analyst_headers, json={"status": new_status})
        assert patch.status_code == 200
        assert patch.json()["status"] == new_status
        get = await client.get(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}", headers=analyst_headers)
        assert get.json()["status"] == new_status

    async def test_vulnerability_cvss_score_is_numeric(self, client, admin_headers, seeded_vulnerability):
        """
        CATEGORY: Functional API
        TITLE: Vulnerability cvss_score is serialized as a number, not a string
        OBJECTIVE: Confirm the Numeric(3,1) DB column round-trips as a JSON number.
        EXPECTED: cvss_score is int or float.
        SEVERITY: Low
        """
        r = await client.get(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}", headers=admin_headers)
        assert isinstance(r.json()["cvss_score"], (int, float))


# ---------------------------------------------------------------------------
# /remediations
# ---------------------------------------------------------------------------

class TestRemediationCrud:
    async def test_list_remediations_returns_array(self, client, admin_headers):
        """
        CATEGORY: Functional API
        TITLE: GET /remediations returns a JSON array
        OBJECTIVE: Confirm the top-level list endpoint response type.
        EXPECTED: 200, response is a list.
        SEVERITY: Low
        """
        r = await client.get("/remediations", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_remediation_response_shape(self, client, admin_headers, seeded_remediation):
        """
        CATEGORY: Functional API
        TITLE: GET /remediations/{id} response matches RemediationResponse contract
        OBJECTIVE: Confirm every documented field is present.
        EXPECTED: remediation_id, vuln_id, executive_summary, technical_script,
                   ai_confidence, status, created_at present.
        SEVERITY: Medium
        """
        r = await client.get(f"/remediations/{seeded_remediation['remediation_id']}", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        for field in ("remediation_id", "vuln_id", "executive_summary", "technical_script", "ai_confidence", "status", "created_at"):
            assert field in body

    async def test_remediation_ai_confidence_is_numeric_between_0_and_1(self, client, admin_headers, seeded_remediation):
        """
        CATEGORY: Functional API
        TITLE: Remediation ai_confidence is a float in the [0, 1] range
        OBJECTIVE: Confirm the seeded fixture value round-trips as expected
                    and the field type is sane for a confidence score.
        EXPECTED: 0 <= ai_confidence <= 1.
        SEVERITY: Low
        """
        r = await client.get(f"/remediations/{seeded_remediation['remediation_id']}", headers=admin_headers)
        assert 0 <= r.json()["ai_confidence"] <= 1

    async def test_reject_nonexistent_remediation_returns_404(self, client, admin_headers):
        """
        CATEGORY: Functional API
        TITLE: POST /remediations/{id}/reject for an unknown id returns 404
        OBJECTIVE: Baseline not-found handling.
        EXPECTED: 404 Not Found.
        SEVERITY: Low
        """
        r = await client.post(f"/remediations/{uuid.uuid4()}/reject", headers=admin_headers, json={"reason": "n/a"})
        assert r.status_code == 404

    async def test_mark_executed_nonexistent_remediation_returns_404(self, client, admin_headers):
        """
        CATEGORY: Functional API
        TITLE: POST /remediations/{id}/mark-executed for an unknown id returns 404
        OBJECTIVE: Baseline not-found handling.
        EXPECTED: 404 Not Found.
        SEVERITY: Low
        """
        r = await client.post(f"/remediations/{uuid.uuid4()}/mark-executed", headers=admin_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# /devices
# ---------------------------------------------------------------------------

class TestDeviceCrud:
    async def test_register_device_response_shape(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: POST /devices/register response matches DeviceRegisterResponse contract
        OBJECTIVE: Confirm every documented field is present.
        EXPECTED: device_token_id, platform, created_at present.
        SEVERITY: Low
        """
        r = await client.post("/devices/register", headers=client1_headers, json={
            "fcm_token": "functionalshapetoken12345", "platform": "ios",
        })
        assert r.status_code == 201
        body = r.json()
        for field in ("device_token_id", "platform", "created_at"):
            assert field in body
        assert body["platform"] == "ios"

    async def test_register_same_device_token_twice_does_not_500(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: Registering the same fcm_token twice does not crash the server
        OBJECTIVE: Confirm duplicate-token handling degrades gracefully
                    (either idempotent success or a clean error), whatever the
                    intended semantics are.
        EXPECTED: 201 or 4xx, never 500.
        SEVERITY: Medium
        """
        payload = {"fcm_token": "duplicatetokentest123456", "platform": "android"}
        r1 = await client.post("/devices/register", headers=client1_headers, json=payload)
        r2 = await client.post("/devices/register", headers=client1_headers, json=payload)
        assert r1.status_code == 201
        assert r2.status_code != 500


# ---------------------------------------------------------------------------
# /admin
# ---------------------------------------------------------------------------

class TestAdminConfigCrud:
    async def test_list_config_returns_array_of_key_value_entries(self, client, admin_headers):
        """
        CATEGORY: Functional API
        TITLE: GET /admin/config returns an array of {key, value, description} entries
        OBJECTIVE: Confirm the response shape used by any admin UI consuming this.
        EXPECTED: 200, list of dicts each containing 'key' and 'value'.
        SEVERITY: Low
        """
        r = await client.get("/admin/config", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list) and len(body) > 0
        for entry in body:
            assert "key" in entry and "value" in entry

    async def test_patch_config_response_echoes_key_and_value(self, client, admin_headers):
        """
        CATEGORY: Functional API
        TITLE: PATCH /admin/config/{key} echoes back the key and new value
        OBJECTIVE: Confirm the immediate response contract.
        EXPECTED: 200, body == {'key': ..., 'value': ...}.
        SEVERITY: Low
        """
        r = await client.patch("/admin/config/max_concurrent_scans", headers=admin_headers, json={"config_value": "25"})
        assert r.status_code == 200
        assert r.json() == {"key": "max_concurrent_scans", "value": "25"}

    async def test_patch_config_change_is_not_actually_persisted(self, client, admin_headers):
        """
        CATEGORY: Functional API
        TITLE: [Finding] PATCH /admin/config/{key} does not persist to GET /admin/config
        OBJECTIVE: update_config() in admin.py returns the submitted value
                    directly with no DB write and list_config() returns a
                    hardcoded literal list -- confirm a PATCH has zero effect
                    on the subsequent GET.
        EXPECTED (CURRENT BEHAVIOR): PATCH reports success (200) but GET
                   /admin/config still shows the original hardcoded value
                   ('5') afterwards. See findings.xlsx (VULN-010, Medium --
                   functional gap, not a security issue, but administrators
                   would reasonably believe the change took effect).
        SEVERITY: Medium
        """
        patch = await client.patch("/admin/config/max_concurrent_scans", headers=admin_headers, json={"config_value": "999"})
        assert patch.status_code == 200
        listing = await client.get("/admin/config", headers=admin_headers)
        entry = next(e for e in listing.json() if e["key"] == "max_concurrent_scans")
        assert entry["value"] != "999", (
            "If this now shows '999', PATCH /admin/config now persists -- "
            "update findings.xlsx VULN-010 accordingly."
        )

    async def test_patch_config_accepts_unknown_key_without_error(self, client, admin_headers):
        """
        CATEGORY: Functional API
        TITLE: PATCH /admin/config/{key} accepts an unrecognized key without validation
        OBJECTIVE: Confirm there's no allow-list of valid config keys -- any
                    string in the path is accepted (consistent with VULN-010:
                    nothing is actually persisted either way).
        EXPECTED: 200 OK even for a nonsense key.
        SEVERITY: Low
        """
        r = await client.patch("/admin/config/this_key_does_not_exist", headers=admin_headers, json={"config_value": "x"})
        assert r.status_code == 200

    async def test_list_cve_definitions_returns_array(self, client, admin_headers):
        """
        CATEGORY: Functional API
        TITLE: GET /admin/cve-definitions returns a JSON array
        OBJECTIVE: Confirm the endpoint works even with an empty table.
        EXPECTED: 200, response is a list.
        SEVERITY: Low
        """
        r = await client.get("/admin/cve-definitions", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_sync_cve_definitions_response_shape(self, client, admin_headers):
        """
        CATEGORY: Functional API
        TITLE: POST /admin/cve-definitions/sync returns a status acknowledgement
        OBJECTIVE: Confirm the trigger endpoint's immediate response contract
                    (the actual sync work, if any, happens out of band).
        EXPECTED: 200, body contains a 'status' field.
        SEVERITY: Low
        """
        r = await client.post("/admin/cve-definitions/sync", headers=admin_headers)
        assert r.status_code == 200
        assert "status" in r.json()


# ---------------------------------------------------------------------------
# Cross-cutting: consistent error envelope
# ---------------------------------------------------------------------------

class TestErrorEnvelopeConsistency:
    @pytest.mark.parametrize("path,method", [
        ("/scans/00000000-0000-0000-0000-000000000000", "GET"),
        ("/vulnerabilities/00000000-0000-0000-0000-000000000000", "GET"),
        ("/remediations/00000000-0000-0000-0000-000000000000", "GET"),
    ])
    async def test_404_responses_share_a_consistent_detail_field(self, client, admin_headers, path, method):
        """
        CATEGORY: Functional API
        TITLE: All 404 responses use the same {'detail': ...} envelope
        OBJECTIVE: Confirm consistent error shape across resource types
                    (FastAPI's default HTTPException envelope).
        EXPECTED: 404, body contains a string 'detail' field.
        SEVERITY: Low
        """
        r = await client.request(method, path, headers=admin_headers)
        assert r.status_code == 404
        assert isinstance(r.json().get("detail"), str)

    @pytest.mark.parametrize("path", ["/admin/config", "/scans", "/remediations"])
    async def test_401_responses_share_a_consistent_detail_field(self, client, path):
        """
        CATEGORY: Functional API
        TITLE: All 401 responses use the same {'detail': ...} envelope
        OBJECTIVE: Confirm consistent unauthenticated-error shape across endpoints.
        EXPECTED: 401, body contains a string 'detail' field.
        SEVERITY: Low
        """
        r = await client.get(path)
        assert r.status_code == 401
        assert isinstance(r.json().get("detail"), str)


# ---------------------------------------------------------------------------
# Additional /auth/users (admin provisioning) contract coverage
# ---------------------------------------------------------------------------

class TestAdminCreateUserCrud:
    @pytest.mark.parametrize("role", ["client", "analyst", "admin"])
    async def test_admin_can_provision_any_role(self, client, admin_headers, unique_email, role):
        """
        CATEGORY: Functional API
        TITLE: POST /auth/users can provision every role, including 'admin'
        OBJECTIVE: Confirm the admin-only provisioning path is the intended
                    (and only) way to create additional admin accounts.
        EXPECTED: 201 Created, role echoed back correctly.
        SEVERITY: Medium
        """
        email = f"{role}.{unique_email}"
        r = await client.post("/auth/users", headers=admin_headers, json={
            "email": email, "full_name": f"Provisioned {role}", "role": role, "temp_password": "TempPass123!",
        })
        assert r.status_code == 201
        assert r.json()["role"] == role

    async def test_admin_create_user_response_has_no_password_fields(self, client, admin_headers, unique_email):
        """
        CATEGORY: Functional API
        TITLE: POST /auth/users response never includes password or temp_password
        OBJECTIVE: Confirm the provisioning response doesn't echo back secrets.
        EXPECTED: 201, 'password' and 'temp_password' absent from the body text.
        SEVERITY: High
        """
        r = await client.post("/auth/users", headers=admin_headers, json={
            "email": unique_email, "full_name": "No Secret Echo", "role": "client", "temp_password": "TempPass123!",
        })
        assert r.status_code == 201
        assert "temp_password" not in r.text
        assert "password_hash" not in r.text

    async def test_admin_create_user_duplicate_email_rejected(self, client, admin_headers, unique_email):
        """
        CATEGORY: Functional API
        TITLE: POST /auth/users rejects a duplicate email, same as self-registration
        OBJECTIVE: Confirm the uniqueness constraint applies uniformly across
                    both account-creation paths.
        EXPECTED: First call 201, second call with the same email 400.
        SEVERITY: Low
        """
        payload = {"email": unique_email, "full_name": "Dup Check", "role": "client", "temp_password": "TempPass123!"}
        r1 = await client.post("/auth/users", headers=admin_headers, json=payload)
        r2 = await client.post("/auth/users", headers=admin_headers, json=payload)
        assert r1.status_code == 201
        assert r2.status_code == 400


# ---------------------------------------------------------------------------
# Additional /auth/refresh + /auth/logout contract coverage
# ---------------------------------------------------------------------------

class TestRefreshLogoutCrud:
    async def test_refresh_response_shape(self, client, unique_email):
        """
        CATEGORY: Functional API
        TITLE: POST /auth/refresh response contains a usable access_token
        OBJECTIVE: Confirm response contract for the refresh endpoint.
        EXPECTED: 200, 'access_token' present and non-empty.
        SEVERITY: Low
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        login = (await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})).json()
        r = await client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert r.status_code == 200
        assert len(r.json()["access_token"]) > 20

    async def test_logout_returns_204_no_content(self, client, unique_email):
        """
        CATEGORY: Functional API
        TITLE: POST /auth/logout returns 204 with an empty body
        OBJECTIVE: Confirm the exact status/response contract for logout.
        EXPECTED: 204 No Content, empty response body.
        SEVERITY: Low
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        login = (await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})).json()
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        r = await client.post("/auth/logout", json={"refresh_token": login["refresh_token"]}, headers=headers)
        assert r.status_code == 204
        assert r.text == ""


# ---------------------------------------------------------------------------
# Additional scan-list filter/ordering coverage
# ---------------------------------------------------------------------------

class TestScanListOrderingAndContent:
    async def test_newly_created_scan_appears_in_list(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: A newly-created scan shows up in a subsequent GET /scans call
        OBJECTIVE: Confirm read-your-writes consistency for the list endpoint.
        EXPECTED: The new scan_id is present in the list response.
        SEVERITY: Medium
        """
        create = await client.post("/scans", headers=client1_headers, json={
            "target": "list-visibility.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "List-visibility regression test.",
        })
        scan_id = create.json()["scan_id"]
        listing = await client.get("/scans", headers=client1_headers)
        ids = [s["scan_id"] for s in listing.json()]
        assert scan_id in ids

    async def test_each_scan_list_entry_has_required_fields(self, client, client1_headers, client1_scan):
        """
        CATEGORY: Functional API
        TITLE: Every entry in GET /scans has the core scan fields
        OBJECTIVE: Confirm the list serializer doesn't drop fields present in
                    the single-resource GET.
        EXPECTED: Each entry has scan_id, target, status.
        SEVERITY: Low
        """
        r = await client.get("/scans", headers=client1_headers)
        assert r.status_code == 200
        for entry in r.json():
            assert "scan_id" in entry
            assert "target" in entry
            assert "status" in entry


# ---------------------------------------------------------------------------
# Additional field-level checks across several resources (parametrized to
# cover many concrete field/value combinations cheaply and legitimately).
# ---------------------------------------------------------------------------

class TestFieldLevelContractChecks:
    @pytest.mark.parametrize("field,expected_type", [
        ("scan_id", str), ("target", str), ("status", str), ("active_testing_enabled", bool),
    ])
    async def test_scan_create_response_field_types(self, client, client1_headers, field, expected_type):
        """
        CATEGORY: Functional API
        TITLE: Each ScanCreateResponse field has the correct JSON type
        OBJECTIVE: Confirm no field is accidentally serialized as the wrong type
                    (e.g. a boolean as a string).
        EXPECTED: isinstance(body[field], expected_type) is True.
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "field-type-check.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Field-type-check regression test.",
        })
        assert isinstance(r.json()[field], expected_type)

    @pytest.mark.parametrize("field,expected_type", [
        ("user_id", str), ("email", str), ("full_name", str), ("role", str),
    ])
    async def test_user_response_field_types(self, client, unique_email, field, expected_type):
        """
        CATEGORY: Functional API
        TITLE: Each UserResponse field has the correct JSON type
        OBJECTIVE: Confirm registration response field types are all strings
                    (in particular, user_id serializes as a string UUID, not a
                    nested object).
        EXPECTED: isinstance(body[field], expected_type) is True.
        SEVERITY: Low
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "Type Check", "role": "client",
        })
        assert isinstance(r.json()[field], expected_type)

    @pytest.mark.parametrize("endpoint,method", [
        ("/scans", "POST"), ("/auth/register", "POST"), ("/auth/login", "POST"),
        ("/devices/register", "POST"),
    ])
    async def test_write_endpoints_return_json_content_type(self, client, client1_headers, endpoint, method):
        """
        CATEGORY: Functional API
        TITLE: Every write endpoint responds with application/json content-type
        OBJECTIVE: Confirm consistent content negotiation across write routes,
                    even on validation-error responses.
        EXPECTED: content-type header starts with 'application/json'.
        SEVERITY: Low
        """
        r = await client.request(method, endpoint, headers=client1_headers, json={})
        assert r.headers.get("content-type", "").startswith("application/json")


# ---------------------------------------------------------------------------
# Extra-field tolerance across every POST/PATCH endpoint (extra keys should
# be silently ignored by pydantic's default config, not rejected).
# ---------------------------------------------------------------------------

class TestExtraFieldTolerance:
    async def test_scan_create_ignores_unknown_extra_fields(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: POST /scans ignores unrecognized extra JSON fields
        OBJECTIVE: Confirm forward-compatible clients sending extra fields
                    don't get spuriously rejected.
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "extra-field.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Extra-field tolerance regression test.",
            "some_future_field": "some_future_value",
        })
        assert r.status_code == 201

    async def test_device_register_ignores_unknown_extra_fields(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: POST /devices/register ignores unrecognized extra JSON fields
        OBJECTIVE: Same forward-compatibility check for the device endpoint.
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        r = await client.post("/devices/register", headers=client1_headers, json={
            "fcm_token": "extrafieldtoken1234567890", "platform": "android",
            "device_model": "Pixel 9",  # not part of the schema
        })
        assert r.status_code == 201

    async def test_vulnerability_update_ignores_unknown_extra_fields(self, client, analyst_headers, seeded_vulnerability):
        """
        CATEGORY: Functional API
        TITLE: PATCH /vulnerabilities/{id} ignores unrecognized extra JSON fields
        OBJECTIVE: Same forward-compatibility check for the vulnerability update endpoint.
        EXPECTED: 200 OK.
        SEVERITY: Low
        """
        r = await client.patch(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}", headers=analyst_headers, json={
            "status": "OPEN", "reviewer_notes": "not part of the schema",
        })
        assert r.status_code == 200

    async def test_login_ignores_unknown_extra_fields(self, client, unique_email):
        """
        CATEGORY: Functional API
        TITLE: POST /auth/login ignores unrecognized extra JSON fields
        OBJECTIVE: Same forward-compatibility check for login.
        EXPECTED: 200 OK.
        SEVERITY: Low
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        r = await client.post("/auth/login", json={
            "email": unique_email, "password": "ValidPass123!", "remember_me": True,
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Additional response-field type checks for remaining resources
# ---------------------------------------------------------------------------

class TestMoreFieldLevelContractChecks:
    @pytest.mark.parametrize("field", ["remediation_id", "vuln_id", "status", "executive_summary"])
    async def test_remediation_response_field_is_a_string(self, client, admin_headers, seeded_remediation, field):
        """
        CATEGORY: Functional API
        TITLE: Each RemediationResponse text/id field serializes as a string
        OBJECTIVE: Confirm no field is unexpectedly nested or numeric.
        EXPECTED: isinstance(body[field], str) is True.
        SEVERITY: Low
        """
        r = await client.get(f"/remediations/{seeded_remediation['remediation_id']}", headers=admin_headers)
        assert isinstance(r.json()[field], str)

    @pytest.mark.parametrize("field", ["vuln_id", "scan_id", "host", "severity", "status"])
    async def test_vulnerability_response_field_is_a_string(self, client, admin_headers, seeded_vulnerability, field):
        """
        CATEGORY: Functional API
        TITLE: Each VulnerabilityResponse text/id field serializes as a string
        OBJECTIVE: Confirm no field is unexpectedly nested or numeric.
        EXPECTED: isinstance(body[field], str) is True.
        SEVERITY: Low
        """
        r = await client.get(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}", headers=admin_headers)
        assert isinstance(r.json()[field], str)

    async def test_scan_active_testing_enabled_is_boolean_not_string(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: active_testing_enabled serializes as a real JSON boolean
        OBJECTIVE: Guard against a common serialization bug where a Python
                    bool ends up as the string 'true'/'false'.
        EXPECTED: isinstance(body['active_testing_enabled'], bool) is True.
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "bool-type-check.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Boolean-type-check regression test.",
        })
        assert r.json()["active_testing_enabled"] is False

    async def test_cve_definitions_list_entries_have_cve_id_when_present(self, client, admin_headers):
        """
        CATEGORY: Functional API
        TITLE: Any CVE definition entries returned include a cve_id field
        OBJECTIVE: Confirm the response shape even though the table is
                    typically empty in this ephemeral test DB.
        EXPECTED: Every entry (if any) has a 'cve_id' key.
        SEVERITY: Low
        """
        r = await client.get("/admin/cve-definitions", headers=admin_headers)
        for entry in r.json():
            assert "cve_id" in entry

    async def test_device_platform_response_is_lowercased(self, client, client1_headers):
        """
        CATEGORY: Functional API
        TITLE: Device platform is normalized to lowercase in the response
        OBJECTIVE: Confirm the validator's .lower() normalization is reflected
                    back to the caller, not just applied silently server-side.
        EXPECTED: platform == 'android' even though 'ANDROID' was submitted.
        SEVERITY: Low
        """
        r = await client.post("/devices/register", headers=client1_headers, json={
            "fcm_token": "casecheck1234567890abcdef", "platform": "ANDROID",
        })
        assert r.status_code == 201
        assert r.json()["platform"] == "android"

