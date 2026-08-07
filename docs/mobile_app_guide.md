# Vulnara Mobile App Testing Guide

This document provides a clear, step-by-step guide to testing the Vulnara Flutter mobile application (`vulnara_mobile_scaffold`). The mobile app is designed to work seamlessly with the FastAPI backend, utilizing WebSockets for live updates and Riverpod for state management.

---

## Prerequisites

1. **Backend Server Running:** Ensure the FastAPI backend is running on your machine:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```
2. **Android Emulator:** Ensure you are using an Android Emulator (e.g., Pixel 7 API 34). The app is pre-configured to point to `http://10.0.2.2:8000`, which automatically routes traffic to your computer's `localhost`.

---

##  Getting Started

1. Open a terminal and navigate to the mobile app directory:
   ```bash
   cd vulnara_mobile_scaffold
   ```
2. Launch the app on your running emulator:
   ```bash
   flutter run
   ```

---

## Test Credentials

Use these pre-seeded accounts to explore different permission levels:

### 1. Demo Client (Standard User)
- **Email:** `client@vulnara.com`
- **Password:** `Client123!`
- **Capabilities:** Can create new scans, view own scans, and execute approved remediations.

### 2. Security Analyst (Reviewer)
- **Email:** `analyst@vulnara.com`
- **Password:** `Analyst123!`
- **Capabilities:** Can review threat logs, update vulnerability statuses, and approve/reject AI remediations.

### 3. System Admin
- **Email:** `admin@vulnara.com`
- **Password:** `Admin123!`
- **Capabilities:** Full access to all scans and system configurations.

---

## Testing Workflows (Step-by-Step)

### Scenario 1: The Client Workflow (Creating a Scan)
**Goal:** Verify authentication, API integration, and WebSocket live updates.

1. **Log In:** 
   - Enter `client@vulnara.com` and `Client123!`. 
   - Tap **Sign in**. You should be routed to the Scans dashboard showing the seeded historical scans.
2. **Start a Scan:**
   - Tap the **"+ New scan"** floating action button at the bottom right.
   - **Target IP/Domain:** Enter `testphp.vulnweb.com` (or any dummy IP like `192.168.1.55`).
   - **Active Testing:** Toggle this **ON**.
   - **Authorization Checkbox:** You MUST check the box confirming you have permission.
   - **Justification:** Enter: `Authorized by security team for Q3 compliance testing.`
   - Tap **Start Scan**.
3. **Verify WebSockets (Live Updates):**
   - You will be immediately redirected to the Scan Details screen.
   - Because of the WebSocket connection, you should see the status pill update automatically from `PENDING` ➔ `IN PROGRESS` ➔ `COMPLETED` without you needing to pull-to-refresh or restart the app.

### Scenario 2: The Analyst Workflow (Approving Remediations)
**Goal:** Verify role-based access and data parsing for complex nested JSON.

1. **Log In:**
   - Tap the **Logout** icon in the top right of the AppBar.
   - Log back in as `analyst@vulnara.com` / `Analyst123!`.
2. **Review a Scan:**
   - Tap on the scan that was just created by the client (or any seeded completed scan).
   - You will see a list of discovered vulnerabilities (e.g., SQL Injection, XSS).
3. **Approve a Remediation:**
   - Tap on one of the vulnerabilities to open its details.
   - Scroll down to the **Remediation Script** section.
   - As an analyst, you have the authority to review the AI-generated fix (e.g., a python script or firewall rule).
   - Tap **Approve**. The status should immediately update to `APPROVED`.

### Scenario 3: The Client Execution (Closing the Loop)
**Goal:** Verify state updates across different sessions.

1. **Log In:**
   - Log out and back in as the Client (`client@vulnara.com` / `Client123!`).
2. **Execute Remediation:**
   - Navigate back to the scan and the specific vulnerability.
   - Notice that the remediation now says `APPROVED` (thanks to the Analyst).
   - The Client can now view the script, apply it to their real-world infrastructure, and finally tap **Mark Executed**.
   - The UI should update to show the vulnerability has been successfully remediated.

---

## 🛠 Troubleshooting

* **App gets stuck on the Login Screen with a loading spinner?**
  Ensure the backend is running. The app is making an API call; if the server is off, it will time out after 10-15 seconds.
* **Network Error / Connection Refused?**
  If testing on a physical Android device or iOS simulator, `10.0.2.2` won't work. You must change the `baseUrl` and `wsBaseUrl` in `lib/core/constants.dart` to your computer's local network IP (e.g., `192.168.1.X`) or `localhost` for iOS simulator.
