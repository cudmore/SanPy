# -*- mode: python ; coding: utf-8 -*-

# we are not specifying target_arch, it gets picked up by the python interpreter

import sanpy
VERSION = sanpy.__version__

import platform
_platform = platform.machine()

binaries = None

# arm64
# /Users/cudmore/Desktop/SanPy.app/Contents/MacOS/libblosc2.2.dylib
# rename this as /Users/cudmore/opt/miniconda3/envs/sanpy-pyinstaller-arm/lib/libblosc2.dylib
# /Users/cudmore/opt/miniconda3/envs/sanpy-pyinstaller-arm/lib/libblosc2.2.8.0.dylib
#if _platform == 'arm64':
#    binaries = [('/Users/cudmore/opt/miniconda3/envs/sanpy-pyinstaller-i386/lib/python3.9/site-packages/tables/libblosc2.dylib', 'tables')]

# x86, used with 'tables'
if _platform == 'x86_64':
    binaries = [('/Users/cudmore/opt/miniconda3/envs/sanpy-pyinstaller-i386/lib/python3.9/site-packages/tables/libblosc2.dylib', 'tables')]

hiddenimports=['pkg_resources']
block_cipher = None

a = Analysis(
    ['../../sanpy/interface/sanpy_app.py'],
    # TODO: replace this with --paths
    #pathex=['/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller-i386/lib/python3.11/site-packages'],
    binaries=binaries,
    datas=[
            ('../../sanpy/_userFiles', '_userFiles'),
        ],
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

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SanPy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    # TODO: replace this with --target-arch
    #target_arch='x86_64',  # x86_64, arm64, universal2
    codesign_identity="Developer ID Application: Robert Cudmore (794C773KDS)",
    entitlements_file="entitlements.plist",
    icon='sanpy_transparent.icns',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SanPy',
)
app = BUNDLE(
    coll,
    name='SanPy.app',
    icon='sanpy_transparent.icns',
    bundle_identifier=None,
    version=VERSION,
    info_plist = {
        'CFBundleShortVersionString': VERSION,
    }
)
