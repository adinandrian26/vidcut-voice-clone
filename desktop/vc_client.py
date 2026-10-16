"""Klien API layanan Voice Clone untuk software desktop.

Sengaja tanpa dependensi berat (hanya `requests`): bisa dibundel jadi
satu file .exe kecil. Seluruh logika jaringan ada di sini agar mudah
diuji tanpa membuka jendela GUI.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

DEFAULT_URL = os.environ.get("VC_API_URL", "http://localhost:8520")
ALLOWED_EXTS = ("wav", "mp3", "m4a", "ogg", "flac")


class ApiError(RuntimeError):
    pass


def headers(api_key: str) -> dict:
    return {"X-API-Key": api_key} if (api_key or "").strip() else {}


def _problem(response: requests.Response) -> str:
    try:
        return str(response.json().get("detail", response.text))
    except Exception:
        return response.text


def _check(response: requests.Response, api_key: str) -> None:
    if response.ok:
        return
    if response.status_code == 401:
        raise ApiError(
            "Kunci akses salah / belum diisi (HTTP 401). "
            "Samakan dengan VC_API_KEY di layanan.")
    raise ApiError(f"API {response.status_code}: {_problem(response)}")


def normalize_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url:
        raise ValueError("URL layanan wajib diisi.")
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL harus diawali http:// atau https://")
    return url


def validate_inputs(text: str, consent: bool,
                    file_path: str = "", youtube_url: str = "") -> None:
    if not (text or "").strip():
        raise ValueError("Teks masih kosong.")
    if not consent:
        raise ValueError("Centang persetujuan penggunaan suara.")
    if file_path:
        path = Path(file_path)
        if not path.is_file():
            raise ValueError(f"File tidak ditemukan: {file_path}")
        if path.suffix.lower().lstrip(".") not in ALLOWED_EXTS:
            raise ValueError(
                "Format file: " + ", ".join(ALLOWED_EXTS))
    elif not (youtube_url or "").strip():
        raise ValueError("Pilih file audio atau isi link YouTube.")


def health(base_url: str, timeout: int = 10) -> dict:
    try:
        response = requests.get(f"{normalize_url(base_url)}/api/health",
                                timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ApiError(f"Layanan tidak terhubung: {exc}") from exc


def create_job_upload(base_url: str, api_key: str, text: str,
                      language: str, file_path: str,
                      timeout: int = 180) -> str:
    validate_inputs(text, True, file_path=file_path)
    path = Path(file_path)
    try:
        with open(path, "rb") as handle:
            response = requests.post(
                f"{normalize_url(base_url)}/api/jobs/upload",
                data={"text": text.strip(), "language": language,
                      "consent": "true"},
                files={"upload": (path.name, handle,
                                  "application/octet-stream")},
                headers=headers(api_key), timeout=timeout)
    except requests.RequestException as exc:
        raise ApiError(f"Gagal mengirim job: {exc}") from exc
    _check(response, api_key)
    return response.json()["id"]


def create_job_link(base_url: str, api_key: str, text: str, language: str,
                    youtube_url: str, start_seconds: float = 0.0,
                    duration_seconds: float = 30.0,
                    timeout: int = 60) -> str:
    validate_inputs(text, True, youtube_url=youtube_url)
    try:
        response = requests.post(
            f"{normalize_url(base_url)}/api/jobs",
            json={"text": text.strip(), "language": language,
                  "consent": True,
                  "youtube_url": youtube_url.strip(),
                  "start_seconds": float(start_seconds),
                  "duration_seconds": float(duration_seconds)},
            headers=headers(api_key), timeout=timeout)
    except requests.RequestException as exc:
        raise ApiError(f"Gagal mengirim job: {exc}") from exc
    _check(response, api_key)
    return response.json()["id"]


def job_status(base_url: str, api_key: str, jid: str,
               timeout: int = 30) -> dict:
    try:
        response = requests.get(
            f"{normalize_url(base_url)}/api/jobs/{jid}",
            headers=headers(api_key), timeout=timeout)
    except requests.RequestException as exc:
        raise ApiError(f"Tidak bisa membaca progres: {exc}") from exc
    _check(response, api_key)
    return response.json()


def download_audio(base_url: str, api_key: str, jid: str,
                   format: str = "mp3", timeout: int = 300) -> bytes:
    if format not in ("wav", "mp3", "srt"):
        raise ValueError("Format: wav, mp3, atau srt.")
    try:
        response = requests.get(
            f"{normalize_url(base_url)}/api/jobs/{jid}/audio",
            params={"format": format},
            headers=headers(api_key), timeout=timeout)
    except requests.RequestException as exc:
        raise ApiError(f"Gagal mengunduh: {exc}") from exc
    _check(response, api_key)
    return response.content


def delete_job(base_url: str, api_key: str, jid: str,
               timeout: int = 30) -> None:
    try:
        requests.delete(f"{normalize_url(base_url)}/api/jobs/{jid}",
                        headers=headers(api_key), timeout=timeout)
    except requests.RequestException:
        pass


def wait_done(base_url: str, api_key: str, jid: str,
              on_progress=None, poll_seconds: int = 2,
              timeout_seconds: int = 3600) -> dict:
    """Tunggu sampai done/failed. on_progress(progress, stage, detail)."""
    import time
    waited = 0
    while True:
        status = job_status(base_url, api_key, jid)
        if on_progress:
            on_progress(int(status.get("progress", 0)),
                        status.get("status", ""),
                        status.get("stage_detail", ""))
        if status.get("status") == "done":
            return status
        if status.get("status") == "failed":
            raise ApiError(
                f"Generate gagal: {status.get('error', '') or status}")
        if waited >= timeout_seconds:
            raise ApiError("Timeout menunggu hasil.")
        time.sleep(poll_seconds)
        waited += poll_seconds
