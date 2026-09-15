#!/usr/bin/env python3
"""Watch a folder and convert any dropped-in files to Markdown using MarkItDown.

Usage:
    python watch_and_convert.py [--input INPUT_DIR] [--output OUTPUT_DIR]

Everything runs locally: no file is ever uploaded anywhere.
"""

import argparse
import sys
import time
from pathlib import Path

from markitdown import MarkItDown
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Files matching these are ignored (partial downloads, lock files, OS cruft).
IGNORED_PREFIXES = ("~$", ".~", ".")
IGNORED_SUFFIXES = (".tmp", ".crdownload", ".part", ".md")

# How long a file's size must stay unchanged before we treat it as
# "done writing" and safe to convert (handles slow copies/cloud syncs).
STABLE_CHECK_INTERVAL = 0.5
STABLE_CHECK_ROUNDS = 3


def should_skip(path: Path) -> bool:
    name = path.name
    if name.startswith(IGNORED_PREFIXES):
        return True
    if name.lower().endswith(IGNORED_SUFFIXES):
        return True
    return False


def wait_until_stable(path: Path) -> bool:
    """Poll file size until it stops changing. Returns False if the file disappeared."""
    last_size = -1
    stable_rounds = 0
    while stable_rounds < STABLE_CHECK_ROUNDS:
        if not path.exists():
            return False
        size = path.stat().st_size
        if size == last_size:
            stable_rounds += 1
        else:
            stable_rounds = 0
            last_size = size
        time.sleep(STABLE_CHECK_INTERVAL)
    return True


class ConversionHandler(FileSystemEventHandler):
    def __init__(self, input_dir: Path, output_dir: Path, converter: MarkItDown):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.converter = converter

    def on_created(self, event):
        if not event.is_directory:
            self.convert(Path(event.src_path))

    def on_modified(self, event):
        if not event.is_directory:
            self.convert(Path(event.src_path))

    def convert(self, src: Path) -> None:
        if should_skip(src):
            return
        if not wait_until_stable(src):
            return  # file was removed/renamed before it settled

        rel = src.relative_to(self.input_dir)
        dest = (self.output_dir / rel).with_suffix(".md")
        if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
            return  # already converted and up to date (avoids double-firing on created+modified)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = self.converter.convert(str(src))
        except Exception as exc:
            print(f"[FAILED]  {rel} -> {exc}")
            return

        dest.write_text(result.text_content, encoding="utf-8")
        print(f"[OK]      {rel} -> {dest.relative_to(self.output_dir)}")


def convert_existing(input_dir: Path, output_dir: Path, converter: MarkItDown) -> None:
    """Catch up on any files already sitting in the input folder."""
    for src in sorted(input_dir.rglob("*")):
        if src.is_dir() or should_skip(src):
            continue
        rel = src.relative_to(input_dir)
        dest = (output_dir / rel).with_suffix(".md")
        if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
            continue  # already converted and up to date
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = converter.convert(str(src))
        except Exception as exc:
            print(f"[FAILED]  {rel} -> {exc}")
            continue
        dest.write_text(result.text_content, encoding="utf-8")
        print(f"[OK]      {rel} -> {dest.relative_to(output_dir)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    script_dir = Path(__file__).resolve().parent
    parser.add_argument("--input", type=Path, default=script_dir / "input")
    parser.add_argument("--output", type=Path, default=script_dir / "output")
    args = parser.parse_args()

    input_dir = args.input.resolve()
    output_dir = args.output.resolve()
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = MarkItDown()

    print(f"Watching:  {input_dir}")
    print(f"Output to: {output_dir}")
    print("Converting existing files...")
    convert_existing(input_dir, output_dir, converter)

    handler = ConversionHandler(input_dir, output_dir, converter)
    observer = Observer()
    observer.schedule(handler, str(input_dir), recursive=True)
    observer.start()
    print("Watching for new files. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped.")
    observer.join()


if __name__ == "__main__":
    sys.exit(main())
