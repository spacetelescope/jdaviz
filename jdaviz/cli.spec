# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('..\\envmain\\Lib\\site-packages\\glue', 'glue\\'), ('..\\envmain\\Lib\\site-packages\\glue_jupyter\\', 'glue_jupyter\\'), ('..\\envmain\\Lib\\site-packages\\bqplot\\', 'bqplot\\'), ('..\\envmain\\Lib\\site-packages\\regions\\CITATION.rst', 'regions\\'), ('.\\components\\', 'jdaviz\\components'), ('.\\configs\\', 'jdaviz\\configs'), ('.\\container.vue', 'jdaviz\\'), ('.\\data\\', 'jdaviz\\data'), ('..\\envmain\\Lib\\site-packages\\photutils\\CITATION.rst', 'photutils'), ('..\\envmain\\Lib\\site-packages\\debugpy\\_vendored\\', 'debugpy\\_vendored'), ('..\\share\\', 'share\\')]
binaries = []
hiddenimports = []
hiddenimports += collect_submodules('regions')
hiddenimports += collect_submodules('photutils')
hiddenimports += collect_submodules('jupyter_client')
tmp_ret = collect_all('astropy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('.')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


block_cipher = None


a = Analysis(
    ['cli.py'],
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
    name='cli',
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
    name='cli',
)
