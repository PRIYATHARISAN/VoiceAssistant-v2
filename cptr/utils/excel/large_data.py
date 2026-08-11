"""Large Data Summarizer for Phase 3 Excel reliability.

Provides metadata, header extraction, pagination, and statistical summaries
so that large Excel datasets do not exceed LLM context window limits.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from cptr.utils.excel.backend_base import ExcelBackend, ExcelResult

logger = logging.getLogger(__name__)


class LargeDataSummarizer:
    """Utilities to inspect large workbooks and construct concise summaries."""

    @staticmethod
    def summarize_sheet(
        backend: ExcelBackend,
        sheet_name: str | None = None,
        sample_rows: int = 5,
    ) -> dict[str, Any]:
        """Generate a concise structural summary of a sheet for reasoning."""
        sheet_info_res = backend.get_sheet_info(sheet_name)
        if not sheet_info_res.success:
            return {"error": sheet_info_res.message}

        info = sheet_info_res.data or {}
        max_row = info.get("max_row", 0)
        max_col = info.get("max_column", 0)
        used_range = info.get("used_range", "A1")

        # Read top row (headers)
        headers_res = backend.read_range(cell_range=f"A1:{chr(64 + min(max_col, 26))}{min(max_row, 1)}", sheet_name=sheet_name)
        headers = []
        if headers_res.success and headers_res.data and "rows" in headers_res.data:
            rows = headers_res.data["rows"]
            if rows:
                headers = [str(cell) if cell is not None else "" for cell in rows[0]]

        # Read sample rows
        sample_res = backend.read_range(max_rows=sample_rows + 1, sheet_name=sheet_name)
        sample_data = sample_res.data.get("rows", []) if sample_res.success and sample_res.data else []

        return {
            "sheet_name": info.get("sheet_name", sheet_name),
            "max_row": max_row,
            "max_column": max_col,
            "used_range": used_range,
            "headers": headers,
            "sample_rows": sample_data[: sample_rows + 1],
            "total_rows": max_row,
        }

    @staticmethod
    def get_column_statistics(
        backend: ExcelBackend,
        col_index: int,
        sheet_name: str | None = None,
        has_header: bool = True,
    ) -> dict[str, Any]:
        """Compute statistical summary (min, max, mean, count) for a numeric column."""
        read_res = backend.read_range(sheet_name=sheet_name, max_rows=5000)
        if not read_res.success or not read_res.data or "rows" not in read_res.data:
            return {"error": "Could not read sheet data"}

        rows = read_res.data["rows"]
        start_idx = 1 if has_header else 0
        values = []
        for r in rows[start_idx:]:
            if len(r) >= col_index:
                val = r[col_index - 1]
                if isinstance(val, (int, float)):
                    values.append(float(val))
                elif isinstance(val, str) and val.replace(".", "", 1).isdigit():
                    values.append(float(val))

        if not values:
            return {"count": 0, "numeric": False}

        return {
            "count": len(values),
            "numeric": True,
            "min": min(values),
            "max": max(values),
            "mean": round(sum(values) / len(values), 2),
        }
