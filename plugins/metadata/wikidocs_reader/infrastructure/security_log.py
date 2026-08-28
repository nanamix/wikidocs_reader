"""Server-side security event logging with a hard 24-hour retention window."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from threading import Lock

LOG_PATH = Path(__file__).resolve().parents[1] / "data" / "security.log"
RETENTION_SECONDS = 24 * 60 * 60
_LOCK = Lock()


def _prune(now: float) -> None:
    if not LOG_PATH.exists():
        return
    cutoff = now - RETENTION_SECONDS
    try:
        lines = []
        with LOG_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    record = json.loads(line)
                    if float(record.get("ts", 0)) >= cutoff:
                        lines.append(line.rstrip("\n"))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
        tmp = LOG_PATH.with_suffix(".tmp")
        tmp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        os.replace(tmp, LOG_PATH)
    except OSError:
        return


def security_event(event: str, **details: object) -> None:
    """Write a minimal server-only event; never expose logging failures to users."""
    now = time.time()
    record = {"ts": now, "event": event, **details}
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            _prune(now)
            with LOG_PATH.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    except OSError:
        pass
