from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .language import LanguageBook


PRICE_RE = re.compile(r"(?P<left>[+-]?\d+(?:\.\d+)?)\s*/\s*(?P<right>[+-]?\d+(?:\.\d+)?)")


@dataclass
class ParsedQuote:
    raw: str
    parsed_at: str
    term_code: str | None = None
    term_text: str | None = None
    hub_code: str | None = None
    hub_name: str | None = None
    price_type: str = "basis_to_henry"
    bid: float | None = None
    offer: float | None = None
    market_text: str | None = None
    size_text: str | None = None
    display: str | None = None
    confidence: str = "low"
    confidence_score: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "parsed_at": self.parsed_at,
            "term_code": self.term_code,
            "term_text": self.term_text,
            "hub_code": self.hub_code,
            "hub_name": self.hub_name,
            "price_type": self.price_type,
            "bid": self.bid,
            "offer": self.offer,
            "market_text": self.market_text,
            "size_text": self.size_text,
            "display": self.display,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "warnings": self.warnings,
        }


class QuoteParser:
    def __init__(self, language: LanguageBook):
        self.language = language

    def parse(self, raw: str) -> dict[str, Any]:
        clean_raw = " ".join(raw.strip().split())
        parsed = ParsedQuote(raw=clean_raw, parsed_at=datetime.now(UTC).isoformat())
        score = 0.0

        if not clean_raw:
            parsed.warnings.append("Empty line.")
            return parsed.to_dict()

        term = self._find_term(clean_raw)
        if term:
            parsed.term_code = term["code"]
            parsed.term_text = term["text"]
            score += 0.25
        else:
            parsed.warnings.append("No recognized term code.")

        hub = self._find_hub(clean_raw)
        if hub:
            parsed.hub_code = hub["code"]
            parsed.hub_name = hub["name"]
            parsed.price_type = hub.get("price_type", "basis_to_henry")
            score += 0.25
        else:
            parsed.warnings.append("No recognized hub.")

        price_match = PRICE_RE.search(clean_raw)
        if price_match:
            raw_left = price_match.group("left")
            raw_right = price_match.group("right")
            left = float(raw_left)
            right = float(raw_right)
            had_explicit_sign = raw_left.startswith(("-", "+")) or raw_right.startswith(("-", "+"))

            if hub and not had_explicit_sign:
                default_sign = hub.get("default_sign", "unknown")
                if default_sign == "negative":
                    left = -abs(left)
                    right = -abs(right)
                elif default_sign == "positive":
                    left = abs(left)
                    right = abs(right)
                else:
                    parsed.warnings.append("Hub has no default sign; displayed price may need review.")
                    score -= 0.15

            parsed.bid = left
            parsed.offer = right
            parsed.market_text = f"{_format_number(left)} / {_format_number(right)}"
            parsed.size_text = clean_raw[price_match.end() :].strip() or None
            score += 0.35
        else:
            parsed.warnings.append("No bid/offer price pair found.")

        if parsed.size_text:
            score += 0.05

        parsed.display = self._build_display(parsed)
        parsed.confidence_score = max(0.0, min(1.0, score))
        parsed.confidence = self._confidence_label(parsed.confidence_score)
        return parsed.to_dict()

    def _find_term(self, raw: str) -> dict[str, str] | None:
        tokens = _tokens(raw)
        prefixes = self.language.term_prefixes()
        ordered_prefixes = sorted(prefixes, key=len, reverse=True)

        for index, token in enumerate(tokens):
            normalized = token.upper()
            for prefix in ordered_prefixes:
                year_part = None
                code_prefix = prefix
                if normalized == prefix and index + 1 < len(tokens) and tokens[index + 1].isdigit():
                    year_part = tokens[index + 1]
                elif normalized.startswith(prefix):
                    year_part = normalized[len(prefix) :]
                if year_part is None:
                    continue
                if not year_part.isdigit() or len(year_part) not in (2, 4):
                    continue
                year = int(year_part)
                if len(year_part) == 2:
                    year += 2000
                text = f"{prefixes[code_prefix]} {year}"
                return {"code": f"{code_prefix}{year_part}", "text": text}
        return None

    def _find_hub(self, raw: str) -> dict[str, Any] | None:
        aliases = self.language.alias_map()
        hubs = self.language.data["hubs"]

        for token in _tokens(raw):
            code = aliases.get(token.upper())
            if not code:
                continue
            hub = hubs[code]
            return {"code": code, **hub}
        return None

    def _build_display(self, parsed: ParsedQuote) -> str:
        parts = []
        if parsed.hub_code:
            parts.append(parsed.hub_code)
        if parsed.term_text:
            parts.append(parsed.term_text)
        if parsed.market_text:
            parts.append(parsed.market_text)
        if parsed.size_text:
            parts.append(parsed.size_text)
        return " | ".join(parts) if parts else parsed.raw

    def _confidence_label(self, score: float) -> str:
        if score >= 0.8:
            return "high"
        if score >= 0.55:
            return "medium"
        return "low"


def _tokens(raw: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:/[A-Za-z0-9]+)?", raw)


def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")
