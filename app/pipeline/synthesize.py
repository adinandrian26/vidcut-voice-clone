"""Orkestrasi satu job: sampel -> vokal -> quality -> clone per kalimat."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from ..store import JobStore
from . import chunk as chunk_mod
from .audio import probe_seconds, to_mp3, to_wav_mono
from .backends.openvoice_piper import get_backend
from .quality import check_sample
from .watermark import tag_mp3, tag_wav

Progress = Callable[[int, str, str], None]


def _srt_time(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _write_srt(sentences: list[str], parts: list[str], out_path: Path,
               gap_seconds: float = 0.25) -> None:
    """Buat subtitle berdasarkan durasi asli setiap potongan clone."""
    cursor = 0.0
    cues: list[str] = []
    for index, (sentence, part) in enumerate(zip(sentences, parts), 1):
        duration = probe_seconds(Path(part))
        cues.extend([
            str(index),
            f"{_srt_time(cursor)} --> {_srt_time(cursor + duration)}",
            sentence,
            "",
        ])
        cursor += duration + gap_seconds
    out_path.write_text("\n".join(cues), encoding="utf-8")


def run_job(store: JobStore, jid: str, job_dir: Path, params: dict,
            backend_name: str, backend_kwargs: dict,
            on_progress: Progress) -> None:
    """Jalankan pipeline penuh. Update store tiap tahap."""
    text = params["text"]
    language = params.get("language", "id")
    backend = get_backend(backend_name, **backend_kwargs)

    def prog(p: int, stage: str, detail: str = "") -> None:
        store.update(jid, status=stage, progress=p, stage_detail=detail)
        on_progress(p, stage, detail)

    # 1. sampel: voice tersimpan, upload, atau unduh YouTube
    from ..config import settings
    voice_id = params.get("voice_id")
    if voice_id:
        saved = settings.voices_dir / f"{voice_id}" / "vocals_24k.wav"
        if not saved.exists():
            raise RuntimeError(f"Suara tersimpan '{voice_id}' tidak ada.")
        prog(30, "separating", "Memakai suara tersimpan...")
        vocals = saved  # sudah 24k mono, sudah lolos cek kualitas
    else:
        prog(5, "downloading", "Menyiapkan sampel suara...")
        sample_src = job_dir / "sample_src"
        if params.get("upload_path"):
            sample_src = Path(params["upload_path"])
            prepared_seconds = min(settings.sample_seconds,
                                   settings.max_sample_seconds)
        else:
            from .download import download_audio, probe_duration
            dur = probe_duration(params["youtube_url"])
            start = float(params.get("start_seconds", 0))
            length = float(params.get("duration_seconds", 30))
            if start + length > dur:
                raise RuntimeError(
                    f"Rentang sampel berakhir di detik {start + length:.0f}, "
                    f"sedangkan durasi video hanya {dur:.0f} detik.")
            sample_src = job_dir / "sample_raw.wav"
            download_audio(params["youtube_url"], sample_src, start, length)
            prepared_seconds = length

        # 2. konversi + pisahkan vokal
        prog(20, "separating", "Memisahkan vokal dari musik...")
        clean = job_dir / "sample_clean.wav"
        # Batasi sampel sebelum Demucs agar proses clone tetap stabil.
        to_wav_mono(sample_src, clean, max_seconds=prepared_seconds)
        from .separate import separate_vocals
        vocals_raw = separate_vocals(clean, job_dir / "demucs_out")
        # Demucs keluar 44100 Hz -> samakan ke 24k mono pipeline
        vocals = job_dir / "vocals_24k.wav"
        to_wav_mono(vocals_raw, vocals)

        # 3. cek kualitas
        prog(45, "separating", "Memeriksa kualitas sampel...")
        report = check_sample(vocals)
        if not report.ok:
            raise RuntimeError(" | ".join(report.warnings))
        if report.warnings:
            store.update(jid, warning=" | ".join(report.warnings))

    # 4. clone per kalimat
    prog(55, "cloning", "Membuat suara...")
    sentences = chunk_mod.split_sentences(text)
    parts: list[str] = []
    for i, sent in enumerate(sentences):
        part = job_dir / f"part_{i:04d}.wav"
        # Resume a retry without regenerating completed sentences.
        if not part.exists() or part.stat().st_size == 0:
            backend.synthesize(sent, vocals, language, part)
        parts.append(str(part))
        prog(55 + int(40 * (i + 1) / max(1, len(sentences))),
             "cloning", f"Kalimat {i + 1}/{len(sentences)}...")
    merged = job_dir / "result_raw.wav"
    chunk_mod.join_wavs(parts, str(merged))
    _write_srt(sentences, parts, job_dir / "result.srt")

    # 5. label AI + mp3
    prog(96, "cloning", "Memberi label AI...")
    final_wav = job_dir / "result.wav"
    final_mp3 = job_dir / "result.mp3"
    tag_wav(merged, final_wav)
    to_mp3(final_wav, job_dir / "result_tmp.mp3")
    tag_mp3(job_dir / "result_tmp.mp3", final_mp3)
    prog(100, "done", "Selesai.")
