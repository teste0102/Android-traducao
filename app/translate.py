"""Traduz texto EN→PT via Ollama."""
import requests
from app import config

_SYSTEM = (
    "Você é um tradutor profissional inglês→português brasileiro. "
    "Traduza apenas o texto fornecido, sem explicações, notas ou prefixos. "
    "Preserve nomes próprios e termos técnicos. Responda somente com a tradução."
)


def translate(text: str) -> str:
    if not text.strip():
        return ""
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text.strip()},
        ],
        "stream": False,
        "options": {"temperature": 0.1},
    }
    try:
        r = requests.post(
            f"{config.OLLAMA_URL}/api/chat",
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception as e:
        raise RuntimeError(f"Ollama erro: {e}")
