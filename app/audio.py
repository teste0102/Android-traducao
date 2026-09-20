"""Extrai áudio PCM 16kHz mono de qualquer arquivo de vídeo/áudio via ffmpeg."""
import subprocess
import os


def extract_wav(src: str, dst: str) -> None:
    """Converte src para WAV 16kHz mono 16-bit PCM."""
    cmd = [
        "ffmpeg", "-y", "-i", src,
        "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
        dst,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou: {result.stderr.decode()}")


def get_duration(path: str) -> float:
    """Retorna duração em segundos usando ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def concat_wav_files(paths: list, dst: str, sample_rate: int = 22050) -> None:
    """Concatena múltiplos WAVs em ordem para dst."""
    if not paths:
        raise ValueError("Nenhum arquivo para concatenar")
    if len(paths) == 1:
        import shutil
        shutil.copyfile(paths[0], dst)
        return
    list_file = dst + ".list.txt"
    with open(list_file, "w") as f:
        for p in paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, dst]
    result = subprocess.run(cmd, capture_output=True)
    os.remove(list_file)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat falhou: {result.stderr.decode()}")


def to_mp3(src: str, dst: str, bitrate: str = "128k") -> None:
    cmd = ["ffmpeg", "-y", "-i", src, "-b:a", bitrate, dst]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mp3 falhou: {result.stderr.decode()}")
