"""Monta a trilha PT final: cada segmento colocado no seu timestamp original,
acelerado só o necessário pra caber na janela, sobre uma base de silêncio."""
import os, subprocess, wave
import numpy as np
from . import config

SR = 22050  # saída do Piper


def _load_2205(path: str) -> np.ndarray:
    """Carrega qualquer wav como float32 mono 22050 (via ffmpeg, robusto)."""
    tmp = path + ".n.wav"
    subprocess.run(["ffmpeg", "-y", "-i", path, "-ac", "1", "-ar", str(SR),
                    "-acodec", "pcm_s16le", tmp], check=True, capture_output=True)
    with wave.open(tmp, "rb") as w:
        raw = w.readframes(w.getnframes())
    os.remove(tmp)
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def _speedup(path: str, tempo: float) -> str:
    out = path + f".s.wav"
    subprocess.run(["ffmpeg", "-y", "-i", path, "-filter:a", f"atempo={tempo:.3f}",
                    out], check=True, capture_output=True)
    return out


def build(total_duration: float, placed):
    """placed = [ {start, end, wav} ]. Retorna caminho do WAV final."""
    n_total = int(total_duration * SR) + SR  # margem de 1s
    track = np.zeros(n_total, dtype=np.float32)

    for seg in placed:
        window = max(0.05, seg["end"] - seg["start"])
        clip_path = seg["wav"]
        clip = _load_2205(clip_path)
        clip_dur = len(clip) / SR
        if clip_dur > window * 1.02:
            tempo = min(clip_dur / window, config.MAX_SPEEDUP)
            if tempo > 1.01:
                sp = _speedup(clip_path, tempo)
                clip = _load_2205(sp)
                os.remove(sp)
        start_i = int(seg["start"] * SR)
        end_i = min(start_i + len(clip), n_total)
        track[start_i:end_i] += clip[: end_i - start_i]

    # anti-clip suave
    peak = float(np.max(np.abs(track))) if len(track) else 0.0
    if peak > 1.0:
        track = track / peak * 0.98

    out_wav = os.path.join(config.TMP_DIR, "final.wav")
    pcm = (np.clip(track, -1, 1) * 32767).astype(np.int16)
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_wav


def to_mp3(wav_path: str) -> str:
    mp3 = wav_path[:-4] + ".mp3"
    subprocess.run(["ffmpeg", "-y", "-i", wav_path, "-b:a", "128k", mp3],
                   check=True, capture_output=True)
    return mp3
