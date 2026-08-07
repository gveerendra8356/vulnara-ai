# Running nmap Without Running the Backend as Root

## The core problem

`nmap`'s faster/stealthier scan techniques need raw socket access:
- **SYN scan (`-sS`)** — nmap's default and fastest port scan, builds raw TCP packets.
- **OS detection (`-O`)** — also raw sockets.
- **Ping sweep (`-sn`)** with ICMP — raw sockets for ICMP echo.

Historically the answer was "just run nmap as root." You explicitly don't
want to run the whole FastAPI process as root — correctly, since a bug or
RCE anywhere in your app would then have full root on the VM. The fix is
**Linux capabilities**, not root.

## Option A (recommended): grant capabilities to the nmap binary itself

Linux capabilities let a binary have *just* the specific kernel privileges
it needs, not full root. `CAP_NET_RAW` covers raw socket creation;
`CAP_NET_ADMIN` covers a few additional interface-level operations some
nmap features use (e.g. some timing/interface options).

```bash
# One-time setup on the Oracle Cloud VM (or in the Docker image build step)
sudo setcap cap_net_raw,cap_net_admin+eip $(which nmap)

# Verify it took:
getcap $(which nmap)
# Expected output: /usr/bin/nmap cap_net_raw,cap_net_admin=eip
```

With this set, **any** user (including a non-root `vulnara` service
account) can run `nmap -sS` / `-O` / `-sn` successfully, because the
capability lives on the binary, not the process's effective UID.

Your FastAPI process (and the `vulnara` user it runs as) never needs
`sudo` or root — it just shells out to `nmap`, which already has exactly
the two capabilities it needs and nothing else.

## Option B: same idea, inside Docker

Since the backend is Dockerized, you have two sub-choices:

**B1 — bake the setcap call into the image (preferred):**
```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends nmap libcap2-bin \
    && setcap cap_net_raw,cap_net_admin+eip /usr/bin/nmap \
    && rm -rf /var/lib/apt/lists/*

# Create and switch to a non-root user for the app process itself
RUN useradd --create-home vulnara
USER vulnara

WORKDIR /app
COPY --chown=vulnara:vulnara . .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
This is the cleanest setup: the container itself never runs as root at
the process level, and `nmap` carries its own scoped capability.

> Caveat: capabilities set via `setcap` inside a Docker image are
> preserved in the image layer, but the **container runtime** still needs
> to allow those capabilities to actually take effect at runtime on some
> Docker configurations. If you find `setcap` capabilities aren't being
> honored at container runtime (this varies by Docker/kernel version),
> fall back to B2.

**B2 — grant capabilities at the container level instead:**
```yaml
# docker-compose.yml
services:
  backend:
    build: .
    cap_add:
      - NET_RAW
      - NET_ADMIN
    # Do NOT use privileged: true — that grants everything, defeating the point.
    ...
```
Here the *container* (not necessarily nmap specifically) is allowed
`NET_RAW`/`NET_ADMIN`, and the app inside can still run as the non-root
`vulnara` user. Slightly broader than B1 (any process in the container
gets the capability, not just nmap), but still dramatically narrower than
running the container as root or `--privileged`.

Use B1 if it works cleanly on your Oracle VM's kernel/Docker version;
fall back to B2 otherwise. Test with `getcap` (B1) or by simply running a
`-sS` scan as the non-root user and confirming it doesn't fall back to
a "requires root privileges" error (B2).

## Option C: fallback if capabilities aren't available at all

If for some reason neither option works in your environment, nmap can run
fully unprivileged using `-sT` (TCP connect scan) instead of `-sS`. This
uses the OS's normal `connect()` syscall rather than raw packets — no
special privileges needed at all. Trade-offs: slower, and more visible to
the target (completes the full TCP handshake rather than nmap's
half-open SYN scan), which also means it's noisier against IDS/logging
on the target side. `-sV` version detection and `--script=banner` both
work fine over `-sT`. If you go this route, change the scan flags in
`nmap_wrapper.py`'s `scan_host()` from the implicit default (`-sS` when
run privileged) by adding `-sT` explicitly:

```python
args = ["-sT", "-sV", "--script=banner", "-T4", *port_range.split(), ip]
```

## Recommendation for this project

Use **Option A/B1** (setcap on the nmap binary inside the Docker image).
It's the standard, well-documented approach for exactly this situation
(services that need raw sockets without running as root), keeps your
attack surface minimal, and needs zero code changes — nmap will use
`-sS` by default once the capability is present, no `-sT` fallback flag
needed.
