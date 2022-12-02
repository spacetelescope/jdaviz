# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

import bqplot
import debugpy
import glue
import glue_jupyter
import ipypopout
import photutils
import regions
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

datas = [
    (Path(sys.prefix) / "share" / "jupyter", "./share/jupyter"),
    (Path(sys.prefix) / "etc" / "jupyter", "./etc/jupyter"),
    *collect_data_files("regions"),
    *collect_data_files("photutils"),
    *collect_data_files("debugpy"),
    *collect_data_files("glue"),
    *collect_data_files("glue_jupyter"),
    *collect_data_files("bqplot"),
    *collect_data_files("jdaviz"),
    *collect_data_files("ipypopout"),
]
binaries = []
# jdaviz is not imported condinally in jdaviz-cli-entrypoint.py, so a hidden import
hiddenimports = []
hiddenimports += collect_submodules("jdaviz")
hiddenimports += collect_submodules("regions")
hiddenimports += collect_submodules("photutils")
hiddenimports += collect_submodules("jupyter_client")
tmp_ret = collect_all("astropy")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
# tmp_ret = collect_all('.')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]


block_cipher = None


a = Analysis(
    ["jdaviz-cli-entrypoint.py"],
    pathex=[],
    binaries=binaries,
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
    name="jdaviz-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    name="jdaviz-cli",
)
