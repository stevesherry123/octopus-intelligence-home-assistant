from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


def _read_named_secrets(path: Path, names: set[str]) -> dict[str, str]:
    """Read simple top-level scalar entries without loading unrelated HA secrets."""
    found: dict[str, str] = {}
    key_pattern = re.compile(r"^([A-Za-z0-9_]+)\s*:\s*(.*?)\s*$")
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if raw_line[:1].isspace() or raw_line.lstrip().startswith("#"):
                continue
            match = key_pattern.match(raw_line.rstrip("\r\n"))
            if not match or match.group(1) not in names:
                continue
            key, value = match.groups()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            if not value:
                raise ValueError(f"Secret {key!r} is empty in {path}")
            found[key] = value
    return found


@dataclass(frozen=True)
class Settings:
    ha_url: str = "http://homeassistant.local:8123"
    ha_token: str | None = field(default=None, repr=False)
    openai_api_key: str | None = field(default=None, repr=False)
    openai_model: str = "gpt-5.4-mini"
    forecast_entity: str = "sensor.octopus_price_feed_clean"
    analysis_entity: str = "sensor.octopus_intelligence"
    announcement_entity: str = "input_text.announce_text"
    history_url: str = "https://agilebuddy.uk/historic/download/agile/json"
    history_file: Path = Path("data/agile-history.json")
    output_file: Path = Path("data/latest-analysis.json")
    history_cache_hours: int = 24
    lookback_days: int = 14
    timezone_name: str = "Europe/London"

    @classmethod
    def from_environment(cls) -> "Settings":
        secrets_path = Path(os.getenv("OIE_SECRETS_FILE", "/config/secrets.yaml"))
        ha_secret_name = os.getenv("OIE_HA_TOKEN_SECRET", "oie_ha_token")
        openai_secret_name = os.getenv(
            "OIE_OPENAI_API_KEY_SECRET", "oie_openai_api_key"
        )
        openai_model_name = os.getenv("OIE_OPENAI_MODEL_SECRET", "oie_openai_model")
        secrets = (
            _read_named_secrets(
                secrets_path, {ha_secret_name, openai_secret_name, openai_model_name}
            )
            if secrets_path.is_file()
            else {}
        )

        def secret(name: str) -> str | None:
            value = secrets.get(name)
            return str(value) if value is not None else None

        return cls(
            ha_url=os.getenv("HA_URL", cls.ha_url),
            ha_token=os.getenv("HA_TOKEN") or secret(ha_secret_name),
            openai_api_key=os.getenv("OPENAI_API_KEY") or secret(openai_secret_name),
            openai_model=(
                os.getenv("OPENAI_MODEL")
                or secret(openai_model_name)
                or cls.openai_model
            ),
            forecast_entity=os.getenv("OIE_FORECAST_ENTITY", cls.forecast_entity),
            analysis_entity=os.getenv("OIE_ANALYSIS_ENTITY", cls.analysis_entity),
            announcement_entity=os.getenv(
                "OIE_ANNOUNCEMENT_ENTITY", cls.announcement_entity
            ),
            history_url=os.getenv("OIE_HISTORY_URL", cls.history_url),
            history_file=Path(os.getenv("OIE_HISTORY_FILE", str(cls.history_file))),
            output_file=Path(os.getenv("OIE_OUTPUT_FILE", str(cls.output_file))),
            history_cache_hours=int(
                os.getenv("OIE_HISTORY_CACHE_HOURS", str(cls.history_cache_hours))
            ),
            lookback_days=int(os.getenv("OIE_LOOKBACK_DAYS", str(cls.lookback_days))),
            timezone_name=os.getenv("OIE_TIMEZONE", cls.timezone_name),
        )
