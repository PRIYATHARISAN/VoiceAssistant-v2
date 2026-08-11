"""Backup, Working Copy & Rollback Manager for Phase 3 Excel reliability."""

from __future__ import annotations

import logging
import os
import shutil
import time
from typing import Optional

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages working copies, snapshots, and rollback for Excel workbooks."""

    def __init__(self, original_path: str, workspace: str = ""):
        self.original_path: str = original_path
        if original_path and not os.path.isabs(original_path) and workspace:
            self.original_path = os.path.join(workspace, original_path)

        self.working_copy_path: str = ""
        self.snapshots: list[str] = []
        self.workspace: str = workspace

    def create_working_copy(self) -> str:
        """Create a dedicated working copy before performing multi-step modifications."""
        if not self.original_path or not os.path.exists(self.original_path):
            # If original file doesn't exist yet, construct working path
            base, ext = os.path.splitext(self.original_path or "workbook.xlsx")
            self.working_copy_path = f"{base}_working{ext}"
            return self.working_copy_path

        base, ext = os.path.splitext(self.original_path)
        self.working_copy_path = f"{base}_working{ext}"
        try:
            shutil.copy2(self.original_path, self.working_copy_path)
            logger.info(f"[BackupManager] Created working copy '{self.working_copy_path}' from '{self.original_path}'")
        except Exception as exc:
            logger.warning(f"[BackupManager] Failed to create working copy: {exc}")
            self.working_copy_path = self.original_path
        return self.working_copy_path

    def create_snapshot(self) -> str | None:
        """Create a point-in-time snapshot of current working state for rollback."""
        target = self.working_copy_path or self.original_path
        if not target or not os.path.exists(target):
            return None
        try:
            base, ext = os.path.splitext(target)
            ts = int(time.time() * 1000)
            snapshot_path = f"{base}_snap_{ts}{ext}"
            shutil.copy2(target, snapshot_path)
            self.snapshots.append(snapshot_path)
            logger.info(f"[BackupManager] Created snapshot '{snapshot_path}'")
            return snapshot_path
        except Exception as exc:
            logger.warning(f"[BackupManager] Failed to create snapshot: {exc}")
            return None

    def rollback_to_latest_snapshot(self) -> bool:
        """Restore the working copy to the most recent snapshot."""
        if not self.snapshots:
            return False
        latest = self.snapshots[-1]
        target = self.working_copy_path or self.original_path
        if os.path.exists(latest) and target:
            try:
                shutil.copy2(latest, target)
                logger.info(f"[BackupManager] Rolled back '{target}' to snapshot '{latest}'")
                return True
            except Exception as exc:
                logger.error(f"[BackupManager] Rollback failed: {exc}")
                return False
        return False

    def finalize(self, save_as_path: str | None = None, overwrite_original: bool = False) -> str:
        """Finalize working copy into final output file or restore original if aborted."""
        target_src = self.working_copy_path if (self.working_copy_path and os.path.exists(self.working_copy_path)) else self.original_path

        if save_as_path:
            out_path = save_as_path if os.path.isabs(save_as_path) else os.path.join(self.workspace, save_as_path) if self.workspace else save_as_path
            if target_src and os.path.exists(target_src) and target_src != out_path:
                shutil.copy2(target_src, out_path)
            logger.info(f"[BackupManager] Saved final output to '{out_path}'")
            return out_path
        elif overwrite_original and self.original_path and target_src and target_src != self.original_path:
            shutil.copy2(target_src, self.original_path)
            logger.info(f"[BackupManager] Overwrote original workbook '{self.original_path}'")
            return self.original_path
        elif self.working_copy_path:
            return self.working_copy_path
        return self.original_path

    def cleanup_snapshots(self) -> None:
        """Clean up temporary snapshot files."""
        for snap in self.snapshots:
            if os.path.exists(snap):
                try:
                    os.remove(snap)
                except Exception:
                    pass
        self.snapshots.clear()
