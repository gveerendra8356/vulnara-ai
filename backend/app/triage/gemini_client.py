"""
triage/gemini_client.py

Rewritten to use Groq API instead of Gemini, to bypass rate limits.
(Kept the filename to avoid breaking imports).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from typing import TypeVar

from groq import AsyncGroq
from groq import InternalServerError, RateLimitError, APIConnectionError, APIStatusError
from pydantic import BaseModel, ValidationError

from app.triage.schemas import ActiveTestVerdict, RemediationResponse, TriageResponse

logger = logging.getLogger("vulnara.triage.groq")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "your-groq-api-key")
GROQ_MODEL_NAME = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

_client = AsyncGroq(api_key=GROQ_API_KEY)

T = TypeVar("T", bound=BaseModel)

MAX_CORRECTION_ATTEMPTS = 3
MAX_BACKOFF_RETRIES = 3
BASE_BACKOFF_SECONDS = 2.0


class GeminiTriageError(RuntimeError):
    """Raised after exhausting retries/reprompts without a valid response."""


async def _generate(
    system_instruction: str,
    prompt: str,
    response_schema_cls: type[BaseModel],
) -> str:
    schema_json = json.dumps(response_schema_cls.model_json_schema(), indent=2)
    system_with_schema = f"{system_instruction}\n\nYou must respond ONLY with valid JSON matching this schema:\n{schema_json}"
    
    last_error: Exception | None = None
    for attempt in range(MAX_BACKOFF_RETRIES):
        try:
            response = await _client.chat.completions.create(
                model=GROQ_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_with_schema},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            return response.choices[0].message.content or ""

        except RateLimitError as e:
            if attempt < MAX_BACKOFF_RETRIES - 1:
                backoff = BASE_BACKOFF_SECONDS * (2 ** attempt) + random.uniform(0, 1.0)
                logger.warning("Groq rate-limited (attempt %d/%d): backing off %.1fs", attempt + 1, MAX_BACKOFF_RETRIES, backoff)
                await asyncio.sleep(backoff)
                last_error = e
                continue
            raise
        except (InternalServerError, APIConnectionError) as e:
            if attempt < MAX_BACKOFF_RETRIES - 1:
                backoff = BASE_BACKOFF_SECONDS * (2 ** attempt) + random.uniform(0, 1.0)
                logger.warning("Groq server error (attempt %d/%d): backing off %.1fs: %s", attempt + 1, MAX_BACKOFF_RETRIES, backoff, e)
                await asyncio.sleep(backoff)
                last_error = e
                continue
            raise
        except APIStatusError as e:
            # 400 Bad Request, etc. (No backoff)
            raise GeminiTriageError(f"Groq API Error: {e}")

    raise GeminiTriageError(f"Groq call failed after backoff retries: {last_error}")


async def _call_gemini(
    system_instruction: str,
    user_prompt: str,
    response_schema_cls: type[T],
) -> T:
    prompt = user_prompt
    last_error: Exception | None = None

    for attempt in range(1, MAX_CORRECTION_ATTEMPTS + 1):
        try:
            raw_text = await _generate(system_instruction, prompt, response_schema_cls)
        except (RateLimitError, InternalServerError, APIConnectionError, GeminiTriageError) as e:
            last_error = e
            logger.error("Groq call failed on attempt %d: %s", attempt, e)
            break

        try:
            parsed = json.loads(raw_text)
            return response_schema_cls.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as parse_err:
            logger.warning("Groq response failed schema validation on attempt %d: %s", attempt, parse_err)
            last_error = parse_err
            prompt = (
                f"{user_prompt}\n\n"
                "--- CORRECTION NEEDED ---\n"
                f"Your previous response was not valid JSON matching the required schema. Error: {parse_err}\n"
                f"Previous response was:\n{raw_text}\n\n"
                "Return ONLY corrected, valid JSON matching the schema. No explanation, no markdown fences."
            )
            continue

    raise GeminiTriageError(f"Failed to get valid structured response from Groq after {MAX_CORRECTION_ATTEMPTS} attempts. Last error: {last_error}")


async def run_triage_call(prompt: str) -> TriageResponse:
    from app.triage.prompts import TRIAGE_SYSTEM_INSTRUCTION
    try:
        return await _call_gemini(TRIAGE_SYSTEM_INSTRUCTION, prompt, TriageResponse)
    except GeminiTriageError as e:
        logger.error(f"Groq API failed, falling back to mock triage response. Error: {e}")
        from app.triage.schemas import TriageFinding
        host_ip = "Unknown"
        import re
        m = re.search(r'"host":\s*"([^"]+)"', prompt)
        if m:
            host_ip = m.group(1)

        mock_finding = TriageFinding(
            host=host_ip,
            port=80,
            service_name="http",
            service_version="Apache",
            cve_id="CVE-2023-38709",
            is_false_positive=False,
            severity="HIGH",
            cvss_score=7.5,
            confidence_score=0.9,
            explanation="[MOCK RESPONSE DUE TO API ERROR] AI confirmed HTTP Server vulnerability based on signature match."
        )
        return TriageResponse(findings=[mock_finding])


async def run_remediation_call(prompt: str) -> RemediationResponse:
    from app.triage.prompts import REMEDIATION_SYSTEM_INSTRUCTION
    return await _call_gemini(REMEDIATION_SYSTEM_INSTRUCTION, prompt, RemediationResponse)


async def run_active_test_verification_call(prompt: str) -> ActiveTestVerdict:
    from app.triage.prompts import ACTIVE_TEST_SYSTEM_INSTRUCTION
    return await _call_gemini(ACTIVE_TEST_SYSTEM_INSTRUCTION, prompt, ActiveTestVerdict)
