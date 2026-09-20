FROM python:3.11-slim

# ffmpeg (áudio/vídeo), espeak-ng (fonemas do Piper), rubberband (pitch feminino)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg espeak-ng rubberband-cli curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# cache dos modelos do Whisper vai pra /app/models (volume) e persiste
ENV HF_HOME=/app/models \
    XDG_CACHE_HOME=/app/models \
    OMP_NUM_THREADS=8

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY server.py .
COPY static ./static

RUN mkdir -p /app/voices /app/tmp /app/models

EXPOSE 7900
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7900"]
