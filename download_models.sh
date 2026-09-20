#!/usr/bin/env bash
# Baixa as vozes do Piper para ./voices  (rode 1x antes do primeiro build)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p voices

baixar() { # url destino
  echo ">> $2"
  curl -L --fail --retry 3 --max-time 600 -o "$2" "$1"
}

tam_ok() { [ -f "$1" ] && [ "$(stat -c%s "$1")" -gt 1000000 ]; }

# ---- Masculina: pt_BR-faber-medium (oficial rhasspy; mirror Trelis de reserva) ----
if tam_ok voices/male.onnx; then
  echo "male.onnx já existe, pulando."
else
  baixar "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx" voices/male.onnx \
    || baixar "https://huggingface.co/Trelis/piper-pt-br-faber-medium/resolve/main/model.onnx" voices/male.onnx
  baixar "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json" voices/male.onnx.json \
    || baixar "https://huggingface.co/Trelis/piper-pt-br-faber-medium/resolve/main/model.onnx.json" voices/male.onnx.json
fi

# ---- Feminina: OPCIONAL ----
# Não há voz feminina pt-BR oficial no Piper. Por padrão o servidor gera a voz
# feminina a partir da faber com deslocamento de pitch preservando formantes.
# Para usar uma voz feminina REAL depois, copie o par de arquivos para:
#     voices/female.onnx   e   voices/female.onnx.json
# (formato Piper/VITS). O servidor detecta e passa a usá-la automaticamente.
if tam_ok voices/female.onnx; then
  echo "female.onnx encontrada — o servidor vai usar a voz feminina nativa."
else
  echo "female.onnx ausente — feminina será por pitch-shift do faber (ok pra v1)."
fi

echo "Vozes prontas em ./voices:"
ls -la voices/
