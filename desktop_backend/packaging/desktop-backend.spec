# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

_repo_root = Path(SPECPATH).resolve().parent.parent
_repo = str(_repo_root)
if _repo not in sys.path:
    sys.path.insert(0, _repo)

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

from desktop_backend.packaging.build_config import SIDECAR_SOURCE_PACKAGES

_entry = Path(SPECPATH) / "entrypoint.py"

hiddenimports: list[str] = []
datas: list[tuple[str, str]] = []
for pkg in SIDECAR_SOURCE_PACKAGES:
    hiddenimports.extend(collect_submodules(pkg))
    datas.extend(collect_data_files(pkg))

a = Analysis(
    [str(_entry)],
    pathex=[_repo],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="desktop-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="desktop-backend",
)
