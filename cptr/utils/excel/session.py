"""Excel Session & State Manager for cptr context integration."""

from __future__ import annotations

import logging
import os
import shutil
import time
from typing import Dict, Optional

from cptr.utils.excel.backend_base import ExcelBackend, ExcelResult
from cptr.utils.excel.openpyxl_backend import OpenPyXLBackend
from cptr.utils.excel.win32com_backend import Win32COMBackend, is_win32com_available

logger = logging.getLogger(__name__)


class ExcelSession:
    """Session state container for a single chat/session context."""

    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.active_workbook_path: str = ""
        self.active_sheet_name: str = ""
        self.backend: ExcelBackend | None = None
        self.backups: list[str] = []

    def ensure_backend(
        self,
        file_path: str | None = None,
        live_mode: bool | None = None,
        workspace: str = "",
    ) -> ExcelBackend:
        """Get or initialize the backend for this session."""
        target_path = file_path or self.active_workbook_path

        # Resolve relative path against workspace if provided
        if target_path and not os.path.isabs(target_path) and workspace:
            target_path = os.path.join(workspace, target_path)

        if live_mode is None:
            use_live = is_win32com_available()
        else:
            use_live = live_mode

        if use_live:
            if not is_win32com_available():
                logger.warning("[ExcelSession] Win32COM requested but unavailable. Falling back to OpenPyXL.")
                if self.backend is None or not isinstance(self.backend, OpenPyXLBackend):
                    self.backend = OpenPyXLBackend(target_path)
            else:
                if self.backend is None or not isinstance(self.backend, Win32COMBackend):
                    self.backend = Win32COMBackend(target_path)
        else:
            if self.backend is None or not isinstance(self.backend, OpenPyXLBackend):
                self.backend = OpenPyXLBackend(target_path)

        if target_path and target_path != self.active_workbook_path:
            self.active_workbook_path = target_path
            if self.backend and os.path.exists(target_path):
                self.backend.open_workbook(target_path)

        return self.backend

    def create_backup(self) -> str | None:
        """Create a safety backup snapshot of the active workbook before destructive operations."""
        if not self.active_workbook_path or not os.path.exists(self.active_workbook_path):
            return None
        try:
            base, ext = os.path.splitext(self.active_workbook_path)
            ts = int(time.time())
            backup_path = f"{base}_backup_{ts}{ext}"
            shutil.copy2(self.active_workbook_path, backup_path)
            self.backups.append(backup_path)
            logger.info(f"[ExcelSession] Created safety backup: '{backup_path}'")
            return backup_path
        except Exception as exc:
            logger.warning(f"[ExcelSession] Failed to create backup: {exc}")
            return None


# Global session storage indexed by session_id/chat_id
_SESSIONS: dict[str, ExcelSession] = {}


def get_excel_session(__context__: dict | None = None) -> ExcelSession:
    """Retrieve or create session instance for current context."""
    ctx = __context__ or {}
    session_id = ctx.get("chat_id") or ctx.get("user_id") or "global_default"

    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = ExcelSession(session_id)

    session = _SESSIONS[session_id]

    # Sync workspace path if active workbook is relative
    workspace = ctx.get("workspace", "")
    if session.active_workbook_path and not os.path.isabs(session.active_workbook_path) and workspace:
        session.active_workbook_path = os.path.join(workspace, session.active_workbook_path)

    return session
