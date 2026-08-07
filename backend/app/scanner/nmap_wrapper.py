"""
nmap_wrapper.py

Async wrapper around the nmap CLI (NOT python-nmap) using
asyncio.create_subprocess_exec so scans never block the FastAPI event loop.

We shell out to the real `nmap` binary and parse its XML output (-oX -)
ourselves with xml.etree.ElementTree. Reasons for this over python-nmap:
  - python-nmap wraps subprocess.Popen synchronously under the hood,
    which would block the event loop unless run in a thread executor.
  - Shelling out directly gives us full control over flags, timeouts,
    and streaming partial progress (needed for the WebSocket updates).

This module performs three phases, matching Data Flow 1 in the project spec:
  1. Host discovery   (-sn)
  2. Port enumeration  (-p<range> --open)
  3. Service/version + banner grab (-sV)

Each phase returns plain Python data structures. Nothing here writes to the
database or touches AI/triage logic — this module's only job is to produce
clean, structured recon output.
"""

from __future__ import annotations

import asyncio
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional


class NmapNotFoundError(RuntimeError):
    """Raised if the nmap binary isn't on PATH in the container/VM."""


class NmapExecutionError(RuntimeError):
    """Raised if nmap exits non-zero or produces unparsable output."""


@dataclass
class OpenPort:
    port: int
    protocol: str  # "tcp" | "udp"
    service_name: Optional[str]
    service_version: Optional[str]
    banner: Optional[str]


@dataclass
class HostResult:
    ip: str
    status: str  # "up" | "down"
    ports: list[OpenPort] = field(default_factory=list)


# Type alias for an optional progress callback the caller can pass in,
# e.g. to push WebSocket messages as phases complete.
ProgressCallback = Callable[[str, dict], Awaitable[None]]


class NmapScanner:
    """
    Thin async wrapper around the nmap CLI.

    Usage:
        scanner = NmapScanner()
        hosts = await scanner.discover_hosts("example.com")
        for host in hosts:
            result = await scanner.scan_host(host.ip)
    """

    def __init__(self, nmap_path: Optional[str] = None, timeout_seconds: int = 900):
        self.nmap_path = nmap_path or shutil.which("nmap")
        if not self.nmap_path:
            raise NmapNotFoundError(
                "nmap binary not found on PATH. Install it in the Docker image "
                "(apt-get install -y nmap) and ensure it's in the container's PATH."
            )
        self.timeout_seconds = timeout_seconds

    # ------------------------------------------------------------------
    # Low-level subprocess runner
    # ------------------------------------------------------------------
    async def _run_nmap_xml(self, args: list[str]) -> ET.Element:
        """
        Runs nmap with the given args plus `-oX -` (XML to stdout) and
        returns the parsed XML root element. Raises NmapExecutionError on
        failure or on timeout.
        """
        cmd = [self.nmap_path, *args, "-oX", "-"]
        import subprocess

        def run_sync():
            return subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.timeout_seconds,
            )

        try:
            proc = await asyncio.to_thread(run_sync)
        except subprocess.TimeoutExpired:
            raise NmapExecutionError(
                f"nmap timed out after {self.timeout_seconds}s running: {' '.join(cmd)}"
            )
        except Exception as e:
            raise NmapExecutionError(f"Failed to execute nmap: {e}")

        if proc.returncode != 0:
            raise NmapExecutionError(
                f"nmap exited {proc.returncode}: {proc.stderr.decode(errors='replace')}"
            )

        try:
            return ET.fromstring(proc.stdout)
        except ET.ParseError as e:
            raise NmapExecutionError(f"Failed to parse nmap XML output: {e}")

    # ------------------------------------------------------------------
    # Phase 1: Host discovery
    # ------------------------------------------------------------------
    async def discover_hosts(self, target: str) -> list[HostResult]:
        """
        Ping-sweep style discovery (-sn = no port scan, just liveness).
        For a single IP/domain target this will almost always return one
        host, but we keep it list-based since `target` could be a CIDR
        range in future (e.g. client authorizes a whole subnet).
        """
        root = await self._run_nmap_xml(["-sn", "-Pn", "-T4", target])

        hosts: list[HostResult] = []
        for host_el in root.findall("host"):
            status_el = host_el.find("status")
            status = status_el.get("state") if status_el is not None else "unknown"

            addr_el = host_el.find("address")
            ip = addr_el.get("addr") if addr_el is not None else None
            if ip is None:
                continue

            hosts.append(HostResult(ip=ip, status=status))

        return hosts

    # ------------------------------------------------------------------
    # Phase 2 + 3: Port enumeration + service/version + banner grab
    # ------------------------------------------------------------------
    async def scan_host(
        self,
        ip: str,
        port_range: str = "--top-ports 1000",
    ) -> HostResult:
        """
        Runs a combined port-enum + service/version detection scan against
        a single live host. -sV performs version detection which includes
        banner grabbing for most services; we additionally pull the raw
        banner via NSE's banner script for protocols where -sV alone is
        thin (e.g. plain-text protocols like FTP/SMTP/Telnet).

        `port_range` accepts either an explicit nmap port spec
        (e.g. "-p 1-65535" or "-p 22,80,443") or a top-ports shortcut
        (default: top 1000 TCP ports — a reasonable default for a
        time-boxed scan; full -p- is available for deeper authorized scans).
        """
        args = [
            "-sV",  # service + version detection (implies banner grabbing)
            "--script=banner",  # NSE script: explicit raw banner grab as backup
            "-Pn",  # skip host discovery (assume up) to bypass unprivileged ICMP drops
            "-T4",  # timing template: aggressive but safe for most targets
            *port_range.split(),
            ip,
        ]

        root = await self._run_nmap_xml(args)
        host_el = root.find("host")
        if host_el is None:
            return HostResult(ip=ip, status="down")

        status_el = host_el.find("status")
        status = status_el.get("state") if status_el is not None else "unknown"

        result = HostResult(ip=ip, status=status)

        ports_el = host_el.find("ports")
        if ports_el is None:
            return result

        for port_el in ports_el.findall("port"):
            state_el = port_el.find("state")
            if state_el is None or state_el.get("state") != "open":
                continue  # only care about open ports for the threat matrix

            port_num = int(port_el.get("portid"))
            protocol = port_el.get("protocol")

            service_el = port_el.find("service")
            service_name = service_el.get("name") if service_el is not None else None
            service_product = service_el.get("product") if service_el is not None else None
            service_version = service_el.get("version") if service_el is not None else None

            # Combine product + version into one human-readable string,
            # e.g. "Apache httpd 2.4.41" -- this is what gets matched
            # against CVE data in the AI triage step.
            version_str = " ".join(filter(None, [service_product, service_version])) or None

            # Pull raw banner from the NSE banner script output, if present.
            banner = None
            for script_el in port_el.findall("script"):
                if script_el.get("id") == "banner":
                    banner = script_el.get("output")
                    break

            result.ports.append(
                OpenPort(
                    port=port_num,
                    protocol=protocol,
                    service_name=service_name,
                    service_version=version_str,
                    banner=banner,
                )
            )

        return result

    # ------------------------------------------------------------------
    # Convenience: full pipeline for a single target with progress hooks
    # ------------------------------------------------------------------
    async def run_full_scan(
        self,
        target: str,
        port_range: str = "--top-ports 1000",
        on_progress: Optional[ProgressCallback] = None,
    ) -> list[HostResult]:
        """
        Runs discovery -> per-host port/service scan, invoking on_progress
        after each phase. This is the function the FastAPI background task
        calls; it contains no FastAPI/DB/WebSocket imports so it stays unit
        testable in isolation.
        """
        if on_progress:
            await on_progress("host_discovery", {"percent_complete": 0})

        live_hosts = await self.discover_hosts(target)
        up_hosts = [h for h in live_hosts if h.status == "up"]

        if on_progress:
            await on_progress(
                "host_discovery",
                {"percent_complete": 100, "hosts_found": len(up_hosts)},
            )

        results: list[HostResult] = []
        total = len(up_hosts) or 1  # avoid div-by-zero if target itself is down

        for i, host in enumerate(up_hosts, start=1):
            if on_progress:
                await on_progress(
                    "port_scan",
                    {"percent_complete": int((i - 1) / total * 100), "current_host": host.ip},
                )

            scanned = await self.scan_host(host.ip, port_range=port_range)
            results.append(scanned)

            if on_progress:
                await on_progress(
                    "banner_grab",
                    {
                        "percent_complete": int(i / total * 100),
                        "current_host": host.ip,
                        "ports_found": len(scanned.ports),
                    },
                )

        return results
