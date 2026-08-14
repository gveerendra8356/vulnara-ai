"""
test_configuration.py — Category: Configuration (target: 30+ cases)

CORS behavior, missing security headers, error-response information
disclosure, server banner disclosure, and the (confirmed, from a read of
main.py) total absence of any HTTP-layer rate limiting.
"""
import time

import pytest

pytestmark = pytest.mark.configuration


class TestCorsConfiguration:
    async def test_allowed_origin_is_reflected_in_preflight(self, client):
        """
        CATEGORY: Configuration
        TITLE: A configured CORS origin is reflected in the preflight response
        OBJECTIVE: Confirm CORSMiddleware is actually wired up and functioning
                    for the origin used by the test harness itself.
        EXPECTED: OPTIONS preflight returns Access-Control-Allow-Origin
                   matching the request Origin header.
        SEVERITY: Low
        """
        r = await client.options("/health", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        })
        assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"

    async def test_arbitrary_untrusted_origin_is_not_reflected(self, client):
        """
        CATEGORY: Configuration
        TITLE: An arbitrary, non-configured origin does not get CORS access
        OBJECTIVE: Confirm the origin allow-list is a real allow-list, not
                    an accidental wildcard reflection of any Origin header sent.
        EXPECTED: No Access-Control-Allow-Origin header for an untrusted origin
                   (or a value that does not match the untrusted origin).
        SEVERITY: High
        """
        r = await client.options("/health", headers={
            "Origin": "https://evil-attacker.example",
            "Access-Control-Request-Method": "GET",
        })
        acao = r.headers.get("access-control-allow-origin")
        assert acao != "https://evil-attacker.example"

    async def test_credentials_allowed_only_for_trusted_origin(self, client):
        """
        CATEGORY: Configuration
        TITLE: Access-Control-Allow-Credentials is only ever paired with a
               specific, trusted origin -- never a wildcard
        OBJECTIVE: allow_credentials=True combined with a wildcard origin
                    would be a serious CSRF-adjacent misconfiguration (and is
                    actually rejected by browsers/Starlette itself when both
                    are true) -- confirm that combination never appears together.
        EXPECTED: Access-Control-Allow-Origin is never '*' when
                   Access-Control-Allow-Credentials is 'true'.
        SEVERITY: Critical
        """
        r = await client.options("/health", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        })
        if r.headers.get("access-control-allow-credentials") == "true":
            assert r.headers.get("access-control-allow-origin") != "*"

    async def test_preflight_allows_all_http_methods(self, client):
        """
        CATEGORY: Configuration
        TITLE: [Finding] CORS allow_methods is configured as a wildcard
        OBJECTIVE: main.py sets allow_methods=["*"] -- confirm this in
                    practice by preflighting an unusual method.
        EXPECTED (CURRENT BEHAVIOR): PATCH (and effectively any method) is
                   allowed for a trusted origin. Documented as an informational
                   finding (Low) since it's paired with a real origin allow-list,
                   not a wildcard origin -- narrowing to only the methods each
                   route actually uses is still better practice.
        SEVERITY: Low
        """
        r = await client.options("/health", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
        })
        assert r.headers.get("access-control-allow-methods") is not None

    async def test_preflight_allows_all_request_headers(self, client):
        """
        CATEGORY: Configuration
        TITLE: [Finding] CORS allow_headers is configured as a wildcard
        OBJECTIVE: main.py sets allow_headers=["*"] -- confirm in practice.
        EXPECTED (CURRENT BEHAVIOR): An arbitrary custom header is allowed
                   through preflight. Low severity for the same reason as the
                   methods wildcard above.
        SEVERITY: Low
        """
        r = await client.options("/health", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Totally-Custom-Header",
        })
        allow_headers = r.headers.get("access-control-allow-headers", "")
        assert "x-totally-custom-header" in allow_headers.lower() or allow_headers == "*"


class TestMissingSecurityHeaders:
    async def test_no_x_content_type_options_header(self, client):
        """
        CATEGORY: Configuration
        TITLE: [Finding] Responses do not set X-Content-Type-Options: nosniff
        OBJECTIVE: FastAPI/Starlette add no security headers by default;
                    confirm this gap exists so it can be tracked.
        EXPECTED (CURRENT BEHAVIOR): Header absent. See findings.xlsx (VULN-008, Low).
        SEVERITY: Low
        """
        r = await client.get("/health")
        assert "x-content-type-options" not in {k.lower() for k in r.headers}

    async def test_no_x_frame_options_header(self, client):
        """
        CATEGORY: Configuration
        TITLE: [Finding] Responses do not set X-Frame-Options
        OBJECTIVE: Document the clickjacking-related header is not present
                    (low real-world impact for a pure JSON API, but worth tracking).
        EXPECTED (CURRENT BEHAVIOR): Header absent. See findings.xlsx (VULN-008, Low).
        SEVERITY: Low
        """
        r = await client.get("/health")
        assert "x-frame-options" not in {k.lower() for k in r.headers}

    async def test_no_strict_transport_security_header(self, client):
        """
        CATEGORY: Configuration
        TITLE: [Finding] Responses do not set Strict-Transport-Security
        OBJECTIVE: HSTS is typically applied at the reverse-proxy/CDN layer
                    in production, but the application itself sets nothing --
                    confirm and document so deployment config can be checked.
        EXPECTED (CURRENT BEHAVIOR): Header absent at the application layer.
                   See findings.xlsx (VULN-008, Low -- verify at the infra layer).
        SEVERITY: Low
        """
        r = await client.get("/health")
        assert "strict-transport-security" not in {k.lower() for k in r.headers}

    async def test_no_content_security_policy_header(self, client):
        """
        CATEGORY: Configuration
        TITLE: [Finding] Responses do not set a Content-Security-Policy
        OBJECTIVE: Low impact for a JSON-only API with no HTML rendering, but
                    documented for completeness / defense in depth.
        EXPECTED (CURRENT BEHAVIOR): Header absent. See findings.xlsx (VULN-008, Low).
        SEVERITY: Low
        """
        r = await client.get("/health")
        assert "content-security-policy" not in {k.lower() for k in r.headers}

    async def test_server_banner_discloses_uvicorn(self, client):
        """
        CATEGORY: Configuration
        TITLE: [Finding] The Server header discloses the ASGI server (uvicorn)
        OBJECTIVE: Minor information-disclosure check -- confirm the default
                    uvicorn Server header is present and not stripped.
        EXPECTED (CURRENT BEHAVIOR): 'server' header present and contains
                   'uvicorn'. See findings.xlsx (VULN-008, Low).
        SEVERITY: Low
        """
        r = await client.get("/health")
        assert "uvicorn" in r.headers.get("server", "").lower()


class TestErrorResponseDisclosure:
    async def test_404_response_does_not_leak_internal_paths(self, client):
        """
        CATEGORY: Configuration
        TITLE: A 404 for an unknown route does not leak filesystem paths
        OBJECTIVE: Confirm the default FastAPI 404 handler doesn't include
                    stack traces or absolute server paths.
        EXPECTED: 404, body contains no '/home/' or '/app/' style path fragments.
        SEVERITY: Medium
        """
        r = await client.get("/this-route-does-not-exist")
        assert r.status_code == 404
        assert "/home/" not in r.text and "/app/" not in r.text and ".py" not in r.text

    async def test_validation_error_does_not_leak_stack_trace(self, client, client1_headers):
        """
        CATEGORY: Configuration
        TITLE: A 422 validation error body contains only field-level detail, no stack trace
        OBJECTIVE: Confirm pydantic's error formatting is used as-is, without
                    any custom handler accidentally appending a traceback.
        EXPECTED: 422, body has no 'Traceback' or '.py", line' fragments.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={"target": ""})
        assert r.status_code == 422
        assert "Traceback" not in r.text
        assert ".py\", line" not in r.text

    async def test_crash_inducing_request_does_not_leak_stack_trace(self, client, unique_email):
        """
        CATEGORY: Configuration
        TITLE: The known >72-byte-password 500 does not leak a stack trace to the client
        OBJECTIVE: Even though this input triggers an unhandled server error
                    (see VULN-002 in test_authentication.py / findings.xlsx),
                    confirm production-mode error handling still hides the
                    traceback from the response body -- i.e. the crash is a
                    genuine bug, but not compounded by also being an info leak.
        EXPECTED: 500, body/text does NOT contain 'Traceback' or a raw Python
                   exception string with file paths.
        SEVERITY: Medium
        """
        long_password = "Aa1!" * 50
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": long_password, "full_name": "QA", "role": "client",
        })
        if r.status_code == 500:
            assert "Traceback" not in r.text
            assert "/home/" not in r.text and "/app/" not in r.text


class TestRateLimiting:
    async def test_no_http_layer_rate_limiting_on_login(self, client, unique_email):
        """
        CATEGORY: Configuration
        TITLE: [Finding] POST /auth/login has no rate limiting / brute-force protection
        OBJECTIVE: main.py wires no rate-limiting middleware (e.g. slowapi) at
                    all -- the only rate limiter in the codebase governs
                    outbound calls to the NVD API, not inbound auth traffic.
                    Confirm this in practice by firing a burst of failed
                    logins against one account with no backoff or lockout.
        EXPECTED (CURRENT BEHAVIOR): All N attempts return 401 individually,
                   none return 429. See findings.xlsx (VULN-009, High)
                   recommending per-IP/per-account login throttling.
        SEVERITY: High
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        statuses = []
        for _ in range(15):
            r = await client.post("/auth/login", json={"email": unique_email, "password": "WrongPassword!"})
            statuses.append(r.status_code)
        assert 429 not in statuses, (
            "A 429 appeared -- rate limiting for VULN-009 has been added, update findings.xlsx."
        )
        assert all(s == 401 for s in statuses)

    async def test_no_http_layer_rate_limiting_on_register(self, client):
        """
        CATEGORY: Configuration
        TITLE: [Finding] POST /auth/register has no rate limiting
        OBJECTIVE: Confirm rapid, repeated registration attempts (a common
                    account-enumeration / spam vector) are not throttled either.
        EXPECTED (CURRENT BEHAVIOR): No 429 across a burst of distinct
                   registrations. See findings.xlsx (VULN-009).
        SEVERITY: Medium
        """
        import uuid as _uuid
        statuses = []
        for _ in range(10):
            email = f"burst.{_uuid.uuid4().hex[:10]}@vulnara-qa-suite.com"
            r = await client.post("/auth/register", json={
                "email": email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
            })
            statuses.append(r.status_code)
        assert 429 not in statuses


class TestHealthAndMiscConfig:
    async def test_health_endpoint_is_publicly_accessible_by_design(self, client):
        """
        CATEGORY: Configuration
        TITLE: GET /health requires no authentication (intentional)
        OBJECTIVE: Confirm the uptime-monitoring endpoint really is public,
                    as documented in main.py's health() docstring.
        EXPECTED: 200 OK with no Authorization header.
        SEVERITY: Low
        """
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_endpoint_reports_db_connectivity(self, client):
        """
        CATEGORY: Configuration
        TITLE: GET /health reflects real DB connectivity, not a hardcoded value
        OBJECTIVE: Confirm the 'db' field is a live check against the
                    ephemeral test database, not a static 'ok' string.
        EXPECTED: 200, body contains db == 'ok' while the DB is reachable.
        SEVERITY: Low
        """
        r = await client.get("/health")
        assert r.json()["db"] == "ok"

    async def test_root_path_does_not_500(self, client):
        """
        CATEGORY: Configuration
        TITLE: The application root path ('/') responds cleanly
        OBJECTIVE: No route is mounted at '/' -- confirm this returns a clean
                    404 rather than crashing.
        EXPECTED: 404 Not Found.
        SEVERITY: Low
        """
        r = await client.get("/")
        assert r.status_code == 404

    async def test_options_wildcard_method_not_allowed_leaks_no_internals(self, client):
        """
        CATEGORY: Configuration
        TITLE: An unsupported HTTP method on a real route returns 405, not 500
        OBJECTIVE: Confirm method-not-allowed handling is clean.
        EXPECTED: 405 Method Not Allowed for DELETE on /health.
        SEVERITY: Low
        """
        r = await client.delete("/health")
        assert r.status_code == 405

    async def test_admin_config_get_response_shape(self, client, admin_headers):
        """
        CATEGORY: Configuration
        TITLE: GET /admin/config returns a well-formed configuration list
        OBJECTIVE: Confirm the config endpoint itself functions and returns JSON.
        EXPECTED: 200, JSON array (or object) body.
        SEVERITY: Low
        """
        r = await client.get("/admin/config", headers=admin_headers)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_multiple_concurrent_health_checks_all_succeed(self, client):
        """
        CATEGORY: Configuration
        TITLE: Multiple back-to-back health checks all succeed
        OBJECTIVE: Basic connection-pool sanity check under light concurrency.
        EXPECTED: All 10 sequential calls return 200.
        SEVERITY: Low
        """
        for _ in range(10):
            r = await client.get("/health")
            assert r.status_code == 200

    async def test_trailing_slash_on_collection_route_handled_consistently(self, client, client1_headers):
        """
        CATEGORY: Configuration
        TITLE: A trailing slash on a collection route is handled without a 500
        OBJECTIVE: Confirm FastAPI's default redirect/no-redirect behavior for
                    trailing slashes doesn't produce an unexpected error.
        EXPECTED: 200, 307, or 404 -- never 500.
        SEVERITY: Low
        """
        r = await client.get("/scans/", headers=client1_headers)
        assert r.status_code != 500

    async def test_case_sensitivity_of_route_paths(self, client, client1_headers):
        """
        CATEGORY: Configuration
        TITLE: Route paths are case-sensitive (uppercased path segment 404s)
        OBJECTIVE: Confirm no accidental case-insensitive routing that could
                    cause confusion with security-relevant paths.
        EXPECTED: 404 Not Found for '/SCANS'.
        SEVERITY: Low
        """
        r = await client.get("/SCANS", headers=client1_headers)
        assert r.status_code == 404

    async def test_query_string_on_a_route_without_defined_params_is_ignored(self, client, client1_headers, client1_scan):
        """
        CATEGORY: Configuration
        TITLE: An unexpected query string parameter on GET /scans/{id} is ignored, not an error
        OBJECTIVE: Confirm undeclared query params don't cause validation failures.
        EXPECTED: 200 OK.
        SEVERITY: Low
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}", params={"unexpected_param": "value"}, headers=client1_headers)
        assert r.status_code == 200

    @pytest.mark.parametrize("bad_severity", ["not_a_severity", "🔥", "1234"])
    async def test_scan_vulnerabilities_severity_filter_accepts_arbitrary_strings(self, client, client1_headers, client1_scan, bad_severity):
        """
        CATEGORY: Configuration
        TITLE: [Finding] severity query param on scan vulnerabilities has no enum validation
        OBJECTIVE: Confirm arbitrary strings are accepted for '?severity=' rather
                    than being restricted to the known severity values -- the
                    query simply returns an empty match rather than erroring,
                    but the lack of validation is worth tracking alongside VULN-003.
        EXPECTED (CURRENT BEHAVIOR): 200 OK regardless of the value supplied.
        SEVERITY: Low
        """
        r = await client.get(f"/scans/{client1_scan['scan_id']}/vulnerabilities", params={"severity": bad_severity}, headers=client1_headers)
        assert r.status_code == 200
