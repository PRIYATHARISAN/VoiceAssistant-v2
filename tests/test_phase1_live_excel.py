"""Phase 1 Unit & Integration Tests: Live Excel Natural Language Control Architecture."""

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from cptr.utils.excel.backend_base import ExcelResult
from cptr.utils.excel.openpyxl_backend import OpenPyXLBackend
from cptr.utils.excel.session import ExcelSession, get_excel_session
from cptr.utils.excel.win32com_backend import is_win32com_available
from cptr.utils.excel import EXCEL_TOOLS
from cptr.utils.tools import execute_tool, get_tool_list


class TestPhase1SessionBackendSelection(unittest.TestCase):
    """Verify ExcelSession backend selection behavior on Windows vs fallback."""

    @patch("cptr.utils.excel.session.is_win32com_available")
    def test_session_selects_win32com_when_available(self, mock_com_avail):
        """1. Excel session selects live Win32COM backend on Windows when COM is available."""
        mock_com_avail.return_value = True
        session = ExcelSession("test_session_win")

        with patch("cptr.utils.excel.session.Win32COMBackend") as mock_backend_cls:
            mock_inst = MagicMock()
            mock_backend_cls.return_value = mock_inst
            backend = session.ensure_backend()
            mock_backend_cls.assert_called_once()
            self.assertEqual(backend, mock_inst)

    @patch("cptr.utils.excel.session.is_win32com_available")
    def test_session_falls_back_to_openpyxl_when_com_unavailable(self, mock_com_avail):
        """7. Session falls back to OpenPyXL when Win32COM is unavailable."""
        mock_com_avail.return_value = False
        session = ExcelSession("test_session_fallback")
        backend = session.ensure_backend()
        self.assertIsInstance(backend, OpenPyXLBackend)

    def test_explicit_live_mode_false_forces_openpyxl(self):
        """Preserves explicit live_mode=False setting."""
        session = ExcelSession("test_session_explicit_false")
        backend = session.ensure_backend(live_mode=False)
        self.assertIsInstance(backend, OpenPyXLBackend)


class TestPhase1ExcelToolsUnit(unittest.TestCase):
    """Unit tests for Phase 1 tools (open, create, cell write, range write, formula)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="phase1_excel_test_")
        self.ctx = {"workspace": self.temp_dir, "user_id": "user1", "chat_id": "chat_phase1"}

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

    def test_excel_open_workbook_accepts_empty_path(self):
        """2. excel_open_workbook accepts an empty/no-path request ("Open Excel")."""
        async def _run():
            res_str = await execute_tool("excel_open_workbook", {"file_path": ""}, __context__=self.ctx)
            res = json.loads(res_str)
            self.assertTrue(res["success"])
            self.assertIn("operation", res)

        asyncio.run(_run())

    def test_excel_create_workbook_creates_workbook(self):
        """3. excel_create_workbook creates a new workbook ("Create a new workbook")."""
        async def _run():
            res_str = await execute_tool("excel_create_workbook", {}, __context__=self.ctx)
            res = json.loads(res_str)
            self.assertTrue(res["success"])
            self.assertEqual(res["operation"], "create_workbook")

        asyncio.run(_run())

    def test_writing_single_cell(self):
        """4. Writing a single cell works ("Enter 10 in A1")."""
        async def _run():
            await execute_tool("excel_create_workbook", {}, __context__=self.ctx)
            res_str = await execute_tool("excel_update_cell", {"cell": "A1", "value": 10}, __context__=self.ctx)
            res = json.loads(res_str)
            self.assertTrue(res["success"])

            # Read back cell
            read_str = await execute_tool("excel_read_range", {"cell_range": "A1"}, __context__=self.ctx)
            read_res = json.loads(read_str)
            self.assertTrue(read_res["success"])
            self.assertEqual(read_res["data"]["rows"][0][0], 10)

        asyncio.run(_run())

    def test_writing_multiple_values(self):
        """5. Writing multiple values works ("Create a column called Numbers and add 10, 20, 30, 40 and 50")."""
        async def _run():
            await execute_tool("excel_create_workbook", {}, __context__=self.ctx)
            data = [["Numbers"], [10], [20], [30], [40], [50]]
            res_str = await execute_tool("excel_write_range", {"data": data, "start_cell": "A1"}, __context__=self.ctx)
            res = json.loads(res_str)
            self.assertTrue(res["success"])

            # Read back range
            read_str = await execute_tool("excel_read_range", {"cell_range": "A1:A6"}, __context__=self.ctx)
            read_res = json.loads(read_str)
            self.assertTrue(read_res["success"])
            self.assertEqual(len(read_res["data"]["rows"]), 6)

        asyncio.run(_run())

    def test_formula_writing(self):
        """6. Formula writing works ("calculate total in A4")."""
        async def _run():
            await execute_tool("excel_create_workbook", {}, __context__=self.ctx)
            await execute_tool("excel_update_cell", {"cell": "A1", "value": 10}, __context__=self.ctx)
            await execute_tool("excel_update_cell", {"cell": "A2", "value": 20}, __context__=self.ctx)
            await execute_tool("excel_update_cell", {"cell": "A3", "value": 30}, __context__=self.ctx)

            res_str = await execute_tool("excel_write_formula", {"cell": "A4", "formula": "=SUM(A1:A3)"}, __context__=self.ctx)
            res = json.loads(res_str)
            self.assertTrue(res["success"])

            # Read back formula cell (live mode returns evaluated 60.0, openpyxl returns formula string)
            read_str = await execute_tool("excel_read_range", {"cell_range": "A4"}, __context__=self.ctx)
            read_res = json.loads(read_str)
            self.assertTrue(read_res["success"])
            val = read_res["data"]["rows"][0][0]
            self.assertTrue(val == 60 or val == 60.0 or val == "=SUM(A1:A3)")

        asyncio.run(_run())


class TestPhase1ToolRegistration(unittest.TestCase):
    """8. Tool registration exposes all required Excel tools with proper approval settings."""

    def test_excel_tools_exported_and_registered(self):
        self.assertIn("excel_open_workbook", EXCEL_TOOLS)
        self.assertIn("excel_create_workbook", EXCEL_TOOLS)
        self.assertIn("excel_update_cell", EXCEL_TOOLS)
        self.assertIn("excel_write_range", EXCEL_TOOLS)
        self.assertIn("excel_write_formula", EXCEL_TOOLS)
        self.assertIn("excel_format_range", EXCEL_TOOLS)

        # Check approval settings
        self.assertEqual(EXCEL_TOOLS["excel_open_workbook"].get("approval"), "allow")
        self.assertEqual(EXCEL_TOOLS["excel_create_workbook"].get("approval"), "allow")
        self.assertEqual(EXCEL_TOOLS["excel_update_cell"].get("approval"), "allow")
        self.assertEqual(EXCEL_TOOLS["excel_write_range"].get("approval"), "allow")
        self.assertEqual(EXCEL_TOOLS["excel_write_formula"].get("approval"), "allow")

        # Destructive tools must NOT be blindly allowed
        self.assertNotIn("approval", EXCEL_TOOLS["excel_delete_sheet"])
        self.assertNotIn("approval", EXCEL_TOOLS["excel_clear_range"])

    def test_get_tool_list_includes_excel_tools(self):
        async def _run():
            tools = await get_tool_list()
            names = {t["name"] for t in tools}
            self.assertIn("excel_open_workbook", names)
            self.assertIn("excel_create_workbook", names)
            self.assertIn("excel_update_cell", names)
            self.assertIn("excel_write_range", names)
            self.assertIn("excel_write_formula", names)

        asyncio.run(_run())


class TestPhase1LiveWin32COMIntegration(unittest.TestCase):
    """Optional Windows live integration test (runs only on Windows when Excel COM is present)."""

    def test_real_live_excel_workflow_if_available(self):
        if not is_win32com_available():
            self.skipTest("Live Win32COM Excel is unavailable on this machine. Skipping live desktop test.")

        ctx = {"workspace": "", "user_id": "live_user", "chat_id": "live_chat"}

        async def _run_live():
            # 1. Open Excel
            res1 = json.loads(await execute_tool("excel_open_workbook", {"file_path": ""}, __context__=ctx))
            self.assertTrue(res1["success"])

            # 2. Create workbook
            res2 = json.loads(await execute_tool("excel_create_workbook", {}, __context__=ctx))
            self.assertTrue(res2["success"])

            # 3. Enter 10 in A1
            res3 = json.loads(await execute_tool("excel_update_cell", {"cell": "A1", "value": 10}, __context__=ctx))
            self.assertTrue(res3["success"])

            # 4. Enter 20 in A2
            res4 = json.loads(await execute_tool("excel_update_cell", {"cell": "A2", "value": 20}, __context__=ctx))
            self.assertTrue(res4["success"])

            # 5. Formula in A3
            res5 = json.loads(await execute_tool("excel_write_formula", {"cell": "A3", "formula": "=SUM(A1:A2)"}, __context__=ctx))
            self.assertTrue(res5["success"])

            # Close without error
            await execute_tool("excel_close_workbook", {}, __context__=ctx)

        asyncio.run(_run_live())


if __name__ == "__main__":
    unittest.main()
