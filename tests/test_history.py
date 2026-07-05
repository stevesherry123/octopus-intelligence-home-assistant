from datetime import datetime, timezone
import unittest

from octopus_intelligence.history import parse_agile_buddy


class HistoryTests(unittest.TestCase):
    def test_agile_buddy_timestamp_is_normalised_from_end_to_start(self):
        points = parse_agile_buddy([{"dt": "2026-07-05T00:30:00Z", "r": -1.25}])

        self.assertEqual(
            points[0].start_utc, datetime(2026, 7, 5, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(points[0].price_p_per_kwh, -1.25)
