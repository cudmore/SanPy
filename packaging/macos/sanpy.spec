# -*- mode: python ; coding: utf-8 -*-
# Unsigned arm64 app. Runtime assets live next to sys._MEIPASS (Contents/Frameworks).
# Icons come from sanpy/interface/icons, not pyinstaller/macos.

import re
import os
from importlib.metadata import version

from PyInstaller.utils.hooks import collect_data_files

SANPY_VERSION = version('sanpy-ephys')
ARCH = os.environ.get('SANPY_ARCH', 'arm64')
BUNDLE_ID = os.environ.get('SANPY_BUNDLE_ID', 'org.sanpy.SanPy')
MIN_MACOS_VERSION = os.environ.get('SANPY_MIN_MACOS_VERSION', '11.0')
BUILD_INFO_PATH = os.environ.get('SANPY_BUILD_INFO')
if not BUILD_INFO_PATH or not os.path.isfile(BUILD_INFO_PATH):
    raise ValueError('SANPY_BUILD_INFO must name an existing build_info.json')
version_match = re.match(r'^(\d+)\.(\d+)\.(\d+)', SANPY_VERSION)
if version_match is None:
    raise ValueError(f'Cannot convert SanPy version for macOS: {SANPY_VERSION}')
SHORT_VERSION = '.'.join(version_match.groups())
BUILD_VERSION = '.'.join(re.findall(r'\d+', SANPY_VERSION))

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
    target_arch=ARCH,
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
    bundle_identifier=BUNDLE_ID,
    version=SHORT_VERSION,
    info_plist={
        'CFBundleVersion': BUILD_VERSION,
        'LSMinimumSystemVersion': MIN_MACOS_VERSION,
        'NSPrincipalClass': 'NSApplication',
    },
)
