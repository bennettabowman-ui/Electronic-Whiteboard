# Electronic Whiteboard MVP

Local Windows-friendly MVP for turning fast natural-gas broker chat quotes into a shared TV whiteboard.

## Set Up On A Windows Work Computer

Install Python 3.11 or newer, then clone the private GitHub repo:

```powershell
git clone https://github.com/bennettabowman-ui/Electronic-Whiteboard.git
cd Electronic-Whiteboard
```

The core whiteboard uses only Python's standard library. You can run it directly:

```powershell
python run.py
```

Then open:

- TV board: http://127.0.0.1:8765/board
- Admin/corrections: http://127.0.0.1:8765/admin

Optional virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python run.py
```

## Run

```powershell
python run.py
```

Open:

- TV board: http://127.0.0.1:8765/board
- Admin/corrections: http://127.0.0.1:8765/admin

## Ingest Quotes

For the MVP, quotes can enter the system two ways:

1. Paste one or more raw chat lines into the admin page.
2. Append lines to `capture/inbox.txt`; the server watches that file and ingests new lines.

Example:

```text
Jv27 HSC 22/21 1/2 day
```

The seeded language file interprets that as Houston Ship Channel, Summer 2027, bid -22 / offer -21, size `1/2 day`.

## OCR Capture

`tools/ocr_capture.py` is an optional adapter for a locked ICE chat window region. It requires extra local dependencies and a native Tesseract install:

```powershell
pip install -r requirements-ocr.txt
```

Copy `capture/ocr_config.example.json` to `capture/ocr_config.json`, set the screen region, start `python run.py`, then run:

```powershell
python tools/ocr_capture.py
```

The adapter posts newly recognized OCR lines to the local server. Keep this off until compliance/IT approves screen capture on the ICE workstation.

## Language File

The parser is driven by `data/language.json`. It contains:

- month and strip codes
- hub names and aliases
- per-hub basis sign defaults
- stale and cache settings

The admin page can add or update hub aliases without editing JSON manually.
