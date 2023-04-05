# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_dynamic_libs

# added april 4, 2023. tables was in the wrong folder and could not notarize with apple
binaries = []
binaries += collect_dynamic_libs('tables')

print('xxx got binaries:')
for _binary in binaries:
    print('  ', _binary)

# for conda env
#binaries = [('/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/libblosc2.dylib', 'tables')]
# for venv
#binaries = [('/Users/cudmore/Sites/SanPy/pyinstaller/monterey/sanpy_env_pyinstaller/lib/python3.9/site-packages/tables/libblosc2.dylib', 'tables')]
binaries = [('sanpy_env_pyinstaller/lib/python3.9/site-packages/tables/libblosc2.dylib', 'tables')]
print('2 xxx got binaries:')
for _binary in binaries:
    print('  ', _binary)

# maybe use this
# datas, binaries, hiddenimports = collect_all('my_module_name')

# april 4, 2023, was this
#hiddenimports=['pkg_resources', 'tables']
#hiddenimports=['pkg_resources']
# ading appdirs for venv
hiddenimports=['pkg_resources', 'tables', 'appdirs']

block_cipher = None

# TODO: start using pyinstaller Tree
#extras_toc = Tree('../sanpy/_userFiles', prefix='_userFiles', excludes=['.DS_Store'])
#print('extras_toc')
#print(extras_toc)

a = Analysis(
    ['../../sanpy/interface/sanpy_app.py'],
    #pathex=['/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/'],
    pathex=['sanpy_env_pyinstaller/lib/python3.9/site-packages'],
    binaries=binaries,
    datas=[
            # ('/Users/cudmore/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/pyqtgraph/colors', 'pyqtgraph/colors'),
            # removed april 4, 2023
            #('/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/libblosc2.dylib', 'tables'),
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
    target_arch=universal2,
    codesign_identity=None,  #"Developer ID Application: Robert Cudmore (794C773KDS)",
    entitlements_file=None,
    icon='../../sanpy/interface/icons/sanpy_transparent.icns',
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
    icon='../../sanpy/interface/icons/sanpy_transparent.icns',
    bundle_identifier=None,
)
