from __future__ import annotations

import json
import logging
import threading
from pathlib import Path


logger = logging.getLogger(__name__)


class JobStore:
    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self._lock = threading.Lock()
        if not self.path.exists():
            self._write({})

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        text = self.path.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            # Corrupted state file should not take down the app.
            logger.warning("Job state file is corrupted (%s): %s", self.path, exc)
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    def _write(self, payload: dict) -> None:
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(self.path)

    def load_all(self) -> dict:
        with self._lock:
            return self._read()

    def upsert(self, job_id: str, job_payload: dict) -> None:
        with self._lock:
            data = self._read()
            data[job_id] = job_payload
            self._write(data)
