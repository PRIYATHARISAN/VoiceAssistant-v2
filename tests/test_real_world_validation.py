"""Real-World Validation & End-to-End Testing Suite for Sofie Excel Assistant."""

import asyncio
import os
import shutil
import tempfile
import time
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
    get_excel_session,
)
from cptr.utils.stt import IndicConformerSTTProvider, get_stt_provider


class TestRealWorldValidation(unittest.TestCase):
    """Real-World Validation covering Steps 3-15 of Phase 3 Verification."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="real_world_val_")
        self.ctx = {"workspace": self.temp_dir, "user_id": "val_user", "chat_id": "val_chat_999"}

        # Create Workbooks for Step 5
        # A. Sales Workbook
        self.sales_wb = os.path.join(self.temp_dir, "Sales_Q1.xlsx")
        b1 = OpenPyXLBackend()
        b1.create_workbook(self.sales_wb)
        b1.create_sheet("Jan")
        b1.write_range([["Product", "Jan Sales"], ["Laptop", 100], ["Phone", 150]], sheet_name="Jan")
        b1.create_sheet("Feb")
        b1.write_range([["Product", "Feb Sales"], ["Laptop", 80], ["Phone", 180]], sheet_name="Feb")
        b1.save_workbook()

        # B. Student Marks Workbook
        self.marks_wb = os.path.join(self.temp_dir, "Student_Marks.xlsx")
        b2 = OpenPyXLBackend()
        b2.create_workbook(self.marks_wb)
        b2.write_range([["Student", "Math", "Science", "English"], ["Alice", 85, 90, 78], ["Bob", 92, 88, 95], ["Charlie", 60, 65, 70]], start_cell="A1")
        b2.save_workbook()

        # C. Employee Workbook
        self.emp_wb = os.path.join(self.temp_dir, "Employees.xlsx")
        b3 = OpenPyXLBackend()
        b3.create_workbook(self.emp_wb)
        b3.write_range([["Name", "Department", "Salary"], ["John", "Sales", 50000], ["Mary", "Engineering", 75000], ["David", "Sales", 52000]], start_cell="A1")
        b3.save_workbook()

        # D. Expense Workbook
        self.exp_wb = os.path.join(self.temp_dir, "Expenses.xlsx")
        b4 = OpenPyXLBackend()
        b4.create_workbook(self.exp_wb)
        b4.write_range([["Category", "Amount"], ["Rent", 2000], ["Utilities", 300], ["Food", 600], ["Utilities", 300]], start_cell="A1")
        b4.save_workbook()

        # E. Large Dataset Workbook (>1000 rows)
        self.large_wb = os.path.join(self.temp_dir, "LargeData.xlsx")
        b5 = OpenPyXLBackend()
        b5.create_workbook(self.large_wb)
        large_rows = [["ID", "Region", "Value"]] + [[i, f"Region_{i % 5}", i * 10.5] for i in range(1, 1001)]
        b5.write_range(large_rows, start_cell="A1")
        b5.save_workbook()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

    def test_step3_stt_provider_interface(self):
        """STEP 3: Test IndicConformer STT provider interface, language resolution, audio check."""
        stt = get_stt_provider()
        self.assertIsNotNone(stt)

        # Test language resolution
        if isinstance(stt, IndicConformerSTTProvider):
            self.assertEqual(stt._resolve_language("hi"), "hi")
            self.assertEqual(stt._resolve_language("ta"), "ta")
            self.assertEqual(stt._resolve_language("invalid_lang"), "hi")

        # Test empty audio file handling
        dummy_audio = os.path.join(self.temp_dir, "silent.wav")
        with open(dummy_audio, "wb") as f:
            f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\x3e\x00\x00\x00\x7d\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        t0 = time.time()
        res_text = stt.transcribe(dummy_audio)
        stt_ms = (time.time() - t0) * 1000
        self.assertEqual(res_text, "")
        self.assertLess(stt_ms, 5000)

    def test_step4_20_varied_natural_language_queries(self):
        """STEP 4: Test 20 varied natural-language Excel queries."""
        queries = [
            "Open my sales file and tell me which products decreased.",
            "Compare the two months and create a summary.",
            "Make this spreadsheet look professional.",
            "Find duplicate records.",
            "Clean up this workbook.",
            "Create a chart showing monthly revenue.",
            "Add a new column calculating profit.",
            "Find anything unusual in this data.",
            "Take the data from Sheet1 and create a summary in another sheet.",
            "Calculate total salary by department.",
            "Format the top row as bold header.",
            "Sort employee data by salary descending.",
            "Filter expenses greater than 500.",
            "Highlight values lower than 100.",
            "Compute average student marks for Math.",
            "Check if there are blank rows.",
            "Create a column chart for quarterly sales.",
            "Rename Sheet1 to Q1_Sales.",
            "Delete duplicate entries from expenses.",
            "Save the updated workbook as a new file.",
        ]

        async def _run_all():
            executor = ReliableExcelExecutor(context=self.ctx)
            for q in queries:
                res = await executor.execute_task(q, workbook_path=self.sales_wb, user_confirmed=True)
                self.assertIsNotNone(res)
                self.assertIn("status", res)

        asyncio.run(_run_all())

    def test_step5_real_workbooks_testing(self):
        """STEP 5: Test against Sales, Student Marks, Employee, Expense workbooks."""
        async def _run_wbs():
            executor = ReliableExcelExecutor(context=self.ctx)

            # Sales WB
            r1 = await executor.execute_task("Compare Jan and Feb sales", workbook_path=self.sales_wb, user_confirmed=True)
            self.assertTrue(r1["success"])

            # Student Marks WB
            r2 = await executor.execute_task("Calculate total marks for all students", workbook_path=self.marks_wb, user_confirmed=True)
            self.assertTrue(r2["success"])

            # Employee WB
            r3 = await executor.execute_task("Find highest paid employee in Engineering", workbook_path=self.emp_wb, user_confirmed=True)
            self.assertTrue(r3["success"])

            # Expense WB
            r4 = await executor.execute_task("Find duplicate records", workbook_path=self.exp_wb, user_confirmed=True)
            self.assertTrue(r4["success"])

        asyncio.run(_run_wbs())

    def test_step6_unanticipated_requests(self):
        """STEP 6: Test open-ended reasoning requests."""
        async def _run_unanticipated():
            executor = ReliableExcelExecutor(context=self.ctx)
            unanticipated = [
                "Can you make this sheet easier to understand?",
                "Which part of this workbook needs attention?",
                "Give me a quick overview of this file.",
                "Why is March revenue lower?",
                "Clean this data but don't delete anything important.",
            ]
            for q in unanticipated:
                res = await executor.execute_task(q, workbook_path=self.sales_wb, user_confirmed=True)
                self.assertTrue(res["success"] or res["status"] in ("ambiguous_request", "completed"))

        asyncio.run(_run_unanticipated())

    def test_step7_ambiguity_handling(self):
        """STEP 7: Test ambiguous request handling asking clarification when not confirmed."""
        async def _run_ambig():
            executor = ReliableExcelExecutor(context=self.ctx)
            res = await executor.execute_task("Clean this file.", workbook_path=self.sales_wb, user_confirmed=False)
            self.assertEqual(res["status"], "ambiguous_request")
            self.assertTrue(res["requires_user_clarification"])

        asyncio.run(_run_ambig())

    def test_step8_destructive_action_confirmation(self):
        """STEP 8: Test destructive actions require confirmation and generate backups."""
        async def _run_destr():
            executor = ReliableExcelExecutor(context=self.ctx)
            # Without confirmation -> blocked
            r1 = await executor.execute_task("Delete sheet Jan", workbook_path=self.sales_wb, user_confirmed=False)
            self.assertEqual(r1["status"], "confirmation_required")

            # Backup manager creates working copy
            bm = BackupManager(self.sales_wb, workspace=self.temp_dir)
            w_path = bm.create_working_copy()
            self.assertTrue(os.path.exists(w_path))
            self.assertEqual(os.path.getsize(self.sales_wb), os.path.getsize(w_path))

        asyncio.run(_run_destr())

    def test_step9_failure_and_recovery(self):
        """STEP 9: Test recovery on wrong sheet name, wrong range, missing column."""
        backend = OpenPyXLBackend(self.sales_wb)
        backend.open_workbook(self.sales_wb)
        recovery = ExcelRecoveryHandler(backend)

        # Wrong sheet name recovery ("January" -> "Jan")
        rec_sheet = recovery.resolve_sheet_name("January")
        self.assertTrue(rec_sheet.can_recover)

        # Range recovery
        rec_range = recovery.resolve_range("A1:Z100", sheet_name="Jan")
        self.assertTrue(rec_range.can_recover)

        # Column recovery ("Feb" -> "Feb Sales")
        rec_col = recovery.resolve_column("Feb", sheet_name="Feb")
        self.assertTrue(rec_col.can_recover)

    def test_step10_large_data_handling(self):
        """STEP 10: Test large dataset (>1000 rows) handling without flooding memory."""
        backend = OpenPyXLBackend(self.large_wb)
        backend.open_workbook(self.large_wb)

        t0 = time.time()
        summ = LargeDataSummarizer.summarize_sheet(backend, sample_rows=5)
        proc_time_ms = (time.time() - t0) * 1000

        self.assertEqual(summ["total_rows"], 1001)
        self.assertEqual(len(summ["sample_rows"]), 6)  # header + 5 samples
        self.assertLess(proc_time_ms, 500)  # fast execution under 500ms

        stats = LargeDataSummarizer.get_column_statistics(backend, col_index=3)
        self.assertTrue(stats["numeric"])
        self.assertEqual(stats["count"], 1000)

    def test_step12_conversational_context(self):
        """STEP 12: Test multi-turn session state persistence."""
        session = get_excel_session(self.ctx)
        session.active_workbook_path = self.sales_wb
        session.active_sheet_name = "Jan"

        # Turn 1
        s1 = get_excel_session(self.ctx)
        self.assertEqual(s1.active_workbook_path, self.sales_wb)

        # Turn 2
        s1.active_sheet_name = "Feb"
        s2 = get_excel_session(self.ctx)
        self.assertEqual(s2.active_sheet_name, "Feb")

    def test_step13_performance_latency_breakdown(self):
        """STEP 13: Measure latency for planning, execution, verification, and total task."""
        async def _perf():
            executor = ReliableExcelExecutor(context=self.ctx)
            t0 = time.time()
            res = await executor.execute_task("Compare Jan and Feb sales", workbook_path=self.sales_wb, user_confirmed=True)
            total_ms = (time.time() - t0) * 1000

            self.assertTrue(res["success"])
            self.assertIn("total_duration_ms", res)
            self.assertLess(total_ms, 3000)  # Fast execution under 3s

        asyncio.run(_perf())

    def test_step15_security_secret_scrubbing(self):
        """STEP 15: Verify secret scrubbing in audit logs."""
        logger = ExcelAuditLogger(session_id="sec_test")
        logger.log_request("Process key sk-1234567890abcdef1234567890 with SOFIE_API_KEY=secret_key_999")
        logs = logger.get_logs()
        log_str = str(logs)

        self.assertNotIn("sk-1234567890abcdef1234567890", log_str)
        self.assertNotIn("secret_key_999", log_str)
        self.assertIn("[REDACTED]", log_str)


if __name__ == "__main__":
    unittest.main()
