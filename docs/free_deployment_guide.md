# How to Deploy Vulnara for FREE (Long-Term Strategy)

Deploying a complex stack (FastAPI, WebSockets, PostgreSQL, React, and Flutter) usually costs money. However, by strategically utilizing modern "Forever Free" tiers and generous developer platforms, you can host Vulnara for $0/month indefinitely.

Here are the two best strategies to achieve this.

---

## Strategy A: The "Zero Server" Cloud Approach (Easiest)

This approach uses managed services. It is the easiest to set up, but has minor limitations (like the backend going to sleep when nobody is using it).

### 1. Frontend (Web Dashboard) ➔ Vercel or Netlify ($0)
- **What to do:** Push your `vulnara-web` folder to GitHub. Log into [Vercel](https://vercel.com/) and import the repository.
- **Settings:** Build command: `npm run build`. Output directory: `dist`.
- **Why:** Vercel provides a forever-free tier with global CDN hosting, automatic SSL, and unlimited bandwidth for most hobby projects.

### 2. Database (PostgreSQL) ➔ Neon.tech or Supabase ($0)
- **What to do:** Create a free account on [Neon.tech](https://neon.tech/) (Serverless Postgres) or [Supabase](https://supabase.com/).
- **Why:** Neon gives you 500MB of storage and generous compute credits for free. Supabase gives you a 500MB database, though Supabase pauses your project after 1 week of zero activity (you just have to click "Unpause"). Neon scales to zero but wakes up instantly.
- **Action:** Copy the provided `DATABASE_URL` string.

### 3. Backend API (FastAPI) ➔ Render or Koyeb ($0)
- **What to do:** Push the `backend` folder to GitHub. Create a "Web Service" on [Render.com](https://render.com/).
- **Settings:** Set the environment to Python. Start command: `uvicorn app.main:app --host 0.0.0.0 --port 10000`. Add your `DATABASE_URL` and `GROQ_API_KEY` to the Environment Variables settings.
- **The Catch:** Render’s free tier **spins down** after 15 minutes of inactivity. The next time a Client requests a scan, the backend will take ~30 seconds to wake up. However, it supports WebSockets out of the box and is completely free.

### 4. AI Engine ➔ Groq API ($0)
- **What to do:** Groq currently offers a generous free tier for developers. Simply use your free `GROQ_API_KEY`. Be mindful of the Requests Per Minute (RPM) limits on the free tier.

---

## Strategy B: The "Always Free VPS" Approach (Best for Long-Term)

If you do not want your backend to ever fall asleep and you want a true production feel without limits, you should use **Oracle Cloud's Always Free** tier. 

### 1. The Server (Backend + Database) ➔ Oracle Cloud Always Free ($0 Forever)
- **What you get:** Oracle Cloud offers an incredibly generous "Always Free" tier. You can provision an ARM Compute Instance with up to **4 OCPUs and 24 GB of RAM** entirely for free, forever.
- **What to do:** 
  1. Sign up for Oracle Cloud (requires a credit card for verification, but won't be charged if you select "Always Free" resources).
  2. Spin up an Ubuntu ARM instance.
  3. SSH into the server and install **Docker** and **Docker Compose**.
  4. Write a `docker-compose.yml` file to run both your FastAPI backend and a PostgreSQL database container directly on the server.
- **Why this is better:** Your backend will run 24/7. It will never sleep. You don't have to worry about database size limits (you get 200GB of block storage for free). You have total control over Nginx and WebSockets.

### 2. Frontend ➔ Vercel ($0)
- Keep the frontend on Vercel. There is no reason to host static files on your VPS when Vercel offers a free global CDN. Just point your Vercel environment variables (`VITE_API_URL`) to your Oracle VPS IP address (or domain).

### 3. Domain Name ➔ DuckDNS or Freenom ($0)
- To secure your Oracle server with HTTPS (required for Secure WebSockets `wss://`), you need a domain name.
- **What to do:** Use [DuckDNS](https://www.duckdns.org/) to get a free sub-domain (e.g., `vulnara.duckdns.org`). Point it to your Oracle VPS IP address, and use **Certbot** to generate a free SSL certificate.

---

## What about the Mobile App (Flutter)?

Distributing a mobile app through official channels costs money:
- **Google Play Store:** One-time $25 fee.
- **Apple App Store:** $99/year fee.

**To deploy the mobile app for 100% FREE:**
1. **For Android:** Build the APK (`flutter build apk --release`). Go to your GitHub repository, create a "Release", and attach the `.apk` file. Users can download and install it directly to their Android phones for free (sideloading).
2. **For iOS:** Apple strictly prohibits sideloading without a paid developer account. The only free way to run the app on an iPhone is to plug it into a Mac with Xcode, sign it with a free personal team, and install it directly via USB (this expires every 7 days).

---

## Summary Checklist for the Ultimate Free Stack

1. **Frontend:** Hosted on **Vercel** (Free).
2. **Database:** Hosted in a Docker container on an **Oracle Cloud Free ARM VPS** (Free).
3. **Backend API:** Hosted via Docker on the same **Oracle Cloud VPS**, behind Nginx (Free & 24/7 Uptime).
4. **Domain & SSL:** **DuckDNS** + **Let's Encrypt** (Free).
5. **AI:** **Groq** Developer API (Free).
6. **Mobile App:** Distribute the Android `.apk` via **GitHub Releases** (Free).
