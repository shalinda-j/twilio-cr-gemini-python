# config.py - all tunables come from environment variables (.env)
import os
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# Gemini (LLM)
# -----------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# -----------------------------
# AudioSocket TCP server (Asterisk connects here)
# -----------------------------
AUDIOSOCKET_HOST = os.getenv("AUDIOSOCKET_HOST", "0.0.0.0")
AUDIOSOCKET_PORT = int(os.getenv("AUDIOSOCKET_PORT", "8090"))

# -----------------------------
# Telephony audio format
# Asterisk AudioSocket streams signed-linear 16-bit, mono, 8 kHz PCM ("slin").
# -----------------------------
TELEPHONY_SAMPLE_RATE = 8000
FRAME_MS = 20
BYTES_PER_SAMPLE = 2
# One 20ms frame at 8kHz mono 16-bit = 160 samples = 320 bytes
FRAME_BYTES = int(TELEPHONY_SAMPLE_RATE * FRAME_MS / 1000) * BYTES_PER_SAMPLE

# -----------------------------
# STT (faster-whisper, multilingual: handles English + Sinhala)
# -----------------------------
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")      # tiny | base | small | medium
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")      # cpu | cuda
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")   # int8 (cheap CPU) | float16 (GPU)
WHISPER_SAMPLE_RATE = 16000

# -----------------------------
# VAD (voice activity detection) - decides when the caller finished talking
# -----------------------------
VAD_AGGRESSIVENESS = int(os.getenv("VAD_AGGRESSIVENESS", "2"))   # 0 (loose) .. 3 (strict)
SILENCE_MS_END = int(os.getenv("SILENCE_MS_END", "800"))        # silence after speech => end of turn
MIN_SPEECH_MS = int(os.getenv("MIN_SPEECH_MS", "300"))          # ignore blips shorter than this

# -----------------------------
# TTS (pluggable). "google" = Google Cloud TTS (good Sinhala + English, small cost).
#                  "piper"  = Piper (free, English good, Sinhala unavailable).
# -----------------------------
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "google")
TTS_VOICE_EN = os.getenv("TTS_VOICE_EN", "en-US-Standard-C")
TTS_VOICE_SI = os.getenv("TTS_VOICE_SI", "si-LK-Standard-A")
# Piper (only used when TTS_PROVIDER=piper)
PIPER_BIN = os.getenv("PIPER_BIN", "piper")
PIPER_MODEL_EN = os.getenv("PIPER_MODEL_EN", "/app/voices/en_US-amy-medium.onnx")

WELCOME_GREETING = os.getenv(
    "WELCOME_GREETING",
    "Hello! I am your voice assistant. You can talk to me in English or Sinhala.",
)

SYSTEM_PROMPT = """You are a helpful and friendly voice assistant on a phone call. Your replies are spoken aloud by a text-to-speech engine, so follow these rules strictly:
1. Reply in the SAME language the caller used. If they speak Sinhala, reply in Sinhala. If they speak English, reply in English.
2. Keep answers short, clear and direct - one or two sentences is ideal for a phone call.
3. Spell things out naturally for speech. Do NOT use asterisks, bullet points, markdown, emojis, or any special characters.
4. Be warm, natural and conversational.
"""
