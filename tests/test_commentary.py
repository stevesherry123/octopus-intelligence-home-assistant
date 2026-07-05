from unittest import TestCase

from octopus_intelligence.commentary import build_announcement, build_prompt_payload


class CommentaryTests(TestCase):
    def test_deterministic_announcement_works_without_ai(self):
        analysis = {
            "timezone": "Europe/London",
            "difference_percent": -12.4,
            "free_or_negative_periods": [],
            "cheapest_windows": {
                "2_hours": {"start_utc": "2026-07-05T00:00:00Z"}
            },
        }
        message = build_announcement(analysis)

        self.assertIn("12% lower", message)
        self.assertIn("Sunday at 01:00", message)
        self.assertLessEqual(len(message), 255)

    def test_prompt_payload_contains_preconverted_local_times(self):
        analysis = {
            "timezone": "Europe/London",
            "lookback_days": 14,
            "average_p_per_kwh": 10,
            "baseline_average_p_per_kwh": 20,
            "difference_percent": -50,
            "free_or_negative_periods": [],
            "peak": {"start_utc": "2026-07-05T17:00:00Z", "price_p_per_kwh": 30},
            "trough": {"start_utc": "2026-07-06T11:00:00Z", "price_p_per_kwh": 1},
            "cheapest_windows": {
                "1_hour": None,
                "2_hours": {
                    "start_utc": "2026-07-06T11:00:00Z",
                    "end_utc": "2026-07-06T13:00:00Z",
                    "average_p_per_kwh": 2,
                },
                "3_hours": None,
            },
        }

        payload = build_prompt_payload(analysis)

        self.assertEqual(payload["peak"]["start_local"], "Sun 05 Jul 18:00")
        self.assertEqual(
            payload["cheapest_windows"]["2_hours"]["start_local"],
            "Mon 06 Jul 12:00",
        )
