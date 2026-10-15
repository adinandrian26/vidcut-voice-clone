"""Deteksi kualitas sampel suara + peringatan bahasa Indonesia."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .audio import energy_bursts_per_min, read_mono, silence_ratio


@dataclass
class QualityReport:
    ok: bool
    duration_s: float
    silence_ratio: float
    warnings: list[str]


def check_sample(wav_path: Path, min_seconds: float = 10.0) -> QualityReport:
    """Nilai sampel vokal. ok=False berarti tolak dengan pesan jelas."""
    from .audio import probe_seconds
    dur = probe_seconds(wav_path)
    warnings: list[str] = []
    if dur < min_seconds:
        return QualityReport(False, dur, 1.0, [
            f"Sampel terlalu pendek ({dur:.1f} dtk). Minimal {min_seconds:.0f} "
            "detik suara bicara bersih."])
    try:
        x = read_mono(wav_path)
    except Exception as e:
        return QualityReport(False, dur, 1.0, [f"Audio tidak terbaca: {e}"])
    sil = silence_ratio(x)
    if sil > 0.6:
        warnings.append(
            f"{sil*100:.0f}% sampel hening. Pakai bagian yang banyak bicara.")
    bursts = energy_bursts_per_min(x)
    if bursts < 40:
        warnings.append("Terdeteksi sedikit aktivitas bicara — mungkin musik "
                        "atau hanya hening. Hasil clone bisa buruk.")
    if bursts > 600:
        warnings.append("Terdeteksi kemungkinan lebih dari satu pembicara / "
                        "suara ramai. Pakai sampel satu suara saja.")
    ok = sil <= 0.85
    if not ok:
        warnings.append("Sampel hampir seluruhnya hening.")
    return QualityReport(ok, dur, sil, warnings)
