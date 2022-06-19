# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['../sanpy/interface/sanpy_app.py'],
    pathex=['/Users/cudmore/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/'],
    binaries=[],
    datas=[('/Users/cudmore/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/pyqtgraph/colors', 'pyqtgraph/colors')],
    hiddenimports=['pkg_resources', 'tables'],
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
    name='SanPy-Monterey',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../sanpy/interface/icons/sanpy_transparent.icns',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SanPy-Monterey',
)
app = BUNDLE(
    coll,
    name='SanPy-Monterey.app',
    icon='../sanpy/interface/icons/sanpy_transparent.icns',
    bundle_identifier=None,
)
