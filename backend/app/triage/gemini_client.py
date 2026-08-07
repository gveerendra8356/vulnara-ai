"""
triage/gemini_client.py

Wraps the Gemini free-tier API for both the triage call and the
remediation call, with:
  - Structured output enforcement via response_mime_type="application/json"
    + response_schema, so Gemini is constrained at generation time, not
    just asked nicely.
  - A Pydantic validation pass on top regardless, since schema enforcement
    narrows the *shape* Gemini can emit but doesn't guarantee every field
    survives intact under generation pressure.
  - One corrective re-prompt if parsing/validation fails: we send the
    invalid output back to Gemini with the validation error and ask it
    to fix it, rather than immediately failing the whole triage batch.
  - Retry with exponential backoff + jitter specifically for rate-limit
    and server-overload errors.

SDK NOTE: this uses the current `google-genai` package (`from google import
genai`), not the older `google-generativeai` package -- that one is
deprecated as of this writing and actively warns on import. `google-genai`
has a native async client (`client.aio.models.generate_content`) and,
importantly, accepts a Pydantic model class directly as `response_schema`
-- it handles the schema conversion internally rather than us needing to
call `.model_json_schema()` and hope Gemini's schema subset supports
whatever `$defs`/`$ref` structure Pydantic happens to emit for nested
models (which was a real risk with the manual-schema approach). Check
https://ai.google.dev/gemini-api/docs for current model names/limits --
both change over time.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from typing import TypeVar

from google import genai
from google.genai import types as genai_types
from google.genai import errors as genai_errors
from pydantic import BaseModel, ValidationError

from app.triage.schemas import ActiveTestVerdict, RemediationResponse, TriageResponse

logger = logging.getLogger("vulnara.triage.gemini")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "your-gemini-api-key")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

_client = genai.Client(api_key=GEMINI_API_KEY)

T = TypeVar("T", bound=BaseModel)

MAX_CORRECTION_ATTEMPTS = 3  # retries for malformed-output reprompting
MAX_BACKOFF_RETRIES = 3      # retries for transient rate-limit/server errors
BASE_BACKOFF_SECONDS = 2.0


class GeminiTriageError(RuntimeError):
    """Raised after exhausting retries/reprompts without a valid response."""


async def _generate(
    system_instruction: str,
    prompt: str,
    response_schema_cls: type[BaseModel],
) -> str:
    """
    Single Gemini call with backoff on transient failures. Returns the
    raw text response (already JSON per response_mime_type) -- validation
    happens one level up so this function's only concern is "did we get
    a response at all."
    """
    config = genai_types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=response_schema_cls,  # Pydantic class passed directly
        temperature=0.2,  # low temperature: consistent, conservative risk
        # judgments, not creative variation -- this is a risk assessment
        # tool, not a writing assistant.
    )

    last_error: Exception | None = None
    for attempt in range(MAX_BACKOFF_RETRIES):
        try:
            response = await _client.aio.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config=config,
            )
            return response.text

        except genai_errors.ClientError as e:
            # google-genai raises ClientError for 4xx including 429; check
            # status code to only backoff-retry on rate limiting, not on
            # e.g. a 400 (bad request) which retrying won't fix.
            if getattr(e, "code", None) == 429 and attempt < MAX_BACKOFF_RETRIES - 1:
                backoff = BASE_BACKOFF_SECONDS * (2 ** attempt) + random.uniform(0, 1.0)
                logger.warning(
                    "Gemini rate-limited (attempt %d/%d): backing off %.1fs",
                    attempt + 1, MAX_BACKOFF_RETRIES, backoff,
                )
                await asyncio.sleep(backoff)
                last_error = e
                continue
            raise

        except genai_errors.ServerError as e:
            # 5xx -- overloaded/unavailable, worth retrying with backoff.
            if attempt < MAX_BACKOFF_RETRIES - 1:
                backoff = BASE_BACKOFF_SECONDS * (2 ** attempt) + random.uniform(0, 1.0)
                logger.warning(
                    "Gemini server error (attempt %d/%d): backing off %.1fs: %s",
                    attempt + 1, MAX_BACKOFF_RETRIES, backoff, e,
                )
                await asyncio.sleep(backoff)
                last_error = e
                continue
            raise

    raise GeminiTriageError(f"Gemini call failed after backoff retries: {last_error}")


async def _call_gemini(
    system_instruction: str,
    user_prompt: str,
    response_schema_cls: type[T],
) -> T:
    """
    Full call-validate-correct loop. Returns a validated instance of
    response_schema_cls, or raises GeminiTriageError if it can't get one
    within MAX_CORRECTION_ATTEMPTS attempts (each of which itself retries
    transient failures internally via _generate).
    """
    prompt = user_prompt
    last_error: Exception | None = None

    for attempt in range(1, MAX_CORRECTION_ATTEMPTS + 1):
        try:
            raw_text = await _generate(system_instruction, prompt, response_schema_cls)
        except (genai_errors.ClientError, genai_errors.ServerError, GeminiTriageError) as e:
            last_error = e
            logger.error("Gemini call failed on attempt %d: %s", attempt, e)
            break  # transient infra failure -- reprompting won't help, stop here

        try:
            parsed = json.loads(raw_text)
            return response_schema_cls.model_validate(parsed)

        except (json.JSONDecodeError, ValidationError) as parse_err:
            logger.warning(
                "Gemini response failed schema validation on attempt %d: %s",
                attempt, parse_err,
            )
            last_error = parse_err
            # Corrective re-prompt: send the bad output + the error back
            # and ask for a fixed version, rather than repeating the
            # identical prompt and likely getting an identical failure.
            prompt = (
                f"{user_prompt}\n\n"
                "--- CORRECTION NEEDED ---\n"
                "Your previous response was not valid JSON matching the "
                f"required schema. Error: {parse_err}\n"
                f"Previous response was:\n{raw_text}\n\n"
                "Return ONLY corrected, valid JSON matching the schema. "
                "No explanation, no markdown fences."
            )
            continue

    raise GeminiTriageError(
        f"Failed to get valid structured response from Gemini after "
        f"{MAX_CORRECTION_ATTEMPTS} attempts. Last error: {last_error}"
    )


# ----------------------------------------------------------------------
# Public functions used by pipeline.py and remediation_service.py
# ----------------------------------------------------------------------
async def run_triage_call(prompt: str) -> TriageResponse:
    from app.triage.prompts import TRIAGE_SYSTEM_INSTRUCTION  # local import avoids cycle
    return await _call_gemini(TRIAGE_SYSTEM_INSTRUCTION, prompt, TriageResponse)


async def run_remediation_call(prompt: str) -> RemediationResponse:
    from app.triage.prompts import REMEDIATION_SYSTEM_INSTRUCTION
    return await _call_gemini(REMEDIATION_SYSTEM_INSTRUCTION, prompt, RemediationResponse)


async def run_active_test_verification_call(prompt: str) -> ActiveTestVerdict:
    from app.triage.prompts import ACTIVE_TEST_SYSTEM_INSTRUCTION
    return await _call_gemini(ACTIVE_TEST_SYSTEM_INSTRUCTION, prompt, ActiveTestVerdict)
