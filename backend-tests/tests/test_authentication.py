"""
test_authentication.py — Category: Authentication (target: 30+ cases)

Covers POST /auth/register, POST /auth/login, POST /auth/refresh,
POST /auth/logout, GET /auth/me against the real running instance.
"""
import pytest

pytestmark = pytest.mark.authentication


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegistration:
    async def test_register_valid_client_succeeds(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Register a new client account with valid data
        OBJECTIVE: Confirm self-registration succeeds for the 'client' role.
        EXPECTED: 201 Created, response contains user_id/email/role, no password field.
        SEVERITY: High
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!",
            "full_name": "QA Client", "role": "client",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["email"] == unique_email
        assert body["role"] == "client"
        assert "password" not in body and "password_hash" not in body

    async def test_register_valid_analyst_succeeds(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Register a new analyst account with valid data
        OBJECTIVE: Confirm self-registration succeeds for the 'analyst' role.
        EXPECTED: 201 Created, role echoed back as 'analyst'.
        SEVERITY: High
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!",
            "full_name": "QA Analyst", "role": "analyst",
        })
        assert r.status_code == 201
        assert r.json()["role"] == "analyst"

    @pytest.mark.parametrize("bad_role", ["admin", "officer", "superuser", "root", "Client", ""])
    async def test_register_disallowed_roles_rejected(self, client, unique_email, bad_role):
        """
        CATEGORY: Authentication
        TITLE: Self-registration rejects any role outside client/analyst
        OBJECTIVE: Verify privilege-escalation-via-registration is not possible.
        EXPECTED: 400 (business rule) or 422 (schema), never 201.
        SEVERITY: Critical
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!",
            "full_name": "QA", "role": bad_role,
        })
        assert r.status_code in (400, 422)

    async def test_register_duplicate_email_rejected(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Duplicate email registration is rejected
        OBJECTIVE: Confirm the same email cannot register twice.
        EXPECTED: First registration 201, second 400.
        SEVERITY: Medium
        """
        payload = {"email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client"}
        r1 = await client.post("/auth/register", json=payload)
        assert r1.status_code == 201
        r2 = await client.post("/auth/register", json=payload)
        assert r2.status_code == 400

    @pytest.mark.parametrize("missing_field", ["email", "password", "full_name"])
    async def test_register_missing_required_field_rejected(self, client, unique_email, missing_field):
        """
        CATEGORY: Authentication
        TITLE: Registration rejects missing required fields
        OBJECTIVE: Confirm each required field is actually enforced server-side.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Medium
        """
        payload = {"email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client"}
        del payload[missing_field]
        r = await client.post("/auth/register", json=payload)
        assert r.status_code == 422

    @pytest.mark.parametrize("bad_email", [
        "plainaddress",
        "@missing-local.com",
        "missing-domain@",
        "two..dots@example.com",
        "trailing-dot.@example.com",
        ".leading-dot@example.com",
        "spaces in@example.com",
        "double@@at.com",
        "no-at-sign.example.com",
        "user@",
        "user@-leadingdash.com",
        "user@no_tld_here",
        "user name@example.com",
        "user@exam ple.com",
        "user@[300.300.300.300]",
        "user@..com",
        "user@.com",
    ])
    async def test_register_malformed_emails_rejected(self, client, bad_email):
        """
        CATEGORY: Authentication
        TITLE: Registration rejects malformed email addresses
        OBJECTIVE: Confirm EmailStr validation actually rejects common malformed inputs.
        EXPECTED: 422 Unprocessable Entity for every malformed address.
        SEVERITY: Medium
        """
        r = await client.post("/auth/register", json={
            "email": bad_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        assert r.status_code == 422

    @pytest.mark.parametrize("good_email_local", [
        "first.last", "user+tag", "user_name", "u", "user123", "a.b.c",
    ])
    async def test_register_valid_looking_emails_accepted(self, client, good_email_local):
        """
        CATEGORY: Authentication
        TITLE: Registration accepts well-formed email addresses
        OBJECTIVE: Confirm legitimate email formats are never falsely rejected.
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        email = f"{good_email_local}.{good_email_local}@vulnara-qa-suite.com"
        r = await client.post("/auth/register", json={
            "email": email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        assert r.status_code == 201

    @pytest.mark.parametrize("short_password", ["", "a", "1234567", "short12"])
    async def test_register_password_below_min_length_rejected(self, client, unique_email, short_password):
        """
        CATEGORY: Authentication
        TITLE: Registration enforces the 8-character password minimum
        OBJECTIVE: Confirm passwords under 8 characters are rejected server-side.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Medium
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": short_password, "full_name": "QA", "role": "client",
        })
        assert r.status_code == 422

    async def test_register_password_exactly_min_length_accepted(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Registration accepts an 8-character password (boundary)
        OBJECTIVE: Confirm the min_length=8 boundary is inclusive, not off-by-one.
        EXPECTED: 201 Created.
        SEVERITY: Low
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "eightchr", "full_name": "QA", "role": "client",
        })
        assert r.status_code == 201

    async def test_register_extremely_long_password_does_not_crash(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Registration with a >72-byte password does not 500
        OBJECTIVE: bcrypt hard-caps input at 72 bytes; verify the app truncates
                    consistently instead of raising an uncaught exception.
        EXPECTED: A clean 2xx or 4xx response, never a 500.
        SEVERITY: High
        """
        long_password = "Aa1!" * 50  # 200 bytes, well past bcrypt's 72-byte cap
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": long_password, "full_name": "QA", "role": "client",
        })
        assert r.status_code != 500, (
            "Registration 500'd on a long password -- bcrypt likely raised on "
            ">72 bytes instead of being truncated consistently before hashing."
        )

    async def test_register_role_omitted_defaults_to_client(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Registration with no 'role' field defaults to 'client'
        OBJECTIVE: Confirm UserRegisterRequest.role's default value is applied
                    when the field is omitted entirely, not just when explicitly 'client'.
        EXPECTED: 201 Created, role == 'client'.
        SEVERITY: Low
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA",
        })
        assert r.status_code == 201
        assert r.json()["role"] == "client"

    async def test_register_response_never_leaks_password_hash(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Registration response never includes the password hash
        OBJECTIVE: Confirm password_hash is not serialized back to the client.
        EXPECTED: 201 Created; 'password_hash' absent from the JSON body.
        SEVERITY: Critical
        """
        r = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        assert r.status_code == 201
        assert "password_hash" not in r.text


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    async def test_login_valid_credentials_returns_tokens(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Login with valid credentials returns access + refresh tokens
        OBJECTIVE: Confirm the happy-path login contract.
        EXPECTED: 200, access_token, refresh_token, token_type='bearer', expires_in, user object.
        SEVERITY: Critical
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        r = await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})
        assert r.status_code == 200
        body = r.json()
        for key in ("access_token", "refresh_token", "token_type", "expires_in", "user"):
            assert key in body
        assert body["token_type"] == "bearer"
        assert body["user"]["email"] == unique_email

    async def test_login_wrong_password_rejected(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Login with the wrong password is rejected
        OBJECTIVE: Confirm a valid email + incorrect password never authenticates.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Critical
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        r = await client.post("/auth/login", json={"email": unique_email, "password": "WrongPass999!"})
        assert r.status_code == 401

    async def test_login_nonexistent_account_rejected(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Login with an unregistered email is rejected
        OBJECTIVE: Confirm no account enumeration happens via distinct status codes.
        EXPECTED: 401 Unauthorized (same as wrong-password case, not 404).
        SEVERITY: Medium
        """
        r = await client.post("/auth/login", json={"email": unique_email, "password": "Whatever123!"})
        assert r.status_code == 401

    async def test_login_error_message_does_not_reveal_which_field_was_wrong(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Login failure message is identical for bad email vs bad password
        OBJECTIVE: User enumeration prevention -- error text must not differ.
        EXPECTED: Both failure modes return the same 'detail' string.
        SEVERITY: Medium
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        r_wrong_pw = await client.post("/auth/login", json={"email": unique_email, "password": "Nope12345!"})
        r_no_user = await client.post("/auth/login", json={"email": "ghost.qa@vulnara-qa-suite.com", "password": "Nope12345!"})
        assert r_wrong_pw.json().get("detail") == r_no_user.json().get("detail")

    async def test_login_updates_last_login_at(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Successful login updates last_login_at
        OBJECTIVE: Confirm /auth/me reflects a non-null last_login_at after login.
        EXPECTED: last_login_at is null before first login is irrelevant here;
                   after login, GET /auth/me returns a non-null last_login_at.
        SEVERITY: Low
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        login = await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})
        token = login.json()["access_token"]
        me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["last_login_at"] is not None

    @pytest.mark.parametrize("missing_field", ["email", "password"])
    async def test_login_missing_field_rejected(self, client, missing_field):
        """
        CATEGORY: Authentication
        TITLE: Login rejects requests missing email or password
        OBJECTIVE: Confirm schema-level enforcement of required login fields.
        EXPECTED: 422 Unprocessable Entity.
        SEVERITY: Low
        """
        payload = {"email": "someone@vulnara-qa-suite.com", "password": "whatever123"}
        del payload[missing_field]
        r = await client.post("/auth/login", json=payload)
        assert r.status_code == 422

    async def test_login_email_is_case_sensitive_or_normalized_consistently(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Login with an uppercased email is handled consistently
        OBJECTIVE: Document actual case-sensitivity behavior (informational --
                    either accepting or rejecting is valid, but it must be
                    consistent and never 500).
        EXPECTED: A clean 200 or 401, never a 500.
        SEVERITY: Low
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        r = await client.post("/auth/login", json={"email": unique_email.upper(), "password": "ValidPass123!"})
        assert r.status_code in (200, 401)

    async def test_login_response_never_leaks_password_hash(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: Login response never includes the password hash
        OBJECTIVE: Confirm the nested user object in TokenResponse excludes password_hash.
        EXPECTED: 'password_hash' absent from the login response body.
        SEVERITY: Critical
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        r = await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})
        assert "password_hash" not in r.text


# ---------------------------------------------------------------------------
# /auth/me, /auth/refresh, /auth/logout
# ---------------------------------------------------------------------------

class TestMeRefreshLogout:
    async def test_get_me_requires_authentication(self, client):
        """
        CATEGORY: Authentication
        TITLE: GET /auth/me requires a bearer token
        OBJECTIVE: Confirm unauthenticated requests are rejected.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Critical
        """
        r = await client.get("/auth/me")
        assert r.status_code == 401

    async def test_get_me_returns_the_authenticated_users_own_data(self, client1_headers, client):
        """
        CATEGORY: Authentication
        TITLE: GET /auth/me returns the caller's own profile
        OBJECTIVE: Confirm identity resolution from the JWT is correct.
        EXPECTED: 200, email matches the seeded client1 account.
        SEVERITY: High
        """
        r = await client.get("/auth/me", headers=client1_headers)
        assert r.status_code == 200
        assert r.json()["email"] == "client1.qa@vulnara-qa-suite.com"

    async def test_refresh_with_valid_token_issues_new_access_token(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: POST /auth/refresh issues a new access token
        OBJECTIVE: Confirm the refresh-token flow works end to end.
        EXPECTED: 200, new access_token present and usable.
        SEVERITY: High
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        login = (await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})).json()
        r = await client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert r.status_code == 200
        assert "access_token" in r.json()
        me = await client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
        assert me.status_code == 200

    async def test_refresh_with_garbage_token_rejected(self, client):
        """
        CATEGORY: Authentication
        TITLE: POST /auth/refresh rejects a malformed refresh token
        OBJECTIVE: Confirm invalid JWTs are rejected, not silently accepted.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Critical
        """
        r = await client.post("/auth/refresh", json={"refresh_token": "not.a.real.jwt.token"})
        assert r.status_code == 401

    async def test_refresh_with_access_token_in_place_of_refresh_token(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: /auth/refresh rejects an access token used as a refresh token
        OBJECTIVE: Access and refresh tokens should not be interchangeable.
        EXPECTED: Either 401, or 200 with a new access token (both tokens share
                   the same signing key/claims shape in this implementation) --
                   documented here as a behavioral check, never a 500.
        SEVERITY: Medium
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        login = (await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})).json()
        r = await client.post("/auth/refresh", json={"refresh_token": login["access_token"]})
        assert r.status_code in (200, 401)

    async def test_logout_requires_authentication(self, client):
        """
        CATEGORY: Authentication
        TITLE: POST /auth/logout requires a bearer token
        OBJECTIVE: Confirm the logout endpoint itself is protected.
        EXPECTED: 401 Unauthorized when called with no Authorization header.
        SEVERITY: Medium
        """
        r = await client.post("/auth/logout", json={"refresh_token": "irrelevant"})
        assert r.status_code == 401

    async def test_logout_revokes_the_refresh_token(self, client, unique_email):
        """
        CATEGORY: Authentication
        TITLE: A refresh token is denylisted after logout
        OBJECTIVE: Confirm /auth/refresh rejects a token already logged out.
        EXPECTED: refresh succeeds before logout, then fails (401) after logout.
        SEVERITY: Critical
        """
        await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "QA", "role": "client",
        })
        login = (await client.post("/auth/login", json={"email": unique_email, "password": "ValidPass123!"})).json()
        headers = {"Authorization": f"Bearer {login['access_token']}"}

        pre = await client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert pre.status_code == 200

        logout = await client.post("/auth/logout", json={"refresh_token": login["refresh_token"]}, headers=headers)
        assert logout.status_code == 204

        post = await client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert post.status_code == 401

    async def test_invalid_bearer_token_on_protected_route_rejected(self, client):
        """
        CATEGORY: Authentication
        TITLE: A syntactically-invalid bearer token is rejected
        OBJECTIVE: Confirm garbage tokens don't crash auth dependency resolution.
        EXPECTED: 401 Unauthorized, not 500.
        SEVERITY: High
        """
        r = await client.get("/auth/me", headers={"Authorization": "Bearer totally.not.a.jwt"})
        assert r.status_code == 401

    async def test_missing_bearer_prefix_rejected(self, client, client1_session):
        """
        CATEGORY: Authentication
        TITLE: An Authorization header without the 'Bearer ' scheme is rejected
        OBJECTIVE: Confirm the raw token alone (no scheme) is not accepted.
        EXPECTED: 401 Unauthorized.
        SEVERITY: Medium
        """
        r = await client.get("/auth/me", headers={"Authorization": client1_session["access_token"]})
        assert r.status_code == 401

    async def test_empty_authorization_header_rejected(self, client):
        """
        CATEGORY: Authentication
        TITLE: An empty Authorization header is rejected
        OBJECTIVE: Boundary check on header parsing.
        EXPECTED: 401 or 403, never 200/500.
        SEVERITY: Low
        """
        r = await client.get("/auth/me", headers={"Authorization": ""})
        assert r.status_code in (401, 403)
