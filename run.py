from __future__ import annotations

from pathlib import Path

from app.server import run_server


if __name__ == "__main__":
    run_server(Path(__file__).resolve().parent)
