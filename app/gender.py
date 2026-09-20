"""Detecta gênero do locutor por pitch médio (F0) em um trecho de áudio WAV."""
import subprocess
import numpy as np
from app import config


def _yin_f0(samples: np.ndarray, sr: int, frame_ms: int = 30) -> list:
    """F0 simplificado via autocorrelação (YIN-like) sem dependências extras."""
    frame_len = int(sr * frame_ms / 1000)
    hop = frame_len // 2
    f0s = []
    for start in range(0, len(samples) - frame_len, hop):
        frame = samples[start: start + frame_len].astype(np.float32)
        frame -= frame.mean()
        if frame.std() < 1e-4:
            continue
        # Autocorrelação
        corr = np.correlate(frame, frame, mode="full")[frame_len - 1:]
        corr /= corr[0] + 1e-9
        # Busca mínimo entre 50 Hz e 400 Hz
        min_lag = int(sr / 400)
        max_lag = int(sr / 50)
        if max_lag >= len(corr):
            continue
        peak = int(np.argmax(corr[min_lag: max_lag])) + min_lag
        if corr[peak] > 0.4:
            f0s.append(sr / peak)
    return f0s


def detect_gender(wav_path: str, start: float, end: float) -> str:
    """Retorna 'male' ou 'female' para o trecho [start, end] do arquivo WAV."""
    import wave, array as arr
    try:
        with wave.open(wav_path, "rb") as wf:
            sr = wf.getframerate()
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            total_frames = wf.getnframes()
            s_frame = min(int(start * sr), total_frames)
            e_frame = min(int(end * sr), total_frames)
            wf.setpos(s_frame)
            raw = wf.readframes(e_frame - s_frame)
    except Exception:
        return "male"

    if sw == 2:
        samples = np.frombuffer(raw, dtype=np.int16)
    elif sw == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.int16)
    else:
        return "male"

    if ch > 1:
        samples = samples[::ch]

    if len(samples) < 400:
        return "male"

    f0s = _yin_f0(samples, sr)
    if not f0s:
        return "male"
    median_f0 = float(np.median(f0s))
    return "female" if median_f0 > config.GENDER_F0_THRESHOLD else "male"
