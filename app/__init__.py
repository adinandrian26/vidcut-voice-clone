"""Init paket: arahkan cache HF ke D: sebelum import apa pun."""
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_HF_CACHE = _ROOT / "models" / "hf_cache"
_HF_CACHE.mkdir(parents=True, exist_ok=True)
# Keep all Hugging Face/Chatterbox weights on the data drive.  HF_HUB_CACHE
# is the variable used by hf_hub_download; HF_HOME also covers auxiliary
# Hugging Face caches when the service is started outside the project folder.
os.environ.setdefault("HF_HOME", str(_HF_CACHE))
os.environ.setdefault("HF_HUB_CACHE", str(_HF_CACHE))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
