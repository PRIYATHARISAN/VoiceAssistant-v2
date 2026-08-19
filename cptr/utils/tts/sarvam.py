"""Sarvam AI Text-to-Speech (TTS) Provider implementation."""

from __future__ import annotations

import base64
import logging
import os
import httpx
from typing import Any

from cptr.utils.tts.base import TTSProvider
from cptr.env import (
    SARVAM_API_KEY,
    SARVAM_TTS_MODEL,
    SARVAM_TTS_VOICE,
    SARVAM_TTS_LANGUAGE,
)

logger = logging.getLogger(__name__)


class SarvamTTSProvider(TTSProvider):
    """TTS Provider implementation using Sarvam AI REST API."""

    SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        default_voice: str | None = None,
        default_language: str | None = None,
    ):
        self._api_key = api_key or os.getenv("SARVAM_API_KEY", SARVAM_API_KEY)
        self._model = model or os.getenv("SARVAM_TTS_MODEL", SARVAM_TTS_MODEL or "bulbul:v2")
        self._default_voice = (
            default_voice or os.getenv("SARVAM_TTS_VOICE", SARVAM_TTS_VOICE or "anushka")
        )
        self._default_language = (
            default_language or os.getenv("SARVAM_TTS_LANGUAGE", SARVAM_TTS_LANGUAGE or "ta-IN")
        )

    @property
    def provider_name(self) -> str:
        return "sarvam"

    @property
    def api_key(self) -> str:
        return self._api_key or os.getenv("SARVAM_API_KEY", SARVAM_API_KEY)

    @property
    def is_available(self) -> bool:
        return bool(self.api_key.strip())

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        language: str | None = None,
        format: str | None = None,
        speed: float | None = None,
    ) -> bytes:
        """Synthesize text into speech audio bytes using Sarvam AI API."""
        key = self.api_key.strip()
        if not key:
            raise RuntimeError("Sarvam API key is not configured.")

        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Text to synthesize cannot be empty.")

        target_voice = (voice or self._default_voice or "anushka").lower()
        if target_voice == "meera":
            target_voice = "anushka"
        target_lang = language or self._default_language or "ta-IN"
        target_model = self._model or "bulbul:v2"

        headers = {
            "api-subscription-key": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        # Sarvam TTS API payload
        payload: dict[str, Any] = {
            "inputs": [clean_text],
            "target_language_code": target_lang,
            "speaker": target_voice,
            "model": target_model,
        }

        if speed is not None and isinstance(speed, (int, float)):
            # Clamp pace/speed ratio
            payload["pace"] = round(min(max(float(speed), 0.5), 2.0), 2)

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.post(self.SARVAM_TTS_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                # Try fallback payload format if inputs format returns 400/422
                fallback_payload = {
                    "text": clean_text,
                    "language_code": target_lang,
                    "speaker": target_voice,
                    "model": target_model,
                }
                resp_fb = await client.post(
                    self.SARVAM_TTS_URL, headers=headers, json=fallback_payload
                )
                if resp_fb.status_code == 200:
                    resp = resp_fb
                else:
                    logger.error(
                        "[SarvamTTS] API error %s: %s",
                        resp.status_code,
                        resp.text[:500],
                    )
                    resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            data = resp.json()
            audios = data.get("audios") or []
            if audios and isinstance(audios, list) and isinstance(audios[0], str):
                return base64.b64decode(audios[0])
            if "audio" in data and isinstance(data["audio"], str):
                return base64.b64decode(data["audio"])
            raise RuntimeError(f"Sarvam TTS API returned JSON without audio data: {data}")

        if not resp.content:
            raise RuntimeError("Sarvam TTS API returned empty audio response.")

        return resp.content
