from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .capture import InboxTailer
from .language import LanguageBook
from .parser import QuoteParser
from .store import QuoteStore


class WhiteboardApp:
    def __init__(self, root: Path):
        self.root = root
        self.static_dir = root / "static"
        self.capture_dir = root / "capture"
        self.language = LanguageBook(root / "data" / "language.json")
        self.parser = QuoteParser(self.language)
        cache_hours = int(self.language.data["parser"].get("rolling_cache_hours", 12))
        self.store = QuoteStore(root / "data" / "quotes.json", cache_hours)
        self.tailer = InboxTailer(self.capture_dir / "inbox.txt", self.ingest_raw_line)

    def start_capture(self) -> None:
        self.tailer.start()

    def ingest_raw_line(self, raw: str) -> dict[str, Any]:
        parsed = self.parser.parse(raw)
        return self.store.ingest(parsed)

    def snapshot(self) -> dict[str, Any]:
        stale_minutes = int(self.language.data["parser"].get("stale_minutes", 15))
        return self.store.snapshot(stale_minutes, self.language.data)


def make_handler(app: WhiteboardApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ElectronicWhiteboard/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/":
                self._redirect("/board")
                return
            if path == "/board":
                self._send_file(app.static_dir / "board.html")
                return
            if path == "/admin":
                self._send_file(app.static_dir / "admin.html")
                return
            if path == "/api/state":
                self._send_json(app.snapshot())
                return
            if path.startswith("/static/"):
                relative = path.removeprefix("/static/")
                self._send_file(app.static_dir / relative)
                return

            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            body = self._read_json()

            try:
                if parsed.path == "/api/ingest":
                    raw_text = str(body.get("raw", ""))
                    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
                    quotes = [app.ingest_raw_line(line) for line in lines]
                    self._send_json({"quotes": quotes})
                    return

                if parsed.path == "/api/quotes/edit":
                    quote_id = str(body.get("id", ""))
                    quote = app.store.edit(quote_id, body)
                    if not quote:
                        self._send_json({"error": "Quote not found"}, status=HTTPStatus.NOT_FOUND)
                        return
                    self._send_json({"quote": quote})
                    return

                if parsed.path == "/api/quotes/delete":
                    quote_id = str(body.get("id", ""))
                    deleted = app.store.delete(quote_id)
                    self._send_json({"deleted": deleted})
                    return

                if parsed.path == "/api/language/hubs":
                    aliases = body.get("aliases", [])
                    if isinstance(aliases, str):
                        aliases = [item.strip() for item in aliases.split(",")]
                    hub = app.language.upsert_hub(
                        code=str(body.get("code", "")),
                        name=str(body.get("name", "")),
                        aliases=aliases,
                        default_sign=str(body.get("default_sign", "unknown")),
                    )
                    app.parser = QuoteParser(app.language)
                    self._send_json({"hub": hub})
                    return
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return

            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}")

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw or "{}")

        def _redirect(self, location: str) -> None:
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", location)
            self.end_headers()

        def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _send_file(self, path: Path) -> None:
            resolved = path.resolve()
            static_root = app.static_dir.resolve()
            if static_root not in resolved.parents and resolved != static_root:
                self._send_json({"error": "Forbidden"}, status=HTTPStatus.FORBIDDEN)
                return
            if not resolved.exists() or not resolved.is_file():
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return

            content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            data = resolved.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    return Handler


def run_server(root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    app = WhiteboardApp(root)
    app.start_capture()
    handler = make_handler(app)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Electronic Whiteboard running at http://{host}:{port}/board")
    print(f"Admin screen running at http://{host}:{port}/admin")
    server.serve_forever()
