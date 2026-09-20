"""Orquestra: extrai -> transcreve -> detecta gênero -> traduz -> sintetiza -> alinha."""
import os, uuid
from . import config, audio_utils as au, asr, translate, tts, align


def process(input_path: str) -> dict:
    job = uuid.uuid4().hex[:8]
    work = os.path.join(config.TMP_DIR, job)
    os.makedirs(work, exist_ok=True)

    # 1) áudio pra análise (mono 16k)
    wav16 = au.to_wav_mono16k(input_path, os.path.join(work, "src16k.wav"))
    samples, sr = au.read_wav_float(wav16)
    total_dur = len(samples) / sr

    # 2) transcrição com timestamps
    language, segments = asr.transcribe(wav16)
    if not segments:
        return {"error": "nenhuma fala detectada", "language": language}

    # 3) gênero por segmento (a partir do áudio original)
    for s in segments:
        a = int(max(0, s["start"]) * sr)
        b = int(min(total_dur, s["end"]) * sr)
        s["gender"] = au.gender_of_segment(samples[a:b], sr, config.GENDER_F0_THRESHOLD)

    # 4) tradução (lote com fallback)
    pt = translate.translate_segments([s["text"] for s in segments])
    for s, t in zip(segments, pt):
        s["pt"] = t

    # 5) TTS por segmento
    placed = []
    for i, s in enumerate(segments):
        out = os.path.join(work, f"seg{i:03d}.wav")
        tts.synth(s["pt"], s["gender"], out)
        placed.append({"start": s["start"], "end": s["end"], "wav": out})

    # 6) monta trilha final
    align.config.TMP_DIR = work
    final_wav = align.build(total_dur, placed)
    final_mp3 = align.to_mp3(final_wav)

    return {
        "job": job,
        "language": language,
        "tts_mode": tts.mode(),
        "duration": round(total_dur, 2),
        "audio_wav": final_wav,
        "audio_mp3": final_mp3,
        "segments": [
            {"start": round(s["start"], 2), "end": round(s["end"], 2),
             "gender": s["gender"], "en": s["text"], "pt": s["pt"]}
            for s in segments
        ],
    }
