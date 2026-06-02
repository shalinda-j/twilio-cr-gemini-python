# tts.py - pluggable Text-to-Speech. Output is always 8kHz slin PCM (ready for Asterisk).
#
#   google -> Google Cloud TTS. Natural English AND Sinhala (si-LK). Small per-minute cost.
#   piper  -> Piper (offline, free). Great English; no good Sinhala voice.
import subprocess

import numpy as np
import soxr

from . import config


def _is_sinhala(lang: str) -> bool:
    return bool(lang) and lang.lower().startswith("si")


class GoogleTTS:
    def __init__(self):
        from google.cloud import texttospeech  # lazy import
        self._tts = texttospeech
        self.client = texttospeech.TextToSpeechClient()
        print("✅ Google Cloud TTS ready (English + Sinhala).")

    def synthesize(self, text: str, lang: str) -> bytes:
        if not text:
            return b""
        tts = self._tts
        if _is_sinhala(lang):
            language_code, name = "si-LK", config.TTS_VOICE_SI
        else:
            language_code, name = "en-US", config.TTS_VOICE_EN

        resp = self.client.synthesize_speech(
            input=tts.SynthesisInput(text=text),
            voice=tts.VoiceSelectionParams(language_code=language_code, name=name),
            audio_config=tts.AudioConfig(
                audio_encoding=tts.AudioEncoding.LINEAR16,
                sample_rate_hertz=config.TELEPHONY_SAMPLE_RATE,  # 8kHz directly
            ),
        )
        data = resp.audio_content
        # Google returns a WAV (RIFF) container for LINEAR16; strip the 44-byte header.
        if data[:4] == b"RIFF":
            data = data[44:]
        return data


class PiperTTS:
    """Free offline TTS. English only here; Sinhala falls back to whatever model is set."""

    def __init__(self):
        self.bin = config.PIPER_BIN
        self.model = config.PIPER_MODEL_EN
        print("✅ Piper TTS ready (English, offline/free).")

    def synthesize(self, text: str, lang: str) -> bytes:
        if not text:
            return b""
        # Piper writes a WAV to stdout at its model's native rate (commonly 22050 Hz).
        proc = subprocess.run(
            [self.bin, "--model", self.model, "--output_file", "-"],
            input=text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        wav = proc.stdout
        # Parse minimal WAV header to find sample rate and data chunk.
        if wav[:4] != b"RIFF":
            return b""
        sample_rate = int.from_bytes(wav[24:28], "little")
        data = wav[44:]
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        audio8k = soxr.resample(audio, sample_rate, config.TELEPHONY_SAMPLE_RATE)
        return (np.clip(audio8k, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()


def make_tts():
    p = config.TTS_PROVIDER.lower()
    if p == "piper":
        return PiperTTS()
    if p == "google":
        return GoogleTTS()
    return GTTSProvider()  # default: free, no credentials, English + Sinhala


class GTTSProvider:
    """Free Google Translate TTS. No credentials. English + Sinhala. Good for demos.
    Returns MP3, which we transcode to 8kHz slin via ffmpeg."""

    def __init__(self):
        from gtts import gTTS  # lazy import
        self._gTTS = gTTS
        print("✅ gTTS ready (free, English + Sinhala, no credentials).")

    def synthesize(self, text: str, lang: str) -> bytes:
        if not text:
            return b""
        import io

        code = "si" if _is_sinhala(lang) else "en"
        buf = io.BytesIO()
        self._gTTS(text=text, lang=code).write_to_fp(buf)
        proc = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", "pipe:0",
                "-f", "s16le", "-ac", "1", "-ar", str(config.TELEPHONY_SAMPLE_RATE),
                "pipe:1",
            ],
            input=buf.getvalue(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return proc.stdout
