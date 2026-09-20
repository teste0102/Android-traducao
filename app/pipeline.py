"""Pipeline principal: áudio/vídeo → dublagem PT sincronizada."""
import os
import uuid
from app import config, audio as aud, tts, align, gender as gen, translate as tr

_whisper = None


def _get_whisper():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        os.makedirs(config.MODELS_DIR, exist_ok=True)
        _whisper = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE,
            download_root=config.MODELS_DIR,
        )
    return _whisper


def process(src_path: str) -> dict:
    job = uuid.uuid4().hex[:8]
    tmp = config.TMP_DIR
    os.makedirs(tmp, exist_ok=True)

    # 1. Extrai WAV 16kHz para o Whisper
    wav16 = os.path.join(tmp, f"{job}_16k.wav")
    try:
        aud.extract_wav(src_path, wav16)
    except Exception as e:
        return {"error": str(e), "job": job}

    duration = aud.get_duration(wav16)

    # 2. Transcreve com timestamps por segmento
    try:
        model = _get_whisper()
        segs_iter, info = model.transcribe(
            wav16,
            language="en",
            word_timestamps=False,
            vad_filter=True,
        )
        segments_raw = list(segs_iter)
    except Exception as e:
        return {"error": f"Whisper: {e}", "job": job}

    if not segments_raw:
        return {"error": "Nenhuma fala detectada no áudio.", "job": job}

    # 3. Para cada segmento: detecta gênero, traduz, sintetiza, alinha
    seg_wavs = []
    result_segs = []
    prev_end = 0.0

    for i, seg in enumerate(segments_raw):
        start = seg.start
        end = seg.end
        text_en = seg.text.strip()
        slot = end - start

        if slot <= 0 or not text_en:
            continue

        # silêncio entre segmentos
        gap = start - prev_end
        if gap > 0.05:
            gap_wav = os.path.join(tmp, f"{job}_gap{i}.wav")
            _silence_wav(gap_wav, gap)
            seg_wavs.append(gap_wav)

        # gênero
        gender = gen.detect_gender(wav16, start, end)

        # tradução
        try:
            text_pt = tr.translate(text_en)
        except Exception as e:
            text_pt = text_en  # fallback: usa o original

        # tts
        raw_wav = os.path.join(tmp, f"{job}_tts{i}.wav")
        fit_wav = os.path.join(tmp, f"{job}_fit{i}.wav")
        try:
            tts.synthesize(text_pt, gender, raw_wav)
            align.fit_segment(raw_wav, slot, fit_wav)
        except Exception as e:
            _silence_wav(fit_wav, slot)

        seg_wavs.append(fit_wav)
        prev_end = end
        result_segs.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "gender": gender,
            "en": text_en,
            "pt": text_pt,
        })

    if not seg_wavs:
        return {"error": "Nenhum segmento processado.", "job": job}

    # 4. Concatena tudo
    out_wav = os.path.join(tmp, f"{job}_out.wav")
    out_mp3 = os.path.join(tmp, f"{job}_out.mp3")
    try:
        aud.concat_wav_files(seg_wavs, out_wav)
        aud.to_mp3(out_wav, out_mp3)
    except Exception as e:
        return {"error": f"Concat/MP3: {e}", "job": job}

    # 5. Limpeza de temporários de segmento
    for p in seg_wavs:
        try:
            os.remove(p)
        except OSError:
            pass
    try:
        os.remove(wav16)
    except OSError:
        pass

    tts_mode = "native_female" if (
        result_segs and result_segs[0]["gender"] == "female"
        and os.path.exists(os.path.join(config.VOICES_DIR, config.VOICE_FEMALE))
    ) else "pitch_shift" if any(s["gender"] == "female" for s in result_segs) else "male"

    return {
        "job": job,
        "language": info.language if hasattr(info, "language") else "en",
        "duration": round(duration, 2),
        "tts_mode": tts_mode,
        "segments": result_segs,
        "audio_wav": out_wav,
        "audio_mp3": out_mp3,
    }


def _silence_wav(path: str, duration: float, sr: int = 22050) -> None:
    import wave, struct
    n = max(1, int(sr * duration))
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{n}h", *([0] * n)))
