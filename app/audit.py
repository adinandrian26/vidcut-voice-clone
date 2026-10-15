"""Log audit minimal: waktu, hash IP, job id. Tanpa isi audio/teks."""
from __future__ import annotations

import hashlib
import logging
import time

logger = logging.getLogger("voiceclone.audit")


def audit(action: str, job_id: str = "", ip: str = "") -> None:
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else "-"
    logger.info("audit t=%.0f action=%s job=%s ip_hash=%s",
                time.time(), action, job_id or "-", ip_hash)
