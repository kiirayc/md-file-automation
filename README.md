# md-file-automation

Local file watcher that auto-converts dropped documents (PDF, DOCX, PPTX, XLSX, images, etc.) into Markdown using Microsoft's [MarkItDown](https://github.com/microsoft/markitdown). No cloud upload, runs automatically at login.

Everything happens on your own machine. Files never leave it, which matters if you're converting confidential or privileged documents.

## Two ways to use this repo

- **[GUI app](gui-app/)** (recommended) — a Windows desktop app with drag-and-drop. Drop in files/folders, choose an output folder, click Convert. No auto-start, nothing runs in the background. See [`gui-app/README.md`](gui-app/README.md).
- **Legacy CLI watcher** (below) — the original background script that auto-converts anything dropped into a fixed `input/` folder and can auto-start at login. Unchanged, still supported.

## Use case

Built for practicing lawyers to automate their document-prep workflow: legal documents (case files, contracts, filings) get converted to Markdown automatically so Claude can efficiently read through them and answer legal queries, without any manual conversion step or file leaving the lawyer's machine.

**Results:** reduced document-prep time by **40%**, measured through end-user testing with real case files.

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
