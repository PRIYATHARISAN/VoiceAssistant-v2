"""IndicConformer Speech-to-Text (STT) provider implementation."""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import time
from typing import Any

from cptr.utils.stt.base import STTProvider

logger = logging.getLogger(__name__)

# Optional heavy dependencies
try:
    import numpy as np
    import torch
    import librosa

    HAS_INDIC_DEPS = True
except ImportError:
    HAS_INDIC_DEPS = False
    np = None  # type: ignore
    torch = None  # type: ignore
    librosa = None  # type: ignore


class IndicConformerSTTProvider(STTProvider):
    """STT Provider implementation using AI4Bharat IndicConformer local ONNX model."""

    # 22 officially supported Indian languages
    SUPPORTED_LANGUAGES = frozenset({
        "as", "bn", "brx", "doi", "gu", "hi", "kn", "kok", "ks",
        "mai", "ml", "mni", "mr", "ne", "or", "pa", "sa", "sat",
        "sd", "ta", "te", "ur",
    })

    def __init__(self, model_path: str | None = None):
        self._model_path = model_path or os.getenv("INDIC_CONFORMER_MODEL_PATH", "")
        self._asr_model: Any = None
        self._is_loaded: bool = False
        self._load_failed: bool = False

    @property
    def provider_name(self) -> str:
        return "indic_conformer"

    @property
    def model_path(self) -> str:
        return self._model_path or os.getenv("INDIC_CONFORMER_MODEL_PATH", "")

    @property
    def is_available(self) -> bool:
        if not HAS_INDIC_DEPS:
            return False
        path = self.model_path
        if not path or not os.path.exists(path):
            return False
        return True

    def load_model(self) -> bool:
        """Lazy load the local IndicConformer ASR model into memory once."""
        if self._is_loaded:
            return True
        if self._load_failed:
            return False

        if not HAS_INDIC_DEPS:
            logger.warning("[IndicConformer] Required dependencies (torch, librosa, numpy) are missing.")
            self._load_failed = True
            return False

        path = self.model_path
        if not path:
            logger.info("[IndicConformer] INDIC_CONFORMER_MODEL_PATH environment variable is not configured.")
            self._load_failed = True
            return False

        if not os.path.exists(path):
            logger.warning(f"[IndicConformer] Model path does not exist: '{path}'")
            self._load_failed = True
            return False

        model_onnx_path = os.path.join(path, "model_onnx.py")
        config_path = os.path.join(path, "config.json")
        if not os.path.exists(model_onnx_path) or not os.path.exists(config_path):
            logger.warning(f"[IndicConformer] Model files missing in '{path}' (model_onnx.py or config.json)")
            self._load_failed = True
            return False

        start_time = time.time()
        logger.info(f"[IndicConformer] STT model loading from '{path}'...")

        try:
            spec = importlib.util.spec_from_file_location("model_onnx", model_onnx_path)
            if spec is None or spec.loader is None:
                raise ImportError("Failed to create spec for model_onnx.py")

            model_onnx_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(model_onnx_module)

            IndicASRConfig = getattr(model_onnx_module, "IndicASRConfig")
            IndicASRModel = getattr(model_onnx_module, "IndicASRModel")

            with open(config_path, "r", encoding="utf-8") as f:
                config_dict = json.load(f)

            config_dict.pop("auto_map", None)
            indic_config = IndicASRConfig(ts_folder=path, **config_dict)
            model = IndicASRModel(indic_config)

            self._asr_model = model
            self._is_loaded = True
            elapsed = time.time() - start_time
            logger.info(f"[IndicConformer] STT model loaded successfully in {elapsed:.2f}s.")
            return True

        except Exception as exc:
            logger.error(f"[IndicConformer] Failed to load model from '{path}': {exc}")
            self._load_failed = True
            return False

    def _normalize_transcription(self, result: Any) -> str:
        """Convert raw ASR output into clean string."""
        if result is None:
            return ""
        if isinstance(result, tuple):
            result = result[0] if result else ""
        if hasattr(result, "item"):
            try:
                result = result.item()
            except Exception:
                result = str(result)
        if isinstance(result, str):
            transcription = result.strip()
        else:
            transcription = str(result).strip()

        if not transcription or transcription.lower() in {"none", "null", "[]", "{}"}:
            return ""
        return transcription.replace("\x00", "").strip()

    def _resolve_language(self, language: str | None) -> str:
        """Resolve language code, defaulting to 'hi' for IndicConformer."""
        lang = (language or os.getenv("INDIC_CONFORMER_DEFAULT_LANG", "hi")).lower().strip()
        if lang not in self.SUPPORTED_LANGUAGES:
            logger.warning(
                f"[IndicConformer] Language '{lang}' not supported. "
                f"Supported: {sorted(self.SUPPORTED_LANGUAGES)}. Falling back to 'hi'."
            )
            lang = "hi"
        return lang

    def transcribe(self, audio_path: str, language: str | None = None) -> str:
        """Transcribe a WAV audio file using loaded IndicConformer model."""
        if not os.path.exists(audio_path):
            logger.error(f"[IndicConformer] Audio file not found: '{audio_path}'")
            return ""

        if not self._is_loaded:
            if not self.load_model():
                logger.warning("[IndicConformer] IndicConformer model unavailable")
                return ""

        lang = self._resolve_language(language)

        logger.info(f"[IndicConformer] STT inference start: audio='{audio_path}', lang='{lang}'")
        start_time = time.time()

        try:
            sample_rate = 16000
            speech_array, _ = librosa.load(audio_path, sr=sample_rate)
            speech_array = np.asarray(speech_array, dtype=np.float32)

            if speech_array.ndim > 1:
                speech_array = np.mean(speech_array, axis=1)
            speech_array = np.ravel(speech_array)

            if speech_array.size == 0:
                logger.warning("[IndicConformer] Audio sample is empty.")
                return ""

            max_amplitude = float(np.max(np.abs(speech_array)))
            if max_amplitude < 1e-4:
                logger.warning("[IndicConformer] Audio sample is silent.")
                return ""

            speech_array = speech_array / (max_amplitude + 1e-8)
            wav_tensor = torch.from_numpy(speech_array).unsqueeze(0).float()

            with torch.no_grad():
                raw_result = self._asr_model(wav_tensor, lang=lang, decoding="ctc")

            transcription = self._normalize_transcription(raw_result)
            elapsed = time.time() - start_time
            logger.info(f"[IndicConformer] STT inference complete in {elapsed:.2f}s: '{transcription}'")
            return transcription

        except Exception as exc:
            logger.error(f"[IndicConformer] Transcription error: {exc}")
            return ""


# Singleton instance container
_GLOBAL_INDIC_PROVIDER: IndicConformerSTTProvider | None = None


def get_indic_conformer_provider() -> IndicConformerSTTProvider:
    global _GLOBAL_INDIC_PROVIDER
    if _GLOBAL_INDIC_PROVIDER is None:
        _GLOBAL_INDIC_PROVIDER = IndicConformerSTTProvider()
    return _GLOBAL_INDIC_PROVIDER
