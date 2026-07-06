from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from octopus_intelligence.config import Settings
from octopus_intelligence.scheduler import run_scheduler


class SchedulerTests(TestCase):
    def test_scheduler_records_success(self):
        with TemporaryDirectory() as directory:
            settings = Settings(output_file=Path(directory) / "analysis.json")
            with patch("octopus_intelligence.scheduler.run_pipeline") as run:
                run_scheduler(settings, interval_hours=0.000001, max_runs=1)
            status = (Path(directory) / "scheduler-status.json").read_text()

        run.assert_called_once()
        self.assertIn('"state": "healthy"', status)

    def test_scheduler_retains_operation_after_failure(self):
        with TemporaryDirectory() as directory:
            settings = Settings(output_file=Path(directory) / "analysis.json")
            with patch(
                "octopus_intelligence.scheduler.run_pipeline",
                side_effect=RuntimeError("temporary"),
            ):
                run_scheduler(settings, interval_hours=0.000001, max_runs=1)
            status = (Path(directory) / "scheduler-status.json").read_text()

        self.assertIn('"state": "degraded"', status)
        self.assertIn('"last_error": "RuntimeError"', status)

    def test_scheduler_triggers_when_forecast_ready_entity_populates(self):
        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                self.states = iter(["", "loaded"])

            def get_state(self, _entity_id):
                return {"state": next(self.states)}

        with TemporaryDirectory() as directory:
            settings = Settings(
                ha_token="test-token",
                output_file=Path(directory) / "analysis.json",
            )
            with patch("octopus_intelligence.scheduler.HomeAssistantClient", FakeClient):
                with patch("octopus_intelligence.scheduler.run_pipeline") as run:
                    run_scheduler(
                        settings,
                        interval_hours=1,
                        poll_seconds=0.01,
                        max_runs=2,
                    )

        self.assertEqual(run.call_count, 2)

    def test_scheduler_keeps_timed_fallback(self):
        with TemporaryDirectory() as directory:
            settings = Settings(output_file=Path(directory) / "analysis.json")
            with patch("octopus_intelligence.scheduler.run_pipeline") as run:
                run_scheduler(
                    settings,
                    interval_hours=0.000001,
                    poll_seconds=0.001,
                    max_runs=2,
                )

        self.assertEqual(run.call_count, 2)
