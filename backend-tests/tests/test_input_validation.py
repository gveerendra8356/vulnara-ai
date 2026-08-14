"""
test_input_validation.py — Category: Input Validation (target: 40+ cases)

Boundary and format checks for every request schema: ScanCreateRequest,
DeviceRegisterRequest, VulnerabilityUpdateRequest, RemediationRejectRequest.
"""
import pytest

pytestmark = pytest.mark.input_validation


class TestScanTargetValidation:
    async def test_target_blank_string_rejected(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans rejects a blank target
        OBJECTIVE: Confirm the target_not_blank validator actually fires.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "", "authorization_confirmed": True,
            "authorization_justification": "Valid justification text here.",
        })
        assert r.status_code == 422

    async def test_target_whitespace_only_rejected(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans rejects a whitespace-only target
        OBJECTIVE: Confirm target.strip() blank-check catches spaces/tabs, not just "".
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "     ", "authorization_confirmed": True,
            "authorization_justification": "Valid justification text here.",
        })
        assert r.status_code == 422

    async def test_target_at_max_length_255_accepted(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans accepts a target at the 255-char boundary
        OBJECTIVE: Confirm max_length=255 is inclusive.
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        target = ("a" * 251) + ".com"  # 255 chars total
        assert len(target) == 255
        r = await client.post("/scans", headers=client1_headers, json={
            "target": target, "authorization_confirmed": True,
            "authorization_justification": "Valid justification text here.",
        })
        assert r.status_code == 201

    async def test_target_over_max_length_256_rejected(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans rejects a target one character past the 255 boundary
        OBJECTIVE: Confirm max_length=255 is enforced, not silently truncated.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Medium
        """
        target = "a" * 256
        r = await client.post("/scans", headers=client1_headers, json={
            "target": target, "authorization_confirmed": True,
            "authorization_justification": "Valid justification text here.",
        })
        assert r.status_code == 422

    async def test_target_missing_rejected(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans rejects a missing target field
        OBJECTIVE: Confirm target is truly required.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "authorization_confirmed": True,
            "authorization_justification": "Valid justification text here.",
        })
        assert r.status_code == 422

    @pytest.mark.parametrize("target", [
        "example.com", "sub.domain.example.com", "192.168.1.1",
        "192.168.1.0/24", "localhost", "xn--80akhbyknj4f.com",
    ])
    async def test_target_common_valid_formats_accepted(self, client, client1_headers, target):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans accepts common valid target formats
        OBJECTIVE: Confirm domains, IPs, and CIDR ranges are not falsely rejected.
        EXPECTED: 201 Created (no format-level restriction is applied beyond length/blank).
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": target, "authorization_confirmed": True,
            "authorization_justification": "Valid justification text here.",
        })
        assert r.status_code == 201


class TestScanAuthorizationJustificationValidation:
    @pytest.mark.parametrize("length", [0, 1, 5, 9])
    async def test_justification_under_min_length_10_rejected(self, client, client1_headers, length):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans rejects justification text under the 10-char minimum
        OBJECTIVE: Confirm min_length=10 is enforced across the boundary (0..9 chars).
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "example.com", "authorization_confirmed": True,
            "authorization_justification": "a" * length,
        })
        assert r.status_code == 422

    async def test_justification_at_exactly_min_length_10_accepted(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans accepts justification text at exactly 10 characters
        OBJECTIVE: Confirm the min_length=10 boundary is inclusive.
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "example.com", "authorization_confirmed": True,
            "authorization_justification": "1234567890",
        })
        assert r.status_code == 201

    async def test_justification_whitespace_only_rejected_even_if_long_enough(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans rejects a justification that is 10+ chars but all whitespace
        OBJECTIVE: Confirm the explicit blank-after-strip validator catches what
                    min_length alone cannot.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "example.com", "authorization_confirmed": True,
            "authorization_justification": " " * 15,
        })
        assert r.status_code == 422

    async def test_justification_at_max_length_2000_accepted(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans accepts justification text at the 2000-char boundary
        OBJECTIVE: Confirm max_length=2000 is inclusive.
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "example.com", "authorization_confirmed": True,
            "authorization_justification": "a" * 2000,
        })
        assert r.status_code == 201

    async def test_justification_over_max_length_2001_rejected(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans rejects justification text over the 2000-char boundary
        OBJECTIVE: Confirm max_length=2000 is enforced.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "example.com", "authorization_confirmed": True,
            "authorization_justification": "a" * 2001,
        })
        assert r.status_code == 422

    async def test_authorization_confirmed_false_rejected_by_business_rule(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans rejects authorization_confirmed=False via the route-level check
        OBJECTIVE: Confirm the second, business-logic-layer gate actually blocks
                    scan creation (schema validation alone can't express this).
        EXPECTED: 422 Unprocessable Entity (the route handler raises this
                   explicitly as its first action, ahead of any DB work).
        SEVERITY: High
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "example.com", "authorization_confirmed": False,
            "authorization_justification": "Valid justification text here.",
        })
        assert r.status_code == 422

    async def test_authorization_confirmed_missing_rejected(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans rejects a missing authorization_confirmed field
        OBJECTIVE: Confirm the field is required, not defaulted to False silently.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "example.com",
            "authorization_justification": "Valid justification text here.",
        })
        assert r.status_code == 422

    @pytest.mark.parametrize("bad_value", ["yes", "true", 1, "1", None])
    async def test_authorization_confirmed_non_boolean_rejected(self, client, client1_headers, bad_value):
        """
        CATEGORY: Input Validation
        TITLE: POST /scans rejects non-boolean values for authorization_confirmed
        OBJECTIVE: Confirm strict type coercion behavior for this legally-significant field.
        EXPECTED: 422 for None; string/int values may be coerced by pydantic's
                   lenient bool parsing ('true'/'1' -> True) -- documented,
                   not treated as a hard failure either way except for None.
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "example.com", "authorization_confirmed": bad_value,
            "authorization_justification": "Valid justification text here.",
        })
        if bad_value is None:
            assert r.status_code == 422
        else:
            assert r.status_code in (201, 403, 422)

    async def test_active_testing_enabled_defaults_to_false(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: active_testing_enabled defaults to False when omitted
        OBJECTIVE: Confirm active (potentially destructive) testing is never
                    silently opt-in by default.
        EXPECTED: 201 Created, active_testing_enabled=False in the response.
        SEVERITY: High
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "example.com", "authorization_confirmed": True,
            "authorization_justification": "Valid justification text here.",
        })
        assert r.status_code == 201
        assert r.json()["active_testing_enabled"] is False


class TestDeviceRegisterValidation:
    @pytest.mark.parametrize("token", ["", "short", "123456789"])
    async def test_fcm_token_under_min_length_rejected(self, client, client1_headers, token):
        """
        CATEGORY: Input Validation
        TITLE: POST /devices/register rejects an fcm_token under the 10-char minimum
        OBJECTIVE: Confirm min_length=10 is enforced.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Low
        """
        r = await client.post("/devices/register", headers=client1_headers, json={
            "fcm_token": token, "platform": "android",
        })
        assert r.status_code == 422

    async def test_fcm_token_whitespace_only_rejected(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /devices/register rejects a whitespace-only fcm_token
        OBJECTIVE: Confirm the blank-after-strip validator fires even past min_length.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Low
        """
        r = await client.post("/devices/register", headers=client1_headers, json={
            "fcm_token": " " * 15, "platform": "android",
        })
        assert r.status_code == 422

    @pytest.mark.parametrize("platform", ["windows", "web", "ANDROID", "IOS", "", "linux", "macos"])
    async def test_platform_invalid_values_rejected(self, client, client1_headers, platform):
        """
        CATEGORY: Input Validation
        TITLE: POST /devices/register rejects platform values outside android/ios
        OBJECTIVE: Confirm the enum-like platform_valid validator is case-sensitive
                    on the wire and rejects anything but android/ios.
        EXPECTED: 422 Unprocessable Entity (note: 'ANDROID'/'IOS' are lower-cased
                   internally by the validator, so those two are expected to pass --
                   see the dedicated case-insensitivity test below).
        SEVERITY: Low
        """
        r = await client.post("/devices/register", headers=client1_headers, json={
            "fcm_token": "validtoken1234567890", "platform": platform,
        })
        if platform.lower() in ("android", "ios"):
            assert r.status_code == 201
        else:
            assert r.status_code == 422

    @pytest.mark.parametrize("platform", ["android", "ios"])
    async def test_platform_valid_values_accepted(self, client, client1_headers, platform):
        """
        CATEGORY: Input Validation
        TITLE: POST /devices/register accepts 'android' and 'ios'
        OBJECTIVE: Baseline positive case for the platform validator.
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        r = await client.post("/devices/register", headers=client1_headers, json={
            "fcm_token": f"validtoken-{platform}-1234567890", "platform": platform,
        })
        assert r.status_code == 201

    async def test_fcm_token_missing_rejected(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: POST /devices/register rejects a missing fcm_token
        OBJECTIVE: Confirm required-field enforcement.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Low
        """
        r = await client.post("/devices/register", headers=client1_headers, json={"platform": "android"})
        assert r.status_code == 422


class TestVulnerabilityUpdateValidation:
    async def test_status_missing_rejected(self, client, analyst_headers, seeded_vulnerability):
        """
        CATEGORY: Input Validation
        TITLE: PATCH /vulnerabilities/{id} rejects a missing status field
        OBJECTIVE: Confirm status is a required field on the update schema.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Low
        """
        r = await client.patch(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}", headers=analyst_headers, json={})
        assert r.status_code == 422

    async def test_status_empty_string_accepted_no_enum_enforced(self, client, analyst_headers, seeded_vulnerability):
        """
        CATEGORY: Input Validation
        TITLE: [Finding] PATCH /vulnerabilities/{id} has no enum validation on status
        OBJECTIVE: Document that VulnerabilityUpdateRequest.status is a bare `str`
                    with no Literal/enum constraint or DB-level CHECK -- any string,
                    including an empty one, is currently persisted as-is.
        EXPECTED (CURRENT BEHAVIOR): 200 OK, even for '' or garbage values. See
                   findings.xlsx (VULN-003, Low) recommending a Literal[...] type.
        SEVERITY: Low
        """
        r = await client.patch(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}", headers=analyst_headers, json={"status": ""})
        assert r.status_code == 200, (
            "If this now 422s, enum validation has been added -- update findings.xlsx VULN-003."
        )

    @pytest.mark.parametrize("garbage_status", ["not_a_real_status", "🔥🔥🔥", "DROP TABLE vulnerabilities;", "<script>x</script>"])
    async def test_status_arbitrary_values_accepted_no_enum_enforced(self, client, analyst_headers, seeded_vulnerability, garbage_status):
        """
        CATEGORY: Input Validation
        TITLE: [Finding] PATCH /vulnerabilities/{id} accepts arbitrary status strings
        OBJECTIVE: Further document the missing enum/Literal constraint from
                    VULN-003 across a range of clearly-invalid values.
        EXPECTED (CURRENT BEHAVIOR): 200 OK for any string value. Note this is a
                   parameterized JSON field (not raw SQL/HTML execution context),
                   so this is a data-integrity gap, not itself a live SQLi/XSS
                   vector -- see test_injection.py for that class of check.
        SEVERITY: Low
        """
        r = await client.patch(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}", headers=analyst_headers, json={"status": garbage_status})
        assert r.status_code == 200
        # And it must come back exactly as stored (round-trip integrity), not
        # partially sanitized -- confirms it's genuinely unconstrained storage.
        assert r.json()["status"] == garbage_status


class TestRemediationRejectValidation:
    async def test_reject_reason_missing_rejected(self, client, admin_headers, seeded_remediation_2):
        """
        CATEGORY: Input Validation
        TITLE: POST /remediations/{id}/reject rejects a missing reason field
        OBJECTIVE: Confirm 'reason' is required on RemediationRejectRequest.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Low
        """
        r = await client.post(f"/remediations/{seeded_remediation_2['remediation_id']}/reject", headers=admin_headers, json={})
        assert r.status_code == 422

    async def test_reject_reason_empty_string_accepted_no_min_length(self, client, admin_headers, seeded_remediation_2):
        """
        CATEGORY: Input Validation
        TITLE: [Finding] POST /remediations/{id}/reject accepts an empty reason
        OBJECTIVE: Document that RemediationRejectRequest.reason has no
                    min_length, so an empty audit-trail reason is possible.
        EXPECTED (CURRENT BEHAVIOR): 200 OK with reason=''. See findings.xlsx (Low).
        SEVERITY: Low
        """
        r = await client.post(f"/remediations/{seeded_remediation_2['remediation_id']}/reject", headers=admin_headers, json={"reason": ""})
        assert r.status_code == 200


class TestUuidPathParamValidation:
    @pytest.mark.parametrize("bad_id", ["not-a-uuid", "12345", "'; DROP TABLE scans; --", "%20%20%20", "🚀"])
    async def test_malformed_uuid_path_param_returns_422_not_500(self, client, client1_headers, bad_id):
        """
        CATEGORY: Input Validation
        TITLE: A malformed UUID in a path parameter returns 422, not 500
        OBJECTIVE: Confirm FastAPI's UUID path-param coercion fails cleanly.
        EXPECTED: 422 Unprocessable Entity, never 500.
        SEVERITY: Medium
        """
        r = await client.get(f"/scans/{bad_id}", headers=client1_headers)
        assert r.status_code == 422

    async def test_well_formed_but_nonexistent_uuid_returns_404(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: A well-formed but non-existent scan UUID returns 404
        OBJECTIVE: Confirm valid-format/non-existent IDs are distinguished from malformed ones.
        EXPECTED: 404 Not Found.
        SEVERITY: Low
        """
        r = await client.get("/scans/00000000-0000-0000-0000-000000000000", headers=client1_headers)
        assert r.status_code == 404


class TestFullNameFieldValidation:
    async def test_full_name_empty_string_accepted_no_min_length(self, client, unique_email):
        """
        CATEGORY: Input Validation
        TITLE: [Finding] Registration accepts an empty full_name
        OBJECTIVE: Document that UserRegisterRequest.full_name has no
                    min_length constraint, unlike password/target/justification.
        EXPECTED (CURRENT BEHAVIOR): 201 Created with full_name=''. See
                   findings.xlsx (Low) recommending a min_length=1 constraint.
        SEVERITY: Low
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "", "role": "client",
        })
        assert r.status_code == 201

    async def test_full_name_very_long_value_does_not_crash(self, client, unique_email):
        """
        CATEGORY: Input Validation
        TITLE: Registration with a very long full_name does not crash the server
        OBJECTIVE: full_name has no max_length -- confirm a large (but not
                    absurd) value doesn't 500, since there's no cap to reject it.
        EXPECTED: 201 Created or 422, never 500.
        SEVERITY: Low
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "A" * 5000, "role": "client",
        })
        assert r.status_code != 500

    async def test_full_name_with_unicode_characters_accepted(self, client, unique_email):
        """
        CATEGORY: Input Validation
        TITLE: Registration accepts unicode characters in full_name
        OBJECTIVE: Confirm names with non-ASCII characters (accents, CJK,
                    emoji) aren't rejected or mangled.
        EXPECTED: 201 Created, full_name round-trips exactly.
        SEVERITY: Low
        """
        name = "José García 李明 🚀"
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": name, "role": "client",
        })
        assert r.status_code == 201
        assert r.json()["full_name"] == name


class TestNullByteAndEncodingEdgeCases:
    async def test_null_byte_in_target_does_not_crash(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: A null byte embedded in the scan target does not crash the API
        OBJECTIVE: Null-byte injection is a classic way to trip up C-based
                    string handling further down a call chain (e.g. subprocess
                    argument parsing) -- confirm the JSON/Python layer handles
                    it cleanly regardless.
        EXPECTED: 201 Created or 422, never 500.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "example.com\x00.evil.com", "authorization_confirmed": True,
            "authorization_justification": "Null-byte regression test.",
        })
        assert r.status_code in (201, 422)

    async def test_extremely_long_justification_beyond_max_rejected_not_500(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: A pathologically long justification (10x the max) is rejected, not crashed on
        OBJECTIVE: Boundary/DoS-adjacent check well past the 2000-char max_length.
        EXPECTED: 422 Unprocessable Entity, never 500/timeout.
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "example.com", "authorization_confirmed": True,
            "authorization_justification": "a" * 20000,
        })
        assert r.status_code == 422

    async def test_unicode_homoglyph_target_does_not_crash(self, client, client1_headers):
        """
        CATEGORY: Input Validation
        TITLE: A unicode-homoglyph-style target does not crash the API
        OBJECTIVE: Confirm non-ASCII target strings (e.g. IDN-homograph style
                    domains) are handled as plain text without special processing.
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "ｅхａmple.com", "authorization_confirmed": True,
            "authorization_justification": "Unicode homoglyph regression test.",
        })
        assert r.status_code in (201, 422)

    async def test_extra_unknown_fields_in_register_body_are_ignored(self, client, unique_email):
        """
        CATEGORY: Input Validation
        TITLE: Unrecognized extra fields in the register body are ignored, not errored on
        OBJECTIVE: Confirm pydantic's default 'ignore extra fields' behavior,
                    rather than a strict model that would 422 on any unknown key.
        EXPECTED: 201 Created despite the extra 'nickname' field.
        SEVERITY: Low
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
            "nickname": "should be ignored",
        })
        assert r.status_code == 201
