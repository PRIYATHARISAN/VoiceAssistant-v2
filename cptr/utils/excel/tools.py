"""General-purpose Excel tools exposed to cptr and Sofie LLM agent."""

from __future__ import annotations

import os
from typing import Any, List, Literal, Optional

from cptr.utils.excel.backend_base import ExcelResult
from cptr.utils.excel.session import get_excel_session
from cptr.utils.excel.win32com_backend import is_win32com_available


def _ensure_active_session_workbook(session, __context__: dict):
    ws_dir = __context__.get("workspace", "")
    backend = session.ensure_backend(workspace=ws_dir)
    if not session.active_workbook_path:
        info = backend.get_workbook_info()
        if info.success and info.workbook:
            session.active_workbook_path = info.workbook
        else:
            create_res = backend.create_workbook()
            if create_res.success:
                session.active_workbook_path = create_res.workbook or "Workbook1.xlsx"
    return backend


async def excel_open_workbook(
    file_path: str = "",
    live_mode: bool | None = None,
    *,
    __context__: dict,
) -> str:
    """Open Microsoft Excel desktop application or an Excel workbook file into session state.

    :param file_path: Optional path to Excel workbook file (.xlsx). If empty, launches or focuses live Microsoft Excel application.
    :param live_mode: Set True to connect to live Microsoft Excel desktop application via COM.
    """
    session = get_excel_session(__context__)
    ws_dir = __context__.get("workspace", "")
    full_path = ""
    if file_path:
        full_path = file_path if os.path.isabs(file_path) else os.path.join(ws_dir, file_path) if ws_dir else file_path
        if not os.path.exists(full_path):
            backend = session.ensure_backend(full_path, live_mode=live_mode, workspace=ws_dir)
            res = backend.create_workbook(full_path)
            if res.success:
                session.active_workbook_path = full_path
            return res.to_json()

    # An empty path means "open the desktop Excel application", not "create
    # an in-memory workbook". Never report success from the OpenPyXL fallback
    # for that request; it makes Kural claim Excel is open when no window exists.
    requested_live = True if not full_path and live_mode is None else live_mode
    if not full_path and requested_live and not is_win32com_available():
        return ExcelResult(
            success=False,
            operation="open_workbook",
            message="Live Microsoft Excel is unavailable. Install pywin32 and run Kural in the Windows desktop session.",
        ).to_json()

    backend = session.ensure_backend(
        full_path if full_path else None, live_mode=requested_live, workspace=ws_dir
    )
    if not full_path and not backend.is_live_mode:
        return ExcelResult(
            success=False,
            operation="open_workbook",
            message="The desktop Excel application could not be selected; no workbook was opened.",
        ).to_json()
    res = backend.open_workbook(full_path)
    if res.success and full_path:
        session.active_workbook_path = full_path
    elif res.success and res.workbook:
        session.active_workbook_path = res.workbook
    return res.to_json()


async def excel_create_workbook(
    file_path: str = "",
    live_mode: bool | None = None,
    *,
    __context__: dict,
) -> str:
    """Create a new blank Excel workbook in the live Microsoft Excel desktop application.

    :param file_path: Optional path to save the new workbook file (.xlsx). If omitted, an unsaved new workbook is created in live Excel.
    :param live_mode: Set True to force live Microsoft Excel application via COM.
    """
    session = get_excel_session(__context__)
    ws_dir = __context__.get("workspace", "")
    full_path = ""
    if file_path:
        full_path = file_path if os.path.isabs(file_path) else os.path.join(ws_dir, file_path) if ws_dir else file_path

    backend = session.ensure_backend(full_path if full_path else None, live_mode=live_mode, workspace=ws_dir)
    res = backend.create_workbook(full_path)
    if res.success and full_path:
        session.active_workbook_path = full_path
    elif res.success and res.workbook:
        session.active_workbook_path = res.workbook
    return res.to_json()


async def excel_get_workbook_info(
    workbook_name: str | None = None,
    *,
    __context__: dict,
) -> str:
    """Get metadata for the currently active workbook.

    :param workbook_name: Optional name of workbook (defaults to currently open session workbook).
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.get_workbook_info().to_json()


async def excel_save_workbook(
    file_path: str | None = None,
    *,
    __context__: dict,
) -> str:
    """Save the active Excel workbook.

    :param file_path: Optional target file path (if saving as new copy).
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    target = None
    if file_path:
        ws_dir = __context__.get("workspace", "")
        target = file_path if os.path.isabs(file_path) else os.path.join(ws_dir, file_path) if ws_dir else file_path

    res = backend.save_workbook(target)
    return res.to_json()


async def excel_close_workbook(*, __context__: dict) -> str:
    """Close the currently active workbook in session."""
    session = get_excel_session(__context__)
    if not session.active_workbook_path:
        return ExcelResult(success=True, operation="close_workbook", message="No active workbook to close.").to_json()
    backend = session.ensure_backend()
    res = backend.close_workbook()
    session.active_workbook_path = ""
    return res.to_json()


async def excel_list_sheets(
    workbook_name: str | None = None,
    *,
    __context__: dict,
) -> str:
    """List all worksheet names in the active workbook.

    :param workbook_name: Optional workbook name filter.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.list_sheets().to_json()


async def excel_create_sheet(
    sheet_name: str,
    index: int | None = None,
    *,
    __context__: dict,
) -> str:
    """Create a new worksheet in the active workbook.

    :param sheet_name: Name for the new worksheet.
    :param index: Optional position index where sheet should be inserted.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.create_sheet(sheet_name, index=index).to_json()


async def excel_delete_sheet(
    sheet_name: str,
    confirm: bool = False,
    *,
    __context__: dict,
) -> str:
    """Delete a worksheet from the active workbook.

    :param sheet_name: Name of worksheet to delete.
    :param confirm: Set True to confirm worksheet deletion (destructive action).
    """
    if not confirm:
        return ExcelResult(
            success=False,
            operation="delete_sheet",
            sheet=sheet_name,
            message=f"Destructive action: Deleting worksheet '{sheet_name}' requires confirmation. Pass confirm=True to execute.",
            requires_confirmation=True,
        ).to_json()

    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    backup_path = session.create_backup()
    res = backend.delete_sheet(sheet_name)
    if backup_path:
        res.backup_path = backup_path
    return res.to_json()


async def excel_rename_sheet(
    old_name: str,
    new_name: str,
    *,
    __context__: dict,
) -> str:
    """Rename a worksheet in the active workbook.

    :param old_name: Current worksheet name.
    :param new_name: New worksheet name.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.rename_sheet(old_name, new_name).to_json()


async def excel_get_sheet_info(
    sheet_name: str | None = None,
    *,
    __context__: dict,
) -> str:
    """Get metadata for a worksheet (used range, max row, max column).

    :param sheet_name: Optional worksheet name (defaults to active sheet).
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.get_sheet_info(sheet_name).to_json()


async def excel_read_range(
    cell_range: str | None = None,
    sheet_name: str | None = None,
    max_rows: int = 100,
    *,
    __context__: dict,
) -> str:
    """Read cell values from a worksheet range.

    :param cell_range: Range string like 'A1:D50' or None for all used range.
    :param sheet_name: Optional target worksheet name.
    :param max_rows: Maximum rows to return (default 100).
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.read_range(cell_range=cell_range, sheet_name=sheet_name, max_rows=max_rows).to_json()


async def excel_write_range(
    data: list[list[Any]],
    start_cell: str = "A1",
    sheet_name: str | None = None,
    *,
    __context__: dict,
) -> str:
    """Write 2D list of values starting at a cell coordinate.

    :param data: 2D array of values [[row1_col1, row1_col2], [row2_col1, row2_col2]].
    :param start_cell: Top-left cell coordinate (default 'A1').
    :param sheet_name: Optional target worksheet name.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.write_range(data=data, start_cell=start_cell, sheet_name=sheet_name).to_json()


async def excel_update_cell(
    cell: str,
    value: Any,
    sheet_name: str | None = None,
    *,
    __context__: dict,
) -> str:
    """Update a single cell value.

    :param cell: Cell coordinate like 'B5'.
    :param value: Value to set (text, number, date).
    :param sheet_name: Optional target worksheet name.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.update_cell(cell=cell, value=value, sheet_name=sheet_name).to_json()


async def excel_append_rows(
    rows: list[list[Any]],
    sheet_name: str | None = None,
    *,
    __context__: dict,
) -> str:
    """Append rows to the end of a worksheet table.

    :param rows: 2D list of row values to append.
    :param sheet_name: Optional target worksheet name.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.append_rows(rows=rows, sheet_name=sheet_name).to_json()


async def excel_clear_range(
    cell_range: str,
    sheet_name: str | None = None,
    confirm: bool = False,
    *,
    __context__: dict,
) -> str:
    """Clear cell values in a range.

    :param cell_range: Range string to clear like 'A1:F100'.
    :param sheet_name: Optional target worksheet name.
    :param confirm: Set True to confirm clearing range (destructive action).
    """
    if not confirm:
        return ExcelResult(
            success=False,
            operation="clear_range",
            affected_range=cell_range,
            message=f"Destructive action: Clearing range '{cell_range}' requires confirmation. Pass confirm=True to execute.",
            requires_confirmation=True,
        ).to_json()

    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    backup_path = session.create_backup()
    res = backend.clear_range(cell_range=cell_range, sheet_name=sheet_name)
    if backup_path:
        res.backup_path = backup_path
    return res.to_json()


async def excel_search_sheet(
    query: str,
    sheet_name: str | None = None,
    max_results: int = 50,
    *,
    __context__: dict,
) -> str:
    """Search worksheet for matching text or value.

    :param query: Text query string to search for.
    :param sheet_name: Optional target worksheet name.
    :param max_results: Maximum cell matches to return.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.search_sheet(query=query, sheet_name=sheet_name, max_results=max_results).to_json()


async def excel_sort_range(
    cell_range: str,
    key_column: int,
    ascending: bool = True,
    has_headers: bool = True,
    sheet_name: str | None = None,
    *,
    __context__: dict,
) -> str:
    """Sort rows in a range by a column index.

    :param cell_range: Range string like 'A1:D50'.
    :param key_column: Column index (1-based, e.g., 2 for column B).
    :param ascending: Set True for ascending sort, False for descending.
    :param has_headers: Set True if the first row of range contains header titles.
    :param sheet_name: Optional target worksheet name.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.sort_range(
        cell_range=cell_range,
        key_column=key_column,
        ascending=ascending,
        has_headers=has_headers,
        sheet_name=sheet_name,
    ).to_json()


async def excel_filter_range(
    cell_range: str,
    column_index: int,
    criteria: str,
    sheet_name: str | None = None,
    *,
    __context__: dict,
) -> str:
    """Filter rows in a range by criteria string without deleting non-matching rows.

    :param cell_range: Target range string like 'A1:E100'.
    :param column_index: Column index (1-based) to apply criteria.
    :param criteria: Filter criteria string.
    :param sheet_name: Optional target worksheet name.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.filter_range(
        cell_range=cell_range,
        column_index=column_index,
        criteria=criteria,
        sheet_name=sheet_name,
    ).to_json()


async def excel_write_formula(
    cell: str,
    formula: str,
    sheet_name: str | None = None,
    *,
    __context__: dict,
) -> str:
    """Write an Excel formula to a cell (e.g. '=SUM(A1:A10)').

    :param cell: Cell coordinate like 'E10'.
    :param formula: Formula string starting with '=' (e.g. '=AVERAGE(B2:B20)').
    :param sheet_name: Optional target worksheet name.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.write_formula(cell=cell, formula=formula, sheet_name=sheet_name).to_json()


async def excel_format_range(
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
    *,
    __context__: dict,
) -> str:
    """Format cells in a range (fonts, fills, colors, number formats, column widths).

    :param cell_range: Range coordinate string like 'A1:F1' or 'B2:B20'.
    :param font_name: Optional font family name like 'Calibri' or 'Arial'.
    :param font_size: Optional font size in pt.
    :param bold: Set True for bold text.
    :param italic: Set True for italic text.
    :param font_color: Hex color string (e.g. '#FF0000') or named color ('red').
    :param fill_color: Hex background fill color (e.g. '#FFFF00', 'light_yellow').
    :param number_format: Format string (e.g. '$#,##0.00', '0.0%').
    :param alignment: Text alignment ('left', 'center', 'right').
    :param borders: Set True to draw thin cell borders.
    :param auto_fit: Set True to auto-adjust column widths.
    :param sheet_name: Optional target worksheet name.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.format_range(
        cell_range=cell_range,
        font_name=font_name,
        font_size=font_size,
        bold=bold,
        italic=italic,
        font_color=font_color,
        fill_color=fill_color,
        number_format=number_format,
        alignment=alignment,
        borders=borders,
        auto_fit=auto_fit,
        sheet_name=sheet_name,
    ).to_json()


async def excel_create_chart(
    cell_range: str,
    chart_type: str = "col",
    title: str = "Chart",
    target_cell: str = "E2",
    sheet_name: str | None = None,
    *,
    __context__: dict,
) -> str:
    """Create a visual chart from data in a cell range.

    :param cell_range: Source data range (e.g. 'A1:C10').
    :param chart_type: Chart type ('col', 'bar', 'line', 'pie', 'scatter').
    :param title: Chart title.
    :param target_cell: Top-left cell coordinate where chart should be placed (e.g. 'E2').
    :param sheet_name: Optional target worksheet name.
    """
    session = get_excel_session(__context__)
    backend = _ensure_active_session_workbook(session, __context__)
    return backend.create_chart(
        cell_range=cell_range,
        chart_type=chart_type,
        title=title,
        target_cell=target_cell,
        sheet_name=sheet_name,
    ).to_json()
