# stt.py - Speech-to-Text using faster-whisper (multilingual: English + Sinhala).
import numpy as np
import soxr
from faster_whisper import WhisperModel

from . import config


class STT:
    def __init__(self):
        print(f"⏳ Loading Whisper model '{config.WHISPER_MODEL}' "
              f"({config.WHISPER_DEVICE}/{config.WHISPER_COMPUTE})...")
        self.model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE,
        )
        print("✅ Whisper model loaded.")

    def transcribe(self, pcm8k: bytes):
        """Take 8kHz slin PCM bytes, return (text, language_code)."""
        if not pcm8k:
            return "", "en"
        audio = np.frombuffer(pcm8k, dtype=np.int16).astype(np.float32) / 32768.0
        # Whisper expects 16kHz float32
        audio16k = soxr.resample(audio, config.TELEPHONY_SAMPLE_RATE, config.WHISPER_SAMPLE_RATE)
        segments, info = self.model.transcribe(
            audio16k,
            beam_size=1,
            language=None,          # auto-detect (en / si)
            vad_filter=False,
        )
        text = " ".join(seg.text for seg in segments).strip()
        return text, (info.language or "en")
