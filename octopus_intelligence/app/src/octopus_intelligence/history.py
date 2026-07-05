from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

from .models import PricePoint

DEFAULT_HISTORY_URL = "https://agilebuddy.uk/historic/download/agile/json"


def parse_datetime_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp has no timezone: {value}")
    return parsed.astimezone(timezone.utc)


def parse_agile_buddy(
    records: Iterable[dict], *, timestamps_are_period_end: bool = True
) -> list[PricePoint]:
    offset = timedelta(minutes=30) if timestamps_are_period_end else timedelta()
    points = [
        PricePoint(
            start_utc=parse_datetime_utc(str(record["dt"])) - offset,
            price_p_per_kwh=float(record["r"]),
        )
        for record in records
    ]
    return sorted(points)


def load_history(path: str | Path) -> list[PricePoint]:
    with Path(path).open(encoding="utf-8") as handle:
        return parse_agile_buddy(json.load(handle))


def download_history(
    output: str | Path,
    *,
    url: str = DEFAULT_HISTORY_URL,
    timeout_seconds: int = 90,
) -> Path:
    """Download atomically, retaining an existing good cache on failure."""
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")

    request = Request(url, headers={"User-Agent": "octopus-intelligence/0.1"})
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)
    if not isinstance(payload, list) or not payload:
        raise ValueError("History endpoint did not return a non-empty list")
    # Validate the schema and timestamps before replacing the cache.
    parse_agile_buddy(payload[:2])

    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))
    temporary.replace(destination)
    return destination
