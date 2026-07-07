from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


def _display_time(iso_utc: str, timezone_name: str) -> str:
    value = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    return value.astimezone(ZoneInfo(timezone_name)).strftime("%H:%M")


def _display_datetime(iso_utc: str, timezone_name: str) -> str:
    value = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    return value.astimezone(ZoneInfo(timezone_name)).strftime("%a %d %b %H:%M")


def build_announcement(analysis: dict[str, Any]) -> str:
    """Create a useful, deterministic announcement even when AI is unavailable."""
    timezone_name = analysis["timezone"]
    change = analysis.get("difference_percent")
    comparison = "No recent baseline is available yet."
    if change is not None:
        direction = "higher" if change > 0 else "lower"
        comparison = f"Prices are {abs(change):.0f}% {direction} than the recent average."

    free = analysis.get("free_or_negative_periods", [])
    if free:
        start = _display_time(free[0]["start_utc"], timezone_name)
        opportunity = f"Free or negative electricity begins at {start}."
    else:
        window = analysis["cheapest_windows"]["2_hours"]
        if window:
            start = datetime.fromisoformat(
                window["start_utc"].replace("Z", "+00:00")
            ).astimezone(ZoneInfo(timezone_name))
            opportunity = (
                "The cheapest two-hour window starts "
                f"{start.strftime('%A at %H:%M')}."
            )
        else:
            opportunity = "No continuous two-hour window is available."
    return f"Octopus update. {comparison} {opportunity}"[:255]


def build_prompt_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    """Keep the AI input compact; calculations remain authoritative and local."""
    timezone_name = analysis["timezone"]

    def point(value: dict[str, Any]) -> dict[str, Any]:
        return {
            "start_local": _display_datetime(value["start_utc"], timezone_name),
            "price_p_per_kwh": value["price_p_per_kwh"],
        }

    windows = {}
    for name, value in analysis["cheapest_windows"].items():
        windows[name] = None if value is None else {
            "start_local": _display_datetime(value["start_utc"], timezone_name),
            "end_local": _display_datetime(value["end_utc"], timezone_name),
            "average_p_per_kwh": value["average_p_per_kwh"],
        }

    return {
        "timezone": timezone_name,
        "lookback_days": analysis["lookback_days"],
        "average_p_per_kwh": analysis["average_p_per_kwh"],
        "baseline_average_p_per_kwh": analysis["baseline_average_p_per_kwh"],
        "difference_percent": analysis["difference_percent"],
        "free_or_negative_periods": [
            point(value) for value in analysis["free_or_negative_periods"]
        ],
        "peak": point(analysis["peak"]),
        "trough": point(analysis["trough"]),
        "cheapest_windows": windows,
        "daily_pattern": analysis["daily_pattern"],
    }


def generate_ai_commentary(
    analysis: dict[str, Any], *, api_key: str, model: str
) -> str:
    """Generate prose through the Responses API using the optional OpenAI SDK."""
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("Install the optional AI dependency: pip install '.[ai]'") from error

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        instructions=(
            "You are a concise UK Agile electricity-price analyst. Treat every "
            "number supplied as authoritative; do not recalculate or invent values. "
            "Write exactly 3 or 4 short sentences for a Home Assistant dashboard. "
            "Use plain prose only: no heading, bullets, markdown, colon-led label, "
            "or separator. Mention the recent-price comparison, the local time and "
            "price of the peak and trough, and any free or negative periods. Recommend "
            "the supplied 2-hour cheap window, not the 1-hour or 3-hour window. All "
            "Include the supplied daily pattern summary as one sentence. All "
            "supplied times are already UK local time. Use p/kWh. Do not discuss "
            "household load optimisation. Call the overall average the forecast "
            "average; never call it the current electricity price."
        ),
        input=json.dumps(build_prompt_payload(analysis), separators=(",", ":")),
        max_output_tokens=300,
    )
    commentary = response.output_text.strip().lstrip("-—– \n")
    if not commentary:
        raise RuntimeError("OpenAI returned empty commentary")
    return commentary
