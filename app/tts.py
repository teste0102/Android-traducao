"""Síntese de voz com Piper (CLI). Masculina = faber. Feminina = arquivo próprio
se existir/carregar; caso contrário, faber com deslocamento de pitch preservando
formantes (rubberband), garantindo distinção de gênero de imediato."""
import os, subprocess, tempfile, wave
from . import config

_female_native = False   # True se houver female.onnx que sintetiza OK
_checked = False


def _piper(model_path: str, text: str, out_wav: str):
    cfg = model_path + ".json"
    cmd = ["piper", "--model", model_path, "--output_file", out_wav]
    if os.path.exists(cfg):
        cmd += ["--config", cfg]
    p = subprocess.run(cmd, input=text.encode("utf-8"),
                       capture_output=True)
    if p.returncode != 0 or not os.path.exists(out_wav) or os.path.getsize(out_wav) < 200:
        raise RuntimeError(p.stderr.decode(errors="ignore")[-500:] or "piper sem saída")


def _pitch_shift(in_wav: str, out_wav: str, semitones: float):
    # rubberband preserva formantes -> voz feminina crível
    try:
        subprocess.run(["rubberband", "-p", str(semitones), "--formant",
                        in_wav, out_wav], check=True, capture_output=True)
        return
    except Exception:
        pass
    # fallback: ffmpeg (muda formantes, menos natural, mas funciona)
    factor = 2 ** (semitones / 12.0)
    with wave.open(in_wav, "rb") as w:
        sr = w.getframerate()
    subprocess.run(
        ["ffmpeg", "-y", "-i", in_wav,
         "-af", f"asetrate={int(sr*factor)},aresample={sr},atempo={1/factor}",
         out_wav], check=True, capture_output=True)


def _init():
    global _female_native, _checked
    if _checked:
        return
    _checked = True
    fem = os.path.join(config.VOICES_DIR, config.VOICE_FEMALE)
    if os.path.exists(fem):
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
                tmp = t.name
            _piper(fem, "teste de voz", tmp)
            _female_native = True
            os.unlink(tmp)
        except Exception as e:
            print(f"[tts] voz feminina nativa indisponível ({e}); usando pitch-shift do faber")
            _female_native = False


def synth(text: str, gender: str, out_wav: str):
    """Sintetiza `text` na voz do gênero pedido -> out_wav (WAV 22.05k)."""
    _init()
    male = os.path.join(config.VOICES_DIR, config.VOICE_MALE)
    if gender == "female":
        if _female_native:
            _piper(os.path.join(config.VOICES_DIR, config.VOICE_FEMALE), text, out_wav)
        else:
            tmp = out_wav + ".m.wav"
            _piper(male, text, tmp)
            _pitch_shift(tmp, out_wav, config.FEMALE_PITCH_FALLBACK)
            os.remove(tmp)
    else:
        _piper(male, text, out_wav)
    return out_wav


def mode() -> str:
    _init()
    return "feminina nativa" if _female_native else "feminina por pitch-shift (faber)"
