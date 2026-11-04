import asyncio
from unittest import TestCase
from unittest.mock import patch

from app.scanner.nmap_wrapper import NmapScanner
from app.triage import gemini_client


def test_nmap_child_process_is_terminated_when_scan_is_cancelled():
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

    async def run_test():
        async def create_process(*args, **kwargs):
            return process

        with patch.object(asyncio, "create_subprocess_exec", create_process):
            scanner = NmapScanner(nmap_path="nmap")
            task = asyncio.create_task(scanner._run_nmap_xml(["-sn", "127.0.0.1"]))
            await asyncio.sleep(0)
            task.cancel()

            with TestCase().assertRaises(asyncio.CancelledError):
                await task

    asyncio.run(run_test())
    assert process.terminated


def test_ai_triage_errors_propagate_without_fabricated_findings():
    async def run_test():
        async def fail_triage(*args, **kwargs):
            raise gemini_client.GeminiTriageError("provider unavailable")

        with patch.object(gemini_client, "_call_gemini", fail_triage):
            with TestCase().assertRaisesRegex(
                gemini_client.GeminiTriageError, "provider unavailable"
            ):
                await gemini_client.run_triage_call("test prompt")

    asyncio.run(run_test())
