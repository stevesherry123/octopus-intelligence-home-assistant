from datetime import datetime, timedelta, timezone
import unittest

from octopus_intelligence.analysis import analyse_prices
from octopus_intelligence.models import PricePoint


def points(start, values):
    return [
        PricePoint(start + timedelta(minutes=30 * index), value)
        for index, value in enumerate(values)
    ]


class AnalysisTests(unittest.TestCase):
    def test_negative_prices_and_cheapest_consecutive_window(self):
        start = datetime(2026, 7, 5, tzinfo=timezone.utc)
        forecast = points(start, [12, 8, -2, -1, 4, 20])
        history = points(start - timedelta(days=1), [10] * 6)
        result = analyse_prices(forecast, history, lookback_days=2)

        self.assertEqual(len(result["free_or_negative_periods"]), 2)
        self.assertEqual(
            result["cheapest_windows"]["1_hour"]["average_p_per_kwh"], -1.5
        )

    def test_gap_is_not_treated_as_a_continuous_window(self):
        start = datetime(2026, 7, 5, tzinfo=timezone.utc)
        forecast = [
            PricePoint(start, -10),
            PricePoint(start + timedelta(hours=1), -10),
            PricePoint(start + timedelta(hours=1, minutes=30), 2),
        ]
        result = analyse_prices(forecast, [])

        self.assertEqual(
            result["cheapest_windows"]["1_hour"]["average_p_per_kwh"], -4
        )

    def test_uk_dst_is_applied_only_to_display_times(self):
        forecast = points(
            datetime(2026, 3, 29, 0, 30, tzinfo=timezone.utc), [10, 11]
        )
        result = analyse_prices(forecast, [])

        self.assertEqual(result["periods"][0]["start_local"], "2026-03-29T00:30:00+00:00")
        self.assertEqual(result["periods"][1]["start_local"], "2026-03-29T02:00:00+01:00")

    def test_data_quality_reports_missing_periods(self):
        start = datetime(2026, 7, 5, tzinfo=timezone.utc)
        forecast = [
            PricePoint(start, 10),
            PricePoint(start + timedelta(hours=1), 12),
        ]
        result = analyse_prices(forecast, [])

        quality = result["data_quality"]
        self.assertEqual(quality["status"], "warning")
        self.assertEqual(quality["expected_periods"], 3)
        self.assertEqual(quality["received_periods"], 2)
        self.assertEqual(
            quality["missing_periods_utc"], ["2026-07-05T00:30:00Z"]
        )

    def test_data_quality_accepts_complete_forecast_and_baseline(self):
        start = datetime(2026, 7, 5, tzinfo=timezone.utc)
        forecast = points(start, [10, 11, 12, 13])
        history = []
        for days_ago in range(1, 9):
            history.extend(points(start - timedelta(days=days_ago), [9, 10, 11, 12]))
        result = analyse_prices(forecast, history, lookback_days=8)

        quality = result["data_quality"]
        self.assertEqual(quality["status"], "good")
        self.assertTrue(quality["periods_are_consecutive"])
        self.assertEqual(quality["baseline_slot_coverage_percent"], 100.0)
        self.assertEqual(quality["baseline_days_used"], 8)
