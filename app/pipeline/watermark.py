"""Label AI: metadata file + string penanda (bukan klaim tak terpatahkan).

Setiap hasil wav/mp3 diberi metadata 'AI-generated voice clone' dan
label teks di nama/track. Frontend WAJIB menampilkan badge "Suara AI".
"""
from __future__ import annotations

from pathlib import Path

AI_LABEL = "AI-generated voice clone (VidCut)"
AI_COMMENT = ("Audio ini dibuat oleh AI (voice clone). Dilarang dipakai untuk "
              "penipuan, hoaks, atau peniruan tanpa izin pemilik suara.")


def tag_wav(src: Path, dest: Path) -> Path:
    import soundfile as sf
    data, rate = sf.read(str(src), always_2d=False)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with sf.SoundFile(str(dest), "w", samplerate=rate, channels=1,
                      subtype="PCM_16") as f:
        f.write(data)
        try:
            f.set_tag("comment", AI_COMMENT)
            f.set_tag("software", AI_LABEL)
        except Exception:
            pass
    return dest


def tag_mp3(src: Path, dest: Path) -> Path:
    from mutagen.id3 import COMM, ID3, TENC
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    dest.write_bytes(data)
    try:
        tags = ID3()
        tags.add(TENC(encoding=3, text=AI_LABEL))
        tags.add(COMM(encoding=3, lang="ind", desc="comment", text=AI_COMMENT))
        tags.save(str(dest))
    except Exception:
        pass
    return dest
