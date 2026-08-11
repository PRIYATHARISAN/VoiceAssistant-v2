"""Base Speech-to-Text (STT) Provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class STTProvider(ABC):
    """Abstract interface for Speech-to-Text providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return unique provider identifier."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return True if model/service is configured and ready."""
        ...

    @abstractmethod
    def transcribe(self, audio_path: str, language: str | None = None) -> str:
        """Transcribe audio file into text.

        Args:
            audio_path: Path to local audio file (WAV preferred).
            language: Optional language code (e.g., 'en', 'ta', 'hi').

        Returns:
            Clean transcribed text string.
        """
        ...
