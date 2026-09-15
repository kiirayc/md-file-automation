from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from converter import ConversionResult, convert_paths, iter_files, should_skip


@pytest.mark.parametrize(
    "name,expected",
    [
        ("~$notes.docx", True),
        (".hidden.txt", True),
        (".DS_Store", True),
        ("draft.tmp", True),
        ("partial.crdownload", True),
        ("already.md", True),
        ("report.pdf", False),
        ("contract.docx", False),
    ],
)
def test_should_skip(name, expected):
    assert should_skip(Path(name)) is expected


def test_iter_files_loose_files_use_own_parent(tmp_path):
    file_a = tmp_path / "a.txt"
    file_a.write_text("a")
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    file_b = other_dir / "b.txt"
    file_b.write_text("b")

    pairs = iter_files([file_a, file_b])

    assert (file_a, tmp_path) in pairs
    assert (file_b, other_dir) in pairs


def test_iter_files_folder_preserves_relative_structure(tmp_path):
    folder = tmp_path / "docs"
    (folder / "sub").mkdir(parents=True)
    top_file = folder / "top.txt"
    nested_file = folder / "sub" / "nested.txt"
    top_file.write_text("top")
    nested_file.write_text("nested")

    pairs = iter_files([folder])

    assert (top_file, folder) in pairs
    assert (nested_file, folder) in pairs


def test_convert_paths_success(tmp_path):
    src = tmp_path / "input"
    src.mkdir()
    text_file = src / "note.txt"
    text_file.write_text("hello world")
    output = tmp_path / "output"

    seen = []
    results = convert_paths([text_file], output, progress_callback=seen.append)

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, ConversionResult)
    assert result.ok is True
    assert result.dest == output / "note.md"
    assert result.dest.read_text(encoding="utf-8").strip() == "hello world"
    assert seen == results


def test_convert_paths_failure_does_not_raise(tmp_path):
    src = tmp_path / "input"
    src.mkdir()
    # MarkItDown has a plain-text fallback for most inputs (arbitrary bytes
    # with an unrecognized extension "succeed" as text), so a genuine failure
    # needs a format-specific converter to choke: binary garbage with a .pdf
    # extension makes the PDF converter raise a real parsing error.
    bad_file = src / "broken.pdf"
    bad_file.write_bytes(b"\x00\x01\x02\xff\xfe not a real pdf \x00\x00")
    output = tmp_path / "output"

    results = convert_paths([bad_file], output)

    assert len(results) == 1
    assert results[0].ok is False
    assert results[0].error is not None


def test_convert_paths_should_stop_halts_batch(tmp_path):
    src = tmp_path / "input"
    src.mkdir()
    files = []
    for i in range(3):
        f = src / f"file{i}.txt"
        f.write_text(f"content {i}")
        files.append(f)
    output = tmp_path / "output"

    call_count = 0

    def should_stop():
        nonlocal call_count
        call_count += 1
        return call_count > 1

    results = convert_paths(files, output, should_stop=should_stop)

    assert len(results) < len(files)
