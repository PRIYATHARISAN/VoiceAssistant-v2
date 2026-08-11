"""Unit tests for Excel tool functions, schemas, and safety controls."""

import asyncio
import json
import os
import tempfile
import unittest

from cptr.utils.excel.tools import (
    excel_clear_range,
    excel_create_sheet,
    excel_delete_sheet,
    excel_open_workbook,
    excel_read_range,
    excel_write_range,
)
from cptr.utils.tools import get_tool_list


class TestExcelTools(unittest.TestCase):
    """Test suite for typed Excel tools."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="excel_tools_test_")
        self.test_file = os.path.join(self.temp_dir, "tools_test.xlsx")
        self.ctx = {"workspace": self.temp_dir, "user_id": "test_user", "chat_id": "test_chat_123"}

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

    def test_excel_tools_registered_in_schemas(self):
        async def _run():
            schemas = await get_tool_list()
            excel_schemas = [s for s in schemas if s["name"].startswith("excel_")]
            self.assertGreaterEqual(len(excel_schemas), 15)
            tool_names = {s["name"] for s in excel_schemas}
            self.assertIn("excel_open_workbook", tool_names)
            self.assertIn("excel_read_range", tool_names)
            self.assertIn("excel_write_range", tool_names)
            self.assertIn("excel_format_range", tool_names)
            self.assertIn("excel_create_chart", tool_names)

        asyncio.run(_run())

    def test_open_write_read_tool_flow(self):
        async def _run():
            # Open (creates file)
            res_open_str = await excel_open_workbook("test_flow.xlsx", __context__=self.ctx)
            res_open = json.loads(res_open_str)
            self.assertTrue(res_open["success"])

            # Write range
            data = [["Month", "Revenue"], ["Jan", 5000], ["Feb", 4200]]
            res_write_str = await excel_write_range(data=data, start_cell="A1", __context__=self.ctx)
            res_write = json.loads(res_write_str)
            self.assertTrue(res_write["success"])

            # Read range
            res_read_str = await excel_read_range("A1:B3", __context__=self.ctx)
            res_read = json.loads(res_read_str)
            self.assertTrue(res_read["success"])
            self.assertEqual(len(res_read["data"]["rows"]), 3)

        asyncio.run(_run())

    def test_confirmation_required_for_destructive_action(self):
        async def _run():
            await excel_open_workbook("test_destruct.xlsx", __context__=self.ctx)
            await excel_create_sheet("SheetToDelete", __context__=self.ctx)

            # Delete without confirmation -> requires_confirmation = True
            res_del_no_confirm_str = await excel_delete_sheet("SheetToDelete", confirm=False, __context__=self.ctx)
            res_del_no_confirm = json.loads(res_del_no_confirm_str)
            self.assertFalse(res_del_no_confirm["success"])
            self.assertTrue(res_del_no_confirm.get("requires_confirmation"))

            # Delete with confirmation -> success + backup path
            res_del_confirm_str = await excel_delete_sheet("SheetToDelete", confirm=True, __context__=self.ctx)
            res_del_confirm = json.loads(res_del_confirm_str)
            self.assertTrue(res_del_confirm["success"])
            self.assertTrue(bool(res_del_confirm.get("backup_path")))

        asyncio.run(_run())

    def test_clear_range_confirmation(self):
        async def _run():
            await excel_open_workbook("test_clear.xlsx", __context__=self.ctx)
            await excel_write_range([["A", "B"]], "A1", __context__=self.ctx)

            res_clear_no_confirm_str = await excel_clear_range("A1:B1", confirm=False, __context__=self.ctx)
            res_clear_no_confirm = json.loads(res_clear_no_confirm_str)
            self.assertTrue(res_clear_no_confirm.get("requires_confirmation"))

            res_clear_confirm_str = await excel_clear_range("A1:B1", confirm=True, __context__=self.ctx)
            res_clear_confirm = json.loads(res_clear_confirm_str)
            self.assertTrue(res_clear_confirm["success"])

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
