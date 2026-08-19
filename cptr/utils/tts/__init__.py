"""TTS provider registry and factory."""

from __future__ import annotations

import logging
from typing import Optional

from cptr.utils.tts.base import TTSProvider
from cptr.utils.tts.sarvam import SarvamTTSProvider
from cptr.env import TTS_PROVIDER

logger = logging.getLogger(__name__)

_PROVIDERS: dict[str, type[TTSProvider]] = {
    "sarvam": SarvamTTSProvider,
}


def get_tts_provider(provider_name: Optional[str] = None) -> Optional[TTSProvider]:
    """Factory function to get configured TTS provider instance.

    Args:
        provider_name: Explicit provider name. Defaults to TTS_PROVIDER env var.

    Returns:
        Instantiated TTSProvider or None if unavailable/unknown.
    """
    name = (provider_name or TTS_PROVIDER or "sarvam").lower().strip()

    cls = _PROVIDERS.get(name)
    if cls is None:
        logger.warning("[TTS] Unknown provider '%s'. Available: %s", name, list(_PROVIDERS.keys()))
        return None

    try:
        provider = cls()
        return provider
    except Exception as exc:
        logger.error("[TTS] Failed to instantiate provider '%s': %s", name, exc)
        return None


__all__ = [
    "TTSProvider",
    "SarvamTTSProvider",
    "get_tts_provider",
]
