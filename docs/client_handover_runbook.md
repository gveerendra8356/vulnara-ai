# Vulnara: Deployment & Client Handover Runbook
---

## 1. Backend Deployment — Render + Neon (Current Stack)

The backend is deployed on **Render** (free Web Service) with **Neon** as the serverless Postgres database. No VM, no Docker, no SSH required. Render auto-deploys from the `render.yaml` Blueprint in the repo on every `git push`.

### Step 1 — Neon Database
1. Have the client create a free account at [neon.tech](https://neon.tech/).
2. Create a new **Project**. Copy the Postgres connection string.
3. Convert it to the `asyncpg` driver prefix (Render env var):
   ```
   # Neon gives you: postgres://user:pass@host/db?sslmode=require
   # Paste this:     postgresql+asyncpg://user:pass@host/db
   ```
   > Drop the `?sslmode=require` suffix — `core/db.py` handles SSL via `connect_args` because `asyncpg` rejects the libpq-style query param.

### Step 2 — Render Blueprint Deploy
1. Have the client create a free [Render](https://render.com) account (GitHub login is fine).
2. **New → Blueprint** → connect the GitHub repo.
3. Render reads `render.yaml` and prompts for the two `sync: false` secrets:
   - `DATABASE_URL` — the `asyncpg` URL from step 1.
   - `GROQ_API_KEY` — from [console.groq.com](https://console.groq.com).
4. After deploy, verify:
   ```
   GET https://<app>.onrender.com/health
   → {"status": "ok", "db": "ok"}
   ```
5. Set `CORS_ORIGINS` in Render → Environment to include the GitHub Pages frontend URL once it is live.

### Step 3 — Keep-Alive (cron-job.org)
Render's free tier sleeps after 15 minutes of inactivity; Neon suspends after 5 minutes.
1. Create a free account at [cron-job.org](https://cron-job.org/).
2. Create a job: `GET https://<app>.onrender.com/health` every **5 minutes**.
3. `/health` runs `SELECT 1` against Neon — one ping keeps both awake.

### Environment Variables Summary

| Variable | Value | Source |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Neon dashboard |
| `VULNARA_SECRET_KEY` | auto-generated | Render `generateValue: true` |
| `GROQ_API_KEY` | your key | console.groq.com |
| `CORS_ORIGINS` | GitHub Pages URL + `http://localhost:5173` | Your Pages domain |

### ⚠️ Render Sandbox Limitation
Render's free containers cannot run `nmap` (raw socket access is sandboxed). The AI features, `/health`, and all API endpoints work fine. If the client needs full active port scanning, they need a **Google Cloud e2-micro VM** (permanently free in `us-central1/us-east1/us-west1`). SSH in, install Docker, and run `docker-compose up -d --build` with the same env vars.

---

## 2. HTTPS Setup: Certbot vs. Cloudflare Tunnel

### Comparison
* **Certbot (Let's Encrypt):** Requires opening Ports 80 and 443 on the VM's firewall. Exposes the VM's raw IP address to the internet (DDoS risk). Requires manual Nginx reverse proxy configuration.
* **Cloudflare Tunnel:** You install a lightweight daemon on the VM. It establishes an outbound connection to Cloudflare. **No ingress ports need to be opened.** Your VM's IP is hidden. Cloudflare handles SSL automatically.

### Recommendation: Cloudflare Tunnel (Zero Trust)
For a security tool, hiding the origin IP is paramount. 
1. Have the client sign up for a free Cloudflare account and add their domain.
2. Go to **Zero Trust > Networks > Tunnels**.
3. Create a Tunnel named `vulnara-backend`.
4. Run the provided installation command on the VM (it will look like `sudo cloudflared service install <token>`).
5. In the Cloudflare Dashboard, route `api.clientdomain.com` to `http://localhost:8000`.
*(Cloudflare natively supports WebSockets out of the box.)*

---

## 3. FastAPI CORS Configuration

CORS is no longer hardcoded. `backend/app/main.py` reads the `CORS_ORIGINS` environment variable (comma-separated list of allowed origins). Set it in the Render dashboard:

```
CORS_ORIGINS=https://<username>.github.io,http://localhost:5173
```

This keeps the API locked to only the frontend domain(s) actually calling it, without touching source code when the frontend URL changes.

---

## 4. Neon Database Setup & Keep-Alive

1. Have the client create an account on **Neon.tech**.
2. Create a new PostgreSQL project and copy the `DATABASE_URL`.
3. Provide this URL to the VM's `.env` file.

**The Keep-Alive Strategy:**
Neon's free tier scales to zero (suspends) after 5 minutes of inactivity. When a scan is initiated, the cold start can take 3-5 seconds, causing timeouts.
* **Solution:** Create a free account on [cron-job.org](https://cron-job.org/) (under the client's email).
* **Setup:** Create a scheduled job that pings a lightweight health-check endpoint on your FastAPI backend (e.g., `GET https://api.clientdomain.com/health`) every **4 minutes**. 
* Ensure the `/health` endpoint executes a simple `SELECT 1` query to the database, keeping the Neon compute node awake indefinitely.

---

## 5. GitHub Pages Deployment (React App)

The frontend deploys automatically via GitHub Actions — no separate hosting account needed.

1. In the GitHub repo, go to **Settings → Pages → Source** and select the `gh-pages` branch.
2. Every push to `main` triggers `.github/workflows/deploy-frontend.yml`, which:
   - Runs `npm ci && npm run build` inside `vulnara-web/`.
   - Publishes the `dist/` folder to the `gh-pages` branch.
3. The site is live at `https://<username>.github.io/vulnara-ai/`.
4. Set `VITE_API_BASE_URL` and `VITE_WS_BASE_URL` in `vulnara-web/.env.production` (or as GitHub Actions secrets) to point to the Render backend.

---

## 6. Firebase App Distribution (Android APK)

To avoid the Google Play Store developer fees and review processes for an internal enterprise tool:

1. Have the client create a **Firebase** project.
2. In the Firebase console, go to **Release & Monitor > App Distribution**.
3. Build the release APK locally: `flutter build apk --release`.
4. Upload the generated `app-release.apk` directly into the Firebase console.
5. **Add Testers:** Enter the client's email addresses.
6. **The Client Experience:** They will receive an email on their Android phone with a secure link. They download a Firebase profile, which allows them to install the APK securely over-the-air (OTA) like a native app store experience.

---

## 7. Client Handover & Liability Checklist

### Why this matters (Legal Liability)
Vulnara is an active vulnerability scanner. It sends exploitative payloads across the internet. If you host this tool on your personal cloud account, **the origin IP traces back to your credit card and name**. If the client accidentally or maliciously scans unauthorized infrastructure, you are personally liable for the cyberattack. **Do not host client security tools on your own infrastructure.**

### The Handover Checklist

**Must be transferred to (or created by) the Client:**
- [ ] **Render Account:** Must be connected to the **client's** GitHub — not yours.
- [ ] **Neon Account:** Database ownership must be under the client's email.
- [ ] *(Optional — only for full nmap scanning)* **Cloud VM Account (Google Cloud e2-micro):** Must be registered with the **client's** credit card and phone number — not yours.
- [ ] **Domain Name & Cloudflare:** The domain `clientdomain.com` must be owned by them.
- [ ] **Neon.tech Account:** Database ownership.
- [ ] **Groq API Key:** The client must generate their own API key. If they run up a massive bill processing threat logs, it charges their account, not yours.
- [ ] **GitHub Repository / GitHub Pages:** Frontend auto-deploys from the repo. Client must have admin access to the repo (or their own fork).
- [ ] **Firebase Account:** For App Distribution and Push Notifications.

**What stays with you:**
- [ ] **The Source Code Repository:** Depending on your contract, keep the code on your GitHub. You can invite the client's Vercel account as a restricted deployment integration, or give them read-only access.
- [ ] **Your Development Environment:** Local `.env` files and local test databases.

### Final Handover Steps
1. Sit on a Zoom call with the client and have them share their screen.
2. Guide them through generating the API keys (Groq, Neon) and creating the VM (Google Cloud e2-micro or Oracle A1).
3. SSH into their VM, install Docker, and deploy the code.
4. Provide them with this Runbook and the Administrator credentials (`admin@clientdomain.com`).
5. Have them sign a final **Acceptance & Sign-off Document** stating the software has been delivered, deployed to their infrastructure, and they accept all legal liability for its usage.
