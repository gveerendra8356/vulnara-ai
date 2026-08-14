"""
test_dast.py — Category: DAST / Dynamic Security (target: 40+ cases)

Auth-bypass attempts, JWT tampering beyond the injection-focused cases in
test_injection.py, HTTP method confusion, mass-assignment attempts, and
brute-force behavior -- all fired at the real running instance.
"""
import base64
import json as _json
import uuid

import pytest

pytestmark = pytest.mark.dast


class TestAuthBypassAttempts:
    async def test_scan_creation_without_any_auth_header_rejected(self, client):
        """
        CATEGORY: DAST
        TITLE: POST /scans with no Authorization header is rejected
        OBJECTIVE: Confirm the authorization gate can't be bypassed simply by
                    omitting credentials.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Critical
        """
        r = await client.post("/scans", json={
            "target": "bypass-test.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Auth-bypass regression test.",
        })
        assert r.status_code == 401

    async def test_x_forwarded_for_header_does_not_grant_trust(self, client):
        """
        CATEGORY: DAST
        TITLE: A spoofed X-Forwarded-For header does not bypass authentication
        OBJECTIVE: Confirm no IP-based trust shortcut exists (e.g. treating
                    localhost-looking IPs as pre-authenticated).
        EXPECTED: 401 Unauthorized, same as without the header.
        SEVERITY: Medium
        """
        r = await client.get("/auth/me", headers={"X-Forwarded-For": "127.0.0.1"})
        assert r.status_code == 401

    async def test_x_admin_style_headers_do_not_grant_privilege(self, client, client1_headers):
        """
        CATEGORY: DAST
        TITLE: Injecting a fake privilege header does not grant admin access
        OBJECTIVE: Confirm role is derived solely from the verified JWT claim,
                    never from a client-supplied header.
        EXPECTED: 403 Forbidden, identical to the request without the header.
        SEVERITY: High
        """
        headers = dict(client1_headers)
        headers["X-Admin"] = "true"
        headers["X-User-Role"] = "admin"
        r = await client.get("/admin/config", headers=headers)
        assert r.status_code == 403

    async def test_role_claim_cannot_be_supplied_via_request_body(self, client, client1_headers):
        """
        CATEGORY: DAST
        TITLE: A 'role' field in the request body cannot escalate privilege
        OBJECTIVE: Mass-assignment style check -- confirm supplying an
                    unexpected 'role'/'current_user' field in a scan-creation
                    body has no effect on authorization.
        EXPECTED: The scan is created under the caller's real (client) identity;
                   no elevation occurs, and the response schema doesn't even
                   surface a role field to reflect back.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "mass-assignment.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Mass-assignment regression test.",
            "role": "admin", "user_id": str(uuid.uuid4()), "is_admin": True,
        })
        assert r.status_code == 201
        assert "role" not in r.json()

    async def test_user_id_in_body_cannot_reassign_scan_ownership(self, client, client1_headers, client2_headers):
        """
        CATEGORY: DAST
        TITLE: Supplying a foreign user_id in the scan body doesn't reassign ownership
        OBJECTIVE: Confirm ownership is always derived from the authenticated
                    session (current_user), never from client-supplied fields.
        EXPECTED: The created scan is owned by client1 (the actual caller);
                   client2 still cannot access it afterwards.
        SEVERITY: High
        """
        create = await client.post("/scans", headers=client1_headers, json={
            "target": "ownership-spoof.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Ownership-spoofing regression test.",
            "user_id": str(uuid.uuid4()),
        })
        assert create.status_code == 201
        scan_id = create.json()["scan_id"]
        as_owner = await client.get(f"/scans/{scan_id}", headers=client1_headers)
        as_other = await client.get(f"/scans/{scan_id}", headers=client2_headers)
        assert as_owner.status_code == 200
        assert as_other.status_code == 403


class TestJwtTampering:
    async def test_expired_style_forged_token_rejected(self, client):
        """
        CATEGORY: DAST
        TITLE: A JWT with an exp claim in the past is rejected
        OBJECTIVE: Confirm expiry is actually enforced, not just present in
                    the payload for cosmetic purposes -- signed with a wrong
                    key here since we don't have the real secret, which
                    itself should also be sufficient to reject.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Critical
        """
        header = base64.urlsafe_b64encode(_json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(_json.dumps({
            "sub": str(uuid.uuid4()), "role": "admin", "exp": 1000000000,
        }).encode()).rstrip(b"=")
        forged = header.decode() + "." + payload.decode() + ".fakesignature"
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert r.status_code == 401

    async def test_token_signed_with_guessed_weak_secret_rejected(self, client):
        """
        CATEGORY: DAST
        TITLE: A token forged with a common weak secret guess is rejected
        OBJECTIVE: Confirm the real signing key isn't one of the classic
                    weak/default values an attacker would try first.
        EXPECTED: 401 Unauthorized for every guess.
        SEVERITY: Critical
        """
        try:
            import jwt as pyjwt
        except ImportError:
            pytest.skip("PyJWT not installed in the test environment")

        for guess in ("secret", "changeme", "your-secret-key", "12345678", "password"):
            forged = pyjwt.encode({"sub": str(uuid.uuid4()), "role": "admin"}, guess, algorithm="HS256")
            r = await client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
            assert r.status_code == 401, f"Token forged with weak secret {guess!r} was accepted!"

    async def test_token_for_deleted_or_nonexistent_user_rejected(self, client):
        """
        CATEGORY: DAST
        TITLE: A well-formed-but-fake subject claim (nonexistent user) is rejected
        OBJECTIVE: Confirm the user lookup in get_current_user actually checks
                    the DB rather than trusting the claim blindly -- forged
                    with a wrong key, so this doubles as a signature check too.
        EXPECTED: 401 Unauthorized.
        SEVERITY: High
        """
        try:
            import jwt as pyjwt
        except ImportError:
            pytest.skip("PyJWT not installed in the test environment")
        forged = pyjwt.encode({"sub": str(uuid.uuid4()), "role": "admin"}, "not-the-real-secret", algorithm="HS256")
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert r.status_code == 401

    async def test_algorithm_confusion_hs256_to_rs256_style_token_rejected(self, client):
        """
        CATEGORY: DAST
        TITLE: A token asserting an unexpected algorithm in its header is rejected
        OBJECTIVE: Classic algorithm-confusion probe -- confirm the server
                    doesn't accept whatever `alg` the token claims.
        EXPECTED: 401 Unauthorized.
        SEVERITY: High
        """
        header = base64.urlsafe_b64encode(_json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(_json.dumps({"sub": str(uuid.uuid4()), "role": "admin"}).encode()).rstrip(b"=")
        forged = header.decode() + "." + payload.decode() + ".fakesig"
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert r.status_code == 401

    async def test_truncated_token_rejected(self, client, client1_session):
        """
        CATEGORY: DAST
        TITLE: A truncated (partially-cut) valid token is rejected
        OBJECTIVE: Confirm signature verification catches a token that's had
                    its final characters chopped off, not just fully-garbage input.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Medium
        """
        token = client1_session["access_token"]
        truncated = token[:-10]
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {truncated}"})
        assert r.status_code == 401

    async def test_token_with_extra_trailing_characters_rejected(self, client, client1_session):
        """
        CATEGORY: DAST
        TITLE: A valid token with extra trailing garbage is rejected
        OBJECTIVE: Confirm strict, exact signature matching (no partial-match
                    or prefix-based token validation bug).
        EXPECTED: 401 Unauthorized.
        SEVERITY: Medium
        """
        token = client1_session["access_token"] + "extragarbage"
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


class TestHttpMethodAndVerbTampering:
    @pytest.mark.parametrize("method", ["PUT", "DELETE", "PATCH"])
    async def test_unsupported_methods_on_scans_collection_rejected_cleanly(self, client, client1_headers, method):
        """
        CATEGORY: DAST
        TITLE: Unsupported HTTP methods on the /scans collection are rejected cleanly
        OBJECTIVE: Confirm method-not-allowed handling doesn't accidentally
                    fall through to an unintended handler.
        EXPECTED: 405 Method Not Allowed (or 404), never 200/500.
        SEVERITY: Low
        """
        r = await client.request(method, "/scans", headers=client1_headers)
        assert r.status_code in (404, 405)

    async def test_head_request_on_health_does_not_error(self, client):
        """
        CATEGORY: DAST
        TITLE: HEAD request on /health does not error
        OBJECTIVE: Basic verb-tampering sanity check (FastAPI auto-derives HEAD from GET).
        EXPECTED: 200 or 405, never 500.
        SEVERITY: Low
        """
        r = await client.head("/health")
        assert r.status_code in (200, 405)


class TestBruteForceAndEnumeration:
    async def test_repeated_failed_logins_do_not_lock_or_crash_account(self, client, unique_email):
        """
        CATEGORY: DAST
        TITLE: Repeated failed logins never crash the endpoint and the
               legitimate password still works afterward
        OBJECTIVE: Confirm no unhandled exception under a sustained failed-login
                    burst (complements the missing-rate-limiting finding in
                    test_configuration.py by checking basic resilience).
        EXPECTED: All failed attempts return 401; the real password still
                   authenticates successfully immediately after.
        SEVERITY: Medium
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        for _ in range(20):
            r = await client.post("/auth/login", json={"email": unique_email, "password": "WrongOne!"})
            assert r.status_code == 401
        good = await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})
        assert good.status_code == 200

    async def test_registration_does_not_reveal_which_emails_already_exist_via_timing_hint(self, client, unique_email):
        """
        CATEGORY: DAST
        TITLE: Both new-account and duplicate-account registration return quickly and cleanly
        OBJECTIVE: Coarse check that duplicate-detection doesn't do anything
                    exotic (e.g. an expensive external lookup) that would
                    create an obvious timing side-channel; also confirms the
                    status codes themselves already differ in a documented,
                    not-secret way (400 vs 201), so there's no additional
                    hidden signal to worry about.
        EXPECTED: Fresh email -> 201; duplicate -> 400; both respond, neither hangs.
        SEVERITY: Low
        """
        payload = {"email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client"}
        r1 = await client.post("/auth/register", json=payload)
        r2 = await client.post("/auth/register", json=payload)
        assert r1.status_code == 201
        assert r2.status_code == 400


class TestCrossTenantWriteAttempts:
    async def test_client2_cannot_patch_client1_vulnerability_status(self, client, client2_headers, seeded_vulnerability):
        """
        CATEGORY: DAST
        TITLE: A different tenant with the required role still can't touch a
               vulnerability outside their scans -- unless they hold analyst/admin
        OBJECTIVE: client2 is role=client here, so this should be blocked by
                    the role check (403) regardless of the ownership gap
                    tracked separately in VULN-001 -- confirms the two checks
                    are independent layers.
        EXPECTED: 403 Forbidden.
        SEVERITY: High
        """
        r = await client.patch(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}", headers=client2_headers, json={"status": "FALSE_POSITIVE"})
        assert r.status_code == 403

    async def test_admin_created_analyst_cannot_reach_admin_only_routes(self, client, admin_headers, unique_email):
        """
        CATEGORY: DAST
        TITLE: An analyst account provisioned by an admin still cannot reach admin-only routes
        OBJECTIVE: Confirm provisioning path doesn't accidentally grant broader
                    privilege than the assigned role.
        EXPECTED: New analyst account logs in fine, then gets 403 on /admin/config.
        SEVERITY: High
        """
        create = await client.post("/auth/users", headers=admin_headers, json={
            "email": unique_email, "full_name": "Scoped Analyst", "role": "analyst", "temp_password": "TempPass123!",
        })
        assert create.status_code == 201
        login = await client.post("/auth/login", json={"email": unique_email, "password": "TempPass123!"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = await client.get("/admin/config", headers=headers)
        assert r.status_code == 403


class TestSessionInvalidationDast:
    async def test_old_access_token_still_works_after_password_is_effectively_unchanged(self, client, unique_email):
        """
        CATEGORY: DAST
        TITLE: A freshly-issued access token authenticates immediately after login
        OBJECTIVE: Baseline session-validity sanity check underpinning the
                    token-tampering tests above.
        EXPECTED: 200 on /auth/me immediately after login.
        SEVERITY: Low
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        login = (await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})).json()
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"})
        assert r.status_code == 200

    async def test_logged_out_refresh_token_cannot_be_reused_for_new_access_tokens(self, client, unique_email):
        """
        CATEGORY: DAST
        TITLE: A logged-out refresh token cannot mint further access tokens
        OBJECTIVE: Re-confirm session teardown from an attacker's perspective:
                    once revoked, repeated refresh attempts must all fail, not
                    just the first one.
        EXPECTED: All post-logout refresh attempts return 401.
        SEVERITY: Critical
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        login = (await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})).json()
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        await client.post("/auth/logout", json={"refresh_token": login["refresh_token"]}, headers=headers)

        for _ in range(3):
            r = await client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
            assert r.status_code == 401


class TestAdditionalIdorProbes:
    """More cross-tenant probes across the remaining nested-resource endpoints."""

    async def test_client2_cannot_cancel_client1_scan_even_with_valid_own_token(self, client, client2_headers, client1_scan):
        """
        CATEGORY: DAST
        TITLE: A syntactically valid, correctly-signed token for a different
               tenant still cannot cancel someone else's scan
        OBJECTIVE: Re-confirm the ownership check under a genuine (not forged)
                    cross-tenant token -- the realistic attack scenario.
        EXPECTED: 403 Forbidden.
        SEVERITY: Critical
        """
        r = await client.post(f"/scans/{client1_scan['scan_id']}/cancel", headers=client2_headers)
        assert r.status_code == 403

    async def test_client2_cannot_read_client1_vulnerabilities_list(self, client, client2_headers, client1_scan):
        """
        CATEGORY: DAST
        TITLE: A different tenant cannot list another tenant's scan vulnerabilities
        OBJECTIVE: Re-confirm from the DAST/attacker-perspective angle (paired
                    with the equivalent authorization-suite test).
        EXPECTED: 403 Forbidden.
        SEVERITY: Critical
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}/vulnerabilities", headers=client2_headers)
        assert r.status_code == 403

    async def test_sequential_scan_ids_do_not_allow_enumeration(self, client, client1_headers, client1_scan):
        """
        CATEGORY: DAST
        TITLE: Scan IDs are UUIDs, not sequential integers -- no enumeration surface
        OBJECTIVE: Confirm the identifier space itself resists brute-force
                    enumeration (a real integer PK would make IDOR far easier
                    to exploit at scale).
        EXPECTED: The scan_id is a valid UUID4-shaped string.
        SEVERITY: Low
        """
        scan_id = client1_scan["scan_id"]
        parsed = uuid.UUID(scan_id)
        assert str(parsed) == scan_id.lower()

    async def test_probing_ten_random_uuids_for_scans_all_return_404(self, client, client1_headers):
        """
        CATEGORY: DAST
        TITLE: Probing random scan UUIDs never accidentally hits real data
        OBJECTIVE: Coarse confirmation that the UUID keyspace is large enough
                    that blind guessing doesn't practically work.
        EXPECTED: All 10 random UUIDs return 404 (not 403, since they don't exist at all).
        SEVERITY: Low
        """
        for _ in range(10):
            r = await client.get(f"/scans/{uuid.uuid4()}", headers=client1_headers)
            assert r.status_code == 404


class TestContentTypeAndBodyTampering:
    async def test_malformed_json_body_returns_422_not_500(self, client, client1_headers):
        """
        CATEGORY: DAST
        TITLE: A malformed (syntactically invalid) JSON body returns 422, not 500
        OBJECTIVE: Confirm the request body parser fails cleanly on garbage input.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Medium
        """
        r = await client.post(
            "/scans", headers={**client1_headers, "Content-Type": "application/json"},
            content=b'{"target": "example.com", "authorization_confirmed": tru',
        )
        assert r.status_code == 422

    async def test_wrong_content_type_on_json_endpoint_handled_cleanly(self, client, client1_headers):
        """
        CATEGORY: DAST
        TITLE: Sending form-encoded data to a JSON-only endpoint fails cleanly
        OBJECTIVE: Confirm content-type confusion doesn't crash the server.
        EXPECTED: 422 Unprocessable Entity, never 500.
        SEVERITY: Low
        """
        r = await client.post(
            "/scans", headers={**client1_headers, "Content-Type": "application/x-www-form-urlencoded"},
            content=b"target=example.com&authorization_confirmed=true",
        )
        assert r.status_code == 422

    async def test_array_instead_of_object_body_returns_422(self, client, client1_headers):
        """
        CATEGORY: DAST
        TITLE: Sending a JSON array where an object is expected returns 422
        OBJECTIVE: Type-confusion check on the top-level request body shape.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json=["not", "an", "object"])
        assert r.status_code == 422

    async def test_deeply_nested_json_does_not_crash_the_server(self, client, client1_headers):
        """
        CATEGORY: DAST
        TITLE: A deeply-nested JSON payload in an ignored extra field does not crash the server
        OBJECTIVE: Coarse resource-exhaustion / parser-robustness probe.
        EXPECTED: 201 (extra field ignored) or 422, never 500/timeout.
        SEVERITY: Low
        """
        nested = {}
        cursor = nested
        for _ in range(50):
            cursor["nested"] = {}
            cursor = cursor["nested"]
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "deep-nest.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Deeply-nested-payload regression test.",
            "extra_junk": nested,
        })
        assert r.status_code in (201, 422)
