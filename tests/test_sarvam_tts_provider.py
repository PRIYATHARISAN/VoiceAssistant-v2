"""Unit tests for Sarvam AI TTS Provider."""

import base64
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from cptr.utils.tts.base import TTSProvider
from cptr.utils.tts.sarvam import SarvamTTSProvider
from cptr.utils.tts import get_tts_provider


class TestSarvamTTSProvider(unittest.TestCase):
    def test_provider_initialization(self):
        provider = SarvamTTSProvider(api_key="test_key_123", model="bulbul:v1", default_voice="meera")
        self.assertEqual(provider.provider_name, "sarvam")
        self.assertTrue(provider.is_available)
        self.assertEqual(provider.api_key, "test_key_123")

    def test_get_tts_provider_factory(self):
        provider = get_tts_provider("sarvam")
        self.assertIsNotNone(provider)
        self.assertIsInstance(provider, SarvamTTSProvider)

    @patch("httpx.AsyncClient.post")
    def test_synthesize_success_base64_json(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        
        sample_audio_bytes = b"RIFF_FAKE_WAV_HEADER_DATA"
        sample_b64 = base64.b64encode(sample_audio_bytes).decode()
        mock_response.json.return_value = {"audios": [sample_b64]}
        mock_post.return_value = mock_response

        async def _test():
            provider = SarvamTTSProvider(api_key="sk_test")
            audio = await provider.synthesize(text="Hello Kural", voice="meera")
            self.assertEqual(audio, sample_audio_bytes)

        import asyncio
        asyncio.run(_test())

    def test_empty_text_validation(self):
        provider = SarvamTTSProvider(api_key="sk_test")
        async def _test():
            with self.assertRaises(ValueError):
                await provider.synthesize(text="   ")
        import asyncio
        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
