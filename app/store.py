from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class QuoteStore:
    def __init__(self, path: Path, rolling_cache_hours: int):
        self.path = path
        self.rolling_cache_hours = rolling_cache_hours
        self.lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"active": {}, "history": []}
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return {"active": data.get("active", {}), "history": data.get("history", [])}

    def save(self) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(self.state, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(self.path)

    def ingest(self, parsed: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            quote = dict(parsed)
            quote["id"] = str(uuid.uuid4())
            quote["updated_at"] = utc_now().isoformat()
            quote["state_key"] = self._state_key(quote)
            quote["deleted"] = False

            existing = self.state["active"].get(quote["state_key"])
            if existing:
                quote["previous_id"] = existing.get("id")

            self.state["active"][quote["state_key"]] = quote
            self.state["history"].append(quote)
            self._prune_history()
            self.save()
            return quote

    def edit(self, quote_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        with self.lock:
            found_key = None
            found_quote = None
            for key, quote in self.state["active"].items():
                if quote.get("id") == quote_id:
                    found_key = key
                    found_quote = quote
                    break

            if not found_quote or found_key is None:
                return None

            edited = dict(found_quote)
            editable_fields = {
                "hub_code",
                "hub_name",
                "term_code",
                "term_text",
                "bid",
                "offer",
                "market_text",
                "size_text",
                "display",
                "confidence",
            }
            for field in editable_fields:
                if field in updates:
                    edited[field] = updates[field]

            if edited.get("bid") is not None and edited.get("offer") is not None:
                edited["market_text"] = f"{_format_number(float(edited['bid']))} / {_format_number(float(edited['offer']))}"

            edited["confidence"] = updates.get("confidence") or "high"
            edited["confidence_score"] = 1.0
            edited["warnings"] = []
            edited["updated_at"] = utc_now().isoformat()
            edited["edited"] = True
            edited["state_key"] = self._state_key(edited)

            del self.state["active"][found_key]
            self.state["active"][edited["state_key"]] = edited
            self.state["history"].append(edited)
            self._prune_history()
            self.save()
            return edited

    def delete(self, quote_id: str) -> bool:
        with self.lock:
            for key, quote in list(self.state["active"].items()):
                if quote.get("id") == quote_id:
                    deleted = dict(quote)
                    deleted["deleted"] = True
                    deleted["updated_at"] = utc_now().isoformat()
                    self.state["history"].append(deleted)
                    del self.state["active"][key]
                    self._prune_history()
                    self.save()
                    return True
        return False

    def snapshot(self, stale_minutes: int, language_data: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            now = utc_now()
            history_by_key = self._history_by_key()
            quotes = []
            for quote in self.state["active"].values():
                item = dict(quote)
                updated_at = parse_dt(item["updated_at"])
                age_seconds = max(0, int((now - updated_at).total_seconds()))
                item["age_seconds"] = age_seconds
                item["bid_age_seconds"] = self._field_age_seconds(item, "bid", history_by_key, now)
                item["offer_age_seconds"] = self._field_age_seconds(item, "offer", history_by_key, now)
                item["stale"] = age_seconds >= stale_minutes * 60
                quotes.append(item)

            quotes.sort(key=lambda q: (q.get("hub_code") or "ZZZ", q.get("term_code") or "ZZZ"))
            return {
                "generated_at": now.isoformat(),
                "stale_minutes": stale_minutes,
                "quotes": quotes,
                "language": language_data,
            }

    def _state_key(self, quote: dict[str, Any]) -> str:
        hub = quote.get("hub_code") or "UNKNOWN_HUB"
        term = quote.get("term_code") or quote.get("term_text") or "UNKNOWN_TERM"
        return f"{hub}|{term}"

    def _history_by_key(self) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for quote in self.state["history"]:
            key = quote.get("state_key")
            if not key:
                continue
            grouped.setdefault(key, []).append(quote)

        for quotes in grouped.values():
            quotes.sort(key=_quote_time, reverse=True)
        return grouped

    def _field_age_seconds(
        self,
        quote: dict[str, Any],
        field: str,
        history_by_key: dict[str, list[dict[str, Any]]],
        now: datetime,
    ) -> int:
        current_value = quote.get(field)
        current_time = _quote_time(quote)
        started_at = current_time

        for historical in history_by_key.get(str(quote.get("state_key")), []):
            historical_time = _quote_time(historical)
            if historical_time > current_time:
                continue
            if historical.get("deleted"):
                break
            if _same_price(historical.get(field), current_value):
                started_at = historical_time
                continue
            break

        return max(0, int((now - started_at).total_seconds()))

    def _prune_history(self) -> None:
        cutoff = utc_now() - timedelta(hours=self.rolling_cache_hours)
        self.state["history"] = [
            quote
            for quote in self.state["history"]
            if parse_dt(quote.get("updated_at", quote.get("parsed_at"))) >= cutoff
        ]


def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _quote_time(quote: dict[str, Any]) -> datetime:
    return parse_dt(str(quote.get("updated_at") or quote.get("parsed_at")))


def _same_price(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return left == right
