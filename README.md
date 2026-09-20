# Tradução do Instagram

Servidor que recebe um vídeo/áudio em inglês e devolve a **dublagem em português**,
sincronizada nos tempos originais e **respeitando voz masculina/feminina** (detecção por F0).

Pipeline: `faster-whisper` (transcreve + timestamps) → detecção de gênero por pitch →
tradução via **Ollama no host** (`qwen3:8b`) → **Piper** (TTS) → alinhamento temporal.

- Roda 100% na sua rede local. GPU **não é obrigatória** (Whisper em CPU int8; Ollama já usa a GPU no host).
- Porta fixa: **7900** → `http://192.168.15.11:7900`
- Vozes: masculina = `faber` (oficial). Feminina = arquivo próprio se existir, senão faber com pitch/formant deslocado.

---

## Instalação (na máquina Linux, user mkinfocell)

Clonar/copiar para dentro do workspace:
```
cd ~/ia-workspace && git clone <REPO> traducao-instagram || true
```

Entrar na pasta:
```
cd ~/ia-workspace/traducao-instagram
```

Criar o `.env`:
```
cp .env.example .env
```

Baixar a voz do Piper (faz 1x):
```
bash download_models.sh
```

Subir o container (você não está no grupo docker → usa sudo):
```
sudo docker compose up -d --build
```

Ver o log da primeira subida (Whisper baixa o modelo `small` na 1ª vez):
```
sudo docker compose logs -f
```

Testar do navegador (do PC ou do celular na mesma rede):
```
http://192.168.15.11:7900
```

Checar saúde por linha de comando:
```
curl -s http://192.168.15.11:7900/health
```

Liberar a porta no firewall (se necessário):
```
sudo ufw allow 7900
```

---

## Uso pela API (o app Android usa isto)

Enviar um arquivo e receber a dublagem:
```
curl -s -F "file=@clipe.mp4" http://192.168.15.11:7900/dublar
```

Resposta (JSON): `language`, `duration`, `tts_mode`, `segments[]` (com `gender`, `en`, `pt`)
e `audio_url`. Baixar o áudio dublado:
```
curl -sL "http://192.168.15.11:7900/audio/<job>?fmt=mp3" -o dublagem.mp3
```

---

## Trocar a voz feminina por uma nativa (fase 2, opcional)

Coloque um par no formato Piper/VITS e o servidor passa a usá-lo sozinho:
```
cp minha_voz_feminina.onnx      voices/female.onnx
```
```
cp minha_voz_feminina.onnx.json voices/female.onnx.json
```
```
sudo docker compose restart
```

---

## Ligar a GPU no Whisper (opcional, se instalar nvidia-container-toolkit)

No `.env`:
```
WHISPER_DEVICE=cuda
WHISPER_COMPUTE=float16
```
E no `docker-compose.yml` adicione ao serviço:
```
    gpus: all
```

---

## Integrar na central 7000

Adicione uma linha na seção "Serviços Docker" apontando para
`http://192.168.15.11:7900` (nome: "Tradução Instagram"), no mesmo padrão dos outros.

---

## Variáveis (.env)

| Variável | Default | O que faz |
|---|---|---|
| PORT | 7900 | porta do servidor |
| WHISPER_MODEL | small | tamanho do modelo (tiny/base/small/medium) |
| WHISPER_DEVICE | cpu | cpu ou cuda |
| OLLAMA_URL | http://host.docker.internal:11434 | Ollama no host |
| OLLAMA_MODEL | qwen3:8b | modelo tradutor |
| GENDER_F0_THRESHOLD | 165 | Hz: abaixo=masc, acima=fem |
| FEMALE_PITCH_FALLBACK | 3.5 | semitons pra voz feminina por shift |
| MAX_SPEEDUP | 1.6 | aceleração máx. pra encaixar fala longa |
