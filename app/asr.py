"""Transcrição com faster-whisper. Modelo carregado uma vez (lazy)."""
from . import config

_model = None

def _get():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # import lazy: sobe só quando usa
        _model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE,
        )
    return _model


def transcribe(wav_path: str):
    """Retorna (idioma, [ {start, end, text} ]). Só detecta; NÃO traduz aqui."""
    model = _get()
    segments, info = model.transcribe(
        wav_path,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
        beam_size=5,
    )
    out = []
    for s in segments:
        txt = (s.text or "").strip()
        if txt:
            out.append({"start": float(s.start), "end": float(s.end), "text": txt})
    return info.language, out
