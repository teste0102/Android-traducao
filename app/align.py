"""Alinha segmentos de áudio TTS nos slots de tempo originais.

Para cada segmento:
  - Se o TTS gerado for mais curto → preenche o resto com silêncio.
  - Se for mais longo → acelera até MAX_SPEEDUP; se ainda for longo, corta.
"""
import os
import struct
import subprocess
import wave
from app import config


def _wav_duration(path: str) -> float:
    with wave.open(path, "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def _stretch(src: str, dst: str, factor: float) -> None:
    """Acelera/desacelera via rubberband (factor > 1 = mais rápido)."""
    cmd = [
        "rubberband",
        "--time", str(1.0 / factor),
        src, dst,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"rubberband stretch falhou: {result.stderr.decode()}")


def _silence_wav(path: str, duration: float, sr: int = 22050) -> None:
    n = max(1, int(sr * duration))
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{n}h", *([0] * n)))


def _read_samples(path: str) -> tuple[bytes, int]:
    with wave.open(path, "rb") as wf:
        return wf.readframes(wf.getnframes()), wf.getframerate()


def fit_segment(tts_wav: str, slot_duration: float, out_wav: str) -> None:
    """Encaixa tts_wav no slot_duration e salva em out_wav."""
    tts_dur = _wav_duration(tts_wav)
    if tts_dur <= 0:
        _silence_wav(out_wav, slot_duration)
        return

    ratio = tts_dur / slot_duration  # > 1 significa TTS mais longo

    if ratio <= 1.0:
        # TTS mais curto: usa o TTS + silêncio no final
        samples, sr = _read_samples(tts_wav)
        pad_dur = slot_duration - tts_dur
        pad_n = max(0, int(sr * pad_dur))
        with wave.open(out_wav, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(samples)
            if pad_n:
                wf.writeframes(struct.pack(f"<{pad_n}h", *([0] * pad_n)))
    elif ratio <= config.MAX_SPEEDUP:
        # Acelera para caber
        _stretch(tts_wav, out_wav, ratio)
    else:
        # Muito longo: acelera ao máximo e corta o excedente
        tmp = out_wav + ".fast.wav"
        _stretch(tts_wav, tmp, config.MAX_SPEEDUP)
        fast_dur = _wav_duration(tmp)
        keep = min(fast_dur, slot_duration)
        samples, sr = _read_samples(tmp)
        keep_frames = int(keep * sr) * 2  # bytes (16-bit)
        with wave.open(out_wav, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(samples[:keep_frames])
        os.remove(tmp)
