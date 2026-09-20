"""Síntese de voz via Piper TTS com suporte a fallback pitch-shift para voz feminina."""
import os
import subprocess
import tempfile
import numpy as np
from app import config


def _voice_path(gender: str) -> tuple[str, str]:
    """Retorna (onnx, json) para o gênero solicitado."""
    voices_dir = config.VOICES_DIR
    if gender == "female":
        fem_onnx = os.path.join(voices_dir, config.VOICE_FEMALE)
        fem_json = fem_onnx + ".json"
        if os.path.exists(fem_onnx) and os.path.exists(fem_json):
            return fem_onnx, fem_json
    # fallback masculino (ou feminino ausente)
    male_onnx = os.path.join(voices_dir, config.VOICE_MALE)
    male_json = male_onnx + ".json"
    return male_onnx, male_json


def synthesize(text: str, gender: str, dst_wav: str) -> None:
    """
    Sintetiza `text` para `dst_wav` (WAV 22050 Hz mono).
    Se gender=='female' e não há voz nativa, aplica pitch-shift via rubberband.
    """
    if not text.strip():
        # silêncio de 100 ms
        _write_silence(dst_wav, 100)
        return

    onnx, json_cfg = _voice_path(gender)
    if not os.path.exists(onnx):
        raise FileNotFoundError(
            f"Voz '{os.path.basename(onnx)}' não encontrada em {config.VOICES_DIR}. "
            "Execute download_models.sh primeiro."
        )

    use_pitch_shift = (
        gender == "female"
        and os.path.basename(onnx) == config.VOICE_MALE
    )

    raw_wav = dst_wav if not use_pitch_shift else dst_wav + ".raw.wav"

    cmd = [
        "python", "-m", "piper",
        "--model", onnx,
        "--config", json_cfg,
        "--output_file", raw_wav,
    ]
    result = subprocess.run(cmd, input=text.encode(), capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Piper falhou: {result.stderr.decode()}")

    if use_pitch_shift:
        semitones = config.FEMALE_PITCH_FALLBACK
        _pitch_shift(raw_wav, dst_wav, semitones)
        os.remove(raw_wav)


def _pitch_shift(src: str, dst: str, semitones: float) -> None:
    ratio = 2 ** (semitones / 12)
    cmd = [
        "rubberband",
        "--pitch", str(ratio),
        "--formant",        # preserva formantes (mais natural)
        src, dst,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"rubberband falhou: {result.stderr.decode()}")


def _write_silence(path: str, ms: int, sr: int = 22050) -> None:
    import wave, struct
    samples = [0] * int(sr * ms / 1000)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
