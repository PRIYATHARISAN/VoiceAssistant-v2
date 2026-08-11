"""STT Provider registry and factory."""

from __future__ import annotations

import os
import logging
from typing import Optional

from cptr.utils.stt.base import STTProvider
from cptr.utils.stt.indic_conformer import get_indic_conformer_provider, IndicConformerSTTProvider

logger = logging.getLogger(__name__)


def get_stt_provider(provider_name: Optional[str] = None) -> Optional[STTProvider]:
    """Get configured STT provider instance.

    Configured via STT_PROVIDER env var (default: 'indic_conformer').
    """
    name = (provider_name or os.getenv("STT_PROVIDER") or "indic_conformer").lower()

    if name in {"indic_conformer", "indicconformer", "indic"}:
        provider = get_indic_conformer_provider()
        logger.info(f"[STT Factory] Selected provider: '{provider.provider_name}'")
        return provider

    logger.warning(f"[STT Factory] Unknown STT provider name: '{name}'")
    return None


__all__ = [
    "STTProvider",
    "IndicConformerSTTProvider",
    "get_stt_provider",
    "get_indic_conformer_provider",
]
