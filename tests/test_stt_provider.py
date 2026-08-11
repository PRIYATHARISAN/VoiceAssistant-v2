"""Unit tests for STT Provider interface and IndicConformer implementation."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from cptr.utils.stt.base import STTProvider
from cptr.utils.stt.indic_conformer import IndicConformerSTTProvider
from cptr.utils.stt import get_stt_provider


class TestSTTProviderInterface(unittest.TestCase):
    """Test STTProvider abstract base class and factory."""

    def test_factory_default(self):
        provider = get_stt_provider()
        self.assertIsNotNone(provider)
        self.assertEqual(provider.provider_name, "indic_conformer")

    def test_factory_unknown_provider(self):
        provider = get_stt_provider("unknown_provider_xyz")
        self.assertIsNone(provider)

    def test_missing_model_path_returns_unavailable(self):
        provider = IndicConformerSTTProvider(model_path="/nonexistent/model/path")
        self.assertFalse(provider.is_available)

    def test_missing_model_path_transcribe_returns_empty(self):
        provider = IndicConformerSTTProvider(model_path="/nonexistent/model/path")
        result = provider.transcribe("nonexistent_audio.wav")
        self.assertEqual(result, "")

    def test_invalid_audio_path_returns_empty(self):
        provider = IndicConformerSTTProvider(model_path="/nonexistent/path")
        result = provider.transcribe("nonexistent_audio_file_123.wav")
        self.assertEqual(result, "")

    def test_normalize_transcription(self):
        provider = IndicConformerSTTProvider()
        self.assertEqual(provider._normalize_transcription("  hello world  "), "hello world")
        self.assertEqual(provider._normalize_transcription(("test", 0.9)), "test")
        self.assertEqual(provider._normalize_transcription(None), "")
        self.assertEqual(provider._normalize_transcription("none"), "")
        self.assertEqual(provider._normalize_transcription("[]"), "")


if __name__ == "__main__":
    unittest.main()
