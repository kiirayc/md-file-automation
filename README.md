# md-file-automation

Local file watcher that auto-converts dropped documents (PDF, DOCX, PPTX, XLSX, images, etc.) into Markdown using Microsoft's [MarkItDown](https://github.com/microsoft/markitdown). No cloud upload, runs automatically at login.

Everything happens on your own machine. Files never leave it, which matters if you're converting confidential or privileged documents.

## How it works

Drop a file into `input/` and its Markdown version appears in `output/` within a couple of seconds. Subfolder structure is preserved. Already-converted files are skipped on restart unless the source changed.

## Setup

### macOS

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -u watch_and_convert.py
```

To have it start automatically at login, see the LaunchAgent setup (`~/Library/LaunchAgents/com.student.md-file-generator.plist`). Not included in this repo since it's machine-specific. Logs go to `logs/watcher.log` / `logs/watcher.err`.

### Windows

1. Install Python from [python.org](https://python.org). Check **"Add python.exe to PATH"** during setup.
2. Double-click `windows/install_windows.bat`.
3. Double-click `windows/setup_autostart.bat` to run it automatically on every login (via Windows Task Scheduler).

## Notes

- OCR/text extraction on scanned (image-only) PDFs can be unreliable. Spot-check the first few conversions of scanned documents.
- Requires Python 3.10+.
