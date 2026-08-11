"""Structured Audit Logger for Phase 3 Excel reliability engine."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Patterns for secret scrubbing
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"bearer\s+[A-Za-z0-9_.-]+", re.IGNORECASE),
    re.compile(r"(api[_-]?key|password|secret|token|auth)\s*[:=]\s*[\"']?([^\"'\s]+)", re.IGNORECASE),
]


def scrub_secrets(val: Any) -> Any:
    """Recursively scrub API keys, tokens, passwords from data structures."""
    if isinstance(val, str):
        scrubbed = val
        if "SOFIE_API_KEY" in scrubbed or "api_key" in scrubbed.lower():
            scrubbed = re.sub(r"(SOFIE_API_KEY|api_key)=([^\s&]+)", r"\1=[REDACTED]", scrubbed, flags=re.IGNORECASE)
        for pat in SECRET_PATTERNS:
            scrubbed = pat.sub("[REDACTED]", scrubbed)
        return scrubbed
    elif isinstance(val, dict):
        new_dict = {}
        for k, v in val.items():
            if any(k.lower() == secret_k for secret_k in ["api_key", "password", "token", "secret", "authorization"]):
                new_dict[k] = "[REDACTED]"
            else:
                new_dict[k] = scrub_secrets(v)
        return new_dict
    elif isinstance(val, list):
        return [scrub_secrets(item) for item in val]
    return val


class ExcelAuditLogger:
    """Structured in-memory and file execution logger for Excel tasks."""

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.logs: list[dict[str, Any]] = []

    def _record(self, event_type: str, details: dict[str, Any]) -> dict[str, Any]:
        entry = {
            "timestamp": time.time(),
            "session_id": self.session_id,
            "event": event_type,
            "details": scrub_secrets(details),
        }
        self.logs.append(entry)
        logger.info(f"[ExcelAuditLog] [{event_type}] {json.dumps(entry['details'], ensure_ascii=False)}")
        return entry

    def log_request(self, user_request: str, workbook_path: str = "") -> dict[str, Any]:
        return self._record("user_request", {"request": user_request, "workbook_path": workbook_path})

    def log_plan(self, plan_dict: dict[str, Any]) -> dict[str, Any]:
        return self._record("plan_created", plan_dict)

    def log_step_start(self, step_id: int, description: str, tool_name: str) -> dict[str, Any]:
        return self._record("step_start", {"step_id": step_id, "description": description, "tool": tool_name})

    def log_tool_execution(
        self,
        step_id: int,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
        duration_ms: float = 0.0,
    ) -> dict[str, Any]:
        return self._record(
            "tool_execution",
            {
                "step_id": step_id,
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
                "duration_ms": round(duration_ms, 2),
            },
        )

    def log_verification(
        self,
        step_id: int,
        verification_type: str,
        success: bool,
        message: str,
        duration_ms: float = 0.0,
    ) -> dict[str, Any]:
        return self._record(
            "verification",
            {
                "step_id": step_id,
                "verification_type": verification_type,
                "success": success,
                "message": message,
                "duration_ms": round(duration_ms, 2),
            },
        )

    def log_retry(self, step_id: int, attempt: int, reason: str) -> dict[str, Any]:
        return self._record("retry", {"step_id": step_id, "attempt": attempt, "reason": reason})

    def log_recovery(self, step_id: int, strategy: str, action_taken: str, success: bool) -> dict[str, Any]:
        return self._record(
            "recovery",
            {
                "step_id": step_id,
                "strategy": strategy,
                "action_taken": action_taken,
                "success": success,
            },
        )

    def log_replan(self, step_id: int, reason: str, new_plan_dict: dict[str, Any]) -> dict[str, Any]:
        return self._record(
            "replan",
            {
                "step_id": step_id,
                "reason": reason,
                "new_plan": new_plan_dict,
            },
        )

    def log_final_result(self, success: bool, output_message: str, total_duration_ms: float = 0.0) -> dict[str, Any]:
        return self._record(
            "final_result",
            {
                "success": success,
                "message": output_message,
                "total_duration_ms": round(total_duration_ms, 2),
            },
        )

    def get_logs(self) -> list[dict[str, Any]]:
        return list(self.logs)
