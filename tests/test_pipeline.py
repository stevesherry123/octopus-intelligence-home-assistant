import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from octopus_intelligence.config import Settings
from octopus_intelligence.pipeline import run_pipeline


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 7, 6, 12, 42, tzinfo=timezone.utc)
        return value if tz is None else value.astimezone(tz)


class PipelineTests(TestCase):
    def test_elapsed_periods_do_not_influence_actionable_results(self):
        # Feed labels are Europe/London wall time (BST here), one hour ahead of UTC.
        feed = "; ".join(
            [
                "06/07 12:00=1p",
                "06/07 12:30=2p",
                "06/07 13:00=3p",
                "06/07 13:30=4p",
                "06/07 14:00=20p",
                "06/07 14:30=21p",
                "06/07 15:00=22p",
                "06/07 15:30=23p",
            ]
        )

        with TemporaryDirectory() as directory:
            history_file = Path(directory) / "history.json"
            history_file.write_text(json.dumps([]), encoding="utf-8")
            settings = Settings(
                history_file=history_file,
                output_file=Path(directory) / "analysis.json",
            )
            with (
                patch("octopus_intelligence.pipeline.datetime", FixedDateTime),
                patch("octopus_intelligence.pipeline.download_history"),
            ):
                result = run_pipeline(
                    settings,
                    feed_text=feed,
                    dry_run=True,
                    use_ai=False,
                )

        self.assertEqual(result["source_forecast_periods"], 8)
        self.assertEqual(result["excluded_elapsed_periods"], 4)
        self.assertEqual(result["forecast_periods"], 4)
        self.assertEqual(
            result["cheapest_windows"]["2_hours"]["start_utc"],
            "2026-07-06T13:00:00Z",
        )
        self.assertEqual(result["average_p_per_kwh"], 21.5)

