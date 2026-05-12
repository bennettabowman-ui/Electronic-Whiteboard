from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable


class InboxTailer:
    def __init__(self, path: Path, on_line: Callable[[str], None], interval_seconds: float = 0.5):
        self.path = path
        self.on_line = on_line
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._thread = threading.Thread(target=self._run, name="inbox-tailer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        with self.path.open("r", encoding="utf-8") as handle:
            handle.seek(0, 2)
            while not self._stop.is_set():
                line = handle.readline()
                if not line:
                    time.sleep(self.interval_seconds)
                    continue
                clean_line = line.strip()
                if clean_line:
                    self.on_line(clean_line)
