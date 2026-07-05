from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


class HomeAssistantClient:
    """Small local REST client with no dependency on Home Assistant internals."""

    def __init__(self, base_url: str, token: str, *, timeout_seconds: int = 30):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                content = response.read()
        except HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"Home Assistant returned HTTP {error.code}: {detail}"
            ) from error
        return json.loads(content) if content else {}

    def get_state(self, entity_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/states/{quote(entity_id, safe='._')}")

    def get_ai_feed(self, entity_id: str) -> str:
        state = self.get_state(entity_id)
        feed = state.get("attributes", {}).get("ai_feed")
        if not isinstance(feed, str) or not feed.strip():
            raise ValueError(f"{entity_id} has no non-empty ai_feed attribute")
        return feed

    def set_input_text(self, entity_id: str, value: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/services/input_text/set_value",
            {"entity_id": entity_id, "value": value[:255]},
        )

    def publish_analysis_sensor(
        self,
        analysis: dict[str, Any],
        *,
        entity_id: str = "sensor.octopus_intelligence",
    ) -> dict[str, Any]:
        """Publish dashboard data; rerun after a Home Assistant restart."""
        attributes = {
            **analysis,
            "friendly_name": "Octopus Intelligence",
            "icon": "mdi:lightning-bolt",
            "unit_of_measurement": "p/kWh",
        }
        return self._request(
            "POST",
            f"/api/states/{quote(entity_id, safe='._')}",
            {
                "state": round(analysis["average_p_per_kwh"], 2),
                "attributes": attributes,
            },
        )
