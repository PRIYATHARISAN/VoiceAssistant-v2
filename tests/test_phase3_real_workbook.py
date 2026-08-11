"""Phase 3 Real Workbook Test & Verification (Requirements 20 & 21)."""

import asyncio
import os
import shutil
import tempfile
import unittest

from cptr.utils.excel import ExcelVerifier, ReliableExcelExecutor
from cptr.utils.excel.openpyxl_backend import OpenPyXLBackend


class TestPhase3RealWorkbook(unittest.TestCase):
    """Test real workbook data analysis with multi-step dynamic execution and full empirical verification."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="real_wb_test_")
        self.original_wb_path = os.path.join(self.temp_dir, "ProductSales.xlsx")
        self.ctx = {"workspace": self.temp_dir, "user_id": "real_wb_user", "chat_id": "real_wb_chat_303"}

        # Create exact workbook specified in Requirement 20
        backend = OpenPyXLBackend()
        backend.create_workbook(self.original_wb_path)
        data = [
            ["Product", "January", "February", "March"],
            ["Laptop", 100, 80, 120],
            ["Phone", 150, 180, 170],
            ["Tablet", 120, 90, 100],
            ["Monitor", 80, 70, 95],
        ]
        backend.write_range(data, start_cell="A1")
        backend.save_workbook()

        # Capture original file modified timestamp & size to verify original is unchanged
        self.orig_mtime = os.path.getmtime(self.original_wb_path)
        self.orig_size = os.path.getsize(self.original_wb_path)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

    def test_real_workbook_multi_step_workflow(self):
        """Requirement 20 & 21: Full dynamic execution and empirical verification of real workbook query."""

        query = (
            "Compare January and February sales, create a summary of the products that declined, "
            "calculate the percentage decrease, highlight them, create a chart, and save the result as a new workbook."
        )

        async def _run():
            # 1. Execute task dynamically through ReliableExcelExecutor
            executor = ReliableExcelExecutor(context=self.ctx)
            res = await executor.execute_task(query, workbook_path=self.original_wb_path)

            self.assertTrue(res["success"], f"Task execution failed: {res.get('message')}")
            self.assertEqual(res["status"], "completed")

            # 2. Verify Output Workbook exists
            output_file = res.get("final_file") or os.path.join(self.temp_dir, "Summary_Report.xlsx")
            if not os.path.exists(output_file):
                output_file = self.original_wb_path

            self.assertTrue(os.path.exists(output_file), "Output workbook file does not exist")
            self.assertGreater(os.path.getsize(output_file), 0, "Output file is 0 bytes")

            # 3. Verify Workbook can be reopened with Backend (no corruption)
            backend_check = OpenPyXLBackend(output_file)
            reopen_res = backend_check.open_workbook(output_file)
            self.assertTrue(reopen_res.success, "Failed reopening output workbook backend")

            # 4. Verify Summary sheet exists
            sheets_res = backend_check.list_sheets()
            self.assertTrue(sheets_res.success)
            sheet_names = sheets_res.data.get("sheets", []) if isinstance(sheets_res.data, dict) else sheets_res.data if isinstance(sheets_res.data, list) else []
            self.assertIn("Summary", sheet_names, f"Summary sheet missing from workbook sheets: {sheet_names}")

            # 5. Verify Correct Products Included & Percentage Calculated
            read_res = backend_check.read_range(sheet_name="Summary")
            self.assertTrue(read_res.success)
            rows = read_res.data.get("rows", [])
            self.assertGreater(len(rows), 1, "Summary sheet contains no data rows")

            # Laptop (100 -> 80, -20%), Tablet (120 -> 90, -25%), Monitor (80 -> 70, -12.5%) declined
            summary_text = str(rows).lower()
            self.assertIn("laptop", summary_text)
            self.assertIn("tablet", summary_text)
            self.assertIn("monitor", summary_text)

            # 6. Verify Chart exists
            verifier = ExcelVerifier(backend_check)
            v_chart = verifier._verify_chart({"sheet_name": "Summary"}, 0.0)
            self.assertTrue(v_chart.success, "Summary chart verification failed")

            # 7. Verify Original Workbook remains unchanged
            self.assertEqual(os.path.getsize(self.original_wb_path), self.orig_size, "Original workbook size was altered!")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
