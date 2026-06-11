# audiosocket.py - Asterisk AudioSocket TCP protocol helpers.
#
# Protocol (each message): [1 byte type][2 bytes length, big-endian][payload]
#   0x00 = hangup / terminate (length 0)
#   0x01 = UUID of the call (16-byte payload)
#   0x03 = DTMF digit
#   0x10 = audio (signed-linear 16-bit, 8kHz, mono PCM)
#   0xff = error
import asyncio

TYPE_HANGUP = 0x00
TYPE_UUID = 0x01
TYPE_DTMF = 0x03
TYPE_AUDIO = 0x10
TYPE_ERROR = 0xFF


def build_audio_frame(pcm: bytes) -> bytes:
    """Wrap raw slin PCM into an AudioSocket audio frame."""
    return bytes([TYPE_AUDIO]) + len(pcm).to_bytes(2, "big") + pcm


def build_hangup_frame() -> bytes:
    return bytes([TYPE_HANGUP]) + (0).to_bytes(2, "big")


async def read_message(reader: asyncio.StreamReader):
    """Read one AudioSocket message. Returns (type, payload) or None on EOF."""
    try:
        header = await reader.readexactly(3)
    except asyncio.IncompleteReadError:
        return None
    mtype = header[0]
    length = int.from_bytes(header[1:3], "big")
    payload = b""
    if length:
        try:
            payload = await reader.readexactly(length)
        except asyncio.IncompleteReadError:
            return None
    return mtype, payload
