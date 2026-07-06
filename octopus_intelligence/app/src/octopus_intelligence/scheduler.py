from __future__ import annotations

import fcntl
import json
import logging
import signal
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event

from .config import Settings
from .home_assistant import HomeAssistantClient
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
    poll_seconds: float = 300,
    use_ai: bool = True,
    publish_announcement: bool = True,
    max_runs: int | None = None,
) -> None:
    if interval_hours <= 0:
        raise ValueError("interval_hours must be greater than zero")
    if poll_seconds <= 0:
        raise ValueError("poll_seconds must be greater than zero")

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
        next_run = datetime.now(timezone.utc)
        client = (
            HomeAssistantClient(settings.ha_url, settings.ha_token)
            if settings.ha_token
            else None
        )
        last_ready_state: str | None = None

        def trigger_state() -> str | None:
            if client is None:
                return None
            state = client.get_state(settings.forecast_ready_entity).get("state")
            if isinstance(state, str):
                state = state.strip()
            if state in {"", "unknown", "unavailable", None}:
                return None
            return str(state)

        if client is not None:
            try:
                last_ready_state = trigger_state()
            except Exception:
                logging.exception("Unable to read initial next-day price trigger state")

        def run_once(*, triggered_by_feed: bool = False) -> bool:
            nonlocal failures
            started = datetime.now(timezone.utc)
            status = {
                "state": "running",
                "started_at_utc": started.isoformat().replace("+00:00", "Z"),
                "consecutive_failures": failures,
            }
            if triggered_by_feed:
                status["triggered_by"] = settings.forecast_ready_entity
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
                return True
            except Exception as error:
                failures += 1
                status["state"] = "degraded"
                status["consecutive_failures"] = failures
                status["last_error"] = type(error).__name__
                logging.exception("Scheduled analysis failed; retaining previous output")
                return False
            finally:
                _write_json_atomic(status_file, status)

        while not stop.is_set():
            now = datetime.now(timezone.utc)
            trigger_changed = False
            if runs > 0 and client is not None:
                try:
                    current_ready_state = trigger_state()
                    trigger_changed = (
                        current_ready_state is not None
                        and current_ready_state != last_ready_state
                    )
                    last_ready_state = current_ready_state
                except Exception:
                    logging.exception("Unable to poll next-day price trigger")

            should_run = runs == 0 or now >= next_run or trigger_changed

            if should_run:
                run_once(triggered_by_feed=trigger_changed)
                runs += 1
                next_run = datetime.now(timezone.utc) + timedelta(hours=interval_hours)
                if max_runs is not None and runs >= max_runs:
                    break
                continue

            status = {
                "state": "waiting",
                "started_at_utc": now.isoformat().replace("+00:00", "Z"),
                "consecutive_failures": failures,
                "next_run_utc": next_run.isoformat().replace("+00:00", "Z"),
            }
            if client is not None:
                status["trigger_entity"] = settings.forecast_ready_entity
                if last_ready_state is not None:
                    status["last_trigger_value"] = last_ready_state
            _write_json_atomic(status_file, status)
            if max_runs is not None and runs >= max_runs:
                break
            remaining = min(
                max(0.0, (next_run - datetime.now(timezone.utc)).total_seconds()),
                poll_seconds,
            )
            stop.wait(remaining)
    finally:
        fcntl.flock(lock_handle, fcntl.LOCK_UN)
        lock_handle.close()
