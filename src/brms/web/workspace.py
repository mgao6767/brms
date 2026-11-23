"""On-disk workspace of the web app: banks, runs and their results.

::

    <data dir>/
      banks/<id>/  bank.zip, bank.json (if built from a bank file), meta.json, summary.json
      runs/<id>/   meta.json, payload.json, result.pkl
      cache/       summaries of the packaged demo banks

The server process only reads and writes these files; engine work happens in worker processes.
"""

from __future__ import annotations

import contextlib
import datetime
import json
import os
import re
import shutil
import threading
import uuid
import zipfile
from pathlib import Path
from typing import Any

from brms.data import DEFAULT_DATA_FOLDER

DEMO_PREFIX = "demo-"
_DEMO_DIR = DEFAULT_DATA_FOLDER.parent
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,80}$")


def default_data_dir() -> Path:
    """Return ``$BRMS_WEB_HOME`` or ``~/.brms-web``."""
    return Path(os.environ.get("BRMS_WEB_HOME", Path.home() / ".brms-web"))


def now() -> str:
    """Return the current UTC time as an ISO string."""
    return datetime.datetime.now(tz=datetime.UTC).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    """Return a short random id."""
    return f"{prefix}{uuid.uuid4().hex[:10]}"


def _read(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _write(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, default=str))
    tmp.replace(path)


class Workspace:
    """Banks and runs stored under *root* (thread-safe for metadata updates)."""

    def __init__(self, root: Path) -> None:
        """Create the folders under *root*."""
        self.root = root
        self.banks_dir = root / "banks"
        self.runs_dir = root / "runs"
        self.cache_dir = root / "cache"
        for folder in (self.banks_dir, self.runs_dir, self.cache_dir):
            folder.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._names: dict[str, str] = {}
        self._names_lock = threading.Lock()

    # -- banks ---------------------------------------------------------------------------------

    @staticmethod
    def valid_id(item_id: str) -> bool:
        """Return True for ids this workspace could have issued."""
        return bool(_ID.match(item_id))

    def demo_banks(self) -> dict[str, Path]:
        """Return the packaged demo simulations by bank id."""
        return {f"{DEMO_PREFIX}{p.stem}": p for p in sorted(_DEMO_DIR.glob("*.zip"))}

    def bank_zip(self, bank_id: str) -> Path | None:
        """Return the simulation zip of *bank_id*, or None if unknown or not built yet."""
        if not self.valid_id(bank_id):
            return None
        demo = self.demo_banks().get(bank_id)
        if demo is not None:
            return demo
        path = self.banks_dir / bank_id / "bank.zip"
        return path if path.exists() else None

    def bank_dir(self, bank_id: str) -> Path:
        """Return the folder of a user bank (or the cache folder of a demo bank)."""
        if bank_id.startswith(DEMO_PREFIX):
            folder = self.cache_dir / bank_id
            folder.mkdir(exist_ok=True)
            return folder
        return self.banks_dir / bank_id

    def bank_meta(self, bank_id: str) -> dict[str, Any] | None:
        """Return a bank's metadata (demo banks get theirs from the package)."""
        if not self.valid_id(bank_id):
            return None
        if bank_id in self.demo_banks():
            summary = self.bank_summary(bank_id) or {}
            error = self.demo_error(bank_id)
            status = "ready" if summary else "failed" if error else "pending"
            source = "case_study" if bank_id.startswith(f"{DEMO_PREFIX}case_") else "demo"
            name = summary.get("name") or self.demo_name(bank_id)
            return {"id": bank_id, "name": name, "source": source,
                    "status": status, "error": error, "created": None}
        return _read(self.banks_dir / bank_id / "meta.json")

    def demo_name(self, bank_id: str) -> str:
        """Return a demo bank's name from its zip (shown while its summary is being prepared)."""
        with self._names_lock:
            if bank_id not in self._names:
                name = bank_id[len(DEMO_PREFIX):]
                # A damaged zip keeps its id as the name; preparing its summary reports the error.
                with (contextlib.suppress(OSError, KeyError, ValueError, zipfile.BadZipFile),
                      zipfile.ZipFile(self.demo_banks()[bank_id]) as archive):
                    name = json.loads(archive.read("config.json")).get("name") or name
                self._names[bank_id] = name
            return self._names[bank_id]

    def demo_error(self, bank_id: str) -> str | None:
        """Return why a demo bank could not be summarised, if it could not."""
        marker = _read(self.bank_dir(bank_id) / "error.json")
        return marker.get("error") if marker else None

    def set_demo_error(self, bank_id: str, error: str) -> None:
        """Record that a demo bank could not be summarised (it is not retried until restart)."""
        _write(self.bank_dir(bank_id) / "error.json", {"error": error, "at": now()})

    def clear_demo_errors(self) -> None:
        """Forget summary failures, so a restart (perhaps after regenerating the data) tries again."""
        for marker in self.cache_dir.glob("*/error.json"):
            marker.unlink(missing_ok=True)

    def bank_summary(self, bank_id: str) -> dict[str, Any] | None:
        """Return the cached summary of a bank, if computed."""
        return _read(self.bank_dir(bank_id) / "summary.json")

    def banks(self) -> list[dict[str, Any]]:
        """Return metadata of every bank, demo banks first, then user banks newest first."""
        demos = [self.bank_meta(b) for b in self.demo_banks()]
        users = [_read(p / "meta.json") for p in self.banks_dir.iterdir() if p.is_dir()]
        users = sorted((m for m in users if m and m.get("id")), key=lambda m: m.get("created") or "", reverse=True)
        return [m for m in (*demos, *users) if m]

    def create_bank(self, name: str, source: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Register a user bank that a job will build."""
        bank_id = new_id("b")
        folder = self.banks_dir / bank_id
        folder.mkdir()
        meta = {"id": bank_id, "name": name, "source": source, "status": "building", "created": now(),
                "error": None, **(extra or {})}
        _write(folder / "meta.json", meta)
        return meta

    def update_bank(self, bank_id: str, **changes: Any) -> dict[str, Any] | None:  # noqa: ANN401
        """Update a user bank's metadata (nothing happens if the bank was deleted)."""
        with self._lock:
            path = self.banks_dir / bank_id / "meta.json"
            current = _read(path)
            if current is None:
                return None
            meta = {**current, **changes}
            _write(path, meta)
            return meta

    def delete_bank(self, bank_id: str) -> bool:
        """Delete a user bank (demo banks cannot be deleted)."""
        folder = self.banks_dir / bank_id
        if not self.valid_id(bank_id) or bank_id.startswith(DEMO_PREFIX) or not folder.is_dir():  # demos and cases
            return False
        shutil.rmtree(folder)
        return True

    # -- runs ----------------------------------------------------------------------------------

    def create_run(self, bank: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
        """Register a queued run of *bank* with *spec*."""
        run_id = new_id("r")
        folder = self.runs_dir / run_id
        folder.mkdir()
        meta = {"id": run_id, "bank_id": bank["id"], "bank_name": bank["name"], "unit": bank.get("unit", 1),
                "spec": spec,
                "label": spec.get("label") or "", "status": "queued", "created": now(), "finished": None,
                "error": None, "summary": None}
        _write(folder / "meta.json", meta)
        return meta

    def run_dir(self, run_id: str) -> Path:
        """Return the folder of *run_id*."""
        return self.runs_dir / run_id

    def run_meta(self, run_id: str) -> dict[str, Any] | None:
        """Return a run's metadata."""
        if not self.valid_id(run_id):
            return None
        return _read(self.runs_dir / run_id / "meta.json")

    def update_run(self, run_id: str, **changes: Any) -> dict[str, Any] | None:  # noqa: ANN401
        """Update a run's metadata (nothing happens if the run was deleted)."""
        with self._lock:
            path = self.runs_dir / run_id / "meta.json"
            current = _read(path)
            if current is None:
                return None
            meta = {**current, **changes}
            _write(path, meta)
            return meta

    def runs(self) -> list[dict[str, Any]]:
        """Return every run's metadata, newest first."""
        metas = [_read(p / "meta.json") for p in self.runs_dir.iterdir() if p.is_dir()]
        return sorted((m for m in metas if m and m.get("id")), key=lambda m: m.get("created") or "", reverse=True)

    def delete_run(self, run_id: str) -> bool:
        """Delete a run and its results."""
        folder = self.runs_dir / run_id
        if not self.valid_id(run_id) or not folder.is_dir():
            return False
        shutil.rmtree(folder)
        return True

    def recover(self) -> None:
        """Mark runs and bank builds that were in progress when the server stopped as failed."""
        self.clear_demo_errors()
        for meta in self.runs():
            if meta.get("status") in {"queued", "running"}:
                self.update_run(meta["id"], status="failed", error="Interrupted: the server stopped")
        for path in self.banks_dir.iterdir():
            meta = _read(path / "meta.json")
            if meta and meta.get("status") == "building":
                self.update_bank(meta["id"], status="failed", error="Interrupted: the server stopped")
