"""Safety Manager & Ambiguity Handler for Phase 3 Excel reliability."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DESTRUCTIVE_TOOLS = {"excel_delete_sheet", "excel_clear_range"}
AMBIGUOUS_KEYWORDS = ["clean", "fix", "organize", "do something with", "check", "process"]


class SafetyManager:
    """Evaluates request risk level, safety confirmation policies, and ambiguity."""

    def __init__(self, confirmed_permissions: set[str] | None = None):
        self.confirmed_permissions: set[str] = confirmed_permissions or set()

    def is_ambiguous_request(self, user_request: str) -> bool:
        """Check if request is vague or open-ended (e.g. 'Clean my Excel file')."""
        req_lower = user_request.strip().lower()
        # Short vague requests containing broad keywords without specific targets
        for kw in AMBIGUOUS_KEYWORDS:
            if kw in req_lower and len(req_lower.split()) < 6:
                return True
        return False

    def is_destructive_operation(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Determine if a proposed tool execution is destructive."""
        if tool_name in DESTRUCTIVE_TOOLS:
            if arguments.get("confirm") is not True:
                return True

        if tool_name == "excel_clear_range":
            cell_range = arguments.get("cell_range", "")
            # If clearing a large range, consider high risk
            if ":" in cell_range:
                return True

        if tool_name == "excel_delete_sheet":
            return True

        return False

    def requires_user_confirmation(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_confirmed: bool = False,
    ) -> bool:
        """Check if user confirmation must be requested before tool execution."""
        if user_confirmed:
            return False

        if tool_name in self.confirmed_permissions:
            return False

        return self.is_destructive_operation(tool_name, arguments)

    def grant_permission(self, operation: str) -> None:
        """Explicitly record permission for an operation in the active session."""
        self.confirmed_permissions.add(operation)
