"""Task planner: turns a natural-language task into a list of operations.

Improvements over the original single prompt:
- Uses JSON mode (``response_format``) for reliable parsing.
- Provides few-shot examples for the ambiguous operations.
- Translates non-English tasks before planning.
- Retries on failure and caches identical tasks.
- Extracts operation *parameters* (day name, ticket type, ...) so the
  dispatcher does not need fragile regex post-processing.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import langdetect
from core.config import settings
from core.logging import get_logger
from googletrans import Translator
from operations import SUPPORTED_OPERATIONS

from agent import llm

logger = get_logger(__name__)


class PlanParseError(Exception):
    """Raised when the planner response cannot be parsed into operations."""


SYSTEM_PROMPT = f"""You are an automation agent that executes tasks described in \
plain English by emitting a plan of operations.

Rules:
- Never include any operation that deletes, removes, or destroys files or data.
- Only use operations from this exact allowed set: {SUPPORTED_OPERATIONS}.
- Output a JSON object with a single key "operations" whose value is an array.
- Each operation is an object with an "operation" field (one of the allowed \
set) plus any parameters needed.
- If the task mentions formatting a markdown file with Prettier, use \
"format_file" (do NOT use "md_to_html").
- If the task mentions ticket sales, include "query_tickets" with the \
specific "ticket_type" (Gold/Silver/Bronze).
- Required parameter keys per operation:
  - fetch_api: api_url, output_filename
  - clone_git: repo_url, commit_message
  - run_sql_query: db_filename, query
  - scrape_website: url, output_filename
  - resize_image: input_image_filename, output_image_filename (optional size)
  - transcribe_audio: input_audio_filename, output_text_filename
  - md_to_html: input_md_filename, output_html_filename
  - count_dates: day_name (e.g. "Wednesday")
  - query_tickets: ticket_type (e.g. "Gold")
Respond ONLY with the JSON object, no prose, no markdown fences.
"""

USER_TEMPLATE = """Task: "{task}"

Examples:
Task: "Count how many Wednesdays are in /data/dates.txt"
-> {{"operations": [{{"operation": "count_dates", "day_name": "Wednesday"}}]}}

Task: "Calculate total sales of Gold tickets"
-> {{"operations": [{{"operation": "query_tickets", "ticket_type": "Gold"}}]}}

Task: "Fetch https://api.example.com/users and save to users.json"
-> {{"operations": [{{"operation": "fetch_api", "api_url": "https://api.example.com/users", "output_filename": "users.json"}}]}}

Now produce the plan for the task above.
"""

_DAY_RE = re.compile(
    r"(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)", re.IGNORECASE
)
_TICKET_RE = re.compile(r"(Gold|Silver|Bronze)", re.IGNORECASE)


def detect_and_translate(task: str) -> str:
    """Detect language and translate to English if needed."""
    try:
        lang = langdetect.detect(task)
    except langdetect.LangDetectException:
        return task
    if lang == "en":
        return task
    try:
        translated = asyncio.run(Translator().translate(task, src=lang, dest="en"))
        logger.info("translated task", extra={"src": lang})
        return translated.text
    except Exception as e:  # noqa: BLE001
        logger.warning("translation failed, using original", extra={"error": str(e)})
        return task


def _extract_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _call_planner(task: str) -> list[dict[str, Any]]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(task=task)},
    ]
    last_err: Exception | None = None
    for attempt in range(settings.max_llm_retries):
        try:
            raw = llm.chat(
                messages,
                model=settings.planner_model,
                temperature=0.0,
                max_tokens=600,
                response_format={"type": "json_object"},
            )
            data = _extract_json(raw)
            ops = data.get("operations", [])
            if not isinstance(ops, list):
                raise PlanParseError("'operations' is not a list")
            return ops
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning(
                "planner attempt failed", extra={"attempt": attempt, "error": str(e)}
            )
    raise PlanParseError(f"planner failed after retries: {last_err}")


def _fallback(task_en: str) -> list[dict[str, Any]]:
    desc = task_en.lower()
    if "ticket" in desc and "sales" in desc:
        m = _TICKET_RE.search(task_en)
        ttype = m.group(0).capitalize() if m else "Gold"
        return [{"operation": "query_tickets", "ticket_type": ttype}]
    if "format" in desc and "format.md" in desc:
        return [{"operation": "format_file"}]
    if "dates.txt" in desc:
        m = _DAY_RE.search(task_en)
        if m:
            return [{"operation": "count_dates", "day_name": m.group(0).capitalize()}]
    if "contacts.json" in desc and "sort" in desc:
        return [{"operation": "sort_contacts"}]
    return []


# In-memory cache for identical tasks.
_cache: dict[str, list[dict[str, Any]]] = {}


def plan_task(task: str) -> tuple[list[dict[str, Any]], str]:
    """Return (operations, translated_task)."""
    translated = detect_and_translate(task)
    if settings.enable_llm_cache and task in _cache:
        return _cache[task], translated
    try:
        ops = _call_planner(translated)
    except PlanParseError as e:
        logger.warning("planner parse failed, using fallback", extra={"error": str(e)})
        ops = []
    if not ops:
        ops = _fallback(translated)
    if settings.enable_llm_cache:
        _cache[task] = ops
    return ops, translated
