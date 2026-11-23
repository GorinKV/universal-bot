import struct
import wave

from app.services.whisper import _wav_duration


def _write_wav(path: str, seconds: float = 1.0) -> None:
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        frames = int(seconds * 16000)
        w.writeframes(struct.pack(f'<{frames}h', *([0] * frames)))


def test_wav_duration(tmp_path):
    wav = tmp_path / "v.wav"
    _write_wav(str(wav), seconds=2.5)
    assert abs(_wav_duration(str(wav)) - 2.5) < 0.05


def test_wav_duration_missing(tmp_path):
    assert _wav_duration(str(tmp_path / "nope.wav")) == 0.0
