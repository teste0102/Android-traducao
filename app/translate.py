"""Tradução via Ollama (host). Traduz todos os segmentos numa lista numerada,
com fallback segmento a segmento se o parse falhar."""
import re, requests
from . import config

_SYS = (
    "Você é um tradutor profissional. Traduza CADA linha numerada do inglês para "
    f"{config.TARGET_LANG}. Regras: responda APENAS com as mesmas linhas numeradas, "
    "uma tradução por linha, sem comentar, sem explicar, sem repetir o original. "
    "Mantenha a numeração idêntica. /no_think"
)

def _post(prompt: str) -> str:
    r = requests.post(
        f"{config.OLLAMA_URL}/api/generate",
        json={
            "model": config.OLLAMA_MODEL,
            "system": _SYS,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0.2},
        },
        timeout=300,
    )
    r.raise_for_status()
    txt = r.json().get("response", "")
    return re.sub(r"<think>.*?</think>", "", txt, flags=re.DOTALL).strip()


def _one(text: str) -> str:
    out = _post(f"1. {text}")
    out = re.sub(r"^\s*1[\.\)]\s*", "", out.strip())
    return out.strip() or text


def translate_segments(texts):
    if not texts:
        return []
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
    try:
        resp = _post(numbered)
        parsed = {}
        for line in resp.splitlines():
            m = re.match(r"\s*(\d+)[\.\)]\s*(.+)", line)
            if m:
                parsed[int(m.group(1))] = m.group(2).strip()
        if len(parsed) >= max(1, int(len(texts) * 0.8)):
            return [parsed.get(i + 1) or _one(texts[i]) for i in range(len(texts))]
    except Exception:
        pass
    # fallback: um por um
    return [_one(t) for t in texts]
