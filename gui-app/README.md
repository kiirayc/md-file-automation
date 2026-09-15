# MarkItDown Converter (GUI app)

A Windows desktop app for converting documents (PDF, DOCX, PPTX, XLSX, images, etc.) to Markdown using Microsoft's [MarkItDown](https://github.com/microsoft/markitdown). Everything happens locally — no file is ever uploaded anywhere.

Unlike the [legacy CLI watcher](../watch_and_convert.py) in the repo root, this app does **not** auto-start or watch a folder in the background. You open it, drag in the files or folders you want converted (or use the Browse buttons), choose an output folder, and click **Convert**.

## Run from source

```bash
python -m venv .venv
# macOS/Linux:
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
# Windows:
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\python.exe main.py
```

## Build a standalone Windows .exe

Must be built **on a Windows machine** (or a Windows CI runner, e.g. GitHub Actions `windows-latest`) — PyInstaller does not cross-compile, so a build produced on macOS/Linux will not run on Windows.

```bash
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\pyinstaller.exe build.spec
```

The executable is written to `dist/MarkItDownConverter/MarkItDownConverter.exe`.

### Known build pitfalls

- **Missing markitdown submodules at runtime**: `build.spec` already calls `collect_submodules("markitdown")`, but some of `markitdown[all]`'s optional per-format dependencies (pdfminer, python-docx/pptx, openpyxl, pandas, etc.) may still be imported in a way PyInstaller's static scan misses. If the built exe raises `ModuleNotFoundError` on a particular file type, add that module to `hiddenimports` in `build.spec` and rebuild.
- **Missing data files**: some libraries ship non-`.py` data (e.g. magic-byte detection databases). This tends to fail silently (wrong file-type detection) rather than crash. If a specific format misbehaves only in the built exe, add `collect_data_files("<library>")` to `datas` in `build.spec`.
- **PySide6 "no Qt platform plugin" error**: this can happen in `--onefile` mode if the `platforms` Qt plugin (`qwindows.dll`) isn't bundled. `build.spec` currently builds in `--onedir` mode (the default for the `EXE`/`COLLECT`-less spec above) which avoids this; if you switch to a single-file build, verify `qwindows.dll` is present in the output before distributing.
- **Icon**: drop a real `.ico` file at `gui-app/resources/icon.ico` (before building, or before running from source). It's picked up automatically for both the `.exe` file icon (what shows in File Explorer/Start Menu/taskbar for the built executable) and the in-app window icon (title bar, Alt+Tab) — no other changes needed. Without it, the app falls back to the default PyInstaller/Qt icon. A `.ico` can hold multiple sizes (16/32/48/256px); an online "PNG to ICO" converter or ImageMagick (`magick convert logo.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico`) both work.
- **Windows Defender/SmartScreen**: an unsigned PyInstaller exe will likely be flagged on first run internally ("Windows protected your PC"). This is expected for an unsigned internal tool — users click "More info" → "Run anyway". Code-signing is out of scope for this build.
- Build `--onedir` first while iterating (faster, and you can inspect what got bundled); only move to `--onefile` once you've confirmed no missing imports/data.

## Testing

```bash
pip install pytest
pytest tests/
```

## Notes

- OCR/text extraction on scanned (image-only) PDFs can be unreliable. Spot-check the first few conversions of scanned documents.
- Dropping a folder preserves its internal subfolder structure under the chosen output folder. Dropping loose files places them directly in the output folder.
- A failed conversion for one file (corrupt/unsupported document) is logged and skipped — it does not stop the rest of the batch or crash the app.
