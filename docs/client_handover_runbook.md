# Vulnara: Deployment & Client Handover Runbook
---

## 1. Backend VM Setup (Free Tier Options)

> **Why a full VM is required:** Vulnara runs `nmap` for port scanning — a tool that requires raw socket access and root privileges. Serverless/container platforms (Render, Cloud Run, Railway) sandbox these capabilities and will break scanning. You **must** use a full Linux VM.

### ⚠️ The Credit Card Reality
Every major cloud provider requires a credit/debit card for **identity verification** to prevent free-tier abuse (crypto mining, spam). They will **not charge you** if you stay within the free tier limits. This is unavoidable — it is the same requirement for Oracle, Google Cloud, and AWS.

---

### Option A: Google Cloud Free Tier — e2-micro VM (Recommended Alternative)

This is the **best Oracle alternative**. Google's `e2-micro` VM is **permanently free** (not just a 12-month trial), requires a credit card for verification only, and has full root access.

**Free Tier Specs:** 1 shared vCPU, 1 GB RAM, 30 GB disk. Suitable for Vulnara's backend.

**Critical Constraint:** Create the VM in one of these US regions only for it to remain free:
`us-central1`, `us-east1`, or `us-west1`.

#### Steps
1. Have the client create a **Google Cloud Account** at [cloud.google.com](https://cloud.google.com). Enter card details (verification only — free tier stays free).
2. Go to **Compute Engine > VM Instances > Create Instance**.
3. Set the following:
   - **Machine type:** `e2-micro` (under the "General Purpose" series)
   - **Region:** `us-central1` (Iowa) — cheapest and most reliable free region
   - **Boot disk:** Ubuntu 22.04 LTS, **Standard persistent disk**, 30 GB
   - **Firewall:** Check "Allow HTTP traffic" and "Allow HTTPS traffic"
4. Click **Create** and wait for the VM to start.
5. Click **SSH** in the browser to open a terminal (no local SSH setup needed initially).

#### Firewall Rules (VPC Network)
1. Go to **VPC Network > Firewall > Create Firewall Rule**.
2. Add a rule for **TCP Port 22** (SSH).
3. *If using Cloudflare Tunnels (recommended), you do NOT need to open Port 80 or 443.*

#### Docker & Docker Compose Installation
SSH into the machine and run:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io docker-compose -y
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

#### Deploying the Backend (Restart-on-Reboot)
Create a `docker-compose.yml` file for the FastAPI backend:
```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    restart: always # Critical: Ensures the container boots on VM restart
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - GROQ_API_KEY=${GROQ_API_KEY}
```
Run `docker-compose up -d --build`.

---

### Option B: Oracle Cloud Free Tier — Ampere A1 (Original Plan)

Oracle's Always Free Tier is the most **powerful** free VM available (4 OCPUs, 24 GB RAM) but has two known friction points:
- **Signup requires a credit card** (verification only, same as Google).
- **"Out of Capacity" errors** are common for the A1 shape in popular regions — try `ap-mumbai-1`, `eu-frankfurt-1`, or `sa-saopaulo-1` if your preferred region is full.

#### Steps
1. Have the client create an **Oracle Cloud Account** at [cloud.oracle.com](https://cloud.oracle.com).
2. Go to **Compute > Instances > Create Instance**.
3. Choose the **Ampere A1 Compute (ARM)** shape. Allocate 4 OCPUs and 24 GB RAM.
4. Select **Ubuntu 22.04 / 24.04** as the image.
5. Save the SSH Key.

#### Firewall & Security Groups
1. Go to **Networking > Virtual Cloud Networks**. Click the active VCN → Security Lists.
2. Add Ingress Rules:
   - **TCP Port 22** (SSH — restrict to your IP if possible).
   - *If using Cloudflare Tunnels, you do NOT need to open Port 80 or 443.*
3. Outbound rules are open by default, allowing nmap traffic to scan targets.

#### Docker & Docker Compose Installation
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io docker-compose -y
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu
```

#### Deploying the Backend
Same `docker-compose.yml` as Option A above. Run `docker-compose up -d --build`.

---

### Option C: AWS Free Tier — t3.micro (12-Month Trial)

**Note:** AWS Free Tier (t3.micro, 1 vCPU, 1 GB RAM) is only free for the **first 12 months** after account creation. After that, it costs ~$8–10/month. Suitable only if the client plans to upgrade to a paid plan later anyway.

1. Create an **AWS Account** at [aws.amazon.com](https://aws.amazon.com).
2. Go to **EC2 > Launch Instance**.
3. Choose **Ubuntu 22.04**, instance type `t3.micro`, storage 30 GB (gp2).
4. Create a security group allowing TCP Port 22 (SSH).
5. Download the `.pem` key file.
6. Install Docker the same way as Option A.

---

### Quick Comparison

| Provider | vCPU | RAM | Duration | Credit Card | nmap Works |
|---|---|---|---|---|---|
| **Google Cloud e2-micro** | 0.25 shared | 1 GB | **Permanent** | Verification only | ✅ Yes |
| **Oracle Cloud A1** | 4 | 24 GB | **Permanent** | Verification only | ✅ Yes |
| **AWS t3.micro** | 1 | 1 GB | 12 months only | Verification only | ✅ Yes |
| Render / Cloud Run | — | — | Permanent | No card needed | ❌ No (sandboxed) |

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

To prevent unauthorized domains from hitting the API, configure CORS in `backend/app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "https://vulnara.clientdomain.com", # Vercel Production Domain
    "http://localhost:5173",            # Client local testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

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

## 5. Vercel Deployment (React App)

1. Have the client create a **Vercel** account linked to their GitHub (or invite them to a Vercel team).
2. Import the `vulnara-web` directory.
3. Set the Environment Variables:
   - `VITE_API_URL` = `https://api.clientdomain.com`
   - `VITE_WS_URL` = `wss://api.clientdomain.com/ws`
4. Click Deploy. Vercel handles the SSL and global CDN distribution.

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
- [ ] **Cloud VM Account (Google Cloud / Oracle / AWS):** Must be registered with the **client's** credit card and phone number — not yours.
- [ ] **Domain Name & Cloudflare:** The domain `clientdomain.com` must be owned by them.
- [ ] **Neon.tech Account:** Database ownership.
- [ ] **Groq API Key:** The client must generate their own API key. If they run up a massive bill processing threat logs, it charges their account, not yours.
- [ ] **Vercel Account:** For the frontend hosting.
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
