import asyncio

import pytest

from app.scanner.nmap_wrapper import NmapScanner
from app.triage import gemini_client


@pytest.mark.asyncio
async def test_nmap_child_process_is_terminated_when_scan_is_cancelled(monkeypatch):
    class PendingProcess:
        returncode = None
        terminated = False

        async def communicate(self):
            await asyncio.Event().wait()

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        async def wait(self):
            return self.returncode

    process = PendingProcess()

    async def create_process(*args, **kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)
    scanner = NmapScanner(nmap_path="nmap")
    task = asyncio.create_task(scanner._run_nmap_xml(["-sn", "127.0.0.1"]))
    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert process.terminated


@pytest.mark.asyncio
async def test_ai_triage_errors_propagate_without_fabricated_findings(monkeypatch):
    async def fail_triage(*args, **kwargs):
        raise gemini_client.GeminiTriageError("provider unavailable")

    monkeypatch.setattr(gemini_client, "_call_gemini", fail_triage)

    with pytest.raises(gemini_client.GeminiTriageError, match="provider unavailable"):
        await gemini_client.run_triage_call("test prompt")
