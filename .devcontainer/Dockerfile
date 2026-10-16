FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libsndfile1 git curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/vidcut-requirements.txt

# Codespaces only needs the selected Chatterbox path. Avoid installing the
# second OpenVoice/Piper stack to save build time and storage.
RUN pip install --no-cache-dir -r /tmp/vidcut-requirements.txt \
 && pip install --no-cache-dir torch==2.6.0 torchaudio==2.6.0 \
      --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir demucs av librosa==0.11.0 pydub \
 && pip install --no-cache-dir --no-deps \
      git+https://github.com/resemble-ai/chatterbox.git \
 && pip install --no-cache-dir s3tokenizer diffusers==0.29.0 \
      conformer==0.3.2 safetensors==0.5.3 spacy-pkuseg \
      pykakasi==2.3.0 pyloudnorm omegaconf transformers==5.2.0 \
 && pip install --no-cache-dir \
      git+https://github.com/resemble-ai/Perth.git@master
