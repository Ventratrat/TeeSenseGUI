# -*- mode: python ; coding: utf-8 -*-


import os

data_files = []
data_dir = r'C:\Users\tayta\Documents\TeeSenseGUI-main2\TeeSenseGUI-main2\TeeSenseGUI-main2\TeeSenseGUI-main\data'

for root, dirs, files in os.walk(data_dir):
    for file in files:
        data_files.append((os.path.join(root, file), 'data'))

a = Analysis(
    ['dataCollect.py'],
    pathex=[r'C:\Users\tayta\Documents\TeeSenseGUI-main2\TeeSenseGUI-main2\TeeSenseGUI-main2\TeeSenseGUI-main'],
    binaries=[],
    datas=data_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='dataCollect',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
