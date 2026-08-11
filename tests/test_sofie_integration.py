"""Unit and integration tests for Sofie LLM adapter and tool calling loop."""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from cptr.env import SOFIE_API_KEY, SOFIE_BASE_URL, SOFIE_MODEL
from cptr.routers.chat import _get_connections


class TestSofieConfiguration(unittest.TestCase):
    """Test Sofie configuration and connection resolution."""

    def test_default_env_vars(self):
        self.assertIsNotNone(SOFIE_BASE_URL)
        self.assertIsNotNone(SOFIE_MODEL)
        self.assertEqual(SOFIE_MODEL, "sofie-code")
        self.assertIn("karunya.edu", SOFIE_BASE_URL)

    @patch.dict(os.environ, {"SOFIE_API_KEY": "test-sofie-key-123"})
    def test_get_connections_includes_sofie(self):
        async def _test():
            conns = await _get_connections()
            sofie_conns = [c for c in conns if c.get("prefix_id") == "sofie"]
            self.assertGreaterEqual(len(sofie_conns), 1)
            conn = sofie_conns[0]
            self.assertEqual(conn["api_key"], "test-sofie-key-123")
            self.assertEqual(conn["base_url"], "https://llm.karunya.edu/v1")
            self.assertIn("sofie-code", conn["data"]["models"])

        asyncio.run(_test())


class TestSofieToolCallLoop(unittest.TestCase):
    """Verify that Sofie works with cptr dynamic tool call loop."""

    @patch("cptr.utils.ai.httpx.AsyncClient.post")
    def test_sofie_openai_completion_call(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Sofie response test",
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        from cptr.utils.ai import chat_completion

        async def _run():
            res = await chat_completion(
                provider="sofie",
                base_url="https://llm.karunya.edu/v1",
                api_key="test-key",
                model="sofie-code",
                messages=[{"role": "user", "content": "Hello Sofie"}],
            )
            self.assertEqual(res, "Sofie response test")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
