# vad.py - turn detection using WebRTC VAD.
#
# We feed 20ms frames. Once we have seen speech and then SILENCE_MS_END of
# quiet, we treat that as the end of the caller's turn and return the audio.
import webrtcvad


class UtteranceDetector:
    def __init__(self, sample_rate, frame_ms, aggressiveness, silence_ms_end, min_speech_ms):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        self.frame_bytes = int(sample_rate * frame_ms / 1000) * 2
        self.frame_ms = frame_ms
        self.silence_frames_end = max(1, silence_ms_end // frame_ms)
        self.min_speech_frames = max(1, min_speech_ms // frame_ms)
        self.reset()

    def reset(self):
        self._speech = []
        self._in_speech = False
        self._silence = 0
        self._buf = bytearray()

    def add_audio(self, pcm: bytes):
        """Feed arbitrary-length PCM. Returns a list of completed utterances (bytes)."""
        out = []
        self._buf.extend(pcm)
        while len(self._buf) >= self.frame_bytes:
            frame = bytes(self._buf[: self.frame_bytes])
            del self._buf[: self.frame_bytes]
            utt = self._process_frame(frame)
            if utt:
                out.append(utt)
        return out

    def _process_frame(self, frame: bytes):
        try:
            is_speech = self.vad.is_speech(frame, self.sample_rate)
        except Exception:
            return None

        if is_speech:
            self._speech.append(frame)
            self._in_speech = True
            self._silence = 0
        elif self._in_speech:
            self._speech.append(frame)
            self._silence += 1
            if self._silence >= self.silence_frames_end:
                spoken_frames = len(self._speech) - self._silence
                utt = b"".join(self._speech) if spoken_frames >= self.min_speech_frames else None
                self._speech = []
                self._in_speech = False
                self._silence = 0
                return utt
        return None
