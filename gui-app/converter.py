"""Conversion core shared by the GUI app. No GUI/Qt imports here on purpose,
so this module can be unit-tested headlessly and reused elsewhere.

Mirrors the conversion behavior of the root watch_and_convert.py script:
same skip rules, same relative-path/.md-suffix logic, same MarkItDown call
with per-file error handling that never raises out of a batch.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from markitdown import MarkItDown

# Files matching these are ignored (partial downloads, lock files, OS cruft).
IGNORED_PREFIXES = ("~$", ".~", ".")
IGNORED_SUFFIXES = (".tmp", ".crdownload", ".part", ".md")

# A dropped file can still be mid-copy (cloud-sync placeholder, network
# share, browser download). Poll its size briefly before converting.
STABLE_CHECK_INTERVAL = 0.2
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


def iter_files(paths: Iterable[Path]) -> list[tuple[Path, Path]]:
    """Expand a mixed list of files/folders into (src_file, base_dir) pairs.

    A loose file's base_dir is its own parent, so it lands flat in the
    output root. A folder's base_dir is itself, walked recursively, so its
    internal subfolder structure is mirrored under the output folder.
    """
    pairs: list[tuple[Path, Path]] = []
    for path in paths:
        if path.is_dir():
            for src in sorted(path.rglob("*")):
                if src.is_file():
                    pairs.append((src, path))
        elif path.is_file():
            pairs.append((path, path.parent))
    return pairs


@dataclass
class ConversionResult:
    source: Path
    dest: Path | None
    ok: bool
    error: str | None = None


def convert_paths(
    paths: Iterable[Path],
    output_dir: Path,
    progress_callback: Callable[[ConversionResult], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[ConversionResult]:
    """Convert files/folders in `paths` into `output_dir`.

    Preserves relative structure for folder drops (see iter_files). Never
    raises for a single file's failure - each failure is captured as a
    ConversionResult with ok=False, matching the CLI's try/except-and-
    continue behavior. Calls progress_callback(result) after every file so
    a caller (e.g. the GUI) can update incrementally, and polls
    should_stop() between files to support cancellation.
    """
    converter = MarkItDown()
    results: list[ConversionResult] = []

    for src, base_dir in iter_files(paths):
        if should_stop and should_stop():
            break
        if should_skip(src):
            continue

        rel = src.relative_to(base_dir)
        dest = (output_dir / rel).with_suffix(".md")

        if not wait_until_stable(src):
            res = ConversionResult(src, None, False, "file disappeared before it settled")
            results.append(res)
            if progress_callback:
                progress_callback(res)
            continue

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            text = converter.convert(str(src)).text_content
            dest.write_text(text, encoding="utf-8")
            res = ConversionResult(src, dest, True)
        except Exception as exc:
            res = ConversionResult(src, None, False, str(exc))

        results.append(res)
        if progress_callback:
            progress_callback(res)

    return results
