# server.py - self-hosted voice assistant.
#
#   Asterisk (telephony) --AudioSocket--> this server --> Whisper STT --> Gemini --> TTS --> back
#
# Turn-based v1: we listen until the caller stops, answer, then listen again.
import asyncio

from . import config as C
from .audiosocket import (
    TYPE_AUDIO,
    TYPE_HANGUP,
    TYPE_UUID,
    build_audio_frame,
    read_message,
)
from .llm import LLM
from .stt import STT
from .tts import make_tts
from .vad import UtteranceDetector


async def speak(writer: asyncio.StreamWriter, tts, text: str, lang: str):
    """Synthesize text and stream it back to Asterisk, paced at real time."""
    if not text:
        return
    pcm = await asyncio.to_thread(tts.synthesize, text, lang)
    for i in range(0, len(pcm), C.FRAME_BYTES):
        chunk = pcm[i : i + C.FRAME_BYTES]
        if len(chunk) < C.FRAME_BYTES:
            chunk = chunk + b"\x00" * (C.FRAME_BYTES - len(chunk))
        writer.write(build_audio_frame(chunk))
        await writer.drain()
        await asyncio.sleep(C.FRAME_MS / 1000)  # pace ~20ms per frame


async def handle_connection(reader, writer, stt: STT, llm: LLM, tts):
    peer = writer.get_extra_info("peername")
    print(f"🔗 New AudioSocket connection from {peer}")
    detector = UtteranceDetector(
        C.TELEPHONY_SAMPLE_RATE, C.FRAME_MS, C.VAD_AGGRESSIVENESS,
        C.SILENCE_MS_END, C.MIN_SPEECH_MS,
    )
    chat = llm.new_session()

    try:
        await speak(writer, tts, C.WELCOME_GREETING, "en")
        detector.reset()  # ignore any audio captured during the greeting

        while True:
            msg = await read_message(reader)
            if msg is None:
                break
            mtype, payload = msg

            if mtype == TYPE_HANGUP:
                break
            if mtype == TYPE_UUID:
                print(f"📞 Call UUID: {payload.hex()}")
                continue
            if mtype != TYPE_AUDIO:
                continue

            for utt in detector.add_audio(payload):
                text, lang = await asyncio.to_thread(stt.transcribe, utt)
                text = text.strip()
                if not text:
                    continue
                print(f"🎙️  User ({lang}): {text}")
                try:
                    reply = await llm.reply(chat, text)
                except Exception as e:
                    print("❌ Gemini error:", repr(e))
                    reply = "Sorry, I had trouble with that. Could you please repeat?"
                print(f"🗣️  Assistant ({lang}): {reply}")
                await speak(writer, tts, reply, lang)
                detector.reset()  # discard audio captured while we were speaking

    except (ConnectionResetError, asyncio.IncompleteReadError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass
        print(f"🔌 Connection closed {peer}")


async def main():
    if not C.GOOGLE_API_KEY:
        raise SystemExit("GOOGLE_API_KEY environment variable not set.")

    stt = STT()
    llm = LLM()
    tts = make_tts()

    server = await asyncio.start_server(
        lambda r, w: handle_connection(r, w, stt, llm, tts),
        C.AUDIOSOCKET_HOST,
        C.AUDIOSOCKET_PORT,
    )
    print(f"✅ AudioSocket server listening on {C.AUDIOSOCKET_HOST}:{C.AUDIOSOCKET_PORT}")
    print(f"   TTS provider: {C.TTS_PROVIDER} | Whisper: {C.WHISPER_MODEL} | LLM: {C.GEMINI_MODEL}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down.")
