# Vulnara — Foundation Documents

## 1. Abstract

Vulnara is an AI-augmented vulnerability intelligence platform that automates the core workflow of a junior penetration tester within a strict, human-gated authorization model. The system employs a three-tier architecture — a Flutter mobile app for action-oriented monitoring and approvals, a React/Vite web app for data-dense analysis, and a FastAPI backend that centralizes all business logic — communicating over a shared REST and WebSocket API. Given an explicitly authorized target, Vulnara performs host discovery, port enumeration, and banner grabbing via nmap, then normalizes the raw telemetry and passes it to an AI reasoning layer that cross-references service and version data against the NVD CVE database to score severity, assign confidence, and filter false positives into a prioritized threat matrix. Users may opt in, per scan, to controlled active testing of common web vulnerabilities (SQLi, XSS), with AI-verified exploitation rather than pattern matching alone. For confirmed findings, the system generates dual-output remediation — an executive summary and a technical script — that remains pending until a human reviewer approves execution. Every AI output carries an explicit confidence rating and is never presented as certain. Built entirely on free-tier infrastructure suitable for real client handover, Vulnara demonstrates how AI can accelerate vulnerability triage and remediation while keeping authorization, scope, and execution decisions firmly under human control.

---

## 2. System Architecture — Component List and Data Flow

### Components

| Component | Role |
|---|---|
| **Flutter App (Android)** | Thin client: trigger scans, confirm authorization, view live scan status, receive push alerts on critical findings, approve/reject remediation already reviewed on web. |
| **React + Vite Web App** | Thin client: full threat matrix (filter/sort), scan history & trend comparison, full remediation script review, system config/CVE management. |
| **FastAPI Backend** | Single source of truth for all business logic. Exposes REST (CRUD, triggers) + WebSocket (live scan status, push events). Orchestrates nmap, AI calls, NVD sync, and remediation lifecycle. |
| **nmap Module** | Executes host discovery, port enumeration, banner grabbing, and (opt-in) the custom active-testing payload module. Runs with root access on the Oracle VM for raw sockets. |
| **Gemini API (AI reasoning layer)** | Consumes normalized scan telemetry; performs CVE cross-referencing, severity/CVSS/confidence scoring, false-positive filtering, active-test result verification, and remediation script synthesis. |
| **NVD API** | External source of CVE definitions; periodically synced into `CVE_Definitions` to keep AI reasoning current without backend restarts. |
| **Neon (Postgres)** | Serverless, auto-waking persistent store for scans, vulnerabilities, logs, config, CVEs, remediations, and users. |
| **Ollama (optional, self-hosted)** | Offline fallback AI reasoning layer if Gemini free-tier quota is exhausted or unavailable. |

### End-to-End Data Flow for a Single Scan

**Step 1 — Target submission & authorization gate (Flutter or Web → FastAPI)**
- User authenticates (JWT session against `Users` table).
- User submits target (domain/IP) and explicitly confirms authorization (checkbox + justification text — this is a required, logged field, not a formality).
- FastAPI validates the request, writes a new row to `Scans` with `status = PENDING`, `authorization_confirmed = TRUE`, and the justification text. If authorization is not confirmed, the request is rejected before any scan logic runs.

**Step 2 — Recon execution (FastAPI → nmap module)**
- FastAPI spawns the nmap module (host discovery → port enumeration → banner grabbing) as an async task/subprocess on the Oracle VM.
- `Scans.status` transitions to `IN_PROGRESS`.
- Progress events are pushed to connected clients over WebSocket (both Flutter and Web subscribe to the same scan channel).

**Step 3 — Raw telemetry normalization (nmap module → FastAPI)**
- Raw nmap output (open ports, service names, versions, banners) is parsed into structured JSON by the backend.
- This normalized payload is staged in memory/temp storage, not yet written as findings — it is the input to the AI triage step.

**Step 4 — AI triage (FastAPI → Gemini API → NVD-backed `CVE_Definitions`)**
- FastAPI sends the normalized service/version data to Gemini, along with relevant cached CVE context pulled from `CVE_Definitions` (kept current via the independent NVD sync flow, Step 4-config below).
- Gemini cross-references services/versions against CVE data, assigns CVSS/severity/confidence, and filters out low-confidence/noisy false positives.
- FastAPI writes the resulting prioritized findings to `Vulnerabilities`, each linked to `Scans` (via `scan_id`) and optionally to `CVE_Definitions` (via `cve_id`).
- `Scans.status` transitions toward `COMPLETED` once triage finishes (assuming active testing is not also enabled).

**Step 4a — CVE sync (independent, scheduled flow, not per-scan)**
- A background job in FastAPI periodically calls the NVD API, upserts new/changed CVE records into `CVE_Definitions`, and can adjust AI reasoning thresholds stored in `Configurations` — all without restarting the backend.

**Step 5 — Active testing, opt-in (FastAPI → nmap/custom payload module → Gemini → `Threat_Logs`)**
- Only if the user explicitly enabled `active_testing_enabled` at scan submission.
- The custom payload module fires rate-limited SQLi/XSS-style payloads at discovered forms/params.
- Raw responses are sent to Gemini, which verifies actual reflection/execution (not just string matching).
- Each attempt (verified or not) is logged to `Threat_Logs`, linked to `Scans` and, if it corresponds to a known finding, to `Vulnerabilities`.

**Step 6 — Live status & alerts (FastAPI → Flutter/Web via WebSocket)**
- Throughout Steps 2–5, FastAPI pushes status deltas and critical-finding alerts over WebSocket. Flutter surfaces push notifications for critical severity; Web updates the live threat matrix view in place.

**Step 7 — Remediation (Web → FastAPI → Gemini → `Remediations` → Flutter/Web approval)**
- On the web app, a user selects a finding in `Vulnerabilities` and triggers "generate fix."
- FastAPI sends the vulnerability context (service, version, CVE, target OS) to Gemini, which synthesizes a technical script and an executive summary.
- A new row is written to `Remediations` with `status = PENDING`, linked to the finding via `vuln_id`.
- A human reviews the full script on the web app (data-dense surface) and approves/rejects; Flutter can surface a lightweight approve/reject action for remediation already reviewed on web.
- On approval, `Remediations.status` moves to `APPROVED`, `reviewed_by`/`reviewed_at` are stamped, and execution (external to this diagram's scope — a controlled, separately authorized action) updates `status` to `EXECUTED`.

This sequence (Steps 1→7) is what should be rendered as the primary sequence/flow diagram: **User → FastAPI → nmap → FastAPI (normalize) → Gemini (+ NVD-backed CVE_Definitions) → Postgres (Vulnerabilities) → [optional: active testing → Threat_Logs] → WebSocket push → Remediation request → Gemini → Postgres (Remediations) → human approval.**

---

## 3. Logical Database Schema (Postgres / Neon)

### 3.1 Users

| Field | Type | Constraints | Purpose |
|---|---|---|---|
| user_id | UUID | PK, DEFAULT gen_random_uuid() | Unique user identifier |
| email | VARCHAR(255) | NOT NULL, UNIQUE | Login identifier |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt/argon2 hash, never plaintext |
| full_name | VARCHAR(255) | NOT NULL | Display name |
| role | VARCHAR(20) | NOT NULL, CHECK IN ('admin','analyst','client') | Access control tier |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Soft-disable without deleting account |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Account creation time |
| last_login_at | TIMESTAMPTZ | NULLABLE | Session/audit tracking |

### 3.2 Scans

| Field | Type | Constraints | Purpose |
|---|---|---|---|
| scan_id | UUID | PK, DEFAULT gen_random_uuid() | Unique scan identifier |
| user_id | UUID | FK → Users(user_id), NOT NULL | Who initiated the scan |
| target | VARCHAR(255) | NOT NULL | Domain or IP scanned |
| authorization_confirmed | BOOLEAN | NOT NULL, DEFAULT FALSE | Gate: scan cannot start unless TRUE |
| authorization_justification | TEXT | NOT NULL | Logged reason/proof of permission |
| active_testing_enabled | BOOLEAN | NOT NULL, DEFAULT FALSE | Opt-in flag for SQLi/XSS testing |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'PENDING', CHECK IN ('PENDING','IN_PROGRESS','COMPLETED','FAILED','CANCELLED') | Scan lifecycle state |
| started_at | TIMESTAMPTZ | NULLABLE | Recon start time |
| completed_at | TIMESTAMPTZ | NULLABLE | Recon/triage end time |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Record creation time |

### 3.3 CVE_Definitions

| Field | Type | Constraints | Purpose |
|---|---|---|---|
| cve_id | VARCHAR(20) | PK | e.g. "CVE-2023-12345" |
| description | TEXT | NOT NULL | NVD-provided description |
| cvss_v3_score | NUMERIC(3,1) | NULLABLE | Base CVSS score |
| severity | VARCHAR(10) | NULLABLE, CHECK IN ('CRITICAL','HIGH','MEDIUM','LOW','NONE') | NVD-derived severity band |
| published_date | TIMESTAMPTZ | NULLABLE | Original NVD publish date |
| last_modified_date | TIMESTAMPTZ | NULLABLE | Last NVD update |
| source | VARCHAR(20) | NOT NULL, DEFAULT 'NVD' | Data provenance |
| raw_data | JSONB | NULLABLE | Full NVD record for audit/reprocessing |
| synced_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Last local sync timestamp |

### 3.4 Vulnerabilities

| Field | Type | Constraints | Purpose |
|---|---|---|---|
| vuln_id | UUID | PK, DEFAULT gen_random_uuid() | Unique finding identifier |
| scan_id | UUID | FK → Scans(scan_id), NOT NULL | Which scan produced this finding |
| cve_id | VARCHAR(20) | FK → CVE_Definitions(cve_id), NULLABLE | Matched CVE, if any (AI findings may not always map 1:1) |
| host | VARCHAR(255) | NOT NULL | Affected host within target scope |
| port | INTEGER | NULLABLE | Affected port |
| service_name | VARCHAR(100) | NULLABLE | e.g. "Apache httpd" |
| service_version | VARCHAR(100) | NULLABLE | Detected version from banner |
| severity | VARCHAR(10) | NOT NULL, CHECK IN ('CRITICAL','HIGH','MEDIUM','LOW','INFO') | AI-assigned severity |
| cvss_score | NUMERIC(3,1) | NULLABLE | AI-assigned or CVE-inherited score |
| confidence_score | NUMERIC(3,2) | NOT NULL, CHECK (confidence_score BETWEEN 0 AND 1) | Mandatory AI confidence rating |
| ai_reasoning | TEXT | NULLABLE | Explanation of why this was flagged |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'OPEN', CHECK IN ('OPEN','REMEDIATED','ACCEPTED_RISK','FALSE_POSITIVE') | Finding lifecycle state |
| discovered_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | When AI triage produced this finding |

### 3.5 Threat_Logs

| Field | Type | Constraints | Purpose |
|---|---|---|---|
| log_id | UUID | PK, DEFAULT gen_random_uuid() | Unique log entry |
| scan_id | UUID | FK → Scans(scan_id), NOT NULL | Which scan this active test belongs to |
| vuln_id | UUID | FK → Vulnerabilities(vuln_id), NULLABLE | Linked finding, if the test confirmed one |
| attack_type | VARCHAR(20) | NOT NULL, CHECK IN ('SQLI','XSS') | Type of active test performed |
| target_url | TEXT | NOT NULL | Form/endpoint tested |
| target_param | VARCHAR(255) | NULLABLE | Specific parameter tested |
| payload_used | TEXT | NOT NULL | Exact payload sent (for audit/reproducibility) |
| ai_verified | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether Gemini confirmed real reflection/execution |
| verification_notes | TEXT | NULLABLE | AI's reasoning for verification result |
| risk_rating | VARCHAR(10) | NOT NULL, CHECK IN ('CRITICAL','HIGH','MEDIUM','LOW','INFO') | Severity of confirmed test |
| executed_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | When the payload was fired |

### 3.6 Configurations

| Field | Type | Constraints | Purpose |
|---|---|---|---|
| config_id | UUID | PK, DEFAULT gen_random_uuid() | Unique config entry |
| config_key | VARCHAR(100) | NOT NULL, UNIQUE | e.g. "ai_confidence_threshold" |
| config_value | TEXT | NOT NULL | Value (parsed by app as needed) |
| description | TEXT | NULLABLE | Human-readable explanation |
| updated_by | UUID | FK → Users(user_id), NULLABLE | Who last changed this setting |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Last change timestamp |

### 3.7 Remediations

| Field | Type | Constraints | Purpose |
|---|---|---|---|
| remediation_id | UUID | PK, DEFAULT gen_random_uuid() | Unique remediation record |
| vuln_id | UUID | FK → Vulnerabilities(vuln_id), NOT NULL | Finding this remediation addresses |
| target_os | VARCHAR(100) | NULLABLE | OS the script is tailored for |
| executive_summary | TEXT | NOT NULL | Non-technical explanation output |
| technical_script | TEXT | NOT NULL | AI-generated patch/script |
| ai_confidence | NUMERIC(3,2) | NOT NULL, CHECK (ai_confidence BETWEEN 0 AND 1) | Confidence in the proposed fix |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'PENDING', CHECK IN ('PENDING','APPROVED','REJECTED','EXECUTED') | Approval lifecycle — never auto-executes |
| reviewed_by | UUID | FK → Users(user_id), NULLABLE | Human approver |
| reviewed_at | TIMESTAMPTZ | NULLABLE | Approval/rejection timestamp |
| executed_at | TIMESTAMPTZ | NULLABLE | Execution timestamp, if executed |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | When AI generated the remediation |

### 3.8 Relationships Summary

- `Users.user_id` → `Scans.user_id` (1:N — a user initiates many scans)
- `Users.user_id` → `Configurations.updated_by` (1:N — audit trail of config changes)
- `Users.user_id` → `Remediations.reviewed_by` (1:N — audit trail of approvals)
- `Scans.scan_id` → `Vulnerabilities.scan_id` (1:N — one scan produces many findings)
- `Scans.scan_id` → `Threat_Logs.scan_id` (1:N — one scan produces many active-test attempts)
- `CVE_Definitions.cve_id` → `Vulnerabilities.cve_id` (1:N, nullable — a CVE can appear across many findings; not every finding maps to a CVE)
- `Vulnerabilities.vuln_id` → `Threat_Logs.vuln_id` (1:N, nullable — a confirmed finding may have multiple related active-test log entries)
- `Vulnerabilities.vuln_id` → `Remediations.vuln_id` (1:N — a finding can have multiple remediation attempts over time, e.g. rejected then regenerated)

---

## 4. Raw SQL (Postgres / Neon-ready)

```sql
-- Enable UUID generation (Neon/Postgres 13+ has gen_random_uuid() via pgcrypto)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================
-- Users
-- ============================================
CREATE TABLE Users (
    user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('admin','analyst','client')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);

-- ============================================
-- Scans
-- ============================================
CREATE TABLE Scans (
    scan_id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                         UUID NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    target                          VARCHAR(255) NOT NULL,
    authorization_confirmed         BOOLEAN NOT NULL DEFAULT FALSE,
    authorization_justification     TEXT NOT NULL,
    active_testing_enabled          BOOLEAN NOT NULL DEFAULT FALSE,
    status                          VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                                        CHECK (status IN ('PENDING','IN_PROGRESS','COMPLETED','FAILED','CANCELLED')),
    started_at                      TIMESTAMPTZ,
    completed_at                    TIMESTAMPTZ,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_scans_user_id ON Scans(user_id);
CREATE INDEX idx_scans_status ON Scans(status);

-- ============================================
-- CVE_Definitions
-- ============================================
CREATE TABLE CVE_Definitions (
    cve_id              VARCHAR(20) PRIMARY KEY,
    description         TEXT NOT NULL,
    cvss_v3_score       NUMERIC(3,1),
    severity            VARCHAR(10) CHECK (severity IN ('CRITICAL','HIGH','MEDIUM','LOW','NONE')),
    published_date      TIMESTAMPTZ,
    last_modified_date  TIMESTAMPTZ,
    source              VARCHAR(20) NOT NULL DEFAULT 'NVD',
    raw_data            JSONB,
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cve_severity ON CVE_Definitions(severity);

-- ============================================
-- Vulnerabilities
-- ============================================
CREATE TABLE Vulnerabilities (
    vuln_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id             UUID NOT NULL REFERENCES Scans(scan_id) ON DELETE CASCADE,
    cve_id              VARCHAR(20) REFERENCES CVE_Definitions(cve_id) ON DELETE SET NULL,
    host                VARCHAR(255) NOT NULL,
    port                INTEGER,
    service_name        VARCHAR(100),
    service_version     VARCHAR(100),
    severity            VARCHAR(10) NOT NULL CHECK (severity IN ('CRITICAL','HIGH','MEDIUM','LOW','INFO')),
    cvss_score          NUMERIC(3,1),
    confidence_score    NUMERIC(3,2) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    ai_reasoning        TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'OPEN'
                            CHECK (status IN ('OPEN','REMEDIATED','ACCEPTED_RISK','FALSE_POSITIVE')),
    discovered_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vuln_scan_id ON Vulnerabilities(scan_id);
CREATE INDEX idx_vuln_cve_id ON Vulnerabilities(cve_id);
CREATE INDEX idx_vuln_severity ON Vulnerabilities(severity);
CREATE INDEX idx_vuln_status ON Vulnerabilities(status);

-- ============================================
-- Threat_Logs
-- ============================================
CREATE TABLE Threat_Logs (
    log_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id             UUID NOT NULL REFERENCES Scans(scan_id) ON DELETE CASCADE,
    vuln_id             UUID REFERENCES Vulnerabilities(vuln_id) ON DELETE SET NULL,
    attack_type         VARCHAR(20) NOT NULL CHECK (attack_type IN ('SQLI','XSS')),
    target_url          TEXT NOT NULL,
    target_param        VARCHAR(255),
    payload_used        TEXT NOT NULL,
    ai_verified         BOOLEAN NOT NULL DEFAULT FALSE,
    verification_notes  TEXT,
    risk_rating         VARCHAR(10) NOT NULL CHECK (risk_rating IN ('CRITICAL','HIGH','MEDIUM','LOW','INFO')),
    executed_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_threatlogs_scan_id ON Threat_Logs(scan_id);
CREATE INDEX idx_threatlogs_vuln_id ON Threat_Logs(vuln_id);

-- ============================================
-- Configurations
-- ============================================
CREATE TABLE Configurations (
    config_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key      VARCHAR(100) NOT NULL UNIQUE,
    config_value    TEXT NOT NULL,
    description     TEXT,
    updated_by      UUID REFERENCES Users(user_id) ON DELETE SET NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================
-- Remediations
-- ============================================
CREATE TABLE Remediations (
    remediation_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vuln_id             UUID NOT NULL REFERENCES Vulnerabilities(vuln_id) ON DELETE CASCADE,
    target_os           VARCHAR(100),
    executive_summary   TEXT NOT NULL,
    technical_script    TEXT NOT NULL,
    ai_confidence       NUMERIC(3,2) NOT NULL CHECK (ai_confidence BETWEEN 0 AND 1),
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                            CHECK (status IN ('PENDING','APPROVED','REJECTED','EXECUTED')),
    reviewed_by         UUID REFERENCES Users(user_id) ON DELETE SET NULL,
    reviewed_at         TIMESTAMPTZ,
    executed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_remediations_vuln_id ON Remediations(vuln_id);
CREATE INDEX idx_remediations_status ON Remediations(status);
```

### Notes on the SQL
- All PKs use `gen_random_uuid()` (via `pgcrypto`, already available on Neon) rather than serial IDs — better for a distributed client/mobile sync model and avoids leaking row counts.
- `ON DELETE CASCADE` is used where child records are meaningless without the parent (e.g., a `Vulnerabilities` row without its `Scans` row). `ON DELETE SET NULL` is used where the link is informational and the child record should persist for audit purposes (e.g., a `Remediation` should survive even if the reviewing user's account is later deleted).
- CHECK constraints stand in for Postgres ENUM types — easier to alter later (`ALTER TABLE ... DROP CONSTRAINT / ADD CONSTRAINT`) without the `ALTER TYPE` migration friction that native enums require, which matters for a project still evolving its status vocab.
- `confidence_score` / `ai_confidence` are constrained to `[0,1]` to structurally enforce the non-negotiable "AI outputs always carry a confidence rating" design principle at the database level, not just in application code.
