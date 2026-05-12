from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.language import LanguageBook
from app.parser import QuoteParser


class ParserTest(unittest.TestCase):
    def make_parser(self) -> QuoteParser:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        language = LanguageBook(Path(temp_dir.name) / "language.json")
        return QuoteParser(language)

    def test_hsc_strip_negative_basis(self) -> None:
        parser = self.make_parser()
        parsed = parser.parse("Jv27 HSC 22/21 1/2 day")

        self.assertEqual(parsed["term_code"], "JV27")
        self.assertEqual(parsed["term_text"], "Summer 2027")
        self.assertEqual(parsed["hub_code"], "HSC")
        self.assertEqual(parsed["bid"], -22)
        self.assertEqual(parsed["offer"], -21)
        self.assertEqual(parsed["size_text"], "1/2 day")
        self.assertEqual(parsed["confidence"], "high")

    def test_explicit_sign_overrides_hub_default(self) -> None:
        parser = self.make_parser()
        parsed = parser.parse("JV27 HSC +22/+21")

        self.assertEqual(parsed["bid"], 22)
        self.assertEqual(parsed["offer"], 21)

    def test_unknown_sign_is_warned(self) -> None:
        parser = self.make_parser()
        parsed = parser.parse("JV27 REX 22/21")

        self.assertEqual(parsed["hub_code"], "REX")
        self.assertEqual(parsed["confidence"], "medium")
        self.assertTrue(any("default sign" in warning for warning in parsed["warnings"]))

    def test_spaced_quarter_term(self) -> None:
        parser = self.make_parser()
        parsed = parser.parse("Q3 26 TXOK 2.31/2.34")

        self.assertEqual(parsed["term_code"], "Q326")
        self.assertEqual(parsed["term_text"], "Jul-Sep 2026")
        self.assertEqual(parsed["hub_code"], "TXOK")
        self.assertEqual(parsed["bid"], 2.31)
        self.assertEqual(parsed["offer"], 2.34)

    def test_month_range_term(self) -> None:
        parser = self.make_parser()
        parsed = parser.parse("MV26 HSC 22/21")

        self.assertEqual(parsed["term_code"], "MV26")
        self.assertEqual(parsed["term_text"], "June-October 2026")
        self.assertEqual(parsed["hub_code"], "HSC")
        self.assertEqual(parsed["bid"], -22)
        self.assertEqual(parsed["offer"], -21)

    def test_cross_year_color_strip(self) -> None:
        parser = self.make_parser()
        parsed = parser.parse("X6H7 DOM 22/21")

        self.assertEqual(parsed["term_code"], "X6H7")
        self.assertEqual(parsed["term_text"], "November 2026-March 2027")
        self.assertEqual(parsed["hub_code"], "DOM")
        self.assertEqual(parsed["hub_name"], "Eastern Gas South")


if __name__ == "__main__":
    unittest.main()
