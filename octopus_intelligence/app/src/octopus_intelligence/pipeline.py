from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .analysis import analyse_prices
from .commentary import build_announcement, generate_ai_commentary
from .config import Settings
from .forecast import parse_ai_feed
from .history import download_history, load_history
from .home_assistant import HomeAssistantClient


def run_pipeline(
    settings: Settings,
    *,
    feed_text: str | None = None,
    dry_run: bool = False,
    use_ai: bool = True,
    publish_announcement: bool = True,
) -> dict[str, Any]:
    client = None
    if feed_text is None:
        if not settings.ha_token:
            raise ValueError("HA_TOKEN is required when no feed file is supplied")
        client = HomeAssistantClient(settings.ha_url, settings.ha_token)
        feed_text = client.get_ai_feed(settings.forecast_entity)

    forecast = parse_ai_feed(
        feed_text,
        reference_utc=datetime.now(timezone.utc),
        source_timezone=settings.timezone_name,
    )
    history_refresh_status = "cache_current"
    if not settings.history_file.exists():
        download_history(settings.history_file, url=settings.history_url)
        history_refresh_status = "updated"
    history = load_history(settings.history_file)
    newest_history = history[-1].end_utc if history else None
    refresh_before = forecast[0].start_utc - timedelta(days=2)
    file_age_hours = (
        datetime.now(timezone.utc).timestamp() - settings.history_file.stat().st_mtime
    ) / 3600
    if (
        newest_history is None
        or newest_history < refresh_before
        or file_age_hours >= settings.history_cache_hours
    ):
        try:
            download_history(settings.history_file, url=settings.history_url)
            history = load_history(settings.history_file)
            history_refresh_status = "updated"
        except Exception as error:
            if not history:
                raise
            history_refresh_status = f"stale_cache: {type(error).__name__}"
    analysis = analyse_prices(
        forecast,
        history,
        lookback_days=settings.lookback_days,
        timezone_name=settings.timezone_name,
    )
    analysis["generated_at_utc"] = datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    analysis["history_refresh_status"] = history_refresh_status
    analysis["announcement"] = build_announcement(analysis)
    analysis["commentary"] = None
    analysis["commentary_status"] = "disabled"

    if use_ai and settings.openai_api_key:
        try:
            analysis["commentary"] = generate_ai_commentary(
                analysis,
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )
            analysis["commentary_status"] = "ok"
        except Exception as error:  # numerical results remain publishable
            analysis["commentary_status"] = f"error: {type(error).__name__}"

    settings.output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = settings.output_file.with_suffix(settings.output_file.suffix + ".tmp")
    temporary.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    temporary.replace(settings.output_file)

    if not dry_run:
        if not settings.ha_token:
            raise ValueError("HA_TOKEN is required to publish results")
        client = client or HomeAssistantClient(settings.ha_url, settings.ha_token)
        client.publish_analysis_sensor(analysis, entity_id=settings.analysis_entity)
        if publish_announcement:
            client.set_input_text(settings.announcement_entity, analysis["announcement"])

    return analysis
