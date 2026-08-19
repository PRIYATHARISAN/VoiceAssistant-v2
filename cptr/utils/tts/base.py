"""Base Text-to-Speech (TTS) Provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TTSProvider(ABC):
    """Abstract interface for Text-to-Speech providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return unique provider identifier."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return True if service/credentials are configured and ready."""
        ...

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        language: str | None = None,
        format: str | None = None,
        speed: float | None = None,
    ) -> bytes:
        """Synthesize text into speech audio bytes.

        Args:
            text: Text content to speak.
            voice: Optional speaker / persona identifier.
            language: Optional BCP-47 language tag (e.g., 'hi-IN', 'ta-IN', 'en-IN').
            format: Optional audio format (e.g., 'wav', 'mp3').
            speed: Optional playback speed multiplier.

        Returns:
            Raw audio binary data bytes (WAV/MP3).
        """
        ...
