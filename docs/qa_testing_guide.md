# Vulnara — QA Feature Testing Guide

> **Purpose:** Step-by-step manual testing of every screen, form, button, and edge-case in both the **Web App** and the **Flutter Mobile App**. Use this as a checklist — tick off each item and note `✅ PASS` or `❌ FAIL (notes)`.

---

## Table of Contents

1. [Environment & Credentials](#1-environment--credentials)
2. [WEB APP — Full Feature Walkthrough](#2-web-app--full-feature-walkthrough)
   - [2.1 Authentication (Login / Register / Logout)](#21-authentication-login--register--logout)
   - [2.2 Dashboard](#22-dashboard)
   - [2.3 Scans List](#23-scans-list)
   - [2.4 New Scan — Form & Validation](#24-new-scan--form--validation)
   - [2.5 Scan Detail — 4 Tabs](#25-scan-detail--4-tabs)
   - [2.6 Vulnerability Detail](#26-vulnerability-detail)
   - [2.7 Remediation Queue](#27-remediation-queue)
   - [2.8 Remediation Review](#28-remediation-review)
   - [2.9 Profile Settings](#29-profile-settings)
   - [2.10 Admin — User Management](#210-admin--user-management)
   - [2.11 Admin — Configuration](#211-admin--configuration)
   - [2.12 Admin — CVE Definitions](#212-admin--cve-definitions)
3. [MOBILE APP — Full Feature Walkthrough](#3-mobile-app--full-feature-walkthrough)
   - [3.1 Login Screen](#31-login-screen)
   - [3.2 Scan List Screen](#32-scan-list-screen)
   - [3.3 New Scan Screen](#33-new-scan-screen)
   - [3.4 Scan Status Screen](#34-scan-status-screen)
   - [3.5 Vulnerability Detail Screen](#35-vulnerability-detail-screen)
   - [3.6 Remediation List Screen](#36-remediation-list-screen)
   - [3.7 Remediation Approval Screen](#37-remediation-approval-screen)
   - [3.8 Notifications / Alerts Hub](#38-notifications--alerts-hub)
   - [3.9 Profile Screen](#39-profile-screen)
   - [3.10 Admin Users Screen (Admin only)](#310-admin-users-screen-admin-only)
   - [3.11 Audit Log Screen](#311-audit-log-screen)
4. [Cross-Cutting Tests](#4-cross-cutting-tests)
5. [Known Mock-Mode Behaviours](#5-known-mock-mode-behaviours)

---

## 1. Environment & Credentials

### Web App URL
```
http://localhost:5173/vulnara-ai/
```
*(or the deployed URL if running from a hosted server)*

### Mobile App
- Run via: `flutter run` inside `vulnara_mobile_scaffold/`
- Works on Android emulator / physical device / iOS simulator

---

### Test Accounts (Web — Mock Mode)

> **Mock Mode** is enabled when `USE_MOCK=true` is set. The login page shows an info banner. Any email/password pair will work for users already seeded.

| Role    | Email                    | Password          | Access Level                          |
|---------|--------------------------|-------------------|---------------------------------------|
| Admin   | `admin@vulnara.dev`      | `any-password`    | All pages including Admin nav items   |
| Analyst | `analyst@vulnara.dev`    | `any-password`    | Scans, vulns, remediations (no Admin) |
| Client  | `client@vulnara.dev`     | `any-password`    | View-only; can mark remediation executed |

### Self-Registration Test Data
Use these when testing the **Register** form:
- Full Name: `Test Operator`
- Email: `testoperator@example.com`
- Password: `TestPass123`
- Role: `Analyst` or `Client`

---

## 2. WEB APP — Full Feature Walkthrough

---

### 2.1 Authentication (Login / Register / Logout)

#### 2.1.1 Login Page
**URL:** `/login`

**Elements to verify:**
- [ ] Page loads with cyber-grid background animation
- [ ] Logo image renders at top
- [ ] "Login" tab is active (underlined), "Register" tab is inactive
- [ ] "Operator Email" field is present
- [ ] "Access Key" (password) field is present
- [ ] "INITIALIZE LINK" button is present
- [ ] Mock Mode info banner appears (if USE_MOCK=true)
- [ ] "Sys Status: Optimal" indicator at bottom pulses

**Test Case A — Valid Login (Admin)**

| Field          | Input                    |
|----------------|--------------------------|
| Operator Email | `admin@vulnara.dev`      |
| Access Key     | `admin-password`         |

Expected: Redirected to Dashboard `/`. Admin nav items (Users, Config, CVE) visible in sidebar.

**Test Case B — Valid Login (Analyst)**

| Field          | Input                    |
|----------------|--------------------------|
| Operator Email | `analyst@vulnara.dev`    |
| Access Key     | `analyst-pass`           |

Expected: Redirected to Dashboard `/`. No Admin nav items visible.

**Test Case C — Valid Login (Client)**

| Field          | Input                    |
|----------------|--------------------------|
| Operator Email | `client@vulnara.dev`     |
| Access Key     | `client-pass`            |

Expected: Redirected to Dashboard `/`. Limited role access.

**Test Case D — Empty Form Submission**

| Field          | Input     |
|----------------|-----------|
| Operator Email | *(blank)* |
| Access Key     | *(blank)* |

Expected: Browser native `required` validation fires; form does not submit.

**Test Case E — Invalid Email Format**

| Field          | Input        |
|----------------|--------------|
| Operator Email | `notanemail` |
| Access Key     | `anything`   |

Expected: Browser validation blocks submission (`type="email"` enforcement).

---

#### 2.1.2 Register Page
**URL:** `/register`

**Elements to verify:**
- [ ] Shield icon renders
- [ ] "NEW OPERATOR" heading displayed
- [ ] Four fields: Full Name, Email, Password, Role dropdown
- [ ] Role dropdown has two options: `Client` and `Analyst`
- [ ] Note text: *"Admin accounts are created by an existing admin"* is shown
- [ ] "CREATE ACCOUNT" button present
- [ ] "Login" tab switches back to login

**Test Case A — Valid Registration (Client role)**

| Field     | Input                       |
|-----------|-----------------------------|
| Full Name | `Jane Operator`             |
| Email     | `jane.test@company.com`     |
| Password  | `SecurePass99`              |
| Role      | `Client — view findings...` |

Expected: Account created → auto-logged in → redirected to Dashboard.

**Test Case B — Valid Registration (Analyst role)**

| Field     | Input                      |
|-----------|----------------------------|
| Full Name | `Bob Analyst`              |
| Email     | `bob.analyst@security.com` |
| Password  | `Analyst!Pass1`            |
| Role      | `Analyst — run scans...`   |

Expected: Account created → auto-logged in → redirected to Dashboard.

**Test Case C — Missing Fields**

| Field     | Input     |
|-----------|-----------|
| Full Name | *(blank)* |
| Email     | *(blank)* |
| Password  | *(blank)* |

Expected: `required` validation fires on all empty fields.

**Test Case D — Invalid Email**

| Field | Input          |
|-------|----------------|
| Email | `bademail.com` |

Expected: Browser email validation blocks submission.

---

#### 2.1.3 Logout

- [ ] Click user avatar / name in sidebar → Logout option
- [ ] After logout: redirected to `/login`
- [ ] Navigating back to `/` while logged out → redirected to `/login`

---

### 2.2 Dashboard

**URL:** `/` (after login)

**Elements to verify:**
- [ ] "Global Analytics Overview" heading
- [ ] "New Scan" button in top-right — clicking navigates to `/scans/new`
- [ ] **4 KPI cards** displayed:
  - Total Scans (shows a number)
  - Scans In Progress
  - Open Critical Findings (red border)
  - Remediations Pending
- [ ] **Findings by Severity** — Pie/donut chart renders with legend (CRITICAL, HIGH, MEDIUM, LOW, INFO)
- [ ] **Findings per scan (trend)** — Bar chart with last 6 completed scans
- [ ] **Recent Scans** table — shows Target, Status, Active Testing, Created columns
- [ ] Clicking a row in Recent Scans navigates to `/scans/<scanId>`
- [ ] "View All" link navigates to `/scans`

**Verify Empty States:**
- If no scans exist: empty state with icon and message in the Recent Scans area
- If no vulns exist: pie chart shows "No findings yet" empty state

---

### 2.3 Scans List

**URL:** `/scans`

**Elements to verify:**
- [ ] Page heading: "My Scans" (Analyst/Client) or "All Scans" (Admin)
- [ ] Admin sees an "Admin View — All Users" badge
- [ ] "New Scan" button navigates to `/scans/new`
- [ ] Filter target search input works — type a hostname and list filters live
- [ ] Status filter tabs: `ALL`, `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `CANCELLED`
- [ ] Clicking a tab filters the table correctly
- [ ] Table columns: Target, Status (pill), Active Testing, Started, Completed
- [ ] Admin sees additional "Initiated By" column with user name + email + role color
- [ ] Clicking a row navigates to `/scans/<scanId>`

**Filter Tests:**

| Filter Button | Expected Result                                   |
|---------------|---------------------------------------------------|
| `ALL`         | All scans shown                                   |
| `COMPLETED`   | Only COMPLETED scans visible                      |
| `IN_PROGRESS` | Only running scans visible (empty if none)        |
| `PENDING`     | Only PENDING scans visible                        |
| `FAILED`      | Only FAILED scans (empty if none in mock)         |
| `CANCELLED`   | Only CANCELLED scans (empty if none)              |

**Search Test:**

| Search Input  | Expected                               |
|---------------|----------------------------------------|
| `staging`     | Only scans with "staging" in target    |
| `10.0`        | Only scans with "10.0" in target       |
| `xxxxxxxxxx`  | No results → empty state shown         |
| *(blank)*     | All scans shown again                  |

---

### 2.4 New Scan — Form & Validation

**URL:** `/scans/new`

**Elements to verify:**
- [ ] "← Back to Scans" back button works
- [ ] "New Scan Configurator" heading
- [ ] **Target Configuration** panel with IP/hostname input
- [ ] **Active AI Testing** toggle (off by default)
- [ ] **Authorization Gate** panel (red border)
  - Justification textarea
  - Authorization checkbox
- [ ] "Cancel" button navigates back
- [ ] "Initialize Scan" button (disabled until valid)

**Test Case A — Missing Target**

| Field         | Input                                  |
|---------------|----------------------------------------|
| Target        | *(blank)*                              |
| Justification | `Valid reason for testing this server` |
| Authorization | checked                                |

Expected: Validation fires, form won't submit.

**Test Case B — Missing Justification**

| Field         | Input                 |
|---------------|-----------------------|
| Target        | `staging.example.com` |
| Justification | *(blank)*             |
| Authorization | checked               |

Expected: Error message about justification being required (min 10 characters).

**Test Case C — Justification Too Short**

| Field         | Input                 |
|---------------|-----------------------|
| Target        | `staging.example.com` |
| Justification | `short`               |
| Authorization | checked               |

Expected: Error — justification must be at least 10 characters.

**Test Case D — Authorization Not Confirmed**

| Field         | Input                                              |
|---------------|----------------------------------------------------|
| Target        | `staging.example.com`                              |
| Justification | `Written pentest authorization from Acme Corp CTO` |
| Authorization | NOT checked                                        |

Expected: Error — authorization must be confirmed.

**Test Case E — Valid Scan (Passive, domain)**

| Field             | Input                                                                                           |
|-------------------|-------------------------------------------------------------------------------------------------|
| Target            | `staging.example.com`                                                                           |
| Justification     | `Written pentest authorization from Acme Corp CTO, ref AUTH-2026-014, valid through 2026-09-30.` |
| Authorization     | checked                                                                                         |
| Active AI Testing | Off (default)                                                                                   |

Expected: Scan created → redirected to `/scans/<scanId>`. Scan starts PENDING then moves to IN_PROGRESS automatically (mock simulates lifecycle).

**Test Case F — Valid Scan (Active Testing ON, IP address)**

| Field             | Input                                                                              |
|-------------------|------------------------------------------------------------------------------------|
| Target            | `10.0.4.22`                                                                        |
| Justification     | `Internal pentest authorized by security team, JIRA-SEC-99, approved 2026-08-01.` |
| Authorization     | checked                                                                            |
| Active AI Testing | On (toggle switched)                                                               |

Expected: Scan created → redirected to detail page. Active testing log tab will populate during scan simulation.

**Test Case G — Valid Scan (with IP range)**

| Field         | Input                                                                             |
|---------------|-----------------------------------------------------------------------------------|
| Target        | `192.168.1.1`                                                                     |
| Justification | `Authorized internal network scan for quarterly audit ref AUD-Q3-2026.`           |
| Authorization | checked                                                                           |

Expected: Scan created and lifecycle simulated.

---

### 2.5 Scan Detail — 4 Tabs

**URL:** `/scans/<scanId>` (navigate from Scans List or Dashboard)

**Elements to verify (Header):**
- [ ] Target hostname/IP shown as heading
- [ ] Status pill (PENDING / IN_PROGRESS / COMPLETED / FAILED / CANCELLED)
- [ ] Scan ID shown as code-styled badge
- [ ] "← Back to scans" button works
- [ ] "Cancel scan" button visible for PENDING/IN_PROGRESS scans

**Elements to verify (Status Grid — 3 cards):**
- [ ] Scan Status card (repeats status + mode description)
- [ ] Progress card — percentage bar updates live during scan
- [ ] Threats Detected card — Critical / High / Medium / Low counts

**Tab: Overview**
- [ ] Shows: Target, Status, Active testing (On/Off), Authorization justification, Started, Completed timestamps
- [ ] WebSocket connection status: "connected — receiving live updates" or "disconnected"
- [ ] Live event stream appears while scan is IN_PROGRESS (shows timestamped events)

**Tab: Threat Matrix**
- [ ] Risk Summary panel with stacked severity bar
- [ ] Severity legend chips (CRITICAL, HIGH, MEDIUM, LOW, INFO) each with count
- [ ] Vulnerability table with all columns
- [ ] Clicking a vulnerability row navigates to `/vulnerabilities/<vulnId>`

**Tab: Active Testing Log**
- [ ] If active testing was OFF: empty state saying "Active testing was not enabled"
- [ ] If active testing was ON: table with columns: Type, Target URL, Param, Payload, AI Verified, Risk
- [ ] AI Verified shows "Confirmed" or "Not confirmed"

**Tab: Remediation**
- [ ] If no remediations generated yet: empty state
- [ ] If remediations exist: table with Vulnerability ID, Target OS, AI Confidence, Status
- [ ] Clicking a row navigates to `/remediations/<remediationId>`

**Cancel Scan Test:**
- [ ] For a PENDING or IN_PROGRESS scan, click "Cancel scan"
- [ ] Confirm dialog appears with warning text
- [ ] Click confirm → scan status changes to CANCELLED
- [ ] "Cancel scan" button disappears after cancellation
- [ ] Try to cancel an already COMPLETED scan — "Cancel scan" button should not appear

---

### 2.6 Vulnerability Detail

**URL:** `/vulnerabilities/<vulnId>` (navigate from Threat Matrix tab)

**Elements to verify:**
- [ ] Sticky header with CVE ID (or vuln ID), severity badge, service + host info
- [ ] Back arrow returns to previous page
- [ ] Link to parent scan ID in header

**Left Pane:**
- [ ] AI Confidence card — percentage + severity + confidence bar + CVSS score + status
- [ ] Matched CVE panel — CVE ID, CVSS v3, severity, description
- [ ] If no CVE: note saying "flagged on version/config heuristics alone"
- [ ] **Update Disposition** buttons (Analyst/Admin only): `OPEN`, `REMEDIATED`, `ACCEPTED RISK`, `FALSE POSITIVE`
- [ ] Currently active disposition is highlighted
- [ ] Client role: disposition buttons NOT shown

**Right Pane:**
- [ ] AI Reasoning block — explains why this vuln was flagged, confidence %
- [ ] Related active-test attempts terminal (shows logged attempts or "None linked")

**Bottom Action Bar (Analyst/Admin):**
- [ ] Target OS dropdown: `ubuntu-22.04`, `ubuntu-20.04`, `debian-12`, `rhel-9`
- [ ] "Generate Remediation Script" button

**Test Case — Change Disposition (as Analyst)**
1. Open a vulnerability
2. Click `ACCEPTED RISK` → button highlights
3. Click `FALSE POSITIVE` → button highlights
4. Click `OPEN` → resets to open

**Test Case — Generate Remediation**

| Field     | Input          |
|-----------|----------------|
| Target OS | `ubuntu-22.04` |

Click "Generate Remediation Script" → loading spinner → redirected to new Remediation page with PENDING status.

**Try different OS values:**

| Target OS     | Expected                                    |
|---------------|---------------------------------------------|
| `ubuntu-22.04`| Script targets ubuntu-22.04 packages        |
| `ubuntu-20.04`| Script targets ubuntu-20.04                 |
| `debian-12`   | Script targets debian-12                    |
| `rhel-9`      | Script targets rhel-9 (yum/dnf commands)    |

---

### 2.7 Remediation Queue

**URL:** `/remediations`

**Elements to verify:**
- [ ] "Remediation Queue" heading
- [ ] Explanation text about human review requirement
- [ ] Status filter tabs: `ALL`, `PENDING`, `APPROVED`, `REJECTED`, `EXECUTED`
- [ ] Default filter is `PENDING`
- [ ] Table columns: Remediation ID, Vulnerability ID, Target OS, AI Confidence bar, Status pill, Created
- [ ] Clicking a row navigates to `/remediations/<remediationId>`

**Filter Tests:**

| Status Filter | Expected                          |
|---------------|-----------------------------------|
| `ALL`         | All remediations shown            |
| `PENDING`     | Only PENDING (awaiting review)    |
| `APPROVED`    | Only APPROVED remediations        |
| `REJECTED`    | Only REJECTED remediations        |
| `EXECUTED`    | Only EXECUTED remediations        |

---

### 2.8 Remediation Review

**URL:** `/remediations/<remediationId>`

**Elements to verify:**
- [ ] Sticky header with remediation ID and status pill
- [ ] Back button works

**Left Pane:**
- [ ] AI Confidence card with percentage and green progress bar
- [ ] Context panel: Finding (vuln ID), Target OS, Status pill
- [ ] Executive Summary card — AI-generated plain-language explanation

**Right Pane:**
- [ ] "Technical script" code viewer with dark background
- [ ] "Copy script" button — copies bash script to clipboard, label changes to "Copied" for 1.5s

**Bottom Action Bar — PENDING (Analyst/Admin):**
- [ ] Warning text: *"This script was generated by AI and has not run anywhere yet..."*
- [ ] **"Reject"** button (red border)
- [ ] **"Approve Script"** button (green)

**Test Case — Approve a Remediation (as Analyst)**
1. Open a PENDING remediation
2. Click "Approve Script"
3. Button shows "Approving..."
4. Status pill changes to `APPROVED`
5. Action bar changes to show reviewer name + date + "Mark as executed" button

**Test Case — Reject a Remediation (as Analyst)**
1. Open a PENDING remediation
2. Click "Reject"
3. Modal opens with textarea for rejection reason
4. Enter reason: `Script needs a rollback step before it's safe to run.`
5. Click "Reject" in modal → status changes to `REJECTED`
6. Action bar shows rejection info: reviewer, date, reason

**Test Case — Reject Without Reason**
1. Open Reject modal
2. Leave reason blank
3. Click Reject → still works (reason is optional)

**Test Case — Mark as Executed (Client role, APPROVED remediation)**
1. Switch to Client account
2. Open an APPROVED remediation
3. Click "Mark as executed"
4. A dialog appears: *"Confirm execution record"*
5. Type `EXECUTED` in the confirmation field
6. "Mark as executed" button enables
7. Click → status changes to `EXECUTED`

**Test Case — Type Wrong Confirmation**
1. In the "Mark as executed" dialog
2. Type `execute` (lowercase/partial)
3. Confirm button stays disabled

**Test Case — Client on PENDING remediation**
1. As Client, open a PENDING remediation
2. Action bar should say *"This remediation is currently pending review by an analyst."*
3. No Approve/Reject buttons visible for client

---

### 2.9 Profile Settings

**URL:** `/profile`

**Elements to verify:**
- [ ] "Profile Settings" heading
- [ ] Avatar circle with initials (first 2 characters of name)
- [ ] Role badge (admin=red, analyst=blue, client=green)
- [ ] Name, email displayed

**Account Information Form:**
- [ ] Full Name field (pre-filled with current name)
- [ ] Email Address field (pre-filled)
- [ ] "Change Password" section header
- [ ] Current Password field
- [ ] New Password field
- [ ] Confirm New Password field
- [ ] "Save Changes" button

**Test Case A — Update Name Only**

| Field     | Input          |
|-----------|----------------|
| Full Name | `Jane Updated` |

Click "Save Changes" → success message: *"Profile updated successfully!"*

**Test Case B — Update Email Only**

| Field | Input                       |
|-------|-----------------------------|
| Email | `updated.email@example.com` |

Click "Save Changes" → success message.

**Test Case C — Change Password (valid)**

| Field            | Input           |
|------------------|-----------------|
| Current Password | `demo-password` |
| New Password     | `NewSecure123`  |
| Confirm Password | `NewSecure123`  |

Expected: Success message, password fields clear.

**Test Case D — Passwords Do Not Match**

| Field            | Input          |
|------------------|----------------|
| Current Password | `demo-password` |
| New Password     | `NewSecure123`  |
| Confirm Password | `Different456`  |

Expected: Error: *"New passwords do not match."*

**Test Case E — Password Too Short**

| Field            | Input   |
|------------------|---------|
| New Password     | `short` |
| Confirm Password | `short` |

Expected: Error: *"New password must be at least 8 characters."*

**Test Case F — No Changes**

Leave all fields unchanged → click "Save Changes"
Expected: Error: *"No changes detected."*

---

### 2.10 Admin — User Management

**URL:** `/admin/users` (Admin only)

**Elements to verify:**
- [ ] "User Management" heading
- [ ] 4 stats cards: Total Users, Active, Analysts, Clients
- [ ] Role filter tabs: `ALL`, `admin`, `analyst`, `client`
- [ ] Search input (searches by name or email)
- [ ] Table columns: User (avatar + name + email), Role badge, Scans (count), Last Login, Status (Active/Disabled), Actions

**Actions (hover over a row to reveal):**
- [ ] **"Scans"** button — opens a modal showing that user's scan history
- [ ] **"Disable" / "Enable"** toggle button

**Test Case — Filter by Role**

| Filter    | Expected                      |
|-----------|-------------------------------|
| `admin`   | Only admin accounts shown     |
| `analyst` | Only analyst accounts         |
| `client`  | Only client accounts          |
| `ALL`     | All users shown               |

**Test Case — Search**

| Search Input   | Expected                                   |
|----------------|--------------------------------------------|
| `admin`        | Shows rows where name or email has "admin" |
| `@vulnara.dev` | All vulnara.dev accounts                   |
| `zzznomatch`   | Empty state: "No users found"              |

**Test Case — View User Scans (click "Scans" button)**
1. Hover over a user row → "Scans" button appears
2. Click "Scans" → modal opens
3. Modal shows: user name, email, role badge
4. Table shows their scans: Target, Status, Created
5. Click X to close modal

**Test Case — Disable a User**
1. Hover over an active user → "Disable" button (red)
2. Click → user status changes to "Disabled" (grey dot)
3. Button changes to "Enable" (green)

**Test Case — Enable a Disabled User**
1. Find a disabled user → "Enable" button (green)
2. Click → status changes to "Active" (green dot)

---

### 2.11 Admin — Configuration

**URL:** `/admin/config` (Admin only)

**Elements to verify:**
- [ ] "Configuration" heading
- [ ] Explanation text about runtime-tunable AI values
- [ ] Table columns: Key, Value, Description, Last Updated, (edit button)

**Test Case — Edit a Config Value**
1. Click "Edit" button next to any config key
2. An inline input appears with current value
3. Clear and type a new value: e.g., change `0.5` to `0.7`
4. Click "Save"
5. Verify value updates in the table
6. "Last updated" timestamp refreshes

**Test Case — Cancel Edit**
1. Click "Edit" on any config key
2. Change the value in the input
3. Click "Cancel"
4. Value reverts to original — no change

**Test Case — Empty Value**
1. Click "Edit" on a config key
2. Clear the input field entirely
3. Click "Save"
4. Check: does it save empty or show an error?

---

### 2.12 Admin — CVE Definitions

**URL:** `/admin/cve` (Admin only)

**Elements to verify:**
- [ ] "CVE Definitions" heading
- [ ] "Sync now" button
- [ ] Search input (search by CVE ID)
- [ ] Severity dropdown filter
- [ ] Table columns: CVE ID, Severity, CVSS v3, Description, Published date

**Test Case — Sync CVE Definitions**
1. Click "Sync now"
2. Button shows "Syncing..." with spinner
3. After ~0.7s: success banner appears ("Sync job sync-X started.")
4. Banner auto-dismisses after 4s

**Test Case — Search by CVE ID**

| Search Input    | Expected                               |
|-----------------|----------------------------------------|
| `CVE-2023`      | Filters to CVEs containing "CVE-2023"  |
| `CVE-2021-417`  | Shows CVE-2021-41773 if seeded         |
| `CVE-9999-9999` | Empty state: "No matching CVEs"        |

**Test Case — Filter by Severity**

| Severity Filter  | Expected                       |
|------------------|--------------------------------|
| `CRITICAL`       | Only CRITICAL CVEs shown       |
| `HIGH`           | Only HIGH CVEs                 |
| `MEDIUM`         | Only MEDIUM CVEs               |
| `LOW`            | Only LOW CVEs                  |
| `NONE`           | Only NONE-severity CVEs        |
| `All severities` | All CVEs shown                 |

---

## 3. MOBILE APP — Full Feature Walkthrough

---

### 3.1 Login Screen

**Route:** `/login` (initial screen, auth-guarded)

**Elements to verify:**
- [ ] Glowing shield icon at top
- [ ] "VULNARA" wordmark
- [ ] "SECURE TERMINAL ACCESS" subtitle
- [ ] Glass-panel auth card
- [ ] "OPERATOR ID / EMAIL" label + email field
- [ ] "ACCESS KEY" label + password field with show/hide toggle eye icon
- [ ] Biometric icon button (face unlock placeholder)
- [ ] "INITIALIZE SESSION" primary CTA button
- [ ] "FORGOT CREDENTIALS?" link
- [ ] "SYSTEM STATUS: OPTIMAL" + "NODE: V-77X" footer indicators

**Test Case A — Valid Login (Analyst)**

| Field    | Input                 |
|----------|-----------------------|
| Email    | `analyst@vulnara.dev` |
| Password | `any-password`        |

Click "INITIALIZE SESSION" → spinner shows → navigated to `/scans` (Scan List).

**Test Case B — Valid Login (Admin)**

| Field    | Input               |
|----------|---------------------|
| Email    | `admin@vulnara.dev` |
| Password | `admin-pass`        |

Expected: Navigated to `/scans`. Admin nav items visible.

**Test Case C — Empty Email**

| Field    | Input      |
|----------|------------|
| Email    | *(blank)*  |
| Password | `password` |

Expected: Validation error: *"Enter a valid email"*

**Test Case D — Invalid Email Format**

| Field    | Input        |
|----------|--------------|
| Email    | `notanemail` |
| Password | `password`   |

Expected: Validation error: *"Enter a valid email"*

**Test Case E — Empty Password**

| Field    | Input                 |
|----------|-----------------------|
| Email    | `analyst@vulnara.dev` |
| Password | *(blank)*             |

Expected: Validation error: *"Enter your password"*

**Test Case F — Password Show/Hide Toggle**
1. Type a password in the Access Key field
2. Tap the eye icon → characters become visible
3. Tap again → obscured again

---

### 3.2 Scan List Screen

**Route:** `/scans`

**Elements to verify:**
- [ ] VulnaraAppBar with wordmark
- [ ] Bottom navigation bar with tabs: Scans, Dashboard, Notifications, Profile
- [ ] Scan list heading
- [ ] List of scan cards showing target, status badge, date
- [ ] FAB or "+" button to create new scan
- [ ] Tapping a scan navigates to `/scans/<scanId>`

**Test Case — Navigate to New Scan**
1. Tap the "+" / new scan button → navigates to `/scans/new`

**Test Case — Tap a Scan Card**
1. Tap any scan in the list
2. Navigates to Scan Status screen for that scan

---

### 3.3 New Scan Screen

**Route:** `/scans/new`

**Elements to verify:**
- [ ] Radar icon + "New Target Configuration" title
- [ ] Close (X) button → pops back to scan list
- [ ] TARGET ADDRESS / IP RANGE field
- [ ] AUTHORIZATION JUSTIFICATION multi-line textarea (3-5 lines)
- [ ] "Explicit Permission Confirmation" checkbox card (custom styled)
- [ ] "Enable AI Active Testing" toggle switch (ON by default in mobile)
- [ ] "INITIALIZE SCAN" footer button (full width, disabled if invalid)
- [ ] Error message shown inline if validation fails

**Test Case A — Missing Target**

| Field                       | Input                           |
|-----------------------------|---------------------------------|
| Target Address              | *(blank)*                       |
| Authorization Justification | `Valid justification text here` |
| Permission Checkbox         | checked                         |

Expected: Validation error: *"Target is required"*

**Test Case B — Missing Justification**

| Field                       | Input                 |
|-----------------------------|-----------------------|
| Target Address              | `staging.example.com` |
| Authorization Justification | *(blank)*             |
| Permission Checkbox         | checked               |

Expected: Validation error: *"Required -- the server rejects an empty justification"*

**Test Case C — Checkbox Not Confirmed**

| Field                       | Input                                               |
|-----------------------------|-----------------------------------------------------|
| Target Address              | `api.internal.corp`                                 |
| Authorization Justification | `Jira ticket SEC-123, approved by CISO 2026-08-01`  |
| Permission Checkbox         | NOT checked                                         |

Expected: Error: *"You must confirm authorization before starting a scan."*

**Test Case D — Valid Scan (domain, active testing ON)**

| Field                       | Input                                                                         |
|-----------------------------|-------------------------------------------------------------------------------|
| Target Address / IP Range   | `https://api.internal.corp`                                                   |
| Authorization Justification | `Jira ticket reference SEC-2026-011, engagement approved by security lead.`   |
| Permission Checkbox         | checked                                                                       |
| AI Active Testing           | ON                                                                            |

Expected: Spinner shows → scan created → modal closes (pops back) → scan appears in list.

**Test Case E — Valid Scan (IP address, active testing OFF)**

| Field                       | Input                                                                          |
|-----------------------------|--------------------------------------------------------------------------------|
| Target Address / IP Range   | `10.0.0.1/24`                                                                  |
| Authorization Justification | `Provide Jira ticket reference SEC-Q3-2026, business context for active scan.` |
| Permission Checkbox         | checked                                                                        |
| AI Active Testing           | OFF (toggle off)                                                               |

Expected: Scan created successfully.

**Test Case F — Valid Scan (localhost/test environment)**

| Field                       | Input                                                                   |
|-----------------------------|-------------------------------------------------------------------------|
| Target Address / IP Range   | `192.168.10.5`                                                          |
| Authorization Justification | `Internal lab environment, owned infrastructure, no permission required.` |
| Permission Checkbox         | checked                                                                 |

Expected: Scan created successfully.

---

### 3.4 Scan Status Screen

**Route:** `/scans/<scanId>`

**Elements to verify:**
- [ ] App bar with back button
- [ ] Target name as main title
- [ ] Status badge (PENDING / IN_PROGRESS / COMPLETED)
- [ ] Progress indicator or summary
- [ ] Vulnerability counts by severity
- [ ] List of discovered vulnerabilities
- [ ] Tapping a vulnerability navigates to `/scans/<scanId>/vulnerabilities/<vulnId>`
- [ ] "Remediations" navigation to `/scans/<scanId>/remediations`

**Test Case — View a Completed Scan**
1. Find a COMPLETED scan in the list
2. Tap it → scan status screen
3. Verify all vulnerability findings are listed
4. Tap a vulnerability → detail screen

**Test Case — View a Running Scan**
1. Create a new scan (Test Case D from 3.3)
2. Immediately navigate to its detail screen
3. Status shows IN_PROGRESS
4. Watch for auto-updates (status refreshes)

---

### 3.5 Vulnerability Detail Screen

**Route:** `/scans/<scanId>/vulnerabilities/<vulnId>`

**Elements to verify:**
- [ ] Back button
- [ ] CVE ID or vuln ID as title
- [ ] Severity badge
- [ ] Host and port info
- [ ] AI Confidence score
- [ ] CVE details (ID, CVSS, description) or "no CVE" note
- [ ] AI Reasoning text
- [ ] Related active-test attempts (if any)
- [ ] "Generate Remediation" button (Analyst/Admin only)
- [ ] Target OS selector before generating remediation

**Test Case — Generate Remediation (Analyst)**
1. Open any vulnerability
2. Select target OS from dropdown/picker
3. Tap "Generate Remediation"
4. Loading indicator shows
5. Navigated to Remediation Approval screen

---

### 3.6 Remediation List Screen

**Route:** `/scans/<scanId>/remediations`

**Elements to verify:**
- [ ] List of remediations for that scan
- [ ] Each card shows: vuln ID, status, AI confidence, target OS
- [ ] Tapping a card navigates to `/remediations/<remediationId>`

---

### 3.7 Remediation Approval Screen

**Route:** `/remediations/<remediationId>`

**Elements to verify:**
- [ ] App bar with back button + avatar icon
- [ ] Severity and status pills at top
- [ ] AI Confidence score panel
- [ ] Executive Summary panel (plain-language AI text)
- [ ] "Remediation Actions" panel showing action buttons
- [ ] Terminal-style code viewer showing the bash script
- [ ] Copy script functionality

**Analyst/Admin Actions:**
- [ ] "Approve Fix" button (PENDING state only)
- [ ] "Reject" option (PENDING state only)

**Client Actions:**
- [ ] "Mark Executed" button (APPROVED state only)

**Test Case — Approve Fix (as Analyst)**
1. Open a PENDING remediation
2. Tap "Approve Fix"
3. Loading indicator
4. Status changes to APPROVED
5. "Mark Executed" button becomes available

**Test Case — Reject (as Analyst)**
1. Open a PENDING remediation
2. Tap Reject
3. Confirm dialog appears
4. Status changes to REJECTED

**Test Case — Mark Executed (as Client)**
1. Switch to Client role
2. Open an APPROVED remediation
3. Tap "Mark Executed"
4. Confirmation dialog
5. Status changes to EXECUTED

---

### 3.8 Notifications / Alerts Hub

**Route:** `/notifications`

**Elements to verify:**
- [ ] "Notifications" or "Alerts Hub" heading in app bar
- [ ] ALL / CRITICAL filter toggle
- [ ] Alert list with rows showing:
  - Accent color stripe on left
  - Icon (varies per alert type)
  - Title + relative timestamp
  - Truncated body text

**Alert Types to verify:**
- [ ] Critical vulnerability alert (red accent, lightning icon)
- [ ] Remediation approved (primary accent, verified icon)
- [ ] Scan completed (secondary accent, check circle icon)
- [ ] Agent heartbeat (grey, globe icon)

**Test Case — Filter: CRITICAL Only**
1. Tap "CRITICAL" toggle
2. Only critical alerts shown (red accent items)

**Test Case — Filter: ALL**
1. Tap "ALL"
2. All alert types visible

---

### 3.9 Profile Screen

**Route:** `/profile`

**Elements to verify:**
- [ ] App bar
- [ ] Avatar circle with initials
- [ ] User name, email, role badge
- [ ] Two tabs: Account Info and Change Password
- [ ] Bottom navigation visible
- [ ] "Notifications Enabled" toggle (preference)
- [ ] "Security (Audit Log)" navigation link → goes to `/audit-log`
- [ ] "Logout" button

**Account Info Tab:**
- [ ] Full Name field (pre-filled)
- [ ] Email field (pre-filled)
- [ ] "Save Account Info" button

**Change Password Tab:**
- [ ] Current Password field
- [ ] New Password field (with show/hide toggle)
- [ ] "Save Password" button

**Test Case A — Update Name**

| Field     | Input               |
|-----------|---------------------|
| Full Name | `Updated Name Test` |

Tap "Save Account Info" → success message.

**Test Case B — No Changes (Account Info)**
Leave fields unchanged → tap "Save" → error: *"No changes detected."*

**Test Case C — Change Password (valid)**

| Field            | Input           |
|------------------|-----------------|
| Current Password | `demo-password` |
| New Password     | `NewPass12345`  |

Tap "Save Password" → success message.

**Test Case D — Missing Current Password**

| Field            | Input       |
|------------------|-------------|
| Current Password | *(blank)*   |
| New Password     | `NewPass12` |

Expected: Error: *"All password fields are required."*

**Test Case E — Toggle Notifications**
1. Toggle "Notifications Enabled" switch ON
2. Toggle OFF
3. Verify toggle reflects state visually

**Test Case F — Logout**
1. Tap Logout button
2. Confirm dialog appears
3. Confirm → navigated back to Login screen
4. Verify protected routes redirect to login

**Test Case G — Navigate to Audit Log**
1. Tap "Security (Audit Log)" item
2. Navigated to `/audit-log`

---

### 3.10 Admin Users Screen (Admin only)

**Route:** `/admin/users`

**Elements to verify:**
- [ ] List of all users with name, email, role badge, status, scan count
- [ ] Role filter: `ALL`, `admin`, `analyst`, `client`
- [ ] Tapping a user card shows that user's details / scan history
- [ ] Disable/Enable user toggle
- [ ] Search by name or email

---

### 3.11 Audit Log Screen

**Route:** `/audit-log` (from Profile > Security)

**Elements to verify:**
- [ ] "Audit Log" heading in app bar
- [ ] Back button (no bottom nav — secondary screen)
- [ ] Filter row: Time Range / Role dropdowns
- [ ] Export button (top right)
- [ ] Striped table of timestamped events
  - Left accent color stripe per row
  - Timestamp
  - Event description (detail)
  - Status chip (CRITICAL, EXEC, INFO, etc.)

**Representative rows to verify:**

| Status Chip | Color                | Example Event                              |
|-------------|----------------------|--------------------------------------------|
| `CRITICAL`  | Red                  | Unauthorized access attempt on API_GATEWAY |
| `EXEC`      | Primary (teal/white) | Analyst approved remediation REM-CVE-...   |
| `INFO`      | Grey                 | Routine scan completed, 0 findings         |

**Test Case — Filter by Time Range**
1. Tap time range dropdown
2. Select a range (e.g., Last 24h)
3. Rows update

**Test Case — Export**
1. Tap Export button
2. Verify action triggers (download prompt or share sheet)

---

## 4. Cross-Cutting Tests

### 4.1 Role-Based Access Control

| Page / Feature                 | Admin | Analyst | Client |
|--------------------------------|-------|---------|--------|
| View Dashboard                 | Yes   | Yes     | Yes    |
| Create New Scan                | Yes   | Yes     | No     |
| View Scan Detail               | Yes   | Yes     | Yes    |
| Change Vuln Disposition        | Yes   | Yes     | No     |
| Generate Remediation Script    | Yes   | Yes     | No     |
| Approve / Reject Remediation   | Yes   | Yes     | No     |
| Mark Remediation Executed      | Yes   | Yes     | Yes    |
| View Admin — User Management   | Yes   | No      | No     |
| View Admin — Configuration     | Yes   | No      | No     |
| View Admin — CVE Definitions   | Yes   | No      | No     |

**Test:** Log in as each role and confirm the above matches.

---

### 4.2 Navigation

- [ ] Sidebar / bottom nav links all navigate to correct pages
- [ ] Browser back button (web) works on every page
- [ ] Mobile back button (Android) / swipe-back (iOS) works on every screen
- [ ] 404 / Not Found page appears for invalid URLs (web only: `/some/random/path`)

---

### 4.3 Real-Time WebSocket (Web Only)

1. Create a new scan
2. Navigate to its detail page
3. Watch the **Overview tab** — "connected — receiving live updates" appears
4. Within seconds: live events stream in the "Live event stream" box:
   - `scan.status_changed` → IN_PROGRESS
   - `recon.progress` events (host_discovery, port_scan, banner_grab)
   - `vulnerability.discovered` events
   - `alert.critical` if critical found
   - If active testing ON: `active_test.attempt`
   - `scan.completed`
5. Progress bar in Scan Status Grid updates live
6. Threat count cards update as vulns are discovered

---

### 4.4 Edge Cases

| Scenario                                    | Expected Behaviour                              |
|---------------------------------------------|-------------------------------------------------|
| Navigate to `/scans/<invalid-id>`           | "Scan not found" error state                    |
| Navigate to `/vulnerabilities/<invalid-id>` | "Vulnerability not found" error state           |
| Navigate to `/remediations/<invalid-id>`    | "Remediation not found" error state             |
| Try to cancel a COMPLETED scan              | "Cancel scan" button not shown                  |
| Mark executed without typing "EXECUTED"     | Confirm button stays disabled                   |
| Client tries to access `/admin/users`       | Redirected (ProtectedRoute guard fires)         |
| Analyst tries to access `/admin/config`     | Redirected (ProtectedRoute guard fires)         |
| Unauthenticated access to any protected URL | Redirected to `/login`                          |

---

## 5. Known Mock-Mode Behaviours

> These are expected in Mock Mode (`USE_MOCK=true`) and are **not bugs**:

| Behaviour                                         | Reason                                               |
|---------------------------------------------------|------------------------------------------------------|
| Any email/password works for existing users        | Mock login only checks email match, ignores password |
| Scan lifecycle auto-simulates after ~700ms         | `simulateScanLifecycle()` runs in-memory             |
| Scan data resets on page refresh                   | Mock state is in-memory only (no real DB)            |
| CVE Sync returns a fake job ID                     | Mock returns `{ sync_job_id: "sync-X", status: "STARTED" }` |
| Remediation script is a generic bash template      | AI generation is simulated, not real Gemini call     |
| WebSocket events come from mock emitter            | Real backend uses actual WebSocket; mock uses in-memory Map |
| Notifications screen shows static placeholder data | No real alerts API endpoint yet                      |
| Audit log screen shows static placeholder data     | No real audit-log API endpoint yet                   |
| Biometric button on mobile login does nothing      | Placeholder UI — no biometric integration yet        |
| "FORGOT CREDENTIALS?" does nothing (mobile)       | Link placeholder — no reset flow implemented yet     |

---

*Document version: 1.0 — Generated 2026-08-18*
*Platform: Vulnara Web (React + Vite) | Mobile (Flutter)*
