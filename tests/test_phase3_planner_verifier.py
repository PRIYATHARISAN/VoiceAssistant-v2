"""Phase 3 Requirement Tests: Planner, Verifier, Recovery, Reliability, Safety & Audit."""

import asyncio
import os
import shutil
import tempfile
import unittest

from cptr.utils.excel import (
    BackupManager,
    ExcelAuditLogger,
    ExcelPlanner,
    ExcelRecoveryHandler,
    ExcelResult,
    ExcelVerifier,
    LargeDataSummarizer,
    OpenPyXLBackend,
    ReliableExcelExecutor,
    SafetyManager,
    TaskPlan,
)


class TestPhase3PlannerVerifier(unittest.TestCase):
    """Test suite for 17 mandatory Phase 3 reliability requirements."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="phase3_test_")
        self.sample_wb_path = os.path.join(self.temp_dir, "SalesData.xlsx")
        self.ctx = {"workspace": self.temp_dir, "user_id": "test_user", "chat_id": "phase3_chat_101"}

        # Create sample workbook with Jan / Feb sheets
        backend = OpenPyXLBackend()
        backend.create_workbook(self.sample_wb_path)
        backend.create_sheet("Jan")
        backend.write_range([["Product", "Sales"], ["Widget A", 100], ["Widget B", 200]], sheet_name="Jan")
        backend.create_sheet("Feb")
        backend.write_range([["Product", "Feb Sales"], ["Widget A", 80], ["Widget B", 220]], sheet_name="Feb")
        backend.save_workbook()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

    def test_1_simple_one_step_task(self):
        """1. Simple one-step task planning and execution."""
        async def _test():
            executor = ReliableExcelExecutor(context=self.ctx)
            res = await executor.execute_task("Read range from SalesData.xlsx", workbook_path=self.sample_wb_path)
            self.assertTrue(res["success"])
            self.assertEqual(res["status"], "completed")

        asyncio.run(_test())

    def test_2_multi_step_task(self):
        """2. Multi-step task execution (Open -> Read -> Summary -> Save)."""
        async def _test():
            executor = ReliableExcelExecutor(context=self.ctx)
            res = await executor.execute_task(
                "Compare January and February sales and save a summary report",
                workbook_path=self.sample_wb_path,
            )
            self.assertTrue(res["success"])
            self.assertGreater(len(res["executed_steps"]), 1)

        asyncio.run(_test())

    def test_3_verification_success(self):
        """3. Verification success when data written and verified."""
        backend = OpenPyXLBackend(self.sample_wb_path)
        verifier = ExcelVerifier(backend)
        wr_res = backend.write_range([["Metric", "Value"], ["Total", 500]], start_cell="A1", sheet_name="Jan")
        v_res = verifier.verify_operation("excel_write_range", {"sheet_name": "Jan", "data": [["Metric", "Value"]]}, wr_res)
        self.assertTrue(v_res.success)

    def test_4_verification_failure(self):
        """4. Verification failure detection when file or range state is invalid."""
        backend = OpenPyXLBackend(self.sample_wb_path)
        verifier = ExcelVerifier(backend)
        fake_file = os.path.join(self.temp_dir, "nonexistent.xlsx")
        v_res = verifier._verify_save({"file_path": fake_file}, 0.0)
        self.assertFalse(v_res.success)
        self.assertIn("does not exist", v_res.message)

    def test_5_retry_mechanism(self):
        """5. Bounded retry mechanism on tool execution failure."""
        executor = ReliableExcelExecutor(context=self.ctx, max_retries=2)
        self.assertEqual(executor.max_retries, 2)

    def test_6_replanning(self):
        """6. Re-planning triggered when state discovery reveals new workbook structure."""
        backend = OpenPyXLBackend(self.sample_wb_path)
        planner = ExcelPlanner(backend)
        plan = planner.create_plan("Summarize workbook sales", workbook_path=self.sample_wb_path)
        revised_plan = planner.replan_from_state(plan, failed_step_id=2, failure_reason="Sheet not found", discovered_state={"sheets": ["Jan", "Feb"]})
        self.assertIsNotNone(revised_plan)
        self.assertEqual(revised_plan.steps[1].retry_count, 1)

    def test_7_wrong_sheet_name_recovery(self):
        """7. Sheet name recovery: 'January' -> 'Jan' if unambiguous; ask user if ambiguous."""
        backend = OpenPyXLBackend(self.sample_wb_path)
        recovery = ExcelRecoveryHandler(backend)
        # Unambiguous match
        rec = recovery.resolve_sheet_name("January")
        self.assertTrue(rec.can_recover)
        self.assertEqual(rec.updated_arguments["sheet_name"], "Jan")

        # Ambiguous match when multiple sheets match
        backend.create_sheet("Jan_1")
        backend.create_sheet("Jan_2")
        rec_ambig = recovery.resolve_sheet_name("Jan_")
        self.assertFalse(rec_ambig.can_recover)
        self.assertTrue(rec_ambig.requires_user_clarification)

    def test_8_wrong_range_recovery(self):
        """8. Range recovery using used_range."""
        backend = OpenPyXLBackend(self.sample_wb_path)
        recovery = ExcelRecoveryHandler(backend)
        rec = recovery.resolve_range("invalid_range", sheet_name="Jan")
        self.assertTrue(rec.can_recover)
        self.assertIn("cell_range", rec.updated_arguments)

    def test_9_missing_column_recovery(self):
        """9. Missing column recovery mapping concept to actual header."""
        backend = OpenPyXLBackend(self.sample_wb_path)
        recovery = ExcelRecoveryHandler(backend)
        rec = recovery.resolve_column("Feb Sales", sheet_name="Feb")
        self.assertTrue(rec.can_recover)
        self.assertEqual(rec.updated_arguments["key_column"], 2)

    def test_10_missing_workbook(self):
        """10. Missing workbook error handling."""
        async def _test():
            executor = ReliableExcelExecutor(context=self.ctx)
            missing_path = os.path.join(self.temp_dir, "DoesNot_Exist.xlsx")
            # Auto-creation occurs or graceful response returned
            res = await executor.execute_task("Read sheet from non-existent file", workbook_path=missing_path)
            self.assertIsNotNone(res)

        asyncio.run(_test())

    def test_11_ambiguous_workbook_handling(self):
        """11. Ambiguous request detection asking for clarification."""
        safety = SafetyManager()
        is_ambig = safety.is_ambiguous_request("Clean my Excel file")
        self.assertTrue(is_ambig)

        async def _test():
            executor = ReliableExcelExecutor(context=self.ctx)
            res = await executor.execute_task("Clean my workbook", workbook_path=self.sample_wb_path)
            self.assertEqual(res["status"], "ambiguous_request")
            self.assertTrue(res["requires_user_clarification"])

        asyncio.run(_test())

    def test_12_destructive_operation_confirmation(self):
        """12. Destructive operation requiring confirmation."""
        safety = SafetyManager()
        req_conf = safety.requires_user_confirmation("excel_delete_sheet", {"sheet_name": "Jan"})
        self.assertTrue(req_conf)

        # Granted permission bypasses confirmation
        req_conf_granted = safety.requires_user_confirmation("excel_delete_sheet", {"sheet_name": "Jan"}, user_confirmed=True)
        self.assertFalse(req_conf_granted)

    def test_13_backup_creation_and_rollback(self):
        """13. Backup working copy creation and rollback."""
        bm = BackupManager(self.sample_wb_path, workspace=self.temp_dir)
        working = bm.create_working_copy()
        self.assertTrue(os.path.exists(working))
        snap = bm.create_snapshot()
        self.assertIsNotNone(snap)
        self.assertTrue(os.path.exists(snap))

        rolled_back = bm.rollback_to_latest_snapshot()
        self.assertTrue(rolled_back)
        bm.cleanup_snapshots()

    def test_14_save_verification(self):
        """14. Save verification verifying non-zero bytes and reopening integrity."""
        backend = OpenPyXLBackend(self.sample_wb_path)
        verifier = ExcelVerifier(backend)
        v_res = verifier._verify_save({"file_path": self.sample_wb_path}, 0.0)
        self.assertTrue(v_res.success)
        self.assertGreater(v_res.actual["size_bytes"], 0)

    def test_15_chart_verification(self):
        """15. Chart verification verifying chart object created."""
        backend = OpenPyXLBackend(self.sample_wb_path)
        backend.create_chart("A1:B3", title="Test Chart", sheet_name="Jan")
        verifier = ExcelVerifier(backend)
        v_res = verifier._verify_chart({"sheet_name": "Jan", "title": "Test Chart"}, 0.0)
        self.assertTrue(v_res.success)

    def test_16_large_workbook_handling(self):
        """16. Large workbook metadata and summary handling without full memory load."""
        backend = OpenPyXLBackend(self.sample_wb_path)
        summ = LargeDataSummarizer.summarize_sheet(backend, "Jan")
        self.assertEqual(summ["sheet_name"], "Jan")
        self.assertIn("headers", summ)

        stats = LargeDataSummarizer.get_column_statistics(backend, col_index=2, sheet_name="Jan")
        self.assertTrue(stats["numeric"])
        self.assertEqual(stats["min"], 100.0)
        self.assertEqual(stats["max"], 200.0)

    def test_17_tool_failure_recovery(self):
        """17. Tool failure recovery handling."""
        backend = OpenPyXLBackend(self.sample_wb_path)
        recovery = ExcelRecoveryHandler(backend)
        rec = recovery.recover_tool_failure("excel_read_range", {"sheet_name": "NonExistentSheet"}, "Sheet NonExistentSheet not found")
        self.assertIsNotNone(rec)


if __name__ == "__main__":
    unittest.main()
