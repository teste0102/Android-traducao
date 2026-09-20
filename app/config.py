import os

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 7900))

WHISPER_MODEL   = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE  = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")

OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

VOICE_MALE   = os.getenv("VOICE_MALE", "male.onnx")
VOICE_FEMALE = os.getenv("VOICE_FEMALE", "female.onnx")

FEMALE_PITCH_FALLBACK = float(os.getenv("FEMALE_PITCH_FALLBACK", 3.5))
GENDER_F0_THRESHOLD   = float(os.getenv("GENDER_F0_THRESHOLD", 165.0))
MAX_SPEEDUP           = float(os.getenv("MAX_SPEEDUP", 1.6))

VOICES_DIR = os.getenv("VOICES_DIR", "/app/voices")
TMP_DIR    = os.getenv("TMP_DIR", "/app/tmp")
MODELS_DIR = os.getenv("MODELS_DIR", "/app/models")
