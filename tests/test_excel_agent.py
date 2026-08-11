"""Agent integration tests: Sofie LLM natural language Excel reasoning & tool execution."""

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from cptr.utils.excel.openpyxl_backend import OpenPyXLBackend
from cptr.utils.tools import execute_tool, get_tool_list


class TestExcelAgentIntegration(unittest.TestCase):
    """Test Sofie LLM natural language Excel multi-step workflows."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="excel_agent_test_")
        self.sales_file = os.path.join(self.temp_dir, "Sales.xlsx")
        self.ctx = {"workspace": self.temp_dir, "user_id": "agent_test_user", "chat_id": "agent_chat_456"}

        # Create sample Sales.xlsx workbook
        backend = OpenPyXLBackend()
        backend.create_workbook(self.sales_file)
        sample_sales_data = [
            ["Product", "January", "February"],
            ["Product A", 100, 80],
            ["Product B", 150, 200],
            ["Product C", 120, 90],
            ["Product D", 200, 210],
        ]
        backend.write_range(sample_sales_data, start_cell="A1")
        backend.save_workbook()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

    def test_excel_tools_available_in_agent_tool_list(self):
        """Verify Excel tool schemas are provided to Sofie agent."""
        async def _run():
            tools = await get_tool_list()
            excel_tool_names = {t["name"] for t in tools if t["name"].startswith("excel_")}
            self.assertIn("excel_open_workbook", excel_tool_names)
            self.assertIn("excel_read_range", excel_tool_names)
            self.assertIn("excel_write_range", excel_tool_names)
            self.assertIn("excel_create_sheet", excel_tool_names)
            self.assertIn("excel_format_range", excel_tool_names)
            self.assertIn("excel_create_chart", excel_tool_names)

        asyncio.run(_run())

    @patch("cptr.utils.ai.httpx.AsyncClient.post")
    def test_mocked_natural_language_compare_sales_loop(self, mock_post):
        """Simulate natural language flow: 'Compare January and February sales'."""
        # 1. Sofie selects excel_open_workbook
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "excel_open_workbook",
                            "arguments": json.dumps({"file_path": "Sales.xlsx"}),
                        },
                    }],
                }
            }]
        }

        # 2. Sofie selects excel_read_range
        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_2",
                        "type": "function",
                        "function": {
                            "name": "excel_read_range",
                            "arguments": json.dumps({"cell_range": "A1:C5"}),
                        },
                    }],
                }
            }]
        }

        # 3. Sofie gives final answer
        resp3 = MagicMock()
        resp3.status_code = 200
        resp3.json.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Products A (100 -> 80) and C (120 -> 90) decreased in revenue from January to February.",
                }
            }]
        }

        mock_post.side_effect = [resp1, resp2, resp3]

        from cptr.utils.ai import chat_completion

        async def _run_agent_flow():
            # Step 1: Open workbook
            res1 = await chat_completion(
                provider="sofie",
                base_url="https://llm.karunya.edu/v1",
                api_key="test-key",
                model="sofie-code",
                messages=[{"role": "user", "content": "Compare January and February sales"}],
            )
            tool_res1 = await execute_tool("excel_open_workbook", {"file_path": "Sales.xlsx"}, __context__=self.ctx)
            res1_json = json.loads(tool_res1)
            self.assertTrue(res1_json["success"])

            # Step 2: Read range
            res2 = await chat_completion(
                provider="sofie",
                base_url="https://llm.karunya.edu/v1",
                api_key="test-key",
                model="sofie-code",
                messages=[{"role": "user", "content": "Compare January and February sales"}],
            )
            tool_res2 = await execute_tool("excel_read_range", {"cell_range": "A1:C5"}, __context__=self.ctx)
            res2_json = json.loads(tool_res2)
            self.assertTrue(res2_json["success"])
            self.assertEqual(len(res2_json["data"]["rows"]), 5)

            # Step 3: Final LLM answer
            res3 = await chat_completion(
                provider="sofie",
                base_url="https://llm.karunya.edu/v1",
                api_key="test-key",
                model="sofie-code",
                messages=[{"role": "user", "content": "Compare January and February sales"}],
            )
            self.assertIn("decreased", res3)

        asyncio.run(_run_agent_flow())

    def test_multi_step_summary_highlight_chart_execution(self):
        """Test multi-step dynamic tools: open -> read -> create summary sheet -> write data -> format highlight -> create chart."""
        async def _run_multistep():
            # 1. Open
            res_open = json.loads(await execute_tool("excel_open_workbook", {"file_path": "Sales.xlsx"}, __context__=self.ctx))
            self.assertTrue(res_open["success"])

            # 2. Read sales data
            res_read = json.loads(await execute_tool("excel_read_range", {"cell_range": "A1:C5"}, __context__=self.ctx))
            self.assertTrue(res_read["success"])
            rows = res_read["data"]["rows"]

            # 3. Identify decreased products in Python logic (simulating LLM reasoning)
            decreased = [rows[0]]  # Header
            for r in rows[1:]:
                prod, jan, feb = r[0], float(r[1]), float(r[2])
                if feb < jan:
                    decreased.append([prod, jan, feb, feb - jan])

            decreased[0].append("Decrease")

            # 4. Create summary sheet
            res_cs = json.loads(await execute_tool("excel_create_sheet", {"sheet_name": "Summary"}, __context__=self.ctx))
            self.assertTrue(res_cs["success"])

            # 5. Write summary data
            res_wr = json.loads(await execute_tool("excel_write_range", {"data": decreased, "start_cell": "A1", "sheet_name": "Summary"}, __context__=self.ctx))
            self.assertTrue(res_wr["success"])

            # 6. Format highlight (light red fill for decreased cells)
            res_fmt = json.loads(await execute_tool("excel_format_range", {"cell_range": "A1:D3", "fill_color": "light_red", "bold": True, "sheet_name": "Summary"}, __context__=self.ctx))
            self.assertTrue(res_fmt["success"])

            # 7. Create summary chart
            res_chart = json.loads(await execute_tool("excel_create_chart", {"cell_range": "A1:C3", "chart_type": "col", "title": "Decreased Products Summary", "target_cell": "F2", "sheet_name": "Summary"}, __context__=self.ctx))
            self.assertTrue(res_chart["success"])

            # 8. Save
            res_save = json.loads(await execute_tool("excel_save_workbook", {}, __context__=self.ctx))
            self.assertTrue(res_save["success"])

        asyncio.run(_run_multistep())


class TestOptionalLiveSofieExcelAgent(unittest.TestCase):
    """Optional live integration test with real Sofie LLM endpoint (skips gracefully if SOFIE_API_KEY not set)."""

    def test_live_sofie_excel_query(self):
        api_key = os.getenv("SOFIE_API_KEY", "")
        if not api_key:
            self.skipTest("SOFIE_API_KEY not configured. Skipping live API test.")

        from cptr.utils.ai import chat_completion

        async def _test_live():
            res = await chat_completion(
                provider="sofie",
                base_url="https://llm.karunya.edu/v1",
                api_key=api_key,
                model="sofie-code",
                messages=[{"role": "user", "content": "Say 'Excel agent online'"}],
                max_tokens=20,
            )
            self.assertIsNotNone(res)

        asyncio.run(_test_live())


if __name__ == "__main__":
    unittest.main()
