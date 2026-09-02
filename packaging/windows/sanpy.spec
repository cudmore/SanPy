# -*- mode: python ; coding: utf-8 -*-
# Windows one-directory build. Add hidden imports or binaries only when a
# Windows build demonstrates that PyInstaller's standard hooks need help.

import os


BUILD_INFO_PATH = os.environ.get('SANPY_BUILD_INFO')
if not BUILD_INFO_PATH or not os.path.isfile(BUILD_INFO_PATH):
    raise ValueError('SANPY_BUILD_INFO must name an existing build_info.json')

a = Analysis(
    ['../../sanpy/interface/sanpy_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../../sanpy/interface/icons/sanpy_transparent.png', '.'),
        ('../../sanpy/detection-presets', 'detection-presets'),
        ('../../sanpy/_userFiles', '_userFiles'),
        (BUILD_INFO_PATH, 'sanpy'),
    ],
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
    [],
    exclude_binaries=True,
    name='SanPy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SanPy',
)
