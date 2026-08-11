"""Unit tests for OpenPyXL Excel backend operations."""

import json
import os
import tempfile
import unittest

from cptr.utils.excel.openpyxl_backend import OpenPyXLBackend


class TestOpenPyXLBackend(unittest.TestCase):
    """Test suite for OpenPyXL file-based Excel backend."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="excel_backend_test_")
        self.test_file = os.path.join(self.temp_dir, "test_sales.xlsx")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

    def test_workbook_create_and_open(self):
        backend = OpenPyXLBackend()
        res_create = backend.create_workbook(self.test_file)
        self.assertTrue(res_create.success)
        self.assertTrue(os.path.exists(self.test_file))

        backend_open = OpenPyXLBackend()
        res_open = backend_open.open_workbook(self.test_file)
        self.assertTrue(res_open.success)
        self.assertIn("Sheet", res_open.data["sheets"])

    def test_sheet_operations(self):
        backend = OpenPyXLBackend()
        backend.create_workbook(self.test_file)

        # Create sheet
        res_create_s = backend.create_sheet("January")
        self.assertTrue(res_create_s.success)

        # List sheets
        res_list = backend.list_sheets()
        self.assertIn("January", res_list.data["sheets"])

        # Rename sheet
        res_rename = backend.rename_sheet("January", "Jan_Sales")
        self.assertTrue(res_rename.success)

        # Delete sheet
        backend.create_sheet("TempSheet")
        res_del = backend.delete_sheet("TempSheet")
        self.assertTrue(res_del.success)

    def test_range_write_and_read(self):
        backend = OpenPyXLBackend()
        backend.create_workbook(self.test_file)

        sample_data = [
            ["Product", "January", "February"],
            ["Widget A", 100, 80],
            ["Widget B", 150, 200],
            ["Widget C", 120, 90],
        ]

        res_write = backend.write_range(sample_data, start_cell="A1")
        self.assertTrue(res_write.success)
        backend.save_workbook()

        # Read back
        backend_read = OpenPyXLBackend(self.test_file)
        res_read = backend_read.read_range("A1:C4")
        self.assertTrue(res_read.success)
        self.assertEqual(len(res_read.data["rows"]), 4)
        self.assertEqual(res_read.data["headers"], ["Product", "January", "February"])

    def test_formula_preservation(self):
        backend = OpenPyXLBackend()
        backend.create_workbook(self.test_file)

        backend.write_range([["Value1", "Value2", "Total"], [10, 20, None]], "A1")
        res_f = backend.write_formula("C2", "=SUM(A2:B2)")
        self.assertTrue(res_f.success)

        res_read = backend.read_range("C2")
        self.assertEqual(res_read.data["rows"][0][0], "=SUM(A2:B2)")

    def test_sort_and_filter(self):
        backend = OpenPyXLBackend()
        backend.create_workbook(self.test_file)

        sample_data = [
            ["Product", "Sales"],
            ["Item C", 30],
            ["Item A", 10],
            ["Item B", 20],
        ]
        backend.write_range(sample_data, "A1")

        # Sort ascending by Product (col 1)
        res_sort = backend.sort_range("A1:B4", key_column=1, ascending=True, has_headers=True)
        self.assertTrue(res_sort.success)

        res_read = backend.read_range("A2:A4")
        sorted_products = [r[0] for r in res_read.data["rows"]]
        self.assertEqual(sorted_products, ["Item A", "Item B", "Item C"])

        # Filter (non-destructive check)
        res_filter = backend.filter_range("A1:B4", column_index=1, criteria="Item A")
        self.assertTrue(res_filter.success)
        self.assertEqual(res_filter.data["total_matches"], 1)
        # Verify no rows were deleted from sheet
        res_check_all = backend.read_range("A1:B4")
        self.assertEqual(len(res_check_all.data["rows"]), 4)

    def test_formatting_and_chart(self):
        backend = OpenPyXLBackend()
        backend.create_workbook(self.test_file)

        data = [
            ["Category", "Value"],
            ["Alpha", 40],
            ["Beta", 60],
        ]
        backend.write_range(data, "A1")

        res_fmt = backend.format_range("A1:B1", bold=True, fill_color="FFFF00", auto_fit=True)
        self.assertTrue(res_fmt.success)

        res_chart = backend.create_chart("A1:B3", chart_type="col", title="Test Chart", target_cell="D2")
        self.assertTrue(res_chart.success)

        backend.save_workbook()


if __name__ == "__main__":
    unittest.main()
