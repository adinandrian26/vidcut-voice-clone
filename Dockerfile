FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir torch==2.6.0 torchaudio==2.6.0 \
    --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir demucs piper-tts av librosa pydub eng_to_ipa transformers \
     whisper-timestamped inflect unidecode pypinyin jieba gruut langcodes cn2an wavmark \
 && pip install --no-cache-dir --no-deps git+https://github.com/myshell-ai/OpenVoice.git \
 && pip install --no-cache-dir --no-deps git+https://github.com/resemble-ai/chatterbox.git \
 && pip install --no-cache-dir s3tokenizer diffusers==0.29.0 conformer==0.3.2 \
    safetensors==0.5.3 spacy-pkuseg pykakasi==2.3.0 pyloudnorm omegaconf \
    "transformers==5.2.0" \
 && pip install --no-cache-dir git+https://github.com/resemble-ai/Perth.git@master

COPY app app
COPY static static
COPY .env.example .env

EXPOSE 8520
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8520}"]
