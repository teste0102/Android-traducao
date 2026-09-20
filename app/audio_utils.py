"""Utilidades de áudio: extração via ffmpeg e estimativa de F0 (gênero) sem librosa."""
import os, subprocess, wave, struct, math
import numpy as np


def run(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou: {' '.join(cmd)}\n{p.stderr.decode(errors='ignore')[-800:]}")
    return p


def to_wav_mono16k(src: str, dst: str, sr: int = 16000):
    """Extrai áudio de qualquer arquivo (vídeo ou áudio) pra WAV mono PCM 16 bits."""
    run(["ffmpeg", "-y", "-i", src, "-vn", "-ac", "1", "-ar", str(sr),
         "-acodec", "pcm_s16le", dst])
    return dst


def read_wav_float(path: str):
    """Lê WAV PCM16 mono -> (np.float32 em [-1,1], sample_rate)."""
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        ch = w.getnchannels()
        raw = w.readframes(n)
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr


def duration_seconds(path: str) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def _autocorr_f0(frame: np.ndarray, sr: int, fmin=70.0, fmax=400.0):
    """F0 de um quadro por autocorrelação. Retorna (f0_hz, clareza[0..1])."""
    frame = frame - frame.mean()
    energy = float(np.sqrt(np.mean(frame ** 2)))
    if energy < 1e-3:
        return 0.0, 0.0
    corr = np.correlate(frame, frame, mode="full")[len(frame) - 1:]
    if corr[0] <= 0:
        return 0.0, 0.0
    lag_min = int(sr / fmax)
    lag_max = int(sr / fmin)
    lag_max = min(lag_max, len(corr) - 1)
    if lag_max <= lag_min:
        return 0.0, 0.0
    seg = corr[lag_min:lag_max]
    peak = int(np.argmax(seg)) + lag_min
    clarity = float(corr[peak] / corr[0])
    if clarity < 0.3:
        return 0.0, clarity
    # interpolação parabólica pro pico
    if 1 <= peak < len(corr) - 1:
        a, b, c = corr[peak - 1], corr[peak], corr[peak + 1]
        denom = (a - 2 * b + c)
        if denom != 0:
            peak = peak + 0.5 * (a - c) / denom
    return sr / peak, clarity


def median_f0(samples: np.ndarray, sr: int) -> float:
    """F0 mediana de um trecho de fala. 0.0 = sem voz detectada."""
    if len(samples) < sr // 20:
        return 0.0
    win = int(0.04 * sr)   # 40 ms
    hop = int(0.02 * sr)   # 20 ms
    vals = []
    for i in range(0, len(samples) - win, hop):
        f0, clarity = _autocorr_f0(samples[i:i + win], sr)
        if f0 > 0 and clarity >= 0.4:
            vals.append(f0)
    if not vals:
        return 0.0
    return float(np.median(vals))


def gender_of_segment(samples: np.ndarray, sr: int, threshold: float) -> str:
    """'male' | 'female' a partir da F0 mediana. Sem voz -> 'male' (default seguro)."""
    f0 = median_f0(samples, sr)
    if f0 <= 0:
        return "male"
    return "female" if f0 >= threshold else "male"
