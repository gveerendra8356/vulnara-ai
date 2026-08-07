# Vulnara Web Application Guide

This document provides all the necessary credentials to log into the seeded Vulnara database, along with a comprehensive guide on how to use the Web Application and test its features.

## Test Credentials

The database has been seeded with three different users, each representing a different role in the system. You can log into the web application using any of these credentials:

### 1. System Administrator
- **Email:** `admin@vulnara.com`
- **Password:** `Admin123!`
- **Role:** `admin`
- **Capabilities:** Can view all scans, manage system configuration, approve/reject any remediation, and access all administrative features.

### 2. Security Analyst
- **Email:** `analyst@vulnara.com`
- **Password:** `Analyst123!`
- **Role:** `analyst`
- **Capabilities:** Can view all scans, review threat logs, update vulnerability statuses (e.g., mark as false positive), and approve or reject AI-generated remediation scripts.

### 3. Demo Client
- **Email:** `client@vulnara.com`
- **Password:** `Client123!`
- **Role:** `client`
- **Capabilities:** Can only view their own scans, initiate new scans, and mark approved remediations as "Executed" for their own infrastructure.

---

## Testing the Features

### 1. Authentication Flow
- **Sign Up:** Try creating a brand new account using the "Create Account" button on the login screen. Upon successful creation, the system will automatically log you in and direct you to the dashboard.
- **Login / Logout:** Test logging in with the seeded accounts above. Use the sidebar to log out and verify that you are redirected to the login screen and your session is cleared.

### 2. The Main Dashboard (`/`)
When you log in, you will land on the Dashboard. This page provides a high-level overview of the security posture.
- **Metrics:** You will see total vulnerabilities, critical issues, and pending remediations.
- **Quick Links:** The dashboard provides recent activity feeds, allowing you to jump straight into recent scans or the remediation queue.

### 3. Scans List & Scanning (`/scans`)
Navigate to the "Scans" tab on the sidebar.
- **View Scans:** You will see a list of historical scans. Click on any scan to view its deep details.
- **New Scan:** Click the "New Scan" button. You will be prompted to enter a target (e.g., `10.0.0.55` or `https://demo.app.com`).
  - **Authorization Gate:** You *must* check the authorization box and provide a justification. If you leave it blank, the backend will strictly reject the request.
  - **Active Testing:** You can toggle active testing to allow the AI to send safe exploit payloads.

### 4. Scan Details & Vulnerabilities (`/scans/{id}`)
Clicking into a specific scan reveals the vulnerabilities discovered during that session.
- **Vulnerability List:** You can see the CVSS score, severity, and the specific service/port that was affected.
- **Threat Logs:** If active testing was enabled, the "Threat Logs" tab will show you the exact payloads (SQLi, XSS, Command Injection) that the scanner fired at the target, along with the AI's verification notes on whether the attack succeeded.
- **Vulnerability Details:** Clicking on a vulnerability opens a detailed modal showing the AI's reasoning for flagging the issue. If logged in as an Analyst or Admin, you can change the status of the vulnerability (e.g., `OPEN` -> `FALSE_POSITIVE`).

### 5. Remediation Queue (`/remediations`)
Navigate to the "Remediation Queue" in the sidebar. This is where AI-generated fix scripts live.
- **Global Queue:** This page lists all remediations generated across all scans, filterable by status (`PENDING`, `APPROVED`, `REJECTED`, `EXECUTED`).
- **Reviewing (Analyst/Admin):** Click on a "Pending" remediation. You will see an executive summary and a technical script (e.g., Python code or a Bash command). Analysts can click **Approve** or **Reject** (with a reason).
- **Execution (Client):** Once a remediation is approved, a Client can log in, view the script, apply the fix to their infrastructure, and click **Mark Executed** to close the loop.

### 6. Admin Settings (`/settings`)
(Available to Admin accounts).
- Currently a stubbed interface demonstrating where system configurations (like max concurrent scans or NVD CVE sync triggers) will be managed.
