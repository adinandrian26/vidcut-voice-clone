# Uji end-to-end: upload -> job -> save-voice -> pakai voice_id -> voices list
import time
from pathlib import Path

import requests

B = "http://localhost:8520"
sampel = Path(r"D:\Automation VidCut\web_vidcut\assets\referensi_homo_sapiens.mp3")
with open(sampel, "rb") as f:
    r = requests.post(f"{B}/api/jobs/upload",
                      data={"text": "Halo, ini uji suara tersimpan.",
                            "language": "id", "consent": "true"},
                      files={"upload": ("sampel.wav", f, "audio/wav")},
                      timeout=60)
r.raise_for_status()
jid = r.json()["id"]
print("job1:", jid)
while True:
    s = requests.get(f"{B}/api/jobs/{jid}", timeout=30).json()
    print(f"{s['progress']:3d}% [{s['status']}] {s['stage_detail']}")
    if s["status"] in ("done", "failed"):
        break
    time.sleep(10)
assert s["status"] == "done", s.get("error")

# simpan suara
r = requests.post(f"{B}/api/jobs/{jid}/save-voice",
                  data={"nama": "Suara Uji"}, timeout=30)
r.raise_for_status()
vid = r.json()["id"]
print("voice tersimpan:", vid)

# job pakai voice_id (tanpa youtube/upload)
r = requests.post(f"{B}/api/jobs",
                  json={"text": "Kalimat kedua memakai suara tersimpan.",
                        "language": "id", "consent": True, "voice_id": vid},
                  timeout=60)
r.raise_for_status()
jid2 = r.json()["id"]
print("job2:", jid2)
while True:
    s = requests.get(f"{B}/api/jobs/{jid2}", timeout=30).json()
    print(f"{s['progress']:3d}% [{s['status']}] {s['stage_detail']}")
    if s["status"] in ("done", "failed"):
        break
    time.sleep(5)
assert s["status"] == "done", s.get("error")

a = requests.get(f"{B}/api/jobs/{jid2}/audio?format=mp3", timeout=120).content
print("MP3:", len(a), "bytes")
print("voices:", requests.get(f"{B}/api/voices", timeout=30).json())

# bersihkan
requests.delete(f"{B}/api/jobs/{jid}", timeout=30)
requests.delete(f"{B}/api/jobs/{jid2}", timeout=30)
requests.delete(f"{B}/api/voices/{vid}", timeout=30)
print("voices setelah hapus:",
      requests.get(f"{B}/api/voices", timeout=30).json())
print("SEMPURNA")
