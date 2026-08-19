"""Windows COM Excel backend implementation for live Microsoft Excel interaction."""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, List, Optional

from cptr.utils.excel.backend_base import ExcelBackend, ExcelResult

logger = logging.getLogger(__name__)

# Check Windows platform & win32com availability
IS_WINDOWS = sys.platform == "win32"
HAS_WIN32COM = False

if IS_WINDOWS:
    try:
        import win32com.client  # type: ignore[import-untyped]
        HAS_WIN32COM = True
    except ImportError:
        HAS_WIN32COM = False


def is_win32com_available() -> bool:
    """Return True if running on Windows and win32com is installed."""
    return IS_WINDOWS and HAS_WIN32COM


class Win32COMBackend(ExcelBackend):
    """Live Microsoft Excel application backend using Win32 COM automation."""

    def __init__(self, file_path: str | None = None):
        self.file_path = file_path or ""
        self.excel_app: Any = None
        self.wb: Any = None

    @property
    def backend_type(self) -> str:
        return "win32com"

    @property
    def is_live_mode(self) -> bool:
        return True

    def _focus_excel_window(self) -> int:
        """Return the real desktop window handle after bringing Excel forward."""
        try:
            import win32gui, win32con

            for _ in range(15):
                hwnd = int(getattr(self.excel_app, "Hwnd", 0) or 0)
                if hwnd and win32gui.IsWindow(hwnd):
                    self.excel_app.Visible = True
                    try:
                        self.excel_app.WindowState = -4137  # xlMaximized
                    except Exception:
                        pass
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
                    win32gui.BringWindowToTop(hwnd)
                    try:
                        win32gui.SetForegroundWindow(hwnd)
                    except Exception:
                        pass
                    return hwnd
                time.sleep(0.2)
        except Exception as exc:
            logger.warning("[Win32COM] Could not focus Excel window: %s", exc)
        return 0

    def _launch_excel_desktop(self) -> int:
        """Launch Excel as a persistent interactive Windows application."""
        if not IS_WINDOWS:
            return 0
        try:
            os.startfile("excel.exe")  # type: ignore[attr-defined]
            import win32gui

            found = 0
            for _ in range(30):
                def on_window(hwnd, _extra):
                    nonlocal found
                    if found or not win32gui.IsWindowVisible(hwnd):
                        return
                    try:
                        if win32gui.GetClassName(hwnd) == "XLMAIN":
                            found = int(hwnd)
                    except Exception:
                        pass

                win32gui.EnumWindows(on_window, None)
                if found:
                    return found
                time.sleep(0.2)
        except Exception as exc:
            logger.warning("[Win32COM] Could not launch desktop Excel: %s", exc)
        return 0

    def _ensure_excel(self) -> bool:
        if not is_win32com_available():
            return False
        if self.excel_app is None:
            try:
                import win32com.client
                try:
                    self.excel_app = win32com.client.GetActiveObject("Excel.Application")
                    # GetActiveObject can return a background Excel instance
                    # (for example one left behind by an add-in).  Such an
                    # instance accepts COM calls but has no user-visible
                    # window, which makes "open Excel" look successful while
                    # nothing appears on the desktop.
                    hwnd = int(getattr(self.excel_app, "Hwnd", 0) or 0)
                    visible = bool(getattr(self.excel_app, "Visible", False))
                    if not hwnd or not visible:
                        self.excel_app = win32com.client.DispatchEx("Excel.Application")
                except Exception:
                    # DispatchEx creates a dedicated Excel process instead of
                    # reusing a possibly hidden automation instance.
                    self.excel_app = win32com.client.DispatchEx("Excel.Application")
                self.excel_app.Visible = True
                self.excel_app.UserControl = True
                self._focus_excel_window()
            except Exception as exc:
                logger.warning(f"[Win32COM] Could not connect to Excel application: {exc}")
                return False
        return True

    def _ensure_workbook(self) -> bool:
        if not self._ensure_excel():
            return False
        if self.wb is None:
            try:
                if self.excel_app.Workbooks.Count > 0:
                    self.wb = self.excel_app.ActiveWorkbook
                else:
                    self.wb = self.excel_app.Workbooks.Add()
            except Exception as exc:
                logger.warning(f"[Win32COM] Could not connect or add active workbook: {exc}")
                return False
        return True

    def open_workbook(self, file_path: str = "") -> ExcelResult:
        desktop_hwnd = self._launch_excel_desktop() if not file_path else 0
        if not self._ensure_excel():
            return ExcelResult(
                success=False,
                operation="open_workbook",
                message="Live Microsoft Excel COM automation is unavailable on this machine.",
            )
        try:
            if self.excel_app:
                self.excel_app.DisplayAlerts = False

            if not file_path:
                if self.excel_app.Workbooks.Count > 0:
                    self.wb = self.excel_app.ActiveWorkbook
                else:
                    self.wb = self.excel_app.Workbooks.Add()
                self.excel_app.Visible = True
                hwnd = self._focus_excel_window()
                hwnd = hwnd or desktop_hwnd
                if not hwnd:
                    return ExcelResult(
                        success=False,
                        operation="open_workbook",
                        message="Excel responded through COM but did not expose a visible desktop window. "
                        "Please start Excel once from the Windows Start menu and try again.",
                    )
                return ExcelResult(
                    success=True,
                    operation="open_workbook",
                    workbook=self.wb.Name if self.wb else "Excel.Application",
                    sheet=self.wb.ActiveSheet.Name if self.wb and self.wb.ActiveSheet else "",
                    data={"window_handle": hwnd, "live": True},
                    message=f"Opened live Microsoft Excel application (Workbook: '{self.wb.Name if self.wb else 'None'}').",
                )

            abs_path = os.path.abspath(file_path)

            # Handle existing open workbooks with the same filename in live Excel
            target_filename = os.path.basename(abs_path).lower()
            try:
                for open_wb in list(self.excel_app.Workbooks):
                    if open_wb.Name.lower() == target_filename:
                        try:
                            if os.path.abspath(open_wb.FullName).lower() == abs_path.lower():
                                self.wb = open_wb
                                self.file_path = abs_path
                                self.excel_app.Visible = True
                                return ExcelResult(
                                    success=True,
                                    operation="open_workbook",
                                    workbook=self.wb.Name,
                                    sheet=self.wb.ActiveSheet.Name,
                                    message=f"Workbook '{self.wb.Name}' is active in live Excel application.",
                                )
                            else:
                                open_wb.Close(SaveChanges=False)
                        except Exception:
                            pass
            except Exception:
                pass

            self.wb = self.excel_app.Workbooks.Open(abs_path)
            self.file_path = abs_path
            self.excel_app.Visible = True
            return ExcelResult(
                success=True,
                operation="open_workbook",
                workbook=self.wb.Name,
                sheet=self.wb.ActiveSheet.Name,
                message=f"Opened workbook '{self.wb.Name}' in live Excel application.",
            )
        except Exception as exc:
            logger.warning(f"[Win32COM] open_workbook failed for '{file_path}': {exc}")
            return ExcelResult(success=False, operation="open_workbook", message=f"COM error: {exc}")

    def create_workbook(self, file_path: str = "") -> ExcelResult:
        if not self._ensure_excel():
            return ExcelResult(
                success=False,
                operation="create_workbook",
                message="Live Microsoft Excel COM automation is unavailable.",
            )
        try:
            self.wb = self.excel_app.Workbooks.Add()
            if file_path:
                abs_path = os.path.abspath(file_path)
                self.wb.SaveAs(abs_path)
                self.file_path = abs_path
            else:
                self.file_path = ""
            self.excel_app.Visible = True
            return ExcelResult(
                success=True,
                operation="create_workbook",
                workbook=self.wb.Name,
                sheet=self.wb.ActiveSheet.Name,
                message=f"Created live workbook '{self.wb.Name}'.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="create_workbook", message=f"COM error: {exc}")

    def get_workbook_info(self) -> ExcelResult:
        if not self._ensure_workbook() or self.wb is None:
            return ExcelResult(success=False, operation="get_workbook_info", message="No live workbook open.")
        return ExcelResult(
            success=True,
            operation="get_workbook_info",
            workbook=self.wb.Name,
            sheet=self.wb.ActiveSheet.Name,
            data={"sheets": [ws.Name for ws in self.wb.Worksheets]},
        )

    def save_workbook(self, target_path: str | None = None) -> ExcelResult:
        if not self._ensure_workbook() or self.wb is None:
            return ExcelResult(success=False, operation="save_workbook", message="No live workbook open.")
        try:
            if self.excel_app:
                self.excel_app.DisplayAlerts = False
            if target_path:
                abs_path = os.path.abspath(target_path)
                ext = os.path.splitext(abs_path)[1].lower()
                fmt = 51 if ext == ".xlsx" else 52 if ext == ".xlsm" else 56 if ext == ".xls" else None
                if fmt:
                    self.wb.SaveAs(abs_path, FileFormat=fmt)
                else:
                    self.wb.SaveAs(abs_path)
                self.file_path = abs_path
            else:
                self.wb.Save()
            if self.excel_app:
                self.excel_app.DisplayAlerts = True
            return ExcelResult(
                success=True,
                operation="save_workbook",
                workbook=self.wb.Name,
                message=f"Saved live workbook '{self.wb.Name}'.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="save_workbook", message=f"COM error: {exc}")

    def close_workbook(self) -> ExcelResult:
        if self.wb is not None:
            try:
                if self.excel_app:
                    self.excel_app.DisplayAlerts = False
                has_file = bool(self.file_path and os.path.exists(self.file_path))
                self.wb.Close(SaveChanges=has_file)
                if self.excel_app:
                    self.excel_app.DisplayAlerts = True
            except Exception as exc:
                logger.warning(f"[Win32COM] Error closing workbook: {exc}")
            self.wb = None
        return ExcelResult(success=True, operation="close_workbook", message="Closed live workbook.")

    def list_sheets(self) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="list_sheets", message="No live workbook open.")
        sheets = [ws.Name for ws in self.wb.Worksheets]
        return ExcelResult(
            success=True,
            operation="list_sheets",
            workbook=self.wb.Name,
            sheet=self.wb.ActiveSheet.Name,
            data={"sheets": sheets},
        )

    def create_sheet(self, sheet_name: str, index: int | None = None) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="create_sheet", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets.Add()
            ws.Name = sheet_name
            return ExcelResult(
                success=True,
                operation="create_sheet",
                workbook=self.wb.Name,
                sheet=sheet_name,
                message=f"Created sheet '{sheet_name}' in live Excel.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="create_sheet", message=f"COM error: {exc}")

    def delete_sheet(self, sheet_name: str) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="delete_sheet", message="No live workbook open.")
        try:
            self.excel_app.DisplayAlerts = False
            self.wb.Worksheets(sheet_name).Delete()
            self.excel_app.DisplayAlerts = True
            return ExcelResult(
                success=True,
                operation="delete_sheet",
                workbook=self.wb.Name,
                message=f"Deleted sheet '{sheet_name}'.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="delete_sheet", message=f"COM error: {exc}")

    def rename_sheet(self, old_name: str, new_name: str) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="rename_sheet", message="No live workbook open.")
        try:
            self.wb.Worksheets(old_name).Name = new_name
            return ExcelResult(
                success=True,
                operation="rename_sheet",
                workbook=self.wb.Name,
                sheet=new_name,
                message=f"Renamed sheet to '{new_name}'.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="rename_sheet", message=f"COM error: {exc}")

    def get_sheet_info(self, sheet_name: str | None = None) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="get_sheet_info", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            used = ws.UsedRange
            return ExcelResult(
                success=True,
                operation="get_sheet_info",
                workbook=self.wb.Name,
                sheet=ws.Name,
                affected_range=used.Address.replace("$", ""),
                data={"name": ws.Name, "address": used.Address.replace("$", "")},
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="get_sheet_info", message=f"COM error: {exc}")

    def read_range(
        self,
        cell_range: str | None = None,
        sheet_name: str | None = None,
        max_rows: int = 100,
        offset_row: int = 1,
    ) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="read_range", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            target = ws.Range(cell_range) if cell_range else ws.UsedRange
            vals = target.Value
            if not isinstance(vals, tuple):
                vals = ((vals,),)
            rows = [list(r) for r in vals[:max_rows]]
            return ExcelResult(
                success=True,
                operation="read_range",
                workbook=self.wb.Name,
                sheet=ws.Name,
                affected_range=cell_range or ws.UsedRange.Address.replace("$", ""),
                data={"rows": rows, "total_rows": len(rows)},
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="read_range", message=f"COM error: {exc}")

    def write_range(
        self,
        data: list[list[Any]],
        start_cell: str = "A1",
        sheet_name: str | None = None,
    ) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="write_range", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            start = ws.Range(start_cell)
            rows_cnt = len(data)
            cols_cnt = max((len(r) for r in data), default=1)
            target = ws.Range(start, ws.Cells(start.Row + rows_cnt - 1, start.Column + cols_cnt - 1))
            target.Value = [tuple(r) for r in data]
            return ExcelResult(
                success=True,
                operation="write_range",
                workbook=self.wb.Name,
                sheet=ws.Name,
                affected_range=target.Address.replace("$", ""),
                message=f"Wrote {rows_cnt} rows in live Excel.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="write_range", message=f"COM error: {exc}")

    def update_cell(self, cell: str, value: Any, sheet_name: str | None = None) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="update_cell", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            ws.Range(cell).Value = value
            return ExcelResult(
                success=True,
                operation="update_cell",
                workbook=self.wb.Name,
                sheet=ws.Name,
                affected_range=cell,
                message=f"Updated live cell {cell}.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="update_cell", message=f"COM error: {exc}")

    def append_rows(self, rows: list[list[Any]], sheet_name: str | None = None) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="append_rows", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            last_r = ws.UsedRange.Row + ws.UsedRange.Rows.Count
            start = ws.Cells(last_r, 1)
            cols_cnt = max((len(r) for r in rows), default=1)
            target = ws.Range(start, ws.Cells(last_r + len(rows) - 1, cols_cnt))
            target.Value = [tuple(r) for r in rows]
            return ExcelResult(
                success=True,
                operation="append_rows",
                workbook=self.wb.Name,
                sheet=ws.Name,
                message=f"Appended {len(rows)} rows in live Excel.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="append_rows", message=f"COM error: {exc}")

    def clear_range(self, cell_range: str, sheet_name: str | None = None) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="clear_range", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            ws.Range(cell_range).ClearContents()
            return ExcelResult(
                success=True,
                operation="clear_range",
                workbook=self.wb.Name,
                sheet=ws.Name,
                affected_range=cell_range,
                message=f"Cleared contents of range '{cell_range}'.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="clear_range", message=f"COM error: {exc}")

    def search_sheet(self, query: str, sheet_name: str | None = None, max_results: int = 50) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="search_sheet", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            found = ws.UsedRange.Find(What=query)
            matches = []
            if found is not None:
                first_addr = found.Address
                while True:
                    matches.append({"cell": found.Address.replace("$", ""), "value": str(found.Value)})
                    found = ws.UsedRange.FindNext(found)
                    if found is None or found.Address == first_addr or len(matches) >= max_results:
                        break
            return ExcelResult(
                success=True,
                operation="search_sheet",
                workbook=self.wb.Name,
                sheet=ws.Name,
                data={"matches": matches},
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="search_sheet", message=f"COM error: {exc}")

    def sort_range(
        self,
        cell_range: str,
        key_column: int,
        ascending: bool = True,
        has_headers: bool = True,
        sheet_name: str | None = None,
    ) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="sort_range", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            target = ws.Range(cell_range)
            key_cell = ws.Cells(target.Row, key_column)
            order = 1 if ascending else 2  # xlAscending = 1, xlDescending = 2
            header = 1 if has_headers else 2  # xlYes = 1, xlNo = 2
            target.Sort(Key1=key_cell, Order1=order, Header=header)
            return ExcelResult(
                success=True,
                operation="sort_range",
                workbook=self.wb.Name,
                sheet=ws.Name,
                affected_range=cell_range,
                message=f"Sorted range '{cell_range}' in live Excel.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="sort_range", message=f"COM error: {exc}")

    def filter_range(
        self,
        cell_range: str,
        column_index: int,
        criteria: str,
        sheet_name: str | None = None,
    ) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="filter_range", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            ws.Range(cell_range).AutoFilter(Field=column_index, Criteria1=f"*{criteria}*")
            return ExcelResult(
                success=True,
                operation="filter_range",
                workbook=self.wb.Name,
                sheet=ws.Name,
                affected_range=cell_range,
                message=f"Applied live Excel auto-filter on column {column_index} (no rows deleted).",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="filter_range", message=f"COM error: {exc}")

    def write_formula(self, cell: str, formula: str, sheet_name: str | None = None) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="write_formula", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            clean_f = formula if formula.startswith("=") else f"={formula}"
            ws.Range(cell).Formula = clean_f
            # Live Excel calculates formula automatically
            calculated_val = ws.Range(cell).Value
            return ExcelResult(
                success=True,
                operation="write_formula",
                workbook=self.wb.Name,
                sheet=ws.Name,
                affected_range=cell,
                message=f"Wrote formula '{clean_f}' to {cell}. Live calculated result: '{calculated_val}'.",
                data={"formula": clean_f, "calculated_value": str(calculated_val)},
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="write_formula", message=f"COM error: {exc}")

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
        if self.wb is None:
            return ExcelResult(success=False, operation="format_range", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            rng = ws.Range(cell_range)
            if font_name:
                rng.Font.Name = font_name
            if font_size:
                rng.Font.Size = font_size
            if bold is not None:
                rng.Font.Bold = bold
            if italic is not None:
                rng.Font.Italic = italic
            if number_format:
                rng.NumberFormat = number_format
            if auto_fit:
                rng.Columns.AutoFit()
            return ExcelResult(
                success=True,
                operation="format_range",
                workbook=self.wb.Name,
                sheet=ws.Name,
                affected_range=cell_range,
                message=f"Formatted range '{cell_range}' in live Excel.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="format_range", message=f"COM error: {exc}")

    def create_chart(
        self,
        cell_range: str,
        chart_type: str = "col",
        title: str = "Chart",
        target_cell: str = "E2",
        sheet_name: str | None = None,
    ) -> ExcelResult:
        if self.wb is None:
            return ExcelResult(success=False, operation="create_chart", message="No live workbook open.")
        try:
            ws = self.wb.Worksheets(sheet_name) if sheet_name else self.wb.ActiveSheet
            chart_obj = ws.ChartObjects().Add(100, 100, 350, 200)
            chart_obj.Chart.SetSourceData(Source=ws.Range(cell_range))
            chart_obj.Chart.HasTitle = True
            chart_obj.Chart.ChartTitle.Text = title
            return ExcelResult(
                success=True,
                operation="create_chart",
                workbook=self.wb.Name,
                sheet=ws.Name,
                affected_range=cell_range,
                message=f"Created live Excel chart '{title}'.",
            )
        except Exception as exc:
            return ExcelResult(success=False, operation="create_chart", message=f"COM error: {exc}")
