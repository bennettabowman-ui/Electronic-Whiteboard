from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ocr import load_ocr_config, run_ocr_capture


def main() -> None:
    try:
        config = load_ocr_config(ROOT, require_exists=True)
        run_ocr_capture(config)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
