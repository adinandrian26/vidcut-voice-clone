#!/usr/bin/env python3
"""Contoh end-to-end: YouTube -> clone -> unduh. Tanpa API key.

Pakai: python scripts/contoh_request.py --url <link> --text "halo dunia"
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import requests

API = "http://localhost:8520"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", default="hasil_clone.wav")
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--dur", type=float, default=30)
    args = ap.parse_args()

    r = requests.post(f"{API}/api/jobs", json={
        "youtube_url": args.url, "start_seconds": args.start,
        "duration_seconds": args.dur, "text": args.text,
        "language": "id", "consent": True,
    }, timeout=60)
    r.raise_for_status()
    jid = r.json()["id"]
    print("job:", jid)
    while True:
        s = requests.get(f"{API}/api/jobs/{jid}", timeout=30).json()
        print(f"{s['progress']:3d}% [{s['status']}] {s['stage_detail']}")
        if s.get("warning"):
            print("peringatan:", s["warning"])
        if s["status"] == "done":
            break
        if s["status"] == "failed":
            raise SystemExit(f"GAGAL: {s['error']}")
        time.sleep(5)
    audio = requests.get(f"{API}/api/jobs/{jid}/audio?format=wav",
                         timeout=120).content
    Path(args.out).write_bytes(audio)
    print(f"tersimpan: {args.out} ({len(audio)} bytes)")


if __name__ == "__main__":
    main()
