from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


QUOTE_PAIR_RE = re.compile(r"(?<!\d)[+-]?\d+(?:\.\d+)?\s*/\s*[+-]?\d+(?:\.\d+)?(?!\d)")
LETTER_RE = re.compile(r"[A-Za-z]")

DEFAULT_OCR_CONFIG: dict[str, Any] = {
    "enabled": False,
    "server_url": "http://127.0.0.1:8765/api/ingest",
    "interval_seconds": 1.0,
    "region": {
        "left": 100,
        "top": 100,
        "width": 900,
        "height": 700,
    },
    "tesseract_cmd": "",
    "recent_line_limit": 80,
    "require_quote_like": True,
    "log_skipped": True,
    "request_timeout_seconds": 3.0,
}


@dataclass(frozen=True)
class OcrCaptureConfig:
    enabled: bool
    server_url: str
    interval_seconds: float
    region: dict[str, int]
    tesseract_cmd: str
    recent_line_limit: int
    require_quote_like: bool
    log_skipped: bool
    request_timeout_seconds: float
    config_path: Path | None = None


@dataclass(frozen=True)
class OcrLineDecision:
    line: str
    accepted: bool
    reason: str


class RecentLineDeduper:
    def __init__(self, limit: int):
        self.limit = max(1, int(limit))
        self._lines: list[str] = []
        self._seen: set[str] = set()

    def add_if_new(self, line: str) -> bool:
        if line in self._seen:
            return False
        self._lines.append(line)
        self._seen.add(line)
        while len(self._lines) > self.limit:
            removed = self._lines.pop(0)
            self._seen.discard(removed)
        return True


class OcrLineProcessor:
    def __init__(self, recent_line_limit: int = 80, require_quote_like: bool = True):
        self.require_quote_like = require_quote_like
        self.accepted = RecentLineDeduper(recent_line_limit)
        self.skipped = RecentLineDeduper(recent_line_limit)

    def process_text(self, text: str) -> list[OcrLineDecision]:
        decisions: list[OcrLineDecision] = []
        for raw_line in text.splitlines():
            line = normalize_ocr_line(raw_line)
            if not line:
                continue
            accepted, reason = classify_ocr_line(line, self.require_quote_like)
            if accepted:
                if self.accepted.add_if_new(line):
                    decisions.append(OcrLineDecision(line=line, accepted=True, reason="accepted"))
                elif self.skipped.add_if_new(f"duplicate:{line}"):
                    decisions.append(OcrLineDecision(line=line, accepted=False, reason="duplicate"))
                continue
            if self.skipped.add_if_new(f"{reason}:{line}"):
                decisions.append(OcrLineDecision(line=line, accepted=False, reason=reason))
        return decisions


class OcrCaptureService:
    def __init__(self, config: OcrCaptureConfig):
        self.config = config
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.config.enabled:
            return
        self._thread = threading.Thread(target=self.run, name="ocr-capture", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def run(self) -> None:
        try:
            run_ocr_capture(self.config, self._stop)
        except RuntimeError as exc:
            print(f"OCR capture not started: {exc}")


def load_ocr_config(root: Path, require_exists: bool = False) -> OcrCaptureConfig:
    path = root / "capture" / "ocr_config.json"
    if not path.exists():
        if require_exists:
            raise RuntimeError("Missing capture/ocr_config.json. Copy capture/ocr_config.example.json first.")
        return make_ocr_config(DEFAULT_OCR_CONFIG, path)

    with path.open("r", encoding="utf-8") as handle:
        local_config = json.load(handle)

    merged = dict(DEFAULT_OCR_CONFIG)
    merged["region"] = dict(DEFAULT_OCR_CONFIG["region"])
    merged.update(local_config)
    if isinstance(local_config.get("region"), dict):
        merged["region"] = dict(DEFAULT_OCR_CONFIG["region"])
        merged["region"].update(local_config["region"])
    return make_ocr_config(merged, path)


def make_ocr_config(data: dict[str, Any], path: Path | None = None) -> OcrCaptureConfig:
    region = data.get("region") or {}
    return OcrCaptureConfig(
        enabled=bool(data.get("enabled", False)),
        server_url=str(data.get("server_url") or DEFAULT_OCR_CONFIG["server_url"]),
        interval_seconds=float(data.get("interval_seconds") or DEFAULT_OCR_CONFIG["interval_seconds"]),
        region={
            "left": int(region.get("left", DEFAULT_OCR_CONFIG["region"]["left"])),
            "top": int(region.get("top", DEFAULT_OCR_CONFIG["region"]["top"])),
            "width": int(region.get("width", DEFAULT_OCR_CONFIG["region"]["width"])),
            "height": int(region.get("height", DEFAULT_OCR_CONFIG["region"]["height"])),
        },
        tesseract_cmd=str(data.get("tesseract_cmd") or ""),
        recent_line_limit=int(data.get("recent_line_limit") or DEFAULT_OCR_CONFIG["recent_line_limit"]),
        require_quote_like=bool(data.get("require_quote_like", True)),
        log_skipped=bool(data.get("log_skipped", True)),
        request_timeout_seconds=float(
            data.get("request_timeout_seconds") or DEFAULT_OCR_CONFIG["request_timeout_seconds"]
        ),
        config_path=path,
    )


def normalize_ocr_line(raw_line: str) -> str:
    return " ".join(str(raw_line).strip().split())


def classify_ocr_line(line: str, require_quote_like: bool = True) -> tuple[bool, str]:
    if len(line) < 4:
        return False, "too short"
    if len(line) > 180:
        return False, "too long"
    if not require_quote_like:
        return True, "accepted"
    if not QUOTE_PAIR_RE.search(line):
        return False, "not quote-like"
    if not LETTER_RE.search(line):
        return False, "no text token"
    return True, "accepted"


def post_line(server_url: str, line: str, timeout_seconds: float = 3.0) -> None:
    payload = json.dumps({"raw": line}).encode("utf-8")
    request = urllib.request.Request(
        server_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response.read()


def run_ocr_capture(config: OcrCaptureConfig, stop_event: threading.Event | None = None) -> None:
    mss_module, pytesseract_module, image_class = load_screen_ocr_dependencies()
    if config.tesseract_cmd:
        pytesseract_module.pytesseract.tesseract_cmd = config.tesseract_cmd

    processor = OcrLineProcessor(
        recent_line_limit=config.recent_line_limit,
        require_quote_like=config.require_quote_like,
    )

    print("OCR capture started. Press Ctrl+C to stop.")
    with mss_module.mss() as screen:
        while not (stop_event and stop_event.is_set()):
            shot = screen.grab(config.region)
            image = image_class.frombytes("RGB", shot.size, shot.rgb)
            text = pytesseract_module.image_to_string(image)
            for decision in processor.process_text(text):
                if decision.accepted:
                    try:
                        post_line(config.server_url, decision.line, config.request_timeout_seconds)
                        print(f"ocr posted: {decision.line}")
                    except urllib.error.URLError as exc:
                        print(f"ocr post failed: {decision.line} ({exc})")
                    continue
                if config.log_skipped:
                    print(f"ocr skipped ({decision.reason}): {decision.line}")
            if stop_event:
                stop_event.wait(config.interval_seconds)
            else:
                time.sleep(config.interval_seconds)


def load_screen_ocr_dependencies() -> tuple[Any, Any, Any]:
    try:
        import mss
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "OCR capture requires mss, pillow, and pytesseract. "
            "Install them with: pip install -r requirements-ocr.txt"
        ) from exc
    return mss, pytesseract, Image
