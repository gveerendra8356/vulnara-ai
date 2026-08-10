# Vulnara: Master Testing & Usage Guide

Welcome to the definitive guide for testing and using the **Vulnara** platform. This document is designed for QA testers, developers, or new users to understand exactly what the application does, how to log in, and how to test the end-to-end features across both the **Web Dashboard** and the **Mobile Companion App**.

---

## 1. What is Vulnara?

**Vulnara** is an AI-powered vulnerability scanner. It doesn't just find security holes in a target IP or domain; it actively verifies them by sending safe exploit payloads. Once a vulnerability is verified, it uses Groq to write a highly technical, custom remediation script (like Python code or Bash commands) to fix the issue.

The platform is designed as a **Closed-Loop System** involving different roles:
1. A **Client** requests a scan.
2. The **System** finds vulnerabilities and AI generates fix scripts.
3. An **Analyst** reviews and approves the AI scripts.
4. The **Client** applies the approved script to their servers and marks it as resolved.

---

## 2. Prerequisites: Getting the Apps Running

Before you can test the UI, you must ensure the systems are running locally.

1. **Backend API:** Run the Python FastAPI server.
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```
2. **Frontend Web Dashboard:** Run the React Vite server.
   ```bash
   cd vulnara-web
   npm run dev
   ```
3. **Mobile App:** Run the Flutter app on an emulator.
   ```bash
   cd vulnara_mobile_scaffold
   flutter run
   ```

---

## 3. Test Credentials & User Roles

Vulnara utilizes Role-Based Access Control (RBAC). The database is pre-seeded with three accounts. You will need to log into these different accounts to test different parts of the system.

| Role | Email Address | Password | What they can do |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@vulnara.com` | `Admin123!` | Has god-mode. Can view all scans, manage system configs, and force-approve anything. |
| **Security Analyst**| `analyst@vulnara.com` | `Analyst123!` | The reviewer. Can view all scans, review raw threat logs, mark false positives, and approve AI remediations. |
| **Demo Client** | `client@vulnara.com` | `Client123!` | The end-user. Can only see their own data. They can request new scans and execute fixes. |

---

## 4. End-to-End Testing Walkthrough

To truly understand how Vulnara works, follow this continuous testing scenario. You can perform these steps on either the **Web App** or the **Mobile App** (or ideally, have both open side-by-side to watch the real-time WebSockets sync!).

### Step 1: The Client Requests a Scan
* **Who:** Log in as the Client (`client@vulnara.com` / `Client123!`).
* **Action:**
  1. Navigate to the **Scans** page.
  2. Click **New Scan** (Web) or the **"+" FAB button** (Mobile).
  3. Enter a target (e.g., `testphp.vulnweb.com` or `192.168.1.55`).
  4. Toggle **Active Testing** ON (so the AI will test exploits).
  5. **Crucial:** You must check the authorization box and type a justification (e.g., "Authorized for Q3 Audit"). The system will reject the scan otherwise.
  6. Submit the scan.

### Step 2: Observe Live WebSockets
* **Action:** Immediately after submitting, you will be taken to the Scan Details page.
* **Observe:** Do not refresh the page! Watch the status pill automatically change from `PENDING` ➔ `IN PROGRESS` ➔ `COMPLETED`. This is powered by real-time WebSockets pushing state directly from the backend to the React/Flutter UI.

### Step 3: The Analyst Reviews the AI Threat Logs
* **Who:** Log OUT of the Client account. Log IN as the Security Analyst (`analyst@vulnara.com` / `Analyst123!`).
* **Action:**
  1. Open the scan that the Client just created.
  2. Click on one of the discovered vulnerabilities (e.g., SQL Injection).
  3. **Observe Threat Logs:** Look at the exact payloads the scanner fired and read the AI's reasoning on why it flagged the issue.
  4. **Approve Remediation:** Scroll down to the AI-generated fix script (e.g., Python code). As an Analyst, click the **Approve** button. The status will immediately update to `APPROVED`.

### Step 4: The Client Executes the Fix
* **Who:** Log OUT of the Analyst account. Log back IN as the Client (`client@vulnara.com` / `Client123!`).
* **Action:**
  1. Go back to the specific vulnerability in the scan.
  2. Notice the status now says `APPROVED`.
  3. The Client can now view the technical script. In a real-world scenario, they would run this script on their server.
  4. Click the **Mark Executed** button.
  5. **Observe:** The vulnerability is now fully closed, and the security loop is complete!

---

## 5. Exploring Additional Features

Once you understand the main loop, try testing these standalone features:

- **The Main Dashboard (Web):** Log in as Admin or Analyst. Review the high-level metrics charts (Total Vulnerabilities vs. Critical Issues) and use the Recent Activity feed to jump directly into scans.
- **The Global Remediation Queue (Web):** Click the "Remediations" tab in the sidebar. This provides a unified table of every single AI fix generated across the entire platform. Use the filters to view only `PENDING` or `REJECTED` scripts.
- **Rejecting a Fix (Mobile/Web):** Log in as an Analyst. Find a pending remediation and click **Reject**. You will be forced to provide a justification string detailing why the AI's script was unacceptable.
- **Push Notifications (Mobile):** If testing on a physical mobile device with Firebase configured, when a scan completes, the Analyst will receive a background push notification alerting them that a new script requires triage.

---

## 🛠️ Troubleshooting Common Issues

* **App gets stuck on the Login Screen with a loading spinner?**
  * *Fix:* The backend is likely not running. Ensure `uvicorn` is running in your terminal. If the backend is off, API requests will time out.
* **Mobile App says "Connection Refused"?**
  * *Fix:* If you are using a physical Android device or iOS simulator, the default `10.0.2.2` IP (which points to localhost on an Android emulator) won't work. You must change the `baseUrl` and `wsBaseUrl` in `vulnara_mobile_scaffold/lib/core/constants.dart` to your computer's actual local IPv4 network address (e.g., `192.168.1.X`).
* **New Scans aren't updating live?**
  * *Fix:* Ensure the backend didn't crash. WebSockets require the persistent connection to remain open. Check your backend terminal logs for any Python exceptions.
