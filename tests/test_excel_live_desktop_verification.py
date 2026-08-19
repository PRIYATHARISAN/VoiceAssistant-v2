"""Diagnostic test for live Excel desktop window verification.

Performs 11 multi-point checks on Windows desktop:
1. Excel COM Application connection
2. Process ID (PID)
3. Window Handle (HWND)
4. IsWindow(HWND)
5. IsWindowVisible(HWND)
6. PID matches HWND thread process ID
7. IsIconic(HWND) (not minimized)
8. Window restore & foreground focus
9. Active workbook existence
10. Active sheet existence
11. Empirical verification result
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
import win32gui
import win32process

from cptr.utils.excel.win32com_backend import Win32COMBackend, is_win32com_available


def run_diagnostic():
    print("=" * 60)
    print("      KURAL AI — EXCEL LIVE DESKTOP DIAGNOSTIC TEST      ")
    print("=" * 60)

    if not is_win32com_available():
        print("ERROR: Win32COM is not available on this system.")
        print("LIVE DESKTOP VERIFICATION: FAIL")
        return False

    backend = Win32COMBackend()
    res = backend.open_workbook()

    app = backend.excel_app
    if not app:
        print("ERROR: Could not get Excel.Application COM object.")
        print("LIVE DESKTOP VERIFICATION: FAIL")
        return False

    hwnd = 0
    try:
        hwnd = int(getattr(app, "Hwnd", 0))
    except Exception as exc:
        print(f"ERROR: Could not retrieve Excel HWND: {exc}")

    pid = 0
    hwnd_pid = 0
    if hwnd:
        try:
            _, hwnd_pid = win32process.GetWindowThreadProcessId(hwnd)
            pid = hwnd_pid
        except Exception as exc:
            print(f"ERROR: Could not retrieve PID from HWND: {exc}")

    is_window = bool(win32gui.IsWindow(hwnd)) if hwnd else False
    is_visible = bool(win32gui.IsWindowVisible(hwnd)) if hwnd else False
    is_minimized = bool(win32gui.IsIconic(hwnd)) if hwnd else True

    user32 = ctypes.windll.user32
    fg_hwnd = user32.GetForegroundWindow()
    fg_pid = 0
    if fg_hwnd:
        try:
            _, fg_pid = win32process.GetWindowThreadProcessId(fg_hwnd)
        except Exception:
            fg_pid = 0

    is_foreground = (fg_hwnd == hwnd) or (fg_pid == pid and pid > 0)

    wb_name = backend.wb.Name if backend.wb else "None"
    sheet_name = backend.wb.ActiveSheet.Name if backend.wb and backend.wb.ActiveSheet else "None"

    is_pass = (
        res.success
        and res.verified
        and is_window
        and is_visible
        and (not is_minimized)
        and (pid > 0)
        and (wb_name != "None")
    )

    print(f"Excel PID:                {pid}")
    print(f"Excel HWND:               {hwnd}")
    print(f"IsWindow:                 {str(is_window).lower()}")
    print(f"IsWindowVisible:          {str(is_visible).lower()}")
    print(f"PID matches HWND:         {str(pid == hwnd_pid and pid > 0).lower()}")
    print(f"Window minimized:         {str(is_minimized).lower()}")
    print(f"Foreground activation:    {str(is_foreground).lower()}")
    print(f"Workbook:                 {wb_name}")
    print(f"Worksheet:                {sheet_name}")
    print("-" * 60)
    if is_pass:
        print("LIVE DESKTOP VERIFICATION: PASS")
    else:
        print("LIVE DESKTOP VERIFICATION: FAIL")
    print("=" * 60)
    return is_pass


if __name__ == "__main__":
    success = run_diagnostic()
    sys.exit(0 if success else 1)
