"""
nmap_wrapper.py

Async wrapper around the nmap CLI. When nmap is not available (e.g.
Windows dev machines), automatically falls back to a pure-Python scanner
that probes common ports using asyncio sockets and httpx HTTP probing.

The fallback produces HostResult / OpenPort objects in the same shape as
the nmap path so the rest of the pipeline (normalizer → triage) is
completely unchanged.

Three phases match Data Flow 1:
  1. Host discovery   (-sn / TCP connect to common port)
  2. Port enumeration (top common ports)
  3. Service/version  (HTTP banner grab or raw TCP banner)
"""

from __future__ import annotations

import asyncio
import shutil
import socket
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional
import logging

logger = logging.getLogger("vulnara.scanner.nmap")


class NmapNotFoundError(RuntimeError):
    """Raised if the nmap binary isn't on PATH — triggers fallback scanner."""


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


ProgressCallback = Callable[[str, dict], Awaitable[None]]

# Well-known ports with their typical service names for the fallback scanner
COMMON_PORTS: dict[int, str] = {
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "dns",
    80: "http",
    110: "pop3",
    143: "imap",
    443: "https",
    445: "microsoft-ds",
    3306: "mysql",
    3389: "ms-wbt-server",
    5432: "postgresql",
    6379: "redis",
    8080: "http-proxy",
    8443: "https-alt",
    8888: "http-alt",
    27017: "mongodb",
}


# ---------------------------------------------------------------------------
# Pure-Python fallback scanner
# ---------------------------------------------------------------------------

async def _tcp_connect(host: str, port: int, timeout: float = 3.0) -> bool:
    """Returns True if a TCP connection can be established."""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


async def _grab_banner(host: str, port: int, timeout: float = 3.0) -> Optional[str]:
    """Attempts to read a raw TCP banner (first 512 bytes)."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        try:
            data = await asyncio.wait_for(reader.read(512), timeout=timeout)
            return data.decode(errors="replace").strip()[:200] if data else None
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
    except Exception:
        return None


async def _http_banner(host: str, port: int) -> Optional[str]:
    """Fetches HTTP Server header and page title for web ports."""
    try:
        import httpx
        scheme = "https" if port in (443, 8443) else "http"
        url = f"{scheme}://{host}:{port}/"
        async with httpx.AsyncClient(verify=False, timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(url)
            server = resp.headers.get("server", "")
            powered = resp.headers.get("x-powered-by", "")
            parts = [p for p in [server, powered] if p]
            return " | ".join(parts) if parts else f"HTTP {resp.status_code}"
    except Exception:
        return None


async def _fallback_discover(target: str) -> HostResult:
    """
    Checks if the target responds on any common port to determine liveness.
    Returns a HostResult with status 'up' or 'down'.
    """
    # Try a quick connection on port 80 or 443 first, then a few others
    probe_ports = [80, 443, 22, 8080, 3306]
    for port in probe_ports:
        if await _tcp_connect(target, port, timeout=2.0):
            return HostResult(ip=target, status="up")

    # Check via DNS resolution at least
    try:
        resolved = socket.gethostbyname(target)
        # If DNS resolves, assume host is up but firewall blocks us
        return HostResult(ip=resolved, status="up")
    except socket.gaierror:
        return HostResult(ip=target, status="down")


async def _fallback_scan_host(host: str) -> HostResult:
    """
    Probes COMMON_PORTS concurrently and grabs banners for open ones.
    """
    result = HostResult(ip=host, status="up")

    async def probe_port(port: int, service_name: str):
        if not await _tcp_connect(host, port):
            return

        # Get banner: HTTP-aware for web ports, raw TCP for others
        if port in (80, 443, 8080, 8443, 8888):
            banner = await _http_banner(host, port)
            svc_version = banner
        else:
            banner = await _grab_banner(host, port)
            svc_version = None

        result.ports.append(OpenPort(
            port=port,
            protocol="tcp",
            service_name=service_name,
            service_version=svc_version,
            banner=banner,
        ))

    await asyncio.gather(*[probe_port(p, s) for p, s in COMMON_PORTS.items()])
    # Sort by port number for consistent output
    result.ports.sort(key=lambda p: p.port)
    return result


# ---------------------------------------------------------------------------
# NmapScanner — uses nmap if available, pure-Python fallback otherwise
# ---------------------------------------------------------------------------

class NmapScanner:
    """
    Async wrapper around the nmap CLI.
    Falls back to pure-Python socket/httpx scanner if nmap is not installed.
    """

    def __init__(self, nmap_path: Optional[str] = None, timeout_seconds: int = 900):
        self.nmap_path = nmap_path or shutil.which("nmap")
        self._use_fallback = self.nmap_path is None
        if self._use_fallback:
            logger.warning(
                "nmap not found on PATH — using pure-Python fallback scanner. "
                "Install nmap for full port/service detection accuracy."
            )
        self.timeout_seconds = timeout_seconds

    # ------------------------------------------------------------------
    # Low-level subprocess runner (nmap path only)
    # ------------------------------------------------------------------
    async def _run_nmap_xml(self, args: list[str]) -> ET.Element:
        import subprocess

        cmd = [self.nmap_path, *args, "-oX", "-"]

        def run_sync():
            return subprocess.run(cmd, capture_output=True, timeout=self.timeout_seconds)

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
        if self._use_fallback:
            host = await _fallback_discover(target)
            return [host]

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
    async def scan_host(self, ip: str, port_range: str = "--top-ports 1000") -> HostResult:
        if self._use_fallback:
            return await _fallback_scan_host(ip)

        args = [
            "-sV",
            "--script=banner",
            "-Pn",
            "-T4",
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
                continue

            port_num = int(port_el.get("portid"))
            protocol = port_el.get("protocol")

            service_el = port_el.find("service")
            service_name = service_el.get("name") if service_el is not None else None
            service_product = service_el.get("product") if service_el is not None else None
            service_version = service_el.get("version") if service_el is not None else None
            version_str = " ".join(filter(None, [service_product, service_version])) or None

            banner = None
            for script_el in port_el.findall("script"):
                if script_el.get("id") == "banner":
                    banner = script_el.get("output")
                    break

            result.ports.append(OpenPort(
                port=port_num,
                protocol=protocol,
                service_name=service_name,
                service_version=version_str,
                banner=banner,
            ))

        return result

    # ------------------------------------------------------------------
    # Convenience: full pipeline with progress hooks
    # ------------------------------------------------------------------
    async def run_full_scan(
        self,
        target: str,
        port_range: str = "--top-ports 1000",
        on_progress: Optional[ProgressCallback] = None,
    ) -> list[HostResult]:
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
        total = len(up_hosts) or 1

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
