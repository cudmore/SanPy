# -*- mode: python ; coding: utf-8 -*-
# Unsigned arm64 app. Runtime assets live next to sys._MEIPASS (Contents/Frameworks).
# Icons come from sanpy/interface/icons, not pyinstaller/macos.

a = Analysis(
    ['../../sanpy/interface/sanpy_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../../sanpy/interface/icons/sanpy_transparent.png', '.'),
        ('../../sanpy/detection-presets', 'detection-presets'),
        ('../../sanpy/_userFiles', '_userFiles'),
    ],
    hiddenimports=['numpy.core.multiarray'],
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
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
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

app = BUNDLE(
    coll,
    name='SanPy.app',
    icon='../../sanpy/interface/icons/sanpy_transparent.icns',
    bundle_identifier=None,
)
