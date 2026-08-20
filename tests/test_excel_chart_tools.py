"""Tests for Excel chart creation, listing, and updating tools."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock

from cptr.utils.excel.openpyxl_backend import OpenPyXLBackend
from cptr.utils.excel.tools import excel_create_chart, excel_list_charts, excel_update_chart


class TestExcelChartTools(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.file_path = os.path.join(self.tmp_dir.name, "chart_test.xlsx")
        self.backend = OpenPyXLBackend(self.file_path)
        self.backend.create_workbook("Sheet1")
        # Write some sample data for the chart
        self.backend.write_range("A1", [["Category", "Value"], ["A", 10], ["B", 25], ["C", 15]])

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_openpyxl_chart_lifecycle(self):
        # 1. Create chart
        res = self.backend.create_chart(cell_range="A1:B4", chart_type="bar", title="Old Title", target_cell="D2")
        self.assertTrue(res.success, res.message)

        # 2. List charts
        list_res = self.backend.list_charts()
        self.assertTrue(list_res.success, list_res.message)
        self.assertEqual(list_res.data.get("count"), 1)
        self.assertEqual(list_res.data["charts"][0]["title"], "Old Title")

        # 3. Update chart title (e.g. rename bar chart)
        upd_res = self.backend.update_chart(chart_identifier=1, title="age wishes number")
        self.assertTrue(upd_res.success, upd_res.message)
        self.assertEqual(upd_res.data.get("title"), "age wishes number")

        # 4. Verify updated list
        list_res2 = self.backend.list_charts()
        self.assertEqual(list_res2.data["charts"][0]["title"], "age wishes number")


if __name__ == "__main__":
    unittest.main()
