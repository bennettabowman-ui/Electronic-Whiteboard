from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from app.store import QuoteStore


class QuoteStoreTest(unittest.TestCase):
    def make_store(self) -> QuoteStore:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return QuoteStore(Path(temp_dir.name) / "quotes.json", rolling_cache_hours=12)

    def test_snapshot_tracks_bid_and_offer_age_independently(self) -> None:
        now = datetime(2026, 5, 12, 14, 0, tzinfo=UTC)
        key = "HSC|JV27"

        first = self.quote(key, bid=-22, offer=-21, updated_at=now - timedelta(minutes=60))
        offer_changed = self.quote(key, bid=-22, offer=-20, updated_at=now - timedelta(minutes=30))
        current = self.quote(key, bid=-22, offer=-20, updated_at=now - timedelta(minutes=10))

        store = self.make_store()
        store.state = {
            "active": {key: current},
            "history": [first, offer_changed, current],
        }

        with patch("app.store.utc_now", return_value=now):
            quote = store.snapshot(stale_minutes=15, language_data={})["quotes"][0]

        self.assertEqual(quote["age_seconds"], 10 * 60)
        self.assertEqual(quote["bid_age_seconds"], 60 * 60)
        self.assertEqual(quote["offer_age_seconds"], 30 * 60)

    def quote(
        self,
        state_key: str,
        bid: float,
        offer: float,
        updated_at: datetime,
    ) -> dict[str, object]:
        hub_code, term_code = state_key.split("|")
        return {
            "id": updated_at.isoformat(),
            "state_key": state_key,
            "hub_code": hub_code,
            "term_code": term_code,
            "bid": bid,
            "offer": offer,
            "updated_at": updated_at.isoformat(),
            "deleted": False,
        }


if __name__ == "__main__":
    unittest.main()
