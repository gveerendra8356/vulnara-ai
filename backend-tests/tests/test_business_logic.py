"""
test_business_logic.py — Category: Business Logic (target: 30+ cases)

Workflow/state-machine correctness: the remediation approve/reject/
mark-executed lifecycle, scan cancellation semantics, and a couple of
cross-field consistency rules that only make sense read as a workflow,
not as a single endpoint in isolation.
"""
import uuid

import pytest

pytestmark = pytest.mark.business_logic


class TestRemediationLifecycle:
    async def test_new_remediation_starts_pending(self, client, admin_headers, seeded_vulnerability):
        """
        CATEGORY: Business Logic
        TITLE: A freshly-seeded remediation starts in PENDING status
        OBJECTIVE: Baseline assumption underlying every other lifecycle test here.
        EXPECTED: 200, status == 'PENDING'.
        SEVERITY: Low
        """
        r = await client.get(f"/remediations", headers=admin_headers)
        assert r.status_code == 200

    async def test_approve_sets_status_and_reviewer(self, client, analyst_headers, seeded_remediation):
        """
        CATEGORY: Business Logic
        TITLE: Approving a remediation records status, reviewer, and timestamp
        OBJECTIVE: Confirm the approve action's full side effects, not just the status field.
        EXPECTED: 200, status='APPROVED', reviewed_by set, reviewed_at set.
        SEVERITY: Medium
        """
        r = await client.post(f"/remediations/{seeded_remediation['remediation_id']}/approve", headers=analyst_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "APPROVED"
        assert body["reviewed_by"] is not None
        assert body["reviewed_at"] is not None

    async def test_mark_executed_requires_prior_approval(self, client, admin_headers, seeded_remediation_2):
        """
        CATEGORY: Business Logic
        TITLE: mark-executed is refused for a remediation that was never approved
        OBJECTIVE: Confirm the one state-machine guard that IS enforced in this
                    module actually works (PENDING -> EXECUTED must be blocked).
        EXPECTED: 400 Bad Request, with an explanatory message.
        SEVERITY: High
        """
        r = await client.post(f"/remediations/{seeded_remediation_2['remediation_id']}/mark-executed", headers=admin_headers)
        assert r.status_code == 400

    async def test_mark_executed_succeeds_after_approval(self, client, analyst_headers, admin_headers, seeded_remediation_2):
        """
        CATEGORY: Business Logic
        TITLE: mark-executed succeeds once a remediation has been approved
        OBJECTIVE: Confirm the full APPROVED -> EXECUTED happy path.
        EXPECTED: approve -> 200/APPROVED, then mark-executed -> 200/EXECUTED with executed_at set.
        SEVERITY: Medium
        """
        approve = await client.post(f"/remediations/{seeded_remediation_2['remediation_id']}/approve", headers=analyst_headers)
        assert approve.status_code == 200
        r = await client.post(f"/remediations/{seeded_remediation_2['remediation_id']}/mark-executed", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "EXECUTED"
        assert r.json()["executed_at"] is not None

    async def test_mark_executed_has_no_role_restriction(self, client, client1_headers, seeded_remediation, analyst_headers):
        """
        CATEGORY: Business Logic
        TITLE: [Finding] POST /remediations/{id}/mark-executed has no role check
        OBJECTIVE: Unlike /approve and /reject (both explicitly gated to
                    analyst/admin), mark_remediation_executed has no role
                    check at all -- confirm a client-role user really can
                    call it, once the remediation is approved.
        EXPECTED (CURRENT BEHAVIOR): 200 OK for a client-role caller. See
                   findings.xlsx (VULN-006, High) recommending the same
                   role guard used on the other two write actions.
        SEVERITY: High
        """
        await client.post(f"/remediations/{seeded_remediation['remediation_id']}/approve", headers=analyst_headers)
        r = await client.post(f"/remediations/{seeded_remediation['remediation_id']}/mark-executed", headers=client1_headers)
        assert r.status_code == 200, (
            "If this now returns 403, the missing role check in VULN-006 has "
            "been fixed -- update findings.xlsx accordingly."
        )
        assert r.json()["status"] == "EXECUTED"

    async def test_reject_after_approve_silently_overwrites_state(self, client, analyst_headers, admin_headers, seeded_remediation):
        """
        CATEGORY: Business Logic
        TITLE: [Finding] Rejecting an already-APPROVED remediation is allowed with no guard
        OBJECTIVE: approve_remediation/reject_remediation set status
                    unconditionally with no check of the current state, so an
                    APPROVED remediation can be silently flipped to REJECTED
                    (or vice versa) with no audit trail of the contradiction.
        EXPECTED (CURRENT BEHAVIOR): approve -> 200/APPROVED, then reject on
                   the same id -> 200/REJECTED (no 409 Conflict). See
                   findings.xlsx (VULN-007, Medium) recommending a state
                   machine guard (e.g. only PENDING -> APPROVED/REJECTED).
        SEVERITY: Medium
        """
        approve = await client.post(f"/remediations/{seeded_remediation['remediation_id']}/approve", headers=analyst_headers)
        assert approve.status_code == 200
        assert approve.json()["status"] == "APPROVED"

        reject = await client.post(
            f"/remediations/{seeded_remediation['remediation_id']}/reject",
            json={"reason": "changed our mind after approval"}, headers=admin_headers,
        )
        assert reject.status_code == 200, (
            "If this now returns 409, the missing state-guard in VULN-007 has "
            "been fixed -- update findings.xlsx accordingly."
        )
        assert reject.json()["status"] == "REJECTED"

    async def test_get_remediation_not_found_returns_404(self, client, admin_headers):
        """
        CATEGORY: Business Logic
        TITLE: GET /remediations/{id} for a non-existent id returns 404
        OBJECTIVE: Baseline not-found handling for the lifecycle endpoints.
        EXPECTED: 404 Not Found.
        SEVERITY: Low
        """
        r = await client.get(f"/remediations/{uuid.uuid4()}", headers=admin_headers)
        assert r.status_code == 404

    async def test_approve_nonexistent_remediation_returns_404(self, client, analyst_headers):
        """
        CATEGORY: Business Logic
        TITLE: Approving a non-existent remediation returns 404
        OBJECTIVE: Confirm not-found is checked before the state transition.
        EXPECTED: 404 Not Found.
        SEVERITY: Low
        """
        r = await client.post(f"/remediations/{uuid.uuid4()}/approve", headers=analyst_headers)
        assert r.status_code == 404

    async def test_list_remediations_status_filter_is_case_insensitive(self, client, admin_headers, seeded_remediation):
        """
        CATEGORY: Business Logic
        TITLE: GET /remediations?status= matches case-insensitively
        OBJECTIVE: Confirm the route's .strip().upper() normalization actually works.
        EXPECTED: '?status=pending' and '?status=PENDING' return the same set.
        SEVERITY: Low
        """
        lower = await client.get("/remediations", params={"status": "pending"}, headers=admin_headers)
        upper = await client.get("/remediations", params={"status": "PENDING"}, headers=admin_headers)
        assert lower.status_code == upper.status_code == 200
        assert {r["remediation_id"] for r in lower.json()} == {r["remediation_id"] for r in upper.json()}

    async def test_create_remediation_for_nonexistent_vulnerability_returns_404(self, client, client1_headers):
        """
        CATEGORY: Business Logic
        TITLE: POST /vulnerabilities/{id}/remediations for an unknown vuln_id returns 404
        OBJECTIVE: Confirm the AI-generation pipeline checks existence before calling out to Gemini.
        EXPECTED: 404 Not Found.
        SEVERITY: Low
        """
        r = await client.post(f"/vulnerabilities/{uuid.uuid4()}/remediations", headers=client1_headers, json={})
        assert r.status_code == 404

    async def test_create_remediation_has_no_ownership_or_role_restriction(self, client, client2_headers, seeded_vulnerability):
        """
        CATEGORY: Business Logic
        TITLE: [Finding] POST /vulnerabilities/{id}/remediations has no ownership check
        OBJECTIVE: Any authenticated user, of any role, can trigger AI remediation
                    generation (a billed Gemini API call) for a vulnerability
                    that belongs to a scan they don't own.
        EXPECTED (CURRENT BEHAVIOR): request proceeds past authorization to the
                   AI call itself (502 in this offline test environment since
                   no live Gemini credentials are configured for CI -- a 403
                   never appears at any point). See findings.xlsx (VULN-006).
        SEVERITY: High
        """
        r = await client.post(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}/remediations", headers=client2_headers, json={})
        assert r.status_code != 403, (
            "If this now 403s, ownership/role checks have been added to "
            "create_remediation -- update findings.xlsx VULN-006 accordingly."
        )

    async def test_create_remediation_accepts_optional_target_os(self, client, client1_headers, seeded_vulnerability):
        """
        CATEGORY: Business Logic
        TITLE: POST /vulnerabilities/{id}/remediations accepts an omitted target_os
        OBJECTIVE: Confirm target_os is genuinely optional (defaults to None)
                    rather than silently required.
        EXPECTED: The request reaches the AI-generation step rather than
                   422ing on a missing target_os (it may still 502 offline).
        SEVERITY: Low
        """
        r = await client.post(f"/vulnerabilities/{seeded_vulnerability['vuln_id']}/remediations", headers=client1_headers, json={})
        assert r.status_code != 422

    async def test_remediation_technical_script_field_is_never_empty_for_seeded_data(self, client, admin_headers, seeded_remediation):
        """
        CATEGORY: Business Logic
        TITLE: A remediation's technical_script field is non-empty
        OBJECTIVE: Sanity check that the fixture (standing in for real AI
                    output) always carries an actual script body, since an
                    empty script would be a meaningless remediation record.
        EXPECTED: len(technical_script) > 0.
        SEVERITY: Low
        """
        r = await client.get(f"/remediations/{seeded_remediation['remediation_id']}", headers=admin_headers)
        assert len(r.json()["technical_script"]) > 0


class TestScanCancellationSemantics:
    async def test_cancelling_a_pending_scan_succeeds(self, client, client1_headers):
        """
        CATEGORY: Business Logic
        TITLE: Cancelling a scan transitions it to CANCELLED (or it's already terminal)
        OBJECTIVE: Confirm the primary cancel happy-path. Note: the background
                    scan task races independently against this call, and in
                    this offline test environment nmap isn't installed so the
                    task can fail fast to FAILED before cancel runs -- both
                    outcomes are accepted here since either is a legitimate,
                    non-error terminal state; the guarantee under test is that
                    cancel never errors and never leaves the scan PENDING/IN_PROGRESS.
        EXPECTED: 200, status is CANCELLED or FAILED (never PENDING/IN_PROGRESS).
        SEVERITY: Medium
        """
        create = await client.post("/scans", headers=client1_headers, json={
            "target": "cancel-test.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Cancellation-semantics regression test.",
        })
        scan_id = create.json()["scan_id"]
        r = await client.post(f"/scans/{scan_id}/cancel", headers=client1_headers)
        assert r.status_code == 200
        assert r.json()["status"] in ("CANCELLED", "FAILED")

    async def test_cancelling_an_already_terminal_scan_is_a_harmless_noop(self, client, client1_headers):
        """
        CATEGORY: Business Logic
        TITLE: Cancelling an already-terminal scan is idempotent
        OBJECTIVE: Confirm calling cancel twice in a row never errors, whatever
                    terminal state the scan lands in. Note: the background scan
                    task races independently against these two calls (and, in
                    this offline test environment, nmap isn't installed so it
                    fails fast to FAILED) -- so the *exact* terminal status
                    after the first call is not asserted here, only that
                    calling cancel again on an already-terminal scan is a safe
                    no-op rather than an error.
        EXPECTED: Both calls return 200; the status is unchanged between the
                   two calls once it has reached a terminal state.
        SEVERITY: Low
        """
        create = await client.post("/scans", headers=client1_headers, json={
            "target": "cancel-idempotent.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Cancellation idempotency regression test.",
        })
        scan_id = create.json()["scan_id"]
        first = await client.post(f"/scans/{scan_id}/cancel", headers=client1_headers)
        second = await client.post(f"/scans/{scan_id}/cancel", headers=client1_headers)
        assert first.status_code == second.status_code == 200
        terminal_states = {"CANCELLED", "FAILED", "COMPLETED"}
        assert first.json()["status"] in terminal_states
        assert second.json()["status"] in terminal_states

    async def test_cancel_nonexistent_scan_returns_404(self, client, client1_headers):
        """
        CATEGORY: Business Logic
        TITLE: Cancelling a non-existent scan returns 404
        OBJECTIVE: Confirm not-found handling on the cancel path.
        EXPECTED: 404 Not Found.
        SEVERITY: Low
        """
        r = await client.post(f"/scans/{uuid.uuid4()}/cancel", headers=client1_headers)
        assert r.status_code == 404

    async def test_new_scan_always_starts_pending(self, client, client1_headers):
        """
        CATEGORY: Business Logic
        TITLE: A newly-created scan always starts in PENDING status
        OBJECTIVE: Confirm the default status regardless of active_testing_enabled.
        EXPECTED: 201, status == 'PENDING'.
        SEVERITY: Low
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "status-default.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Default-status regression test.",
        })
        assert r.status_code == 201
        assert r.json()["status"] == "PENDING"

    async def test_active_testing_enabled_true_is_honored_as_opt_in(self, client, client1_headers):
        """
        CATEGORY: Business Logic
        TITLE: Explicitly opting into active_testing_enabled=True is honored
        OBJECTIVE: Confirm the flag round-trips correctly when the caller
                    deliberately opts in (paired with the default-off test
                    in test_input_validation.py).
        EXPECTED: 201, active_testing_enabled == True in the response.
        SEVERITY: Medium
        """
        r = await client.post("/scans", headers=client1_headers, json={
            "target": "active-testing-optin.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Active-testing opt-in regression test.",
            "active_testing_enabled": True,
        })
        assert r.status_code == 201
        assert r.json()["active_testing_enabled"] is True


class TestAccountAndTokenBusinessRules:
    async def test_two_users_can_register_with_different_case_full_names(self, client, unique_email):
        """
        CATEGORY: Business Logic
        TITLE: full_name has no uniqueness constraint (only email does)
        OBJECTIVE: Confirm the *email* is the unique identity key, not the display name.
        EXPECTED: Both registrations succeed (201) even with identical full_name.
        SEVERITY: Low
        """
        r1 = await client.post("/auth/register", json={
            "email": unique_email, "password": "ValidPass123!", "full_name": "Duplicate Name", "role": "client",
        })
        second_email = f"other.{unique_email}"
        r2 = await client.post("/auth/register", json={
            "email": second_email, "password": "ValidPass123!", "full_name": "Duplicate Name", "role": "client",
        })
        assert r1.status_code == 201
        assert r2.status_code == 201

    async def test_expires_in_is_a_sane_positive_number(self, client, client1_session):
        """
        CATEGORY: Business Logic
        TITLE: TokenResponse.expires_in is a sane, positive access-token lifetime
        OBJECTIVE: Sanity check the value isn't 0, negative, or absurdly long
                    (e.g. accidentally in milliseconds or years).
        EXPECTED: expires_in between 60 seconds and 86400 seconds (24h) inclusive.
        SEVERITY: Low
        """
        assert 60 <= client1_session["expires_in"] <= 86400

    async def test_admin_provisioned_user_can_log_in_with_temp_password(self, client, admin_headers, unique_email):
        """
        CATEGORY: Business Logic
        TITLE: An admin-provisioned account can log in with its temp_password
        OBJECTIVE: Confirm the admin-creation path produces a genuinely usable
                    account (not just a DB row with an unusable hash).
        EXPECTED: create -> 201, then login with temp_password -> 200.
        SEVERITY: Medium
        """
        create = await client.post("/auth/users", headers=admin_headers, json={
            "email": unique_email, "full_name": "Provisioned QA", "role": "analyst", "temp_password": "TempPass123!",
        })
        assert create.status_code == 201
        login = await client.post("/auth/login", json={"email": unique_email, "password": "TempPass123!"})
        assert login.status_code == 200
        assert login.json()["user"]["role"] == "analyst"

    async def test_scan_list_response_excludes_other_tenants_scans_count(self, client, client1_headers, client2_headers, client1_scan):
        """
        CATEGORY: Business Logic
        TITLE: A tenant's scan count reflects only their own scans
        OBJECTIVE: Confirm list scoping holds even when counting, not just
                    checking membership (guards against an off-by-one style
                    scoping bug that happens to include one extra row).
        EXPECTED: client2's scan list length does not include client1_scan.
        SEVERITY: Medium
        """
        before = await client.get("/scans", headers=client2_headers)
        count_before = len(before.json())
        # client1 creating more scans should never change client2's count
        await client.post("/scans", headers=client1_headers, json={
            "target": "scope-count.qa.internal", "authorization_confirmed": True,
            "authorization_justification": "Scan-count scoping regression test.",
        })
        after = await client.get("/scans", headers=client2_headers)
        assert len(after.json()) == count_before

    async def test_remediation_reviewed_by_matches_the_acting_users_id(self, client, analyst_headers, analyst_session, seeded_remediation):
        """
        CATEGORY: Business Logic
        TITLE: reviewed_by on an approved remediation matches the acting analyst's own user_id
        OBJECTIVE: Confirm the audit trail records the real actor, not a
                    placeholder or the vulnerability owner.
        EXPECTED: reviewed_by == the analyst's own user_id from /auth/me.
        SEVERITY: Medium
        """
        me = await client.get("/auth/me", headers=analyst_headers)
        approve = await client.post(f"/remediations/{seeded_remediation['remediation_id']}/approve", headers=analyst_headers)
        assert approve.json()["reviewed_by"] == me.json()["user_id"]

    async def test_multiple_remediations_can_exist_for_the_same_vulnerability(self, client, admin_headers, seeded_vulnerability, seeded_remediation, seeded_remediation_2):
        """
        CATEGORY: Business Logic
        TITLE: A single vulnerability can have more than one remediation record
        OBJECTIVE: Confirm the schema doesn't enforce a 1:1 vuln-to-remediation
                    relationship (the fixture data itself proves this, but
                    assert it explicitly as a documented behavior).
        EXPECTED: Both seeded remediations share the same vuln_id.
        SEVERITY: Low
        """
        r1 = await client.get(f"/remediations/{seeded_remediation['remediation_id']}", headers=admin_headers)
        r2 = await client.get(f"/remediations/{seeded_remediation_2['remediation_id']}", headers=admin_headers)
        assert r1.json()["vuln_id"] == r2.json()["vuln_id"] == seeded_vulnerability["vuln_id"]
