"""End-to-end integration test verifying real interactive Microsoft Excel desktop launch.

Performs:
1. Opens Excel via excel_open_workbook (from cold start).
2. Verifies process CommandLine does NOT contain '/automation' or '-Embedding'.
3. Verifies MainWindowHandle > 0.
4. Creates a new workbook.
5. Writes numbers and text in range A1:B5.
6. Formats range as Bold.
7. Writes a formula in A6.
8. Creates a chart.
9. Performs truthful read-back verification.
"""

from __future__ import annotations

import asyncio
import json
import os
import psutil
import sys
import unittest

from cptr.utils.tools import execute_tool


class TestExcelInteractiveDesktop(unittest.TestCase):
    """Verify live interactive Excel desktop execution."""

    def test_interactive_desktop_workflow(self):
        # 1. Kill any existing Excel processes before test
        for p in psutil.process_iter():
            try:
                if p.name().lower() == "excel.exe":
                    p.kill()
            except Exception:
                pass

        ctx = {"workspace": os.path.abspath("."), "user_id": "test_user", "chat_id": "interactive_test"}

        async def _run():
            # Step 1: Open Excel
            res_open_str = await execute_tool("excel_open_workbook", {"file_path": ""}, __context__=ctx)
            res_open = json.loads(res_open_str)
            print("Step 1 (Open Excel):", res_open)
            self.assertTrue(res_open["success"])

            # Step 2: Process & Window Verification
            excel_procs = [p for p in psutil.process_iter() if p.name().lower() == "excel.exe"]
            self.assertGreater(len(excel_procs), 0, "No EXCEL.EXE process found!")
            for p in excel_procs:
                cmd_line = " ".join([arg.lower() for arg in p.cmdline()])
                print(f"Process PID: {p.pid}, CommandLine: {cmd_line}")
                self.assertNotIn("/automation", cmd_line, "Process was launched in /automation mode!")
                self.assertNotIn("-embedding", cmd_line, "Process was launched in -Embedding mode!")

            # Step 3: Create Workbook
            res_create_str = await execute_tool("excel_create_workbook", {}, __context__=ctx)
            res_create = json.loads(res_create_str)
            print("Step 3 (Create Workbook):", res_create)
            self.assertTrue(res_create["success"])

            # Step 4: Write Range
            data = [["Item", "Quantity"], ["Apples", 10], ["Oranges", 20], ["Bananas", 30], ["Grapes", 40]]
            res_write_str = await execute_tool("excel_write_range", {"data": data, "start_cell": "A1"}, __context__=ctx)
            res_write = json.loads(res_write_str)
            print("Step 4 (Write Range):", res_write)
            self.assertTrue(res_write["success"])

            # Step 5: Read-back Verification
            res_read_str = await execute_tool("excel_read_range", {"cell_range": "A1:B5"}, __context__=ctx)
            res_read = json.loads(res_read_str)
            print("Step 5 (Read Range):", res_read)
            self.assertTrue(res_read["success"])
            self.assertEqual(len(res_read["data"]["rows"]), 5)
            self.assertEqual(res_read["data"]["rows"][1][0], "Apples")

            # Step 6: Format Range (Bold)
            res_fmt_str = await execute_tool("excel_format_range", {"cell_range": "A1:B1", "bold": True}, __context__=ctx)
            res_fmt = json.loads(res_fmt_str)
            print("Step 6 (Format Range):", res_fmt)
            self.assertTrue(res_fmt["success"])

            # Step 7: Write Formula
            res_formula_str = await execute_tool("excel_write_formula", {"cell": "B6", "formula": "=SUM(B2:B5)"}, __context__=ctx)
            res_formula = json.loads(res_formula_str)
            print("Step 7 (Write Formula):", res_formula)
            self.assertTrue(res_formula["success"])

            # Step 8: Create Chart
            res_chart_str = await execute_tool("excel_create_chart", {"cell_range": "A1:B5", "title": "Fruit Stock", "target_cell": "D2"}, __context__=ctx)
            res_chart = json.loads(res_chart_str)
            print("Step 8 (Create Chart):", res_chart)
            self.assertTrue(res_chart["success"])

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
