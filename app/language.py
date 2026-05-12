from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_LANGUAGE: dict[str, Any] = {
    "terms": {
        "months": {
            "F": "January",
            "G": "February",
            "H": "March",
            "J": "April",
            "K": "May",
            "M": "June",
            "N": "July",
            "Q": "August",
            "U": "September",
            "V": "October",
            "X": "November",
            "Z": "December",
        },
        "strips": {
            "JV": "Summer",
            "XH": "Winter",
            "CAL": "Calendar year",
            "Q1": "Jan-Mar",
            "Q2": "Apr-Jun",
            "Q3": "Jul-Sep",
            "Q4": "Oct-Dec",
        },
    },
    "glossary": {
        "strip_notation": {
            "JV": "Summer strip, April through October",
            "XH": "Winter strip, November through March",
            "CAL": "Calendar year",
            "BULLETS": "Individual months inside a strip. Example: JV26 bullets are J26, K26, M26, N26, Q26, U26, and V26.",
        },
        "color_years": {
            "white": {"winter": "X6H7", "summer": "JV26"},
            "red": {"winter": "X7H8", "summer": "JV27"},
            "blue": {"winter": "X8H9", "summer": "JV28"},
        },
        "trade_terms": {
            "FTC": "Firm to close",
            "FOK": "Fill or Kill / Last look",
        },
        "product_terms": {
            "FIZ": "Physical index",
            "FINANCIAL": "Index futures / futures",
        },
    },
    "hubs": {
        "HSC": {
            "name": "Houston Ship Channel",
            "aliases": ["HSC"],
            "price_type": "basis_to_henry",
            "default_sign": "negative",
            "quote_order": "bid_offer",
            "group": "Texas",
            "board_order": 10,
        },
        "WAHA": {
            "name": "West Texas Permian",
            "aliases": ["WAHA", "Waha"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
            "group": "Texas",
            "board_order": 20,
        },
        "REX": {
            "name": "Rockies Express",
            "aliases": ["REX", "Rex"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
        },
        "DOM": {
            "name": "Eastern Gas South",
            "aliases": ["DOM", "Dom", "Dominion", "Dominion South", "Eastern Gas South"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
            "group": "Northeast",
            "board_order": 120,
        },
        "NNY": {
            "name": "Non-NY",
            "aliases": ["NNY"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
            "group": "Northeast",
            "board_order": 110,
        },
        "AGT": {
            "name": "Algonquin",
            "aliases": ["AGT"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
            "group": "Northeast",
            "board_order": 100,
        },
        "WLA": {
            "name": "West LA",
            "aliases": ["WLA"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
            "group": "Gulf Coast",
            "board_order": 70,
        },
        "ELA": {
            "name": "East LA",
            "aliases": ["ELA"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
            "group": "Gulf Coast",
            "board_order": 60,
        },
        "TGT": {
            "name": "Texas Gas",
            "aliases": ["TGT"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
            "group": "Texas",
            "board_order": 30,
        },
        "ML": {
            "name": "Mainline",
            "aliases": ["ML", "Mainline"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
        },
        "CGML": {
            "name": "Columbia Gulf Mainline",
            "aliases": ["CGML", "Columbia Gulf ML"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
        },
        "TXOK": {
            "name": "Texas Oklahoma",
            "aliases": ["TXOK", "Texas Oklahoma"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
            "group": "Texas",
            "board_order": 40,
        },
        "FGT": {
            "name": "Florida",
            "aliases": ["FGT", "Florida"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
            "group": "Gulf Coast",
            "board_order": 80,
        },
        "HH": {
            "name": "Henry Hub Benchmark",
            "aliases": ["HH", "Henry Hub"],
            "price_type": "flat_price",
            "default_sign": "positive",
            "quote_order": "bid_offer",
            "group": "Gulf Coast",
            "board_order": 50,
        },
        "TRANSCO": {
            "name": "Transco Appalachia",
            "aliases": ["TRANSCO", "Transco"],
            "price_type": "basis_to_henry",
            "default_sign": "unknown",
            "quote_order": "bid_offer",
            "group": "Northeast",
            "board_order": 130,
        },
    },
    "board": {
        "fresh_minutes": 10,
        "old_minutes": 30,
        "groups": ["Texas", "Gulf Coast", "Northeast", "Other"],
        "terms": [
            {"code": "JV26", "label": "JV26", "subtitle": "Summer 2026"},
            {"code": "XH26", "label": "XH26", "subtitle": "Winter 2026"},
            {"code": "CAL27", "label": "Cal27", "subtitle": "Calendar 2027"},
            {"code": "Q326", "label": "Q3 26", "subtitle": "Jul-Sep 2026"},
            {"code": "Q426", "label": "Q4 26", "subtitle": "Oct-Dec 2026"},
        ],
    },
    "parser": {
        "default_quote_order": "bid_offer",
        "stale_minutes": 15,
        "rolling_cache_hours": 12,
    },
}


class LanguageBook:
    def __init__(self, path: Path):
        self.path = path
        self.data = self._load_or_seed()

    def _load_or_seed(self) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps(DEFAULT_LANGUAGE, indent=2), encoding="utf-8")
            return json.loads(json.dumps(DEFAULT_LANGUAGE))

        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return self._merge_defaults(data)

    def _merge_defaults(self, data: dict[str, Any]) -> dict[str, Any]:
        merged = json.loads(json.dumps(DEFAULT_LANGUAGE))
        merged["terms"]["months"].update(data.get("terms", {}).get("months", {}))
        merged["terms"]["strips"].update(data.get("terms", {}).get("strips", {}))
        merged["glossary"].update(data.get("glossary", {}))
        merged["hubs"].update(data.get("hubs", {}))
        merged["board"].update(data.get("board", {}))
        merged["parser"].update(data.get("parser", {}))
        return merged

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")

    def term_prefixes(self) -> dict[str, str]:
        prefixes: dict[str, str] = {}
        prefixes.update({key.upper(): value for key, value in self.data["terms"]["months"].items()})
        prefixes.update({key.upper(): value for key, value in self.data["terms"]["strips"].items()})
        return prefixes

    def alias_map(self) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for code, hub in self.data["hubs"].items():
            aliases[code.upper()] = code.upper()
            for alias in hub.get("aliases", []):
                aliases[str(alias).upper()] = code.upper()
        return aliases

    def upsert_hub(
        self,
        code: str,
        name: str,
        aliases: list[str],
        default_sign: str = "unknown",
    ) -> dict[str, Any]:
        normalized_code = code.strip().upper()
        if not normalized_code:
            raise ValueError("Hub code is required.")

        existing = self.data["hubs"].get(normalized_code, {})
        merged_aliases = {normalized_code}
        merged_aliases.update(str(item).strip() for item in existing.get("aliases", []) if str(item).strip())
        merged_aliases.update(str(item).strip() for item in aliases if str(item).strip())

        self.data["hubs"][normalized_code] = {
            "name": name.strip() or existing.get("name") or normalized_code,
            "aliases": sorted(merged_aliases, key=str.upper),
            "price_type": existing.get("price_type", "basis_to_henry"),
            "default_sign": default_sign or existing.get("default_sign", "unknown"),
            "quote_order": existing.get("quote_order", "bid_offer"),
            "group": existing.get("group", "Other"),
            "board_order": existing.get("board_order", 999),
        }
        self.save()
        return self.data["hubs"][normalized_code]
