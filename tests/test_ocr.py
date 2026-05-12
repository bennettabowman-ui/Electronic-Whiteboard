from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.ocr import OcrLineProcessor, classify_ocr_line, load_ocr_config, normalize_ocr_line


class OcrTest(unittest.TestCase):
    def test_normalize_ocr_line_collapses_whitespace(self) -> None:
        self.assertEqual(normalize_ocr_line("  red   summer   HSC  22/21  "), "red summer HSC 22/21")

    def test_quote_like_filter_accepts_chat_quotes(self) -> None:
        accepted, reason = classify_ocr_line("blue winter DOM 22/21")

        self.assertTrue(accepted)
        self.assertEqual(reason, "accepted")

    def test_quote_like_filter_skips_ui_noise(self) -> None:
        examples = [
            "Messages",
            "Last updated 10:41 AM",
            "22/21",
            "Broker list settings",
        ]

        for line in examples:
            with self.subTest(line=line):
                accepted, _reason = classify_ocr_line(line)
                self.assertFalse(accepted)

    def test_processor_dedupes_recent_lines(self) -> None:
        processor = OcrLineProcessor(recent_line_limit=10)

        decisions = processor.process_text(
            """
            Messages
            JV27 HSC 22/21
            JV27 HSC 22/21
            blue winter DOM 31/30
            """
        )

        accepted = [decision.line for decision in decisions if decision.accepted]
        skipped = [(decision.line, decision.reason) for decision in decisions if not decision.accepted]

        self.assertEqual(accepted, ["JV27 HSC 22/21", "blue winter DOM 31/30"])
        self.assertIn(("Messages", "not quote-like"), skipped)
        self.assertIn(("JV27 HSC 22/21", "duplicate"), skipped)

    def test_missing_local_config_loads_disabled_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_ocr_config(Path(temp_dir))

        self.assertFalse(config.enabled)
        self.assertEqual(config.server_url, "http://127.0.0.1:8765/api/ingest")

    def test_local_config_can_enable_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            capture_dir = root / "capture"
            capture_dir.mkdir()
            (capture_dir / "ocr_config.json").write_text(
                json.dumps(
                    {
                        "enabled": True,
                        "region": {
                            "left": 10,
                            "top": 20,
                            "width": 300,
                            "height": 400,
                        },
                        "recent_line_limit": 12,
                    }
                ),
                encoding="utf-8",
            )

            config = load_ocr_config(root)

        self.assertTrue(config.enabled)
        self.assertEqual(config.region["left"], 10)
        self.assertEqual(config.region["height"], 400)
        self.assertEqual(config.recent_line_limit, 12)


if __name__ == "__main__":
    unittest.main()
