# How to Deploy Vulnara for FREE (Current Stack)

Deploying a complex stack (FastAPI, WebSockets, PostgreSQL, React, and Flutter) usually costs money. However, by strategically utilizing modern "Forever Free" tiers and generous developer platforms, you can host Vulnara for **$0/month** indefinitely.

The stack documented here is the **actual deployed stack** as of 2026.

---

## The Current Free Stack

| Component | Service | Cost |
|---|---|---|
| Backend API | [Render](https://render.com) Web Service | $0 |
| Database | [Neon](https://neon.tech) Serverless Postgres | $0 |
| Frontend | [GitHub Pages](https://pages.github.com) | $0 |
| AI Engine | [Groq](https://console.groq.com) Developer API | $0 |
| Keep-Alive | [cron-job.org](https://cron-job.org) | $0 |
| Mobile (Android) | GitHub Releases (APK sideload) | $0 |

---

## 1. Frontend (Web Dashboard) → GitHub Pages ($0)

- **What to do:** The repo includes `.github/workflows/deploy-frontend.yml`. Every push to `main` automatically builds `vulnara-web/` and deploys the `dist/` folder to the `gh-pages` branch.
- **Enable Pages:** GitHub repo → **Settings → Pages → Source:** `gh-pages` branch.
- **Why:** GitHub Pages provides free static hosting with global CDN and automatic HTTPS — no dashboard clicks needed after the first setup.
- **SPA routing:** A `404.html` shim in `vulnara-web/public/` redirects unknown paths back to `index.html` so React Router works on refresh and direct links.
- **Live at:** `https://<username>.github.io/vulnara-ai/`

---

## 2. Database (PostgreSQL) → Neon.tech ($0)

- **What to do:** Create a free account at [Neon.tech](https://neon.tech/). Create a new Project and copy the connection string.
- **Driver note:** Convert the Neon URL to the `asyncpg` prefix before pasting into Render:
  ```
  # From Neon: postgres://user:pass@host/db?sslmode=require
  # To paste:  postgresql+asyncpg://user:pass@host/db
  ```
  `core/db.py` handles the SSL requirement via `connect_args` — the `?sslmode=` suffix will break `asyncpg`.
- **Why:** Neon gives 500 MB storage and scales to zero (wakes in < 1 s). The keep-alive cron keeps it awake continuously.

---

## 3. Backend API (FastAPI) → Render ($0)

- **What to do:** The repo root contains `render.yaml`. On Render: **New → Blueprint** → connect the GitHub repo. Render reads the Blueprint and provisions everything.
- **Required env vars to fill in when prompted:**
  - `DATABASE_URL` — from Neon (step 2 above, `asyncpg` prefix)
  - `GROQ_API_KEY` — from [console.groq.com](https://console.groq.com)
  - `CORS_ORIGINS` — your GitHub Pages URL + `http://localhost:5173`
- **The Catch:** Render's free tier **spins down** after 15 minutes of inactivity. The next request after sleep takes ~20–30 s to wake up.
- **Solution:** Use cron-job.org (step 5 below) to ping `/health` every 5 minutes, preventing sleep.
- **Why Render over Oracle/Google Cloud VMs:** No VM management, SSH, Docker, or Nginx config required. `render.yaml` codifies everything. Auto-redeploys on every `git push`.

> **Important limitation:** Render's free containers are sandboxed — they cannot run `nmap` (raw socket scanning). Vulnara's `/health` and AI features work fine; only the active nmap-based port scan portion requires a real VM (see below).

---

## 4. AI Engine → Groq API ($0)

- **What to do:** Get your API key at [console.groq.com](https://console.groq.com/). Set it as `GROQ_API_KEY` in Render's environment.
- **Why:** Groq offers a generous free tier (RPM-limited). Sufficient for development and small-team usage.

---

## 5. Keep-Alive → cron-job.org ($0)

- **What to do:** Create a free account at [cron-job.org](https://cron-job.org/).
- **Create a job:** `GET https://<your-app>.onrender.com/health` — every **5 minutes**.
- **Why this works:** `/health` runs a real `SELECT 1` against Neon — one ping keeps both the Render service and Neon's compute node awake simultaneously.

---

## If You Need Real nmap Scanning (Optional VM Path)

If you need the full active port-scanning feature (which requires raw socket access), you need a full Linux VM. The cheapest always-free option is **Google Cloud e2-micro** (1 shared vCPU, 1 GB RAM, permanent free in `us-central1/us-east1/us-west1`).

Oracle's Always Free ARM tier was cut in 2026 and is no longer a reliable option.

```bash
# On the GCP e2-micro VM:
sudo apt update && sudo apt install docker.io docker-compose -y
docker-compose up -d --build
```

---

## What about the Mobile App (Flutter)?

Distributing a mobile app through official channels costs money:
- **Google Play Store:** One-time $25 fee.
- **Apple App Store:** $99/year fee.

**To deploy the mobile app for 100% FREE:**

1. **For Android:** Build the APK (`flutter build apk --release`). Go to your GitHub repository, create a **Release**, and attach the `.apk` file. Users can download and sideload it directly onto their Android phones.
2. **For iOS:** Apple strictly prohibits sideloading without a paid developer account. The only free way to run the app on an iPhone is to plug it into a Mac with Xcode, sign it with a free personal team, and install it directly via USB (expires every 7 days).

---

## Summary Checklist for the Current Free Stack

1. **Frontend:** Deployed automatically to **GitHub Pages** on every push via GitHub Actions (Free).
2. **Database:** **Neon** serverless Postgres (Free, scales to zero, kept awake by cron ping).
3. **Backend API:** **Render** Web Service deployed via `render.yaml` Blueprint (Free, kept awake by cron ping).
4. **AI:** **Groq** Developer API (Free).
5. **Keep-Alive:** **cron-job.org** pinging `/health` every 5 minutes (Free).
6. **Mobile App:** Distribute the Android `.apk` via **GitHub Releases** (Free).
