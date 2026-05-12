from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import mss
    import pytesseract
    from PIL import Image
except ImportError as exc:
    raise SystemExit(
        "OCR capture requires mss, pillow, and pytesseract. "
        "Install them with: pip install -r requirements-ocr.txt"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "capture" / "ocr_config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit("Missing capture/ocr_config.json. Copy capture/ocr_config.example.json first.")
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def post_line(server_url: str, line: str) -> None:
    payload = json.dumps({"raw": line}).encode("utf-8")
    request = urllib.request.Request(
        server_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        response.read()


def normalize_ocr_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        if len(line) < 4:
            continue
        if "/" not in line:
            continue
        lines.append(line)
    return lines


def main() -> None:
    config = load_config()
    server_url = config.get("server_url", "http://127.0.0.1:8765/api/ingest")
    interval = float(config.get("interval_seconds", 1.0))
    region = config["region"]
    tesseract_cmd = config.get("tesseract_cmd")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    recent_lines: list[str] = []
    print("OCR capture started. Press Ctrl+C to stop.")
    with mss.mss() as screen:
        while True:
            shot = screen.grab(region)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
            text = pytesseract.image_to_string(image)
            for line in normalize_ocr_lines(text):
                if line in recent_lines:
                    continue
                try:
                    post_line(server_url, line)
                    print(f"posted: {line}")
                except urllib.error.URLError as exc:
                    print(f"post failed: {exc}")
                recent_lines.append(line)
                recent_lines = recent_lines[-80:]
            time.sleep(interval)


if __name__ == "__main__":
    main()
