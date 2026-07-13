"""Dispatcher: executes a plan's operations via the operation registry."""
from __future__ import annotations

import inspect
import re

from core.logging import get_logger
from operations import OPERATION_REGISTRY

logger = get_logger(__name__)

_DAY_RE = re.compile(
    r"(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)", re.IGNORECASE
)
_TICKET_RE = re.compile(r"(Gold|Silver|Bronze)", re.IGNORECASE)


def _bind_params(func, op: dict, translated_task: str) -> dict:
    """Build the kwargs for *func*, filling missing required params from the
    translated task where a heuristic is available."""
    sig = inspect.signature(func)
    params = {k: v for k, v in op.items() if k != "operation"}

    for name, p in sig.parameters.items():
        if name in params:
            continue
        if p.default is not inspect.Parameter.empty:
            continue
        if name == "day_name":
            m = _DAY_RE.search(translated_task)
            if m:
                params["day_name"] = m.group(0).capitalize()
        elif name == "ticket_type":
            m = _TICKET_RE.search(translated_task)
            if m:
                params["ticket_type"] = m.group(0).capitalize()

    return params


def dispatch(operations: list[dict], translated_task: str) -> str:
    results: list[str] = []
    for op in operations:
        name = op.get("operation") if isinstance(op, dict) else None
        if not name:
            results.append("Error: operation missing 'operation' field.")
            continue
        if "delete" in name.lower():
            results.append("Error: data deletion is not permitted.")
            continue

        func = OPERATION_REGISTRY.get(name)
        if func is None:
            results.append(f"Operation '{name}' is not supported.")
            continue

        try:
            params = _bind_params(func, op, translated_task)
            result = func(**params)
            results.append(result)
        except Exception as e:  # noqa: BLE001
            logger.exception("operation failed", extra={"operation": name})
            results.append(f"Error executing {name}: {e}")

    return "\n".join(results)
