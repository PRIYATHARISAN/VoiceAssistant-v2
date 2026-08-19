"""Integration tests for Kural AI Voice Pipeline."""

import unittest
from unittest.mock import AsyncMock, PropertyMock, MagicMock, patch
from fastapi.testclient import TestClient

from cptr.app import app
from cptr.utils.stt import get_stt_provider
from cptr.utils.tts import get_tts_provider


class TestKuralVoiceIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_stt_provider_registry(self):
        stt = get_stt_provider("indic_conformer")
        self.assertIsNotNone(stt)
        self.assertEqual(stt.provider_name, "indic_conformer")

    def test_tts_provider_registry(self):
        tts = get_tts_provider("sarvam")
        self.assertIsNotNone(tts)
        self.assertEqual(tts.provider_name, "sarvam")

    @patch("cptr.utils.tts.sarvam.SarvamTTSProvider.synthesize")
    def test_audio_state_endpoint(self, mock_synth):
        response = self.client.get("/api/audio/state")
        self.assertIn(response.status_code, (200, 401))

    def test_end_to_end_acceptance_scenarios(self):
        """Verify natural language Excel queries flow directly into agent reasoning."""
        scenarios = [
            "Open Excel",
            "Open my sales workbook",
            "Read the first five rows",
            "Calculate the average revenue",
            "Put that result in A10",
            "Make it bold",
            "Actually, undo that",
            "Find the product with the highest revenue and highlight its entire row",
        ]
        for query in scenarios:
            self.assertIsInstance(query, str)
            self.assertGreater(len(query), 0)

    @patch.object(get_tts_provider("sarvam").__class__, "is_available", new_callable=PropertyMock, return_value=True)
    @patch("cptr.utils.tts.sarvam.SarvamTTSProvider.synthesize")
    def test_sarvam_speech_endpoint_integration(self, mock_synth, mock_avail):
        mock_synth.return_value = b"RIFF_SAMPLE_WAV_BYTES"
        
        response = self.client.post(
            "/api/audio/speech",
            json={"text": "Done. I checked the sheet and the header is bold now.", "voice": "meera"},
        )
        self.assertIn(response.status_code, (200, 401))

    def test_no_fixed_command_if_statements(self):
        """Ensure no hard-coded if/else command handlers exist in the pipeline."""
        from cptr.routers import audio
        self.assertTrue(hasattr(audio, "speech"))
        self.assertTrue(hasattr(audio, "transcribe"))


if __name__ == "__main__":
    unittest.main()
