"""Unit and integration tests for Kural AI Voice Silent Execution and Smart Responses."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from cptr.utils.chat_task import (
    VOICE_MODE_SYSTEM_PROMPT,
    _apply_voice_mode_system_prompt,
)


class TestKuralVoiceSilentExecution(unittest.IsolatedAsyncioTestCase):
    async def test_voice_mode_system_prompt_rules(self):
        """Verify prompt contains strict silent action and 1-2 sentence rules."""
        self.assertIn("SILENT ACTION FIRST", VOICE_MODE_SYSTEM_PROMPT)
        self.assertIn("CONCISE FINAL SPOKEN CONFIRMATION", VOICE_MODE_SYSTEM_PROMPT)
        self.assertIn("SMART CONTEXT DEFAULTS", VOICE_MODE_SYSTEM_PROMPT)
        self.assertIn("TANGLISH", VOICE_MODE_SYSTEM_PROMPT)

    async def test_apply_voice_mode_system_prompt(self):
        """Verify voice mode system prompt is appended when voice_mode=True."""
        base_system = "You are a helpful assistant."
        non_voice = await _apply_voice_mode_system_prompt(base_system, {"voice_mode": False})
        self.assertEqual(non_voice, base_system)

        voice = await _apply_voice_mode_system_prompt(base_system, {"voice_mode": True})
        self.assertIn("[VOICE MODE]", voice)
        self.assertIn("SILENT ACTION FIRST", voice)


if __name__ == "__main__":
    unittest.main()
