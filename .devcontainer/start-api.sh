#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/vidcut-voice-clone
mkdir -p data voices models/hf_cache

if curl --silent --fail http://127.0.0.1:8520/api/health >/dev/null 2>&1; then
  echo "VidCut API sudah berjalan di port 8520."
  exit 0
fi

nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8520 \
  > /tmp/vidcut-api.log 2>&1 &
echo $! > /tmp/vidcut-api.pid

for _ in {1..30}; do
  if curl --silent --fail http://127.0.0.1:8520/api/health >/dev/null; then
    echo "VidCut API aktif. Buka tab Ports dan salin URL port 8520."
    exit 0
  fi
  sleep 1
done

echo "API belum siap. Periksa: cat /tmp/vidcut-api.log" >&2
exit 1
