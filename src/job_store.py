"""Thread-safe persistent job-state storage."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import cast

from src.logging_utils import get_logger


logger = get_logger(__name__)


class JobStore:
    """Store and retrieve job payloads from a JSON file."""

    def __init__(self, file_path: str) -> None:
        """Initialize store and create backing file when absent."""
        self.path: Path = Path(file_path)
        self._lock: threading.Lock = threading.Lock()
        if not self.path.exists():
            self._write({})

    def _read(self) -> dict[str, dict[str, object]]:
        """Read and decode store content as a dictionary."""
        if not self.path.exists():
            return {}
        text = self.path.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        try:
            payload = cast(object, json.loads(text))
        except json.JSONDecodeError as exc:
            logger.warning("Job state file is corrupted (%s): %s", self.path, exc)
            return {}
        if not isinstance(payload, dict):
            return {}
        payload_dict = cast(dict[str, object], payload)
        filtered: dict[str, dict[str, object]] = {}
        for key, value in payload_dict.items():
            if isinstance(value, dict):
                filtered[str(key)] = cast(dict[str, object], value)
        return filtered

    def _write(self, payload: dict[str, dict[str, object]]) -> None:
        """Write payload atomically to avoid partial file updates."""
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        _ = tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _ = tmp_path.replace(self.path)

    def load_all(self) -> dict[str, dict[str, object]]:
        """Return all job payloads currently persisted."""
        with self._lock:
            return self._read()

    def upsert(self, job_id: str, job_payload: dict[str, object]) -> None:
        """Insert or update one job payload by identifier."""
        with self._lock:
            data = self._read()
            data[job_id] = job_payload
            self._write(data)
