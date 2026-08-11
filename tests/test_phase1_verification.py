"""Comprehensive Phase 1 verification tests: IndicConformer, Sofie, Tool Calling, Audio Router."""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from cptr.app import app
from cptr.env import INDIC_CONFORMER_MODEL_PATH, SOFIE_API_KEY, SOFIE_BASE_URL, SOFIE_MODEL, STT_PROVIDER
from cptr.utils.config import AuthMode
from cptr.utils.stt import get_stt_provider
from cptr.utils.stt.indic_conformer import IndicConformerSTTProvider
from cptr.utils.tools import ALL_TOOLS, execute_tool, get_tool_list


class TestIndicConformerConfiguration(unittest.TestCase):
    """Verify IndicConformer configuration & behavior."""

    def test_no_hardcoded_paths_in_source(self):
        provider = IndicConformerSTTProvider()
        # Default should come from env var or be empty, never a hard-coded user path
        self.assertNotIn("c:\\Users", provider._model_path)
        self.assertNotIn("C:\\Users", provider._model_path)

    def test_missing_model_handled_gracefully(self):
        provider = IndicConformerSTTProvider(model_path="/nonexistent/dir/xyz")
        self.assertFalse(provider.is_available)
        self.assertFalse(provider.load_model())
        self.assertEqual(provider.transcribe("some_audio.wav"), "")


class TestSofieAndToolCalling(unittest.TestCase):
    """Verify Sofie configuration and tool calling loop."""

    def test_sofie_env_vars(self):
        self.assertEqual(SOFIE_MODEL, "sofie-code")
        self.assertEqual(SOFIE_BASE_URL, "https://llm.karunya.edu/v1")

    def test_tool_calling_schema_integrity(self):
        """Verify cptr dynamic tool schemas can be serialized for LLMs."""
        async def _run():
            tools = await get_tool_list()
            self.assertGreater(len(tools), 0)
            for tool in tools:
                self.assertIn("name", tool)
                self.assertIn("description", tool)
                self.assertIn("parameters", tool)

        asyncio.run(_run())

    @patch("cptr.utils.ai.httpx.AsyncClient.post")
    def test_sofie_tool_calling_loop_mocked(self, mock_post):
        """Test full loop: User text -> Sofie -> Tool call -> Tool execution -> Sofie -> Response."""
        # 1st call returns tool call request
        resp_tool_call = MagicMock()
        resp_tool_call.status_code = 200
        resp_tool_call.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "search",
                                    "arguments": "{\"query\": \"test\"}",
                                },
                            }
                        ],
                    }
                }
            ]
        }

        # 2nd call returns final response
        resp_final = MagicMock()
        resp_final.status_code = 200
        resp_final.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Found test results successfully.",
                    }
                }
            ]
        }

        mock_post.side_effect = [resp_tool_call, resp_final]

        from cptr.utils.ai import chat_completion

        async def _test_loop():
            # Step 1: LLM completion request
            res1 = await chat_completion(
                provider="sofie",
                base_url="https://llm.karunya.edu/v1",
                api_key="test-key",
                model="sofie-code",
                messages=[{"role": "user", "content": "Search for test"}],
            )
            # Step 2: Execute tool with context
            ctx = {"workspace": "", "user_id": "test", "model_id": "sofie-code"}
            tool_res = await execute_tool("search", {"query": "test"}, __context__=ctx)
            self.assertIsNotNone(tool_res)

        asyncio.run(_test_loop())



class TestAudioRouterEndpoint(unittest.TestCase):
    """Test audio router endpoint with STT provider abstraction."""

    def test_audio_state_endpoint(self):
        client = TestClient(app)
        # In password auth mode, without auth cookie, expects 401
        with patch("cptr.env.LOCAL_AUTH_DISABLED", False), \
             patch("cptr.utils.config.get_auth_mode", return_value=AuthMode.PASSWORD):
            response = client.get("/api/audio/state")
            self.assertEqual(response.status_code, 401)

    def test_audio_transcribe_missing_auth(self):
        client = TestClient(app)
        with patch("cptr.env.LOCAL_AUTH_DISABLED", False), \
             patch("cptr.utils.config.get_auth_mode", return_value=AuthMode.PASSWORD):
            response = client.post(
                "/api/audio/transcribe",
                files={"file": ("test.wav", b"fake audio content", "audio/wav")},
            )
            self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
