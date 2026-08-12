"""Excel package for cptr autonomous agent and Phase 3 reliability engine."""

from __future__ import annotations

from cptr.utils.excel.audit_log import ExcelAuditLogger
from cptr.utils.excel.backup import BackupManager
from cptr.utils.excel.backend_base import ExcelBackend, ExcelResult
from cptr.utils.excel.large_data import LargeDataSummarizer
from cptr.utils.excel.openpyxl_backend import OpenPyXLBackend
from cptr.utils.excel.planner import ExcelPlanner, PlanStep, TaskPlan
from cptr.utils.excel.recovery import ExcelRecoveryHandler, RecoveryAction
from cptr.utils.excel.reliable_executor import ReliableExcelExecutor
from cptr.utils.excel.safety import SafetyManager
from cptr.utils.excel.session import ExcelSession, get_excel_session
from cptr.utils.excel.tools import (
    excel_append_rows,
    excel_clear_range,
    excel_close_workbook,
    excel_create_chart,
    excel_create_sheet,
    excel_create_workbook,
    excel_delete_sheet,
    excel_filter_range,
    excel_format_range,
    excel_get_sheet_info,
    excel_get_workbook_info,
    excel_list_sheets,
    excel_open_workbook,
    excel_read_range,
    excel_rename_sheet,
    excel_save_workbook,
    excel_search_sheet,
    excel_sort_range,
    excel_update_cell,
    excel_write_formula,
    excel_write_range,
)
from cptr.utils.excel.verifier import ExcelVerifier, VerificationResult

EXCEL_TOOLS: dict[str, dict] = {
    "excel_open_workbook": {"fn": excel_open_workbook, "approval": "allow"},
    "excel_create_workbook": {"fn": excel_create_workbook, "approval": "allow"},
    "excel_get_workbook_info": {"fn": excel_get_workbook_info, "approval": "allow"},
    "excel_save_workbook": {"fn": excel_save_workbook, "approval": "allow"},
    "excel_close_workbook": {"fn": excel_close_workbook, "approval": "allow"},
    "excel_list_sheets": {"fn": excel_list_sheets, "approval": "allow"},
    "excel_create_sheet": {"fn": excel_create_sheet, "approval": "allow"},
    "excel_delete_sheet": {"fn": excel_delete_sheet},
    "excel_rename_sheet": {"fn": excel_rename_sheet, "approval": "allow"},
    "excel_get_sheet_info": {"fn": excel_get_sheet_info, "approval": "allow"},
    "excel_read_range": {"fn": excel_read_range, "approval": "allow"},
    "excel_write_range": {"fn": excel_write_range, "approval": "allow"},
    "excel_update_cell": {"fn": excel_update_cell, "approval": "allow"},
    "excel_append_rows": {"fn": excel_append_rows, "approval": "allow"},
    "excel_clear_range": {"fn": excel_clear_range},
    "excel_search_sheet": {"fn": excel_search_sheet, "approval": "allow"},
    "excel_sort_range": {"fn": excel_sort_range, "approval": "allow"},
    "excel_filter_range": {"fn": excel_filter_range, "approval": "allow"},
    "excel_write_formula": {"fn": excel_write_formula, "approval": "allow"},
    "excel_format_range": {"fn": excel_format_range, "approval": "allow"},
    "excel_create_chart": {"fn": excel_create_chart, "approval": "allow"},
}

__all__ = [
    "EXCEL_TOOLS",
    "excel_open_workbook",
    "excel_create_workbook",
    "excel_get_workbook_info",
    "excel_save_workbook",
    "excel_close_workbook",
    "excel_list_sheets",
    "excel_create_sheet",
    "excel_delete_sheet",
    "excel_rename_sheet",
    "excel_get_sheet_info",
    "excel_read_range",
    "excel_write_range",
    "excel_update_cell",
    "excel_append_rows",
    "excel_clear_range",
    "excel_search_sheet",
    "excel_sort_range",
    "excel_filter_range",
    "excel_write_formula",
    "excel_format_range",
    "excel_create_chart",
    # Phase 3 Reliability Exports
    "TaskPlan",
    "PlanStep",
    "ExcelPlanner",
    "ExcelVerifier",
    "VerificationResult",
    "ExcelRecoveryHandler",
    "RecoveryAction",
    "BackupManager",
    "LargeDataSummarizer",
    "SafetyManager",
    "ExcelAuditLogger",
    "ReliableExcelExecutor",
    "OpenPyXLBackend",
    "ExcelBackend",
    "ExcelResult",
    "ExcelSession",
    "get_excel_session",
]
