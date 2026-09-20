"""Configuração central — tudo por variável de ambiente, com defaults sensatos."""
import os

def _b(v: str, d: bool) -> bool:
    return os.getenv(v, str(d)).strip().lower() in ("1", "true", "yes", "on")

# --- Rede ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "7900"))

# --- ASR (faster-whisper) ---
WHISPER_MODEL   = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE  = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")

# --- Tradução (Ollama no host) ---
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
TARGET_LANG  = os.getenv("TARGET_LANG", "português do Brasil")

# --- TTS (Piper) ---
VOICES_DIR   = os.getenv("VOICES_DIR", "/app/voices")
VOICE_MALE   = os.getenv("VOICE_MALE", "male.onnx")
VOICE_FEMALE = os.getenv("VOICE_FEMALE", "female.onnx")
FEMALE_PITCH_FALLBACK = float(os.getenv("FEMALE_PITCH_FALLBACK", "3.5"))

# --- Detecção de gênero por F0 ---
GENDER_F0_THRESHOLD = float(os.getenv("GENDER_F0_THRESHOLD", "165"))

# --- Alinhamento ---
MAX_SPEEDUP = float(os.getenv("MAX_SPEEDUP", "1.6"))

# --- Pastas de trabalho ---
TMP_DIR = os.getenv("TMP_DIR", "/app/tmp")
os.makedirs(TMP_DIR, exist_ok=True)
