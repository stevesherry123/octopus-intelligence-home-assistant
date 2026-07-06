from datetime import datetime, timedelta, timezone
import unittest

from octopus_intelligence.forecast import (
    next_usable_period_start,
    parse_ai_feed,
    upcoming_price_points,
)
from octopus_intelligence.models import PricePoint


class ForecastTests(unittest.TestCase):
    def test_exact_half_hour_boundary_is_immediately_usable(self):
        reference = datetime(2026, 7, 6, 14, 30, tzinfo=timezone.utc)

        self.assertEqual(next_usable_period_start(reference), reference)

    def test_partial_period_advances_to_next_half_hour(self):
        reference = datetime(2026, 7, 6, 14, 12, 3, tzinfo=timezone.utc)

        self.assertEqual(
            next_usable_period_start(reference),
            datetime(2026, 7, 6, 14, 30, tzinfo=timezone.utc),
        )

    def test_upcoming_filter_removes_past_and_in_progress_periods(self):
        start = datetime(2026, 7, 6, 11, 0, tzinfo=timezone.utc)
        points = [
            PricePoint(start + timedelta(minutes=30 * index), price)
            for index, price in enumerate([1, 2, 3, 4, 20, 21, 22, 23])
        ]

        result = upcoming_price_points(
            points,
            reference_utc=datetime(2026, 7, 6, 12, 42, tzinfo=timezone.utc),
        )

        self.assertEqual(
            [point.start_utc for point in result],
            [
                datetime(2026, 7, 6, 13, 0, tzinfo=timezone.utc),
                datetime(2026, 7, 6, 13, 30, tzinfo=timezone.utc),
                datetime(2026, 7, 6, 14, 0, tzinfo=timezone.utc),
                datetime(2026, 7, 6, 14, 30, tzinfo=timezone.utc),
            ],
        )

    def test_naive_cutoff_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            next_usable_period_start(datetime(2026, 7, 6, 14, 30))

    def test_sample_is_interpreted_as_british_summer_time(self):
        feed = "05/07 00:00=18.41p; 05/07 00:30=17.93p; 05/07 01:00=-1.2p;"
        points = parse_ai_feed(
            feed, reference_utc=datetime(2026, 7, 5, tzinfo=timezone.utc)
        )

        self.assertEqual(
            points[0].start_utc, datetime(2026, 7, 4, 23, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(points[2].price_p_per_kwh, -1.2)

    def test_new_year_uses_nearest_year(self):
        points = parse_ai_feed(
            "31/12 23:30=10p; 01/01 00:00=11p;",
            reference_utc=datetime(2027, 1, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(points[0].start_utc.year, 2026)
        self.assertEqual(points[1].start_utc.year, 2027)

    def test_nonexistent_spring_clock_time_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Non-existent local time"):
            parse_ai_feed(
                "29/03 01:30=10p;",
                reference_utc=datetime(2026, 3, 29, tzinfo=timezone.utc),
            )

    def test_repeated_autumn_hour_maps_to_distinct_utc_periods(self):
        points = parse_ai_feed(
            "25/10 01:00=10p; 25/10 01:00=11p;",
            reference_utc=datetime(2026, 10, 25, tzinfo=timezone.utc),
        )

        self.assertEqual(points[0].start_utc.hour, 0)
        self.assertEqual(points[1].start_utc.hour, 1)
