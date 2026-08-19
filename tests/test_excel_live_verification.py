"""Diagnostic live desktop verification test for Microsoft Excel on Windows."""

import sys
import os
import time
import pytest

# Ensure cptr imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cptr.utils.excel.win32com_backend import Win32COMBackend, is_win32com_available
from cptr.utils.excel.session import ExcelSession


@pytest.mark.skipif(not is_win32com_available(), reason="Win32COM is required for live Windows Excel verification")
def test_excel_live_desktop_verification():
    """Diagnostic test verifying physical Windows desktop Excel execution."""
    backend = Win32COMBackend()
    res = backend.open_workbook("")

    print("\n--- DIAGNOSTIC TEST RUN ---")
    print(f"Success: {res.success}")
    print(f"Verified: {res.verified}")
    print(f"Visible: {res.visible}")
    print(f"Excel PID: {res.process_id}")
    print(f"Excel HWND: {res.window_handle}")
    print(f"Workbook: {res.workbook}")
    print(f"Worksheet: {res.sheet}")
    print(f"Message: {res.message}")

    # Detailed 12-point checks printout
    if res.success and res.process_id and res.window_handle:
        import win32gui
        import win32process
        import psutil
        import ctypes

        hwnd = res.window_handle
        pid = res.process_id

        is_win = bool(win32gui.IsWindow(hwnd))
        is_vis = bool(win32gui.IsWindowVisible(hwnd))
        _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
        pid_match = window_pid == pid
        is_iconic = bool(win32gui.IsIconic(hwnd))

        proc_exists = False
        try:
            p = psutil.Process(pid)
            proc_exists = p.is_running() and p.name().lower() == "excel.exe"
        except Exception:
            proc_exists = False

        rect = win32gui.GetWindowRect(hwnd)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        rect_valid = width > 100 and height > 100 and rect[0] > -10000

        print(f"IsWindow: {is_win}")
        print(f"IsWindowVisible: {is_vis}")
        print(f"PID matches HWND: {pid_match}")
        print(f"Process exists: {proc_exists}")
        print(f"Window minimized: {is_iconic}")
        print(f"Window rect: {rect} (w={width}, h={height})")
        print(f"Rect valid: {rect_valid}")

        verification_passed = (
            res.success and res.verified and res.visible and
            is_win and is_vis and pid_match and proc_exists and
            (not is_iconic) and rect_valid
        )

        if verification_passed:
            print("LIVE DESKTOP VERIFICATION: PASS")
        else:
            print("LIVE DESKTOP VERIFICATION: FAIL")

        assert verification_passed is True, f"Physical desktop verification failed: {res.message}"
    else:
        print("LIVE DESKTOP VERIFICATION: FAIL")
        assert res.success is True, f"open_workbook failed: {res.message}"


if __name__ == "__main__":
    test_excel_live_desktop_verification()
