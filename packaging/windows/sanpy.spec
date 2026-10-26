# -*- mode: python ; coding: utf-8 -*-
# Windows one-file build. Add hidden imports or binaries only when a
# Windows build demonstrates that PyInstaller's standard hooks need help.

import os

from PyInstaller.utils.hooks import collect_data_files


BUILD_INFO_PATH = os.environ.get('SANPY_BUILD_INFO')
if not BUILD_INFO_PATH or not os.path.isfile(BUILD_INFO_PATH):
    raise ValueError('SANPY_BUILD_INFO must name an existing build_info.json')

datas = [
    ('../../sanpy/interface/icons/sanpy_transparent.png', '.'),
    ('../../sanpy/detection-presets', 'detection-presets'),
    ('../../sanpy/user_files', 'user_files'),
    (BUILD_INFO_PATH, 'sanpy'),
]
# hdmf and pynwb load schema YAML with os.path.exists at import time.
datas += collect_data_files('hdmf', includes=['**/*.yaml', '**/*.json'])
datas += collect_data_files('pynwb', includes=['**/*.yaml', '**/*.json'])

a = Analysis(
    ['../../sanpy/interface/sanpy_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    name='SanPy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
