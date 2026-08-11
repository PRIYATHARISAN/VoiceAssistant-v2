"""Conservative Error Recovery & Resolution Engine for Phase 3 Excel operations."""

from __future__ import annotations

import difflib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from cptr.utils.excel.backend_base import ExcelBackend, ExcelResult

logger = logging.getLogger(__name__)


class RecoveryAction:
    """Represents a proposed recovery correction."""

    def __init__(
        self,
        can_recover: bool,
        strategy: str,
        action_description: str,
        updated_arguments: dict[str, Any] | None = None,
        requires_user_clarification: bool = False,
        clarification_prompt: str = "",
    ):
        self.can_recover: bool = can_recover
        self.strategy: str = strategy
        self.action_description: str = action_description
        self.updated_arguments: dict[str, Any] = updated_arguments or {}
        self.requires_user_clarification: bool = requires_user_clarification
        self.clarification_prompt: str = clarification_prompt


class ExcelRecoveryHandler:
    """Analyzes execution and verification failures and determines conservative recovery actions."""

    def __init__(self, backend: ExcelBackend, max_retries: int = 3):
        self.backend = backend
        self.max_retries = max_retries

    def resolve_sheet_name(self, requested_name: str) -> RecoveryAction:
        """Resolve sheet name mismatch conservatively.

        If exactly ONE reasonable match exists, selects it.
        If MULTIPLE plausible matches exist, requires user clarification (DO NOT GUESS).
        """
        if getattr(self.backend, "wb", None) is None and getattr(self.backend, "file_path", ""):
            self.backend.open_workbook(self.backend.file_path)

        sheets_res = self.backend.list_sheets()
        if not sheets_res.success or not sheets_res.data:
            return RecoveryAction(
                can_recover=False,
                strategy="sheet_resolution",
                action_description="Could not list workbook sheets.",
            )

        available_sheets = (
            sheets_res.data.get("sheets", [])
            if isinstance(sheets_res.data, dict)
            else sheets_res.data
            if isinstance(sheets_res.data, list)
            else []
        )
        if requested_name in available_sheets:
            return RecoveryAction(
                can_recover=True,
                strategy="sheet_resolution",
                action_description=f"Sheet '{requested_name}' exists exactly.",
                updated_arguments={"sheet_name": requested_name},
            )

        req_clean = requested_name.lower().strip()
        candidates = []

        for sheet in available_sheets:
            s_clean = sheet.lower().strip()
            if req_clean in s_clean or s_clean in req_clean:
                candidates.append(sheet)

        if not candidates:
            # Try fuzzy match
            close_matches = difflib.get_close_matches(requested_name, available_sheets, n=3, cutoff=0.5)
            candidates.extend(close_matches)

        # Remove duplicates preserving order
        candidates = list(dict.fromkeys(candidates))

        if len(candidates) == 1:
            best_match = candidates[0]
            logger.info(f"[RecoveryHandler] Unambiguous sheet match found: '{requested_name}' -> '{best_match}'")
            return RecoveryAction(
                can_recover=True,
                strategy="sheet_name_recovery",
                action_description=f"Mapped requested sheet '{requested_name}' to existing sheet '{best_match}'.",
                updated_arguments={"sheet_name": best_match},
            )
        elif len(candidates) > 1:
            prompt = f"Multiple plausible sheet matches found for '{requested_name}': {candidates}. Which worksheet did you mean?"
            logger.info(f"[RecoveryHandler] Ambiguous sheet matches: {prompt}")
            return RecoveryAction(
                can_recover=False,
                strategy="sheet_name_ambiguity",
                action_description=prompt,
                requires_user_clarification=True,
                clarification_prompt=prompt,
            )

        return RecoveryAction(
            can_recover=False,
            strategy="sheet_not_found",
            action_description=f"Sheet '{requested_name}' not found. Available sheets: {available_sheets}.",
            requires_user_clarification=True,
            clarification_prompt=f"Sheet '{requested_name}' does not exist in workbook. Available sheets are: {available_sheets}.",
        )

    def resolve_range(self, requested_range: str, sheet_name: str | None = None) -> RecoveryAction:
        """Resolve range issues conservatively by checking used range."""
        info_res = self.backend.get_sheet_info(sheet_name)
        if not info_res.success or not info_res.data:
            return RecoveryAction(
                can_recover=False,
                strategy="range_recovery",
                action_description="Could not inspect sheet dimensions.",
            )

        used_range = info_res.data.get("used_range", "A1")
        if not requested_range or requested_range == "used_range":
            return RecoveryAction(
                can_recover=True,
                strategy="range_recovery",
                action_description=f"Using sheet used_range '{used_range}'.",
                updated_arguments={"cell_range": used_range},
            )

        return RecoveryAction(
            can_recover=True,
            strategy="range_recovery",
            action_description=f"Adjusted range to valid used_range '{used_range}'.",
            updated_arguments={"cell_range": used_range},
        )

    def resolve_column(self, concept_name: str, sheet_name: str | None = None) -> RecoveryAction:
        """Map conceptual column name (e.g. 'Feb Sales') to actual header in worksheet."""
        if getattr(self.backend, "wb", None) is None and getattr(self.backend, "file_path", ""):
            self.backend.open_workbook(self.backend.file_path)

        read_res = self.backend.read_range(cell_range="A1:Z1", sheet_name=sheet_name)
        if not read_res.success or not read_res.data or "rows" not in read_res.data:
            return RecoveryAction(
                can_recover=False,
                strategy="column_recovery",
                action_description="Could not read sheet headers.",
            )

        rows = read_res.data["rows"]
        if not rows:
            return RecoveryAction(
                can_recover=False,
                strategy="column_recovery",
                action_description="Header row is empty.",
            )

        headers = [str(c).strip() if c is not None else "" for c in rows[0]]
        concept_clean = concept_name.lower().strip()

        matches = []
        for idx, h in enumerate(headers, start=1):
            h_clean = h.lower().strip()
            if h_clean and (concept_clean in h_clean or h_clean in concept_clean):
                matches.append((idx, h))

        if len(matches) == 1:
            col_idx, col_name = matches[0]
            logger.info(f"[RecoveryHandler] Column concept '{concept_name}' mapped to header '{col_name}' (Col {col_idx})")
            return RecoveryAction(
                can_recover=True,
                strategy="column_recovery",
                action_description=f"Mapped column concept '{concept_name}' to header '{col_name}' (column {col_idx}).",
                updated_arguments={"key_column": col_idx, "column_name": col_name},
            )
        elif len(matches) > 1:
            match_names = [m[1] for m in matches]
            prompt = f"Multiple columns match concept '{concept_name}': {match_names}. Please select the intended column."
            return RecoveryAction(
                can_recover=False,
                strategy="column_ambiguity",
                action_description=prompt,
                requires_user_clarification=True,
                clarification_prompt=prompt,
            )

        return RecoveryAction(
            can_recover=False,
            strategy="column_not_found",
            action_description=f"Column concept '{concept_name}' could not be mapped to any header in {headers}.",
            requires_user_clarification=True,
            clarification_prompt=f"Could not find column matching '{concept_name}'. Sheet headers are: {headers}.",
        )

    def recover_tool_failure(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        error_message: str,
    ) -> RecoveryAction:
        """Handle execution tool failure based on error message inspection."""
        msg_lower = error_message.lower()

        if "sheet" in msg_lower and "not found" in msg_lower:
            req_sheet = arguments.get("sheet_name", "")
            if req_sheet:
                return self.resolve_sheet_name(req_sheet)

        if "range" in msg_lower or "cell" in msg_lower:
            req_range = arguments.get("cell_range", "")
            return self.resolve_range(req_range, arguments.get("sheet_name"))

        if "permission" in msg_lower or "locked" in msg_lower or "access denied" in msg_lower:
            return RecoveryAction(
                can_recover=True,
                strategy="file_locked_copy",
                action_description="File is locked or read-only. Creating working copy to execute operations safely.",
                updated_arguments={**arguments, "create_copy": True},
            )

        if tool_name == "excel_create_chart":
            # If chart creation fails due to empty or non-numeric range, adjust to used range
            info_res = self.backend.get_sheet_info(arguments.get("sheet_name"))
            if info_res.success and info_res.data:
                used_range = info_res.data.get("used_range", "A1:C5")
                return RecoveryAction(
                    can_recover=True,
                    strategy="chart_range_adjust",
                    action_description=f"Adjusted chart range to '{used_range}'.",
                    updated_arguments={**arguments, "cell_range": used_range},
                )

        return RecoveryAction(
            can_recover=False,
            strategy="unhandled_failure",
            action_description=f"Tool '{tool_name}' failed unrecoverably: {error_message}",
        )
