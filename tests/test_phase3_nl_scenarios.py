"""Natural Language Scenario Tests for Phase 3 Excel Reliability System."""

import asyncio
import os
import shutil
import tempfile
import unittest

from cptr.utils.excel import ReliableExcelExecutor
from cptr.utils.excel.openpyxl_backend import OpenPyXLBackend


class TestPhase3NLScenarios(unittest.TestCase):
    """Test general natural-language requests through dynamic planning and tool execution."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="nl_scenarios_test_")
        self.sample_wb_path = os.path.join(self.temp_dir, "QuarterlySales.xlsx")
        self.ctx = {"workspace": self.temp_dir, "user_id": "nl_user", "chat_id": "nl_chat_202"}

        backend = OpenPyXLBackend()
        backend.create_workbook(self.sample_wb_path)
        backend.create_sheet("January")
        backend.write_range([["Product", "Sales"], ["Item A", 100], ["Item B", 150], ["Item C", 200]], sheet_name="January")
        backend.create_sheet("February")
        backend.write_range([["Product", "Sales"], ["Item A", 80], ["Item B", 180], ["Item C", 190]], sheet_name="February")
        backend.save_workbook()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

    def test_nl_1_compare_january_february_declined(self):
        """'Compare the January and February sheets and tell me which products declined.'"""
        async def _test():
            executor = ReliableExcelExecutor(context=self.ctx)
            res = await executor.execute_task(
                "Compare the January and February sheets and tell me which products declined.",
                workbook_path=self.sample_wb_path,
            )
            self.assertTrue(res["success"])
            self.assertEqual(res["status"], "completed")

        asyncio.run(_test())

    def test_nl_2_create_summary_largest_changes(self):
        """'Create a summary of the largest changes and save it as a new workbook.'"""
        async def _test():
            executor = ReliableExcelExecutor(context=self.ctx)
            res = await executor.execute_task(
                "Create a summary of the largest changes and save it as a new workbook.",
                workbook_path=self.sample_wb_path,
            )
            self.assertTrue(res["success"])

        asyncio.run(_test())

    def test_nl_3_find_duplicate_records(self):
        """'Find duplicate records and show me what you found before removing them.'"""
        async def _test():
            executor = ReliableExcelExecutor(context=self.ctx)
            res = await executor.execute_task(
                "Find duplicate records and show me what you found before removing them.",
                workbook_path=self.sample_wb_path,
            )
            self.assertTrue(res["success"])

        asyncio.run(_test())

    def test_nl_4_analyze_unusual(self):
        """'Analyze this workbook and tell me what looks unusual.'"""
        async def _test():
            executor = ReliableExcelExecutor(context=self.ctx)
            res = await executor.execute_task(
                "Analyze this workbook and tell me what looks unusual.",
                workbook_path=self.sample_wb_path,
            )
            self.assertTrue(res["success"])

        asyncio.run(_test())

    def test_nl_5_create_professional_summary_sheet(self):
        """'Create a professional summary sheet from the data.'"""
        async def _test():
            executor = ReliableExcelExecutor(context=self.ctx)
            res = await executor.execute_task(
                "Create a professional summary sheet from the data.",
                workbook_path=self.sample_wb_path,
            )
            self.assertTrue(res["success"])

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
