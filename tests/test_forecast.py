from datetime import datetime, timezone
import unittest

from octopus_intelligence.forecast import parse_ai_feed


class ForecastTests(unittest.TestCase):
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

