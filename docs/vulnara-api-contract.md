# Vulnara — REST + WebSocket API Contract

Base URL: `https://api.vulnara.example.com` (Oracle Cloud VM, behind Let's Encrypt/Cloudflare Tunnel)
All request/response bodies are JSON. All timestamps are ISO 8601 UTC. All IDs are UUID strings unless noted.
Auth: Bearer JWT in `Authorization: Header` header, issued by `/auth/login`, unless marked **Public**.

---

## 0. Conventions used below

- **Auth levels**: `Public` (no token), `Authenticated` (any valid role), `Admin` (role = `admin`).
- **Client**: `Mobile`, `Web`, or `Both` — since both clients hit the identical API, this just flags which UI surface is expected to call it in practice.
- Standard error shape for all non-2xx responses:
```json
{ "error": { "code": "string", "message": "string", "details": {} } }
```
- Paginated list endpoints share this wrapper:
```json
{ "items": [ /* ... */ ], "total": 0, "page": 1, "page_size": 20 }
```

---

## 1. Auth

### 1.1 `POST /auth/register`
- **Purpose**: Create a new user account.
- **Auth**: Public
- **Client**: Both
- **Request body**:
```json
{ "email": "string", "password": "string", "full_name": "string", "role": "client" }
```
  - `role` is client-selectable only for `client`/`analyst` self-signup context (project decision — see note below); `admin` accounts are seeded/created by an existing admin via 1.6.
- **Response** `201`:
```json
{ "user_id": "uuid", "email": "string", "full_name": "string", "role": "string", "created_at": "datetime" }
```

### 1.2 `POST /auth/login`
- **Purpose**: Authenticate and receive access + refresh tokens.
- **Auth**: Public
- **Client**: Both
- **Request body**: `{ "email": "string", "password": "string" }`
- **Response** `200`:
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { "user_id": "uuid", "email": "string", "full_name": "string", "role": "string" }
}
```

### 1.3 `POST /auth/refresh`
- **Purpose**: Exchange a valid refresh token for a new access token.
- **Auth**: Public (requires valid refresh token in body)
- **Client**: Both
- **Request body**: `{ "refresh_token": "string" }`
- **Response** `200`: `{ "access_token": "string", "expires_in": 3600 }`

### 1.4 `POST /auth/logout`
- **Purpose**: Invalidate the current refresh token (server-side denylist).
- **Auth**: Authenticated
- **Client**: Both
- **Request body**: `{ "refresh_token": "string" }`
- **Response**: `204 No Content`

### 1.5 `GET /auth/me`
- **Purpose**: Return the currently authenticated user's profile.
- **Auth**: Authenticated
- **Client**: Both
- **Request**: none
- **Response** `200`: `{ "user_id": "uuid", "email": "string", "full_name": "string", "role": "string", "last_login_at": "datetime" }`

### 1.6 `POST /auth/users` *(admin-created accounts)*
- **Purpose**: Admin creates a user with any role (e.g. another admin or analyst).
- **Auth**: Admin
- **Client**: Web
- **Request body**: `{ "email": "string", "full_name": "string", "role": "admin|analyst|client", "temp_password": "string" }`
- **Response** `201`: same shape as 1.1 response.

---

## 2. Scan Lifecycle

### 2.1 `POST /scans`
- **Purpose**: Submit a new scan target with mandatory authorization confirmation. Creates the scan and kicks off recon asynchronously.
- **Auth**: Authenticated
- **Client**: Both
- **Request body**:
```json
{
  "target": "string (domain or IP)",
  "authorization_confirmed": true,
  "authorization_justification": "string (required, min length enforced)",
  "active_testing_enabled": false
}
```
  - Server rejects with `422` if `authorization_confirmed` is not `true` or `authorization_justification` is empty — this is the non-negotiable scope gate, enforced server-side regardless of client.
- **Response** `201`:
```json
{ "scan_id": "uuid", "target": "string", "status": "PENDING", "active_testing_enabled": false, "created_at": "datetime" }
```

### 2.2 `GET /scans/{scan_id}`
- **Purpose**: Get current status and summary of a single scan.
- **Auth**: Authenticated (must own the scan, or be admin)
- **Client**: Both
- **Response** `200`:
```json
{
  "scan_id": "uuid",
  "user_id": "uuid",
  "target": "string",
  "status": "PENDING|IN_PROGRESS|COMPLETED|FAILED|CANCELLED",
  "active_testing_enabled": true,
  "authorization_justification": "string",
  "started_at": "datetime|null",
  "completed_at": "datetime|null",
  "created_at": "datetime",
  "vuln_count_by_severity": { "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0 }
}
```

### 2.3 `GET /scans`
- **Purpose**: List scans (history) for the current user, or all scans if admin, with filtering.
- **Auth**: Authenticated
- **Client**: Both (Web adds trend/history views on top of this)
- **Query params**: `status`, `target` (partial match), `date_from`, `date_to`, `page`, `page_size`
- **Response** `200`: paginated wrapper of the 2.2 shape (summary form, without `vuln_count_by_severity` breakdown to keep the list endpoint light — full detail via 2.2).

### 2.4 `POST /scans/{scan_id}/cancel`
- **Purpose**: Cancel an in-progress scan.
- **Auth**: Authenticated (owner or admin)
- **Client**: Both
- **Request**: none
- **Response** `200`: `{ "scan_id": "uuid", "status": "CANCELLED" }`
- Notes: if the scan is already `COMPLETED`/`FAILED`/`CANCELLED`, returns `409 Conflict`.

---

## 3. Vulnerabilities

### 3.1 `GET /scans/{scan_id}/vulnerabilities`
- **Purpose**: List/filter the threat matrix for a specific scan.
- **Auth**: Authenticated (owner or admin)
- **Client**: Both (Web: full filter/sort UI; Mobile: simplified list, mainly for critical alerts)
- **Query params**: `severity` (comma-separated list), `status`, `min_confidence`, `cve_id`, `sort_by` (`severity|cvss_score|discovered_at`), `sort_dir`, `page`, `page_size`
- **Response** `200`: paginated wrapper of:
```json
{
  "vuln_id": "uuid",
  "scan_id": "uuid",
  "cve_id": "string|null",
  "host": "string",
  "port": 0,
  "service_name": "string|null",
  "service_version": "string|null",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
  "cvss_score": 0.0,
  "confidence_score": 0.0,
  "status": "OPEN|REMEDIATED|ACCEPTED_RISK|FALSE_POSITIVE",
  "discovered_at": "datetime"
}
```

### 3.2 `GET /vulnerabilities/{vuln_id}`
- **Purpose**: Full detail for a single finding, including AI reasoning and linked CVE.
- **Auth**: Authenticated (owner of parent scan, or admin)
- **Client**: Both
- **Response** `200`:
```json
{
  "vuln_id": "uuid",
  "scan_id": "uuid",
  "host": "string",
  "port": 0,
  "service_name": "string|null",
  "service_version": "string|null",
  "severity": "string",
  "cvss_score": 0.0,
  "confidence_score": 0.0,
  "ai_reasoning": "string|null",
  "status": "string",
  "discovered_at": "datetime",
  "cve": { "cve_id": "string", "description": "string", "cvss_v3_score": 0.0, "severity": "string" } ,
  "related_threat_logs": [ /* Threat_Logs summary objects, see 4.1 */ ]
}
```

### 3.3 `PATCH /vulnerabilities/{vuln_id}`
- **Purpose**: Update a finding's disposition (e.g. mark accepted risk or false positive) after human review.
- **Auth**: Authenticated (owner or admin)
- **Client**: Web
- **Request body**: `{ "status": "REMEDIATED|ACCEPTED_RISK|FALSE_POSITIVE" }`
- **Response** `200`: updated object per 3.2 (summary fields).

---

## 4. Threat Logs (Active Testing)

### 4.1 `GET /scans/{scan_id}/threat-logs`
- **Purpose**: List/filter active-testing attempts for a scan.
- **Auth**: Authenticated (owner or admin)
- **Client**: Web (primary review surface for active test evidence)
- **Query params**: `attack_type` (`SQLI|XSS`), `ai_verified` (bool), `risk_rating`, `page`, `page_size`
- **Response** `200`: paginated wrapper of:
```json
{
  "log_id": "uuid",
  "scan_id": "uuid",
  "vuln_id": "uuid|null",
  "attack_type": "SQLI|XSS",
  "target_url": "string",
  "target_param": "string|null",
  "payload_used": "string",
  "ai_verified": true,
  "verification_notes": "string|null",
  "risk_rating": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
  "executed_at": "datetime"
}
```

### 4.2 `GET /threat-logs/{log_id}`
- **Purpose**: Full detail on a single active-test attempt (e.g. for evidentiary review before approving a related remediation).
- **Auth**: Authenticated (owner or admin)
- **Client**: Web
- **Response** `200`: same shape as 4.1 item.

---

## 5. Remediation

### 5.1 `POST /vulnerabilities/{vuln_id}/remediations`
- **Purpose**: Trigger AI generation of a remediation (executive summary + technical script) for a finding. Always created as `PENDING` — never auto-executes.
- **Auth**: Authenticated (owner or admin)
- **Client**: Web
- **Request body**: `{ "target_os": "string (optional hint, e.g. 'ubuntu-22.04')" }`
- **Response** `201`:
```json
{
  "remediation_id": "uuid",
  "vuln_id": "uuid",
  "target_os": "string|null",
  "executive_summary": "string",
  "technical_script": "string",
  "ai_confidence": 0.0,
  "status": "PENDING",
  "created_at": "datetime"
}
```

### 5.2 `GET /remediations/{remediation_id}`
- **Purpose**: Full review view of a remediation (used by web reviewer, and by mobile for a lightweight approve/reject summary).
- **Auth**: Authenticated (owner or admin)
- **Client**: Both
- **Response** `200`: same shape as 5.1 response, plus `reviewed_by`, `reviewed_at`, `executed_at`.

### 5.3 `GET /scans/{scan_id}/remediations`
- **Purpose**: List all remediations tied to findings in a scan (for the web remediation review queue).
- **Auth**: Authenticated (owner or admin)
- **Client**: Web
- **Query params**: `status`, `page`, `page_size`
- **Response** `200`: paginated wrapper of 5.1-shaped summaries.

### 5.4 `POST /remediations/{remediation_id}/approve`
- **Purpose**: Human approves a reviewed remediation. Full script review is expected to have happened on web; this endpoint just records the decision.
- **Auth**: Authenticated (owner or admin) — this is the human-in-the-loop gate; role/ownership rules should be tightened per your access-control policy (e.g. restrict to `analyst`/`admin` only, not `client`)
- **Client**: Both (full review happens on Web; Mobile can call this only for remediations already marked reviewed, per your design principle)
- **Request body**: none required (reviewer identity comes from JWT)
- **Response** `200`: `{ "remediation_id": "uuid", "status": "APPROVED", "reviewed_by": "uuid", "reviewed_at": "datetime" }`

### 5.5 `POST /remediations/{remediation_id}/reject`
- **Purpose**: Human rejects a remediation (e.g. script judged unsafe or irrelevant).
- **Auth**: Authenticated (owner or admin)
- **Client**: Both
- **Request body**: `{ "reason": "string (optional)" }`
- **Response** `200`: `{ "remediation_id": "uuid", "status": "REJECTED", "reviewed_by": "uuid", "reviewed_at": "datetime" }`

### 5.6 `POST /remediations/{remediation_id}/mark-executed`
- **Purpose**: Record that an approved remediation script was actually run (execution itself happens out-of-band, e.g. manually by the client's ops team or a separately authorized runner — this endpoint just logs completion).
- **Auth**: Authenticated (owner or admin); should only succeed if current `status = APPROVED`
- **Client**: Web
- **Request body**: none
- **Response** `200`: `{ "remediation_id": "uuid", "status": "EXECUTED", "executed_at": "datetime" }`
- Returns `409 Conflict` if the remediation is not currently `APPROVED`.

---

## 6. Config & CVE Management (Admin)

### 6.1 `GET /admin/config`
- **Purpose**: List all tunable config values (e.g. AI confidence thresholds).
- **Auth**: Admin
- **Client**: Web
- **Response** `200`: array of `{ "config_id": "uuid", "config_key": "string", "config_value": "string", "description": "string|null", "updated_at": "datetime" }`

### 6.2 `PATCH /admin/config/{config_key}`
- **Purpose**: Update a config value at runtime (tunes AI reasoning thresholds without backend restart).
- **Auth**: Admin
- **Client**: Web
- **Request body**: `{ "config_value": "string" }`
- **Response** `200`: updated config object, `updated_by` set to caller.

### 6.3 `GET /admin/cve-definitions`
- **Purpose**: Browse/search the locally cached CVE database.
- **Auth**: Admin
- **Client**: Web
- **Query params**: `cve_id`, `severity`, `min_cvss`, `page`, `page_size`
- **Response** `200`: paginated wrapper of `CVE_Definitions` rows (per Task 1 schema, minus `raw_data` in list view).

### 6.4 `GET /admin/cve-definitions/{cve_id}`
- **Purpose**: Full detail on one CVE, including raw NVD payload.
- **Auth**: Admin
- **Client**: Web
- **Response** `200`: full `CVE_Definitions` row including `raw_data`.

### 6.5 `POST /admin/cve-definitions/sync`
- **Purpose**: Manually trigger an out-of-cycle NVD sync (in addition to the scheduled background job).
- **Auth**: Admin
- **Client**: Web
- **Request body**: `{ "since": "datetime (optional, defaults to last sync)" }`
- **Response** `202 Accepted`: `{ "sync_job_id": "uuid", "status": "STARTED" }`

---

## 7. WebSocket — Live Scan Status

### Connection
`WSS /ws/scans/{scan_id}?token={access_token}`
- **Auth**: Authenticated (token passed as query param since browsers/Flutter WebSocket clients can't always set headers) — validated against the same JWT used for REST; connection is rejected with close code `4001` if invalid or if the caller doesn't own the scan (and isn't admin).
- **Client**: Both — Flutter subscribes for push-alert-worthy status; Web subscribes to live-update the threat matrix in place.
- One socket per scan; client reconnects per scan_id as needed (e.g. user reopens the app on a scan still in progress).

### Message envelope (server → client)
All messages share this envelope:
```json
{ "event": "string", "scan_id": "uuid", "timestamp": "datetime", "data": { } }
```

### Message types, in the order they'd typically appear across a scan lifecycle

**1. `scan.status_changed`** — sent whenever `Scans.status` transitions.
```json
{ "event": "scan.status_changed", "scan_id": "uuid", "timestamp": "datetime",
  "data": { "status": "IN_PROGRESS" } }
```

**2. `recon.progress`** — periodic updates during nmap host discovery/port enum/banner grabbing.
```json
{ "event": "recon.progress", "scan_id": "uuid", "timestamp": "datetime",
  "data": { "stage": "host_discovery|port_scan|banner_grab", "percent_complete": 42, "hosts_found": 3, "ports_found": 12 } }
```

**3. `vulnerability.discovered`** — sent each time AI triage writes a new row to `Vulnerabilities` (streamed incrementally rather than only at the end, so the web threat matrix fills in live).
```json
{ "event": "vulnerability.discovered", "scan_id": "uuid", "timestamp": "datetime",
  "data": { "vuln_id": "uuid", "severity": "CRITICAL", "host": "string", "port": 443,
            "service_name": "string", "confidence_score": 0.91 } }
```

**4. `alert.critical`** — a narrower, high-signal event fired in addition to (3) specifically when `severity = CRITICAL`, so Flutter can key its push notification off this event alone rather than filtering every `vulnerability.discovered` message client-side.
```json
{ "event": "alert.critical", "scan_id": "uuid", "timestamp": "datetime",
  "data": { "vuln_id": "uuid", "host": "string", "service_name": "string",
            "summary": "string (short human-readable line for the push notification)" } }
```

**5. `active_test.attempt`** — sent only if `active_testing_enabled = true`, once per payload attempt logged to `Threat_Logs`.
```json
{ "event": "active_test.attempt", "scan_id": "uuid", "timestamp": "datetime",
  "data": { "log_id": "uuid", "attack_type": "SQLI", "target_url": "string",
            "ai_verified": true, "risk_rating": "HIGH" } }
```

**6. `scan.completed`** — final message for a successful scan; includes the summary counts also available via `GET /scans/{scan_id}`.
```json
{ "event": "scan.completed", "scan_id": "uuid", "timestamp": "datetime",
  "data": { "status": "COMPLETED", "vuln_count_by_severity": { "CRITICAL": 1, "HIGH": 3, "MEDIUM": 5, "LOW": 2, "INFO": 0 } } }
```

**7. `scan.failed`** — sent if recon or triage errors out unrecoverably.
```json
{ "event": "scan.failed", "scan_id": "uuid", "timestamp": "datetime",
  "data": { "status": "FAILED", "error_message": "string" } }
```

### Client → server messages
The socket is otherwise server-push only. The one client-initiated message is a heartbeat/keepalive:
```json
{ "event": "ping" }
```
Server replies `{ "event": "pong", "timestamp": "datetime" }`. No other client-to-server business logic goes over this socket — actions like cancel or approve remain REST calls (2.4, 5.4, 5.5) so they stay auditable, rate-limitable, and consistent with the "all business logic lives in FastAPI, clients are thin" principle.

---

## 8. Summary Table (quick reference)

| Method & Path | Purpose | Client | Auth |
|---|---|---|---|
| POST /auth/register | Create account | Both | Public |
| POST /auth/login | Login, get tokens | Both | Public |
| POST /auth/refresh | Refresh access token | Both | Public |
| POST /auth/logout | Invalidate refresh token | Both | Authenticated |
| GET /auth/me | Current user profile | Both | Authenticated |
| POST /auth/users | Admin-create a user | Web | Admin |
| POST /scans | Submit new scan | Both | Authenticated |
| GET /scans/{id} | Scan status/summary | Both | Authenticated |
| GET /scans | List/filter scans | Both | Authenticated |
| POST /scans/{id}/cancel | Cancel in-progress scan | Both | Authenticated |
| GET /scans/{id}/vulnerabilities | List findings for scan | Both | Authenticated |
| GET /vulnerabilities/{id} | Finding detail | Both | Authenticated |
| PATCH /vulnerabilities/{id} | Update finding disposition | Web | Authenticated |
| GET /scans/{id}/threat-logs | List active-test attempts | Web | Authenticated |
| GET /threat-logs/{id} | Active-test attempt detail | Web | Authenticated |
| POST /vulnerabilities/{id}/remediations | Generate remediation | Web | Authenticated |
| GET /remediations/{id} | Remediation detail | Both | Authenticated |
| GET /scans/{id}/remediations | List remediations for scan | Web | Authenticated |
| POST /remediations/{id}/approve | Approve remediation | Both | Authenticated |
| POST /remediations/{id}/reject | Reject remediation | Both | Authenticated |
| POST /remediations/{id}/mark-executed | Mark remediation executed | Web | Authenticated |
| GET /admin/config | List config values | Web | Admin |
| PATCH /admin/config/{key} | Update config value | Web | Admin |
| GET /admin/cve-definitions | Browse CVE cache | Web | Admin |
| GET /admin/cve-definitions/{cve_id} | CVE detail | Web | Admin |
| POST /admin/cve-definitions/sync | Manual NVD sync | Web | Admin |
| WSS /ws/scans/{id} | Live scan status stream | Both | Authenticated |

---

### Design notes worth flagging back to you
- **5.4/5.5 auth**: I scoped approve/reject to "owner or admin," matching your other endpoints, but your spec says approval is a human-review gate — you may want to restrict this specifically to `analyst`/`admin` roles and exclude plain `client` accounts, depending on who's meant to hold approval authority in your threat model. Worth deciding explicitly rather than defaulting to ownership.
- **Streaming vs. batch triage events**: I modeled `vulnerability.discovered` as fired per-finding as triage completes, not just once at the end — this matches "live-updated via WebSocket" in your Flow 1, but adds complexity (partial results mid-scan). If you'd rather batch it, collapse (3) into a single `triage.completed` event carrying the full findings array.
