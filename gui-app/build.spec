# PyInstaller spec for the MarkItDown Converter GUI app.
#
# Build (on Windows, from the gui-app/ directory):
#     pyinstaller build.spec
#
# Output: dist/MarkItDownConverter/MarkItDownConverter.exe (onedir) or
# dist/MarkItDownConverter.exe (onefile, once EXE(..., a.binaries, ...) below
# is switched to onefile mode - see gui-app/README.md for the full build notes
# and known pitfalls, e.g. missing markitdown hidden imports and the PySide6
# onefile Qt-platform-plugin issue).

import os

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules("markitdown")
datas = collect_data_files("markitdown")

_icon_path = os.path.join(os.path.dirname(os.path.abspath(SPEC)), "resources", "icon.ico")
icon = _icon_path if os.path.isfile(_icon_path) else None
if icon:
    # Bundle the icon file itself too, so the running app can also set it
    # as the window/taskbar icon at runtime (separate from the .exe's own
    # file icon set via the `icon=` argument to EXE(...) below).
    datas.append((_icon_path, "resources"))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MarkItDownConverter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=icon,
)
