#!/usr/bin/env python3
"""PySide6 desktop app: drag-and-drop files/folders, pick an output folder,
and convert to Markdown via MarkItDown on demand (no auto-watching).

Usage:
    python main.py

Everything runs locally: no file is ever uploaded anywhere.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedLayout,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from converter import ConversionResult, convert_paths, iter_files, should_skip

APP_TITLE = "MarkItDown Converter"

STYLE_SHEET = """
QMainWindow, QWidget {
    background: #f4f5f9;
    color: #1f2430;
    font-size: 13px;
}
QGroupBox {
    background: #ffffff;
    border: 1px solid #e1e4ea;
    border-radius: 10px;
    margin-top: 20px;
    padding: 14px 14px 14px 14px;
    font-weight: 600;
    color: #414a5c;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: -4px;
    padding: 3px 8px;
    background: #f4f5f9;
    border-radius: 5px;
    color: #414a5c;
}
QLabel {
    color: #414a5c;
}
QLabel#hint {
    color: #9aa2b1;
    font-size: 13px;
}
QLabel#progressCaption {
    color: #8a93a6;
    font-size: 12px;
}
QLabel#statusLabel {
    font-weight: 600;
    padding: 4px 2px;
}
QFrame#dropZone {
    border: 2px dashed #c7cce0;
    border-radius: 10px;
    background: #fafbfd;
}
QFrame#dropZone[dragOver="true"] {
    border: 2px dashed #4f46e5;
    background: #eef0ff;
}
QListWidget {
    border: none;
    background: transparent;
    outline: none;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background: #e4e7fb;
    color: #1f2430;
}
QLineEdit {
    border: 1px solid #d8dce6;
    border-radius: 6px;
    padding: 8px 10px;
    background: #ffffff;
}
QLineEdit:read-only {
    color: #667085;
    background: #f7f8fb;
}
QPushButton {
    border: 1px solid #d8dce6;
    border-radius: 6px;
    padding: 8px 16px;
    background: #ffffff;
    color: #333a48;
}
QPushButton:hover {
    background: #f0f1f6;
}
QPushButton:pressed {
    background: #e4e6ee;
}
QPushButton:disabled {
    color: #b3b8c4;
    background: #f4f5f9;
}
QPushButton#convertBtn {
    background: #4f46e5;
    border: 1px solid #4f46e5;
    color: #ffffff;
    font-weight: 600;
    padding: 12px 16px;
    font-size: 14px;
}
QPushButton#convertBtn:hover {
    background: #4338ca;
    border-color: #4338ca;
}
QPushButton#convertBtn:pressed {
    background: #3730a3;
}
QPushButton#convertBtn:disabled {
    background: #c7c9f5;
    border-color: #c7c9f5;
    color: #ffffff;
}
QPushButton#convertBtn[mode="cancel"] {
    background: #dc2626;
    border-color: #dc2626;
}
QPushButton#convertBtn[mode="cancel"]:hover {
    background: #b91c1c;
    border-color: #b91c1c;
}
QProgressBar {
    border: 1px solid #d8dce6;
    border-radius: 6px;
    background: #eef0f5;
    text-align: center;
    height: 16px;
}
QProgressBar::chunk {
    background: #4f46e5;
    border-radius: 5px;
    margin: 0px;
}
QTextEdit#logView {
    border: 1px solid #e1e4ea;
    border-radius: 8px;
    background: #ffffff;
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 12px;
}
"""

# -- UI text (Korean) --------------------------------------------------------

TXT_WINDOW_TITLE = APP_TITLE
TXT_FILES_GROUP = "변환할 파일"
TXT_DROP_HINT = "파일이나 폴더를 여기에 끌어다 놓거나\n아래 버튼을 사용하세요"
TXT_BROWSE_FILES = "파일 선택…"
TXT_BROWSE_FOLDER = "폴더 선택…"
TXT_REMOVE_SELECTED = "선택 항목 제거"
TXT_CLEAR_ALL = "모두 지우기"
TXT_OUTPUT_GROUP = "출력 폴더"
TXT_OUTPUT_PLACEHOLDER = "변환된 .md 파일을 저장할 폴더를 선택하세요"
TXT_CHOOSE = "선택…"
TXT_CONVERT = "변환"
TXT_CANCEL = "취소"
TXT_CANCELLING = "취소 중…"
TXT_LOG_GROUP = "로그"
TXT_CONVERTING = "변환 중…"
TXT_DONE = "완료: {ok}개 변환됨, {fail}개 실패"
TXT_FATAL_STATUS = "오류로 인해 변환이 중지되었습니다."
TXT_FATAL_DIALOG = "변환 중 예기치 못한 오류가 발생했습니다:\n{message}"
TXT_DIALOG_SELECT_FILES = "변환할 파일 선택"
TXT_DIALOG_SELECT_FOLDER = "변환할 폴더 선택"
TXT_DIALOG_CHOOSE_OUTPUT = "출력 폴더 선택"
TXT_LOG_OK = "[성공]"
TXT_LOG_FAILED = "[실패]"


class DropListWidget(QListWidget):
    """A list widget that also accepts dragged-in files and folders."""

    pathsAdded = Signal(list)
    emptyChanged = Signal(bool)  # True when the queue becomes empty

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # No visible scrollbar widgets - scroll via wheel/trackpad instead.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Pixel-based (not per-row) scrolling: the default "per item" mode
        # quantizes wheel/trackpad input into whole-row jumps, which can
        # land short of the final row instead of settling exactly on it,
        # especially with many rows in a short viewport.
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._paths: list[Path] = []

    def _set_drag_over(self, active: bool) -> None:
        frame = self.parentWidget()
        if frame is not None:
            frame.setProperty("dragOver", active)
            frame.style().unpolish(frame)
            frame.style().polish(frame)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            self._set_drag_over(True)
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._set_drag_over(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_drag_over(False)
        urls = event.mimeData().urls()
        new_paths = [Path(url.toLocalFile()) for url in urls if url.toLocalFile()]
        self.add_paths(new_paths)
        event.acceptProposedAction()

    def add_paths(self, paths: list[Path]) -> None:
        added = []
        for path in paths:
            if path in self._paths:
                continue
            self._paths.append(path)
            added.append(path)
            icon = "📁" if path.is_dir() else "📄"
            self.addItem(f"{icon}  {path.name}   —   {path}")
        if added:
            self.pathsAdded.emit(added)
            self.emptyChanged.emit(False)

    def remove_selected(self) -> None:
        for item in self.selectedItems():
            row = self.row(item)
            self.takeItem(row)
            del self._paths[row]
        if not self._paths:
            self.emptyChanged.emit(True)

    def clear_all(self) -> None:
        self.clear()
        self._paths.clear()
        self.emptyChanged.emit(True)

    def paths(self) -> list[Path]:
        return list(self._paths)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.remove_selected()
        else:
            super().keyPressEvent(event)


class ConversionWorker(QObject):
    fileDone = Signal(object)  # ConversionResult
    allDone = Signal(list)  # list[ConversionResult]
    fatalError = Signal(str)

    def __init__(self, paths: list[Path], output_dir: Path):
        super().__init__()
        self.paths = paths
        self.output_dir = output_dir
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            results = convert_paths(
                self.paths,
                self.output_dir,
                progress_callback=lambda r: self.fileDone.emit(r),
                should_stop=lambda: self._stop,
            )
            self.allDone.emit(results)
        except Exception as exc:  # last-resort guard so the UI thread never dies
            self.fatalError.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(TXT_WINDOW_TITLE)
        self.resize(720, 760)

        self.output_dir: Path | None = None
        self.thread: QThread | None = None
        self.worker: ConversionWorker | None = None

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # -- Files group ---------------------------------------------------
        files_group = QGroupBox(TXT_FILES_GROUP)
        files_layout = QVBoxLayout(files_group)
        files_layout.setSpacing(10)

        drop_frame = QFrame()
        drop_frame.setObjectName("dropZone")
        drop_frame.setProperty("dragOver", False)

        self.drop_list = DropListWidget()
        self.drop_list.setMinimumHeight(180)

        self.drop_hint = QLabel(TXT_DROP_HINT)
        self.drop_hint.setObjectName("hint")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setWordWrap(True)
        self.drop_hint.setAttribute(Qt.WA_TransparentForMouseEvents)

        # StackAll keeps both widgets visible at once; the hint is set as the
        # current widget so it paints on top of the (visually empty) list.
        drop_stack = QStackedLayout(drop_frame)
        drop_stack.setStackingMode(QStackedLayout.StackAll)
        drop_stack.setContentsMargins(10, 10, 10, 10)
        drop_stack.addWidget(self.drop_list)
        drop_stack.addWidget(self.drop_hint)
        drop_stack.setCurrentWidget(self.drop_hint)

        files_layout.addWidget(drop_frame, stretch=1)

        queue_row = QHBoxLayout()
        self.browse_files_btn = QPushButton(TXT_BROWSE_FILES)
        self.browse_folder_btn = QPushButton(TXT_BROWSE_FOLDER)
        self.remove_btn = QPushButton(TXT_REMOVE_SELECTED)
        self.clear_btn = QPushButton(TXT_CLEAR_ALL)
        queue_row.addWidget(self.browse_files_btn)
        queue_row.addWidget(self.browse_folder_btn)
        queue_row.addStretch(1)
        queue_row.addWidget(self.remove_btn)
        queue_row.addWidget(self.clear_btn)
        files_layout.addLayout(queue_row)

        layout.addWidget(files_group, stretch=1)

        # -- Output group ----------------------------------------------------
        output_group = QGroupBox(TXT_OUTPUT_GROUP)
        output_layout = QHBoxLayout(output_group)
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText(TXT_OUTPUT_PLACEHOLDER)
        output_layout.addWidget(self.output_edit, stretch=1)
        self.choose_output_btn = QPushButton(TXT_CHOOSE)
        output_layout.addWidget(self.choose_output_btn)
        layout.addWidget(output_group)

        # -- Convert + progress ------------------------------------------
        self.convert_btn = QPushButton(TXT_CONVERT)
        self.convert_btn.setObjectName("convertBtn")
        self.convert_btn.setProperty("mode", "convert")
        self.convert_btn.setEnabled(False)
        self.convert_btn.setMinimumHeight(42)
        layout.addWidget(self.convert_btn)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("progressCaption")
        self.progress_label.setAlignment(Qt.AlignRight)
        self.progress_label.hide()
        layout.addWidget(self.progress_label)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)

        # -- Log group ---------------------------------------------------
        log_group = QGroupBox(TXT_LOG_GROUP)
        log_layout = QVBoxLayout(log_group)
        self.log = QTextEdit()
        self.log.setObjectName("logView")
        self.log.setReadOnly(True)
        log_layout.addWidget(self.log)
        layout.addWidget(log_group, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        self.setCentralWidget(central)

        self.browse_files_btn.clicked.connect(self.on_browse_files)
        self.browse_folder_btn.clicked.connect(self.on_browse_folder)
        self.remove_btn.clicked.connect(self.drop_list.remove_selected)
        self.clear_btn.clicked.connect(self.drop_list.clear_all)
        self.choose_output_btn.clicked.connect(self.on_choose_output)
        self.convert_btn.clicked.connect(self.on_convert_clicked)
        self.drop_list.pathsAdded.connect(lambda _paths: self.update_convert_enabled())
        self.drop_list.emptyChanged.connect(self.drop_hint.setVisible)
        self.drop_list.emptyChanged.connect(lambda _empty: self.update_convert_enabled())

    # -- queue / output selection -----------------------------------------

    def update_convert_enabled(self) -> None:
        ready = bool(self.drop_list.paths()) and self.output_dir is not None
        self.convert_btn.setEnabled(ready)

    def on_browse_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, TXT_DIALOG_SELECT_FILES)
        if files:
            self.drop_list.add_paths([Path(f) for f in files])
            self.update_convert_enabled()

    def on_browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, TXT_DIALOG_SELECT_FOLDER)
        if folder:
            self.drop_list.add_paths([Path(folder)])
            self.update_convert_enabled()

    def on_choose_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, TXT_DIALOG_CHOOSE_OUTPUT)
        if folder:
            self.output_dir = Path(folder)
            self.output_edit.setText(folder)
            self.update_convert_enabled()

    # -- conversion ----------------------------------------------------------

    def _set_convert_mode(self, mode: str) -> None:
        self.convert_btn.setProperty("mode", mode)
        self.convert_btn.style().unpolish(self.convert_btn)
        self.convert_btn.style().polish(self.convert_btn)

    def on_convert_clicked(self) -> None:
        if self.thread is not None:
            # Currently running: this click means Cancel.
            if self.worker:
                self.worker.stop()
            self.convert_btn.setEnabled(False)
            self.convert_btn.setText(TXT_CANCELLING)
            return

        paths = self.drop_list.paths()
        if not paths or self.output_dir is None:
            return

        total = sum(1 for src, _ in iter_files(paths) if not should_skip(src))

        self.log.clear()
        self.progress.setValue(0)
        self.progress.setMaximum(max(total, 1))
        self.progress_label.setText(f"0 / {total}")
        self.progress.show()
        self.progress_label.show()
        self.status_label.setText(TXT_CONVERTING)
        self.status_label.setStyleSheet("color: #414a5c;")

        self._set_controls_enabled(False)
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText(TXT_CANCEL)
        self._set_convert_mode("cancel")

        self.thread = QThread()
        self.worker = ConversionWorker(paths, self.output_dir)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.fileDone.connect(self.on_file_done)
        self.worker.allDone.connect(self.on_all_done)
        self.worker.fatalError.connect(self.on_fatal_error)
        self.worker.allDone.connect(self.thread.quit)
        self.worker.fatalError.connect(self.thread.quit)
        self.thread.finished.connect(self._cleanup_thread)
        self.thread.start()

    def on_file_done(self, result: ConversionResult) -> None:
        done = self.progress.value() + 1
        self.progress.setValue(done)
        self.progress_label.setText(f"{done} / {self.progress.maximum()}")
        source = html.escape(str(result.source))
        if result.ok:
            dest = html.escape(str(result.dest))
            self.log.append(f'<span style="color:#16a34a;">{TXT_LOG_OK}</span> {source} → {dest}')
        else:
            error = html.escape(str(result.error))
            self.log.append(f'<span style="color:#dc2626;">{TXT_LOG_FAILED}</span> {source} — {error}')

    def on_all_done(self, results: list[ConversionResult]) -> None:
        ok_count = sum(1 for r in results if r.ok)
        fail_count = len(results) - ok_count
        self.status_label.setText(TXT_DONE.format(ok=ok_count, fail=fail_count))
        self.status_label.setStyleSheet("color: #16a34a;" if fail_count == 0 else "color: #b45309;")

    def on_fatal_error(self, message: str) -> None:
        self.status_label.setText(TXT_FATAL_STATUS)
        self.status_label.setStyleSheet("color: #dc2626;")
        QMessageBox.critical(self, TXT_WINDOW_TITLE, TXT_FATAL_DIALOG.format(message=message))

    def _cleanup_thread(self) -> None:
        if self.thread:
            self.thread.deleteLater()
        self.thread = None
        self.worker = None
        self._set_controls_enabled(True)
        self.convert_btn.setText(TXT_CONVERT)
        self._set_convert_mode("convert")
        self.progress.setValue(self.progress.maximum())
        self.progress.hide()
        self.progress_label.hide()
        self.update_convert_enabled()

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.browse_files_btn.setEnabled(enabled)
        self.browse_folder_btn.setEnabled(enabled)
        self.remove_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        self.choose_output_btn.setEnabled(enabled)


def resource_path(relative: str) -> Path:
    """Resolve a bundled resource, working both from source and from a
    PyInstaller-frozen executable (which extracts data files to sys._MEIPASS)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    icon_path = resource_path("resources/icon.ico")
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
