from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from statistics import mean
from typing import Iterable
from zoneinfo import ZoneInfo

from .models import PricePoint

HALF_HOUR = timedelta(minutes=30)


def _mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _percent_change(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline in (None, 0):
        return None
    return ((current - baseline) / baseline) * 100


def _cheapest_window(points: list[PricePoint], periods: int) -> dict | None:
    best: tuple[float, list[PricePoint]] | None = None
    for start in range(len(points) - periods + 1):
        window = points[start : start + periods]
        if any(
            right.start_utc - left.start_utc != HALF_HOUR
            for left, right in zip(window, window[1:])
        ):
            continue
        average = mean(point.price_p_per_kwh for point in window)
        if best is None or average < best[0]:
            best = (average, window)
    if best is None:
        return None
    average, window = best
    return {
        "start_utc": window[0].start_utc.isoformat().replace("+00:00", "Z"),
        "end_utc": window[-1].end_utc.isoformat().replace("+00:00", "Z"),
        "average_p_per_kwh": round(average, 4),
    }


def analyse_prices(
    forecast: Iterable[PricePoint],
    history: Iterable[PricePoint],
    *,
    lookback_days: int = 14,
    timezone_name: str = "Europe/London",
) -> dict:
    forecast_points = sorted(forecast)
    if not forecast_points:
        raise ValueError("Forecast is empty")

    tz = ZoneInfo(timezone_name)
    forecast_start = forecast_points[0].start_utc
    history_start = forecast_start - timedelta(days=lookback_days)
    history_points = sorted(
        point for point in history if history_start <= point.start_utc < forecast_start
    )

    by_local_slot: dict[tuple[int, int], list[float]] = defaultdict(list)
    for point in history_points:
        local = point.start_utc.astimezone(tz)
        by_local_slot[(local.hour, local.minute)].append(point.price_p_per_kwh)

    comparisons = []
    for point in forecast_points:
        local = point.start_utc.astimezone(tz)
        baseline = _mean(by_local_slot[(local.hour, local.minute)])
        comparisons.append(
            {
                **point.as_dict(),
                "start_local": local.isoformat(),
                "baseline_p_per_kwh": None if baseline is None else round(baseline, 4),
                "difference_p_per_kwh": (
                    None
                    if baseline is None
                    else round(point.price_p_per_kwh - baseline, 4)
                ),
            }
        )

    forecast_average = _mean([p.price_p_per_kwh for p in forecast_points])
    comparable_baselines = [
        row["baseline_p_per_kwh"]
        for row in comparisons
        if row["baseline_p_per_kwh"] is not None
    ]
    baseline_average = _mean(comparable_baselines)
    free_periods = [row for row in comparisons if row["price_p_per_kwh"] <= 0]
    peak = max(forecast_points, key=lambda point: point.price_p_per_kwh)
    trough = min(forecast_points, key=lambda point: point.price_p_per_kwh)

    received_times = {point.start_utc for point in forecast_points}
    expected_times = []
    cursor = forecast_points[0].start_utc
    while cursor <= forecast_points[-1].start_utc:
        expected_times.append(cursor)
        cursor += HALF_HOUR
    missing_times = [value for value in expected_times if value not in received_times]
    baseline_periods = len(comparable_baselines)
    baseline_coverage = baseline_periods / len(forecast_points)
    history_local_dates = {
        point.start_utc.astimezone(tz).date() for point in history_points
    }
    history_days_used = len(history_local_dates)
    history_day_coverage = min(history_days_used / lookback_days, 1.0)
    quality_warnings = []
    if missing_times:
        quality_warnings.append(f"{len(missing_times)} forecast half-hour periods missing")
    if baseline_coverage < 0.9:
        quality_warnings.append(
            f"Historical baseline covers only {baseline_coverage:.0%} of forecast periods"
        )
    if history_day_coverage < 0.9:
        quality_warnings.append(
            f"Only {history_days_used} of {lookback_days} historical days are available"
        )

    quality = {
        "status": "good" if not quality_warnings else "warning",
        "forecast_start_utc": forecast_points[0].start_utc.isoformat().replace(
            "+00:00", "Z"
        ),
        "forecast_end_utc": forecast_points[-1].end_utc.isoformat().replace(
            "+00:00", "Z"
        ),
        "expected_periods": len(expected_times),
        "received_periods": len(forecast_points),
        "missing_periods_utc": [
            value.isoformat().replace("+00:00", "Z") for value in missing_times
        ],
        "duplicate_periods": 0,
        "periods_are_consecutive": not missing_times,
        "baseline_periods": baseline_periods,
        "baseline_slot_coverage_percent": round(baseline_coverage * 100, 1),
        "baseline_days_used": history_days_used,
        "baseline_days_requested": lookback_days,
        "baseline_day_coverage_percent": round(history_day_coverage * 100, 1),
        "warnings": quality_warnings,
    }

    return {
        "timezone": timezone_name,
        "lookback_days": lookback_days,
        "forecast_periods": len(forecast_points),
        "history_periods_used": len(history_points),
        "average_p_per_kwh": round(forecast_average, 4),
        "baseline_average_p_per_kwh": (
            None if baseline_average is None else round(baseline_average, 4)
        ),
        "difference_percent": (
            None
            if (change := _percent_change(forecast_average, baseline_average)) is None
            else round(change, 2)
        ),
        "free_or_negative_periods": free_periods,
        "peak": peak.as_dict(),
        "trough": trough.as_dict(),
        "cheapest_windows": {
            "1_hour": _cheapest_window(forecast_points, 2),
            "2_hours": _cheapest_window(forecast_points, 4),
            "3_hours": _cheapest_window(forecast_points, 6),
        },
        "data_quality": quality,
        "periods": comparisons,
    }
