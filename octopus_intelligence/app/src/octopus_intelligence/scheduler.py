from __future__ import annotations

import fcntl
import json
import logging
import signal
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event

from .config import Settings
from .pipeline import run_pipeline


def _write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def run_scheduler(
    settings: Settings,
    *,
    interval_hours: float = 3,
    use_ai: bool = True,
    publish_announcement: bool = True,
    max_runs: int | None = None,
) -> None:
    if interval_hours <= 0:
        raise ValueError("interval_hours must be greater than zero")

    data_dir = settings.output_file.parent
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_handle = (data_dir / "scheduler.lock").open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise RuntimeError("Another Octopus Intelligence scheduler is already running") from error

    try:
        stop = Event()
        for signal_number in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signal_number, lambda _signum, _frame: stop.set())

        status_file = data_dir / "scheduler-status.json"
        failures = 0
        runs = 0
        while not stop.is_set():
            started = datetime.now(timezone.utc)
            status = {
                "state": "running",
                "started_at_utc": started.isoformat().replace("+00:00", "Z"),
                "consecutive_failures": failures,
            }
            _write_json_atomic(status_file, status)
            try:
                run_pipeline(
                    settings,
                    use_ai=use_ai,
                    publish_announcement=publish_announcement,
                )
                failures = 0
                status["state"] = "healthy"
                status["last_success_utc"] = datetime.now(timezone.utc).isoformat().replace(
                    "+00:00", "Z"
                )
                status.pop("last_error", None)
                logging.info("Scheduled analysis completed")
            except Exception as error:
                failures += 1
                status["state"] = "degraded"
                status["consecutive_failures"] = failures
                status["last_error"] = type(error).__name__
                logging.exception("Scheduled analysis failed; retaining previous output")

            runs += 1
            next_run = started + timedelta(hours=interval_hours)
            status["next_run_utc"] = next_run.isoformat().replace("+00:00", "Z")
            _write_json_atomic(status_file, status)
            if max_runs is not None and runs >= max_runs:
                break
            remaining = max(0.0, (next_run - datetime.now(timezone.utc)).total_seconds())
            stop.wait(remaining)
    finally:
        fcntl.flock(lock_handle, fcntl.LOCK_UN)
        lock_handle.close()
