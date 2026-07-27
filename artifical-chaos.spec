# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build recipe for Artificial Chaos.

    pyinstaller artifical-chaos.spec --noconfirm

Produces a onedir bundle in ``dist/artifical-chaos/`` whose launcher is
``artifical-chaos`` (``artifical-chaos.exe`` on Windows). onedir is preferred
over onefile for a game: startup is instant (no per-launch temp extraction)
and the assets stay browsable next to the executable.

The ``assets/`` tree is bundled as data and unpacked to the bundle root
(``sys._MEIPASS``); ``__main__.py``'s startup ``os.chdir`` (frozen builds
only -- see its comment) makes every cwd-relative asset path resolve there,
exactly as it resolves against the repo root when run from source.
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821 — injected by PyInstaller

# The only runtime data tree the game loads by relative path (no config/
# folder in this project -- see CLAUDE.md's "plain constants" note).
datas = [
    (str(ROOT / "assets"), "assets"),
]

# Optional per-OS application icon. This project has no logo asset yet
# (unlike chokepoint's scripts/make_icon.py) -- absent icons are fine, the
# build just uses the default. Drop packaging/icon.ico / icon.icns here
# later if that changes.
icon = None
if sys.platform.startswith("win") and (ROOT / "packaging" / "icon.ico").exists():
    icon = str(ROOT / "packaging" / "icon.ico")
elif sys.platform == "darwin" and (ROOT / "packaging" / "icon.icns").exists():
    icon = str(ROOT / "packaging" / "icon.icns")

a = Analysis(
    ["__main__.py"],
    pathex=[str(ROOT / "src"), str(ROOT / "src" / "pygame_core")],
    binaries=[],
    datas=datas,
    # pytmx's pygame loader is imported through a string in the base tilemap;
    # pin both so the module graph can't miss them.
    hiddenimports=["pytmx", "pytmx.util_pygame"],
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
    [],
    exclude_binaries=True,
    name="artifical-chaos",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="artifical-chaos",
)

# On macOS, also wrap the onedir bundle as a .app for a native double-click.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Artificial Chaos.app",
        icon=icon,
        bundle_identifier="com.umutcanekinci.artificalchaos",
    )
