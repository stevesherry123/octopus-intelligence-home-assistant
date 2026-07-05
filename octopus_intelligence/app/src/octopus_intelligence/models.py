from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True, order=True)
class PricePoint:
    """One half-hour unit rate, stored by period start in UTC."""

    start_utc: datetime
    price_p_per_kwh: float

    def __post_init__(self) -> None:
        if self.start_utc.tzinfo is None or self.start_utc.utcoffset() is None:
            raise ValueError("start_utc must be timezone-aware")
        object.__setattr__(self, "start_utc", self.start_utc.astimezone(timezone.utc))

    @property
    def end_utc(self) -> datetime:
        return self.start_utc + timedelta(minutes=30)

    def as_dict(self) -> dict[str, Any]:
        return {
            "start_utc": self.start_utc.isoformat().replace("+00:00", "Z"),
            "price_p_per_kwh": self.price_p_per_kwh,
        }

