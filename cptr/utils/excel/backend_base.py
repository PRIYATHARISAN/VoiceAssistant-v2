"""Abstract base class and data structures for Excel backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
import json
from typing import Any, Dict, List, Literal, Optional


@dataclass
class ExcelResult:
    """Structured result returned by Excel operations to allow agent reasoning."""

    success: bool
    operation: str
    workbook: str = ""
    sheet: str = ""
    affected_range: str = ""
    message: str = ""
    data: Any = None
    backup_path: str = ""
    requires_confirmation: bool = False

    def to_json(self) -> str:
        """Convert result to clean JSON string for LLM tool output."""
        d = {
            "success": self.success,
            "operation": self.operation,
            "workbook": self.workbook,
            "sheet": self.sheet,
            "affected_range": self.affected_range,
            "message": self.message,
        }
        if self.data is not None:
            d["data"] = self.data
        if self.backup_path:
            d["backup_path"] = self.backup_path
        if self.requires_confirmation:
            d["requires_confirmation"] = True
        return json.dumps(d, ensure_ascii=False, indent=2)


class ExcelBackend(ABC):
    """Abstract base class for Excel engines (OpenPyXL file backend / Win32COM live backend)."""

    @property
    @abstractmethod
    def backend_type(self) -> str:
        ...

    @property
    @abstractmethod
    def is_live_mode(self) -> bool:
        ...

    @abstractmethod
    def open_workbook(self, file_path: str = "") -> ExcelResult:
        ...

    @abstractmethod
    def create_workbook(self, file_path: str = "") -> ExcelResult:
        ...

    @abstractmethod
    def get_workbook_info(self) -> ExcelResult:
        ...

    @abstractmethod
    def save_workbook(self, target_path: str | None = None) -> ExcelResult:
        ...

    @abstractmethod
    def close_workbook(self) -> ExcelResult:
        ...

    @abstractmethod
    def list_sheets(self) -> ExcelResult:
        ...

    @abstractmethod
    def create_sheet(self, sheet_name: str, index: int | None = None) -> ExcelResult:
        ...

    @abstractmethod
    def delete_sheet(self, sheet_name: str) -> ExcelResult:
        ...

    @abstractmethod
    def rename_sheet(self, old_name: str, new_name: str) -> ExcelResult:
        ...

    @abstractmethod
    def get_sheet_info(self, sheet_name: str | None = None) -> ExcelResult:
        ...

    @abstractmethod
    def read_range(
        self,
        cell_range: str | None = None,
        sheet_name: str | None = None,
        max_rows: int = 100,
        offset_row: int = 1,
    ) -> ExcelResult:
        ...

    @abstractmethod
    def write_range(
        self,
        data: list[list[Any]],
        start_cell: str = "A1",
        sheet_name: str | None = None,
    ) -> ExcelResult:
        ...

    @abstractmethod
    def update_cell(
        self,
        cell: str,
        value: Any,
        sheet_name: str | None = None,
    ) -> ExcelResult:
        ...

    @abstractmethod
    def append_rows(
        self,
        rows: list[list[Any]],
        sheet_name: str | None = None,
    ) -> ExcelResult:
        ...

    @abstractmethod
    def clear_range(
        self,
        cell_range: str,
        sheet_name: str | None = None,
    ) -> ExcelResult:
        ...

    @abstractmethod
    def search_sheet(
        self,
        query: str,
        sheet_name: str | None = None,
        max_results: int = 50,
    ) -> ExcelResult:
        ...

    @abstractmethod
    def sort_range(
        self,
        cell_range: str,
        key_column: int,
        ascending: bool = True,
        has_headers: bool = True,
        sheet_name: str | None = None,
    ) -> ExcelResult:
        ...

    @abstractmethod
    def filter_range(
        self,
        cell_range: str,
        column_index: int,
        criteria: str,
        sheet_name: str | None = None,
    ) -> ExcelResult:
        ...

    @abstractmethod
    def write_formula(
        self,
        cell: str,
        formula: str,
        sheet_name: str | None = None,
    ) -> ExcelResult:
        ...

    @abstractmethod
    def format_range(
        self,
        cell_range: str,
        font_name: str | None = None,
        font_size: int | None = None,
        bold: bool | None = None,
        italic: bool | None = None,
        font_color: str | None = None,
        fill_color: str | None = None,
        number_format: str | None = None,
        alignment: str | None = None,
        borders: bool | None = None,
        auto_fit: bool = False,
        sheet_name: str | None = None,
    ) -> ExcelResult:
        ...

    @abstractmethod
    def create_chart(
        self,
        cell_range: str,
        chart_type: str = "col",
        title: str = "Chart",
        target_cell: str = "E2",
        sheet_name: str | None = None,
    ) -> ExcelResult:
        ...

    @abstractmethod
    def list_charts(self, sheet_name: str | None = None) -> ExcelResult:
        ...

    @abstractmethod
    def update_chart(
        self,
        chart_identifier: str | int = 1,
        title: str | None = None,
        chart_type: str | None = None,
        cell_range: str | None = None,
        name: str | None = None,
        sheet_name: str | None = None,
    ) -> ExcelResult:
        ...
