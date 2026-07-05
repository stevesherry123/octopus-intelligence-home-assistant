from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .models import PricePoint

FEED_ENTRY = re.compile(
    r"(?P<day>\d{1,2})/(?P<month>\d{1,2})\s+"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*=\s*"
    r"(?P<price>[+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*p",
    re.IGNORECASE,
)


def _nearest_year(day: int, month: int, reference_local: datetime) -> int:
    candidates = []
    for year in (reference_local.year - 1, reference_local.year, reference_local.year + 1):
        try:
            candidate = datetime(year, month, day)
        except ValueError:
            continue
        candidates.append((abs((candidate.date() - reference_local.date()).days), year))
    if not candidates:
        raise ValueError(f"Invalid calendar date: {day:02d}/{month:02d}")
    return min(candidates)[1]


def _valid_utc_candidates(wall_time: datetime, tz: ZoneInfo) -> list[datetime]:
    """Return UTC instants that round-trip to a UK wall-clock timestamp."""
    candidates: list[datetime] = []
    for fold in (0, 1):
        aware = wall_time.replace(tzinfo=tz, fold=fold)
        utc = aware.astimezone(timezone.utc)
        round_trip = utc.astimezone(tz)
        if round_trip.replace(tzinfo=None) == wall_time and utc not in candidates:
            candidates.append(utc)
    return sorted(candidates)


def parse_ai_feed(
    feed: str,
    *,
    reference_utc: datetime | None = None,
    source_timezone: str = "Europe/London",
) -> list[PricePoint]:
    """Parse the Home Assistant ``ai_feed`` attribute into UTC price points.

    The feed omits both year and UTC offset. The year nearest to ``reference_utc``
    is selected. During the repeated autumn hour, repeated wall-clock labels are
    assigned to the first and second occurrence in input order.
    """
    if reference_utc is None:
        reference_utc = datetime.now(timezone.utc)
    if reference_utc.tzinfo is None or reference_utc.utcoffset() is None:
        raise ValueError("reference_utc must be timezone-aware")

    tz = ZoneInfo(source_timezone)
    reference_local = reference_utc.astimezone(tz)
    occurrence_count: dict[datetime, int] = defaultdict(int)
    points: list[PricePoint] = []

    for match in FEED_ENTRY.finditer(feed):
        parts = {key: match.group(key) for key in match.groupdict()}
        day, month = int(parts["day"]), int(parts["month"])
        year = _nearest_year(day, month, reference_local)
        wall_time = datetime(
            year, month, day, int(parts["hour"]), int(parts["minute"])
        )
        candidates = _valid_utc_candidates(wall_time, tz)
        if not candidates:
            raise ValueError(
                f"Non-existent local time in {source_timezone}: {wall_time.isoformat()}"
            )

        occurrence = occurrence_count[wall_time]
        occurrence_count[wall_time] += 1
        if occurrence >= len(candidates):
            raise ValueError(f"Duplicate feed timestamp: {wall_time.isoformat()}")
        points.append(PricePoint(candidates[occurrence], float(parts["price"])))

    if not points:
        raise ValueError("No price entries found in ai_feed")
    if len({point.start_utc for point in points}) != len(points):
        raise ValueError("ai_feed resolves to duplicate UTC timestamps")
    return sorted(points)

