# -*- mode: python ; coding: utf-8 -*-

import sys

block_cipher = None


a = Analysis(['sanpy/sanpy_app.py'],
             pathex=['/Users/cudmore/Sites/SanPy'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='sanpy_app',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='sanpy_app')

# Package the executable file into .app if on OS X
if sys.platform == 'darwin':
	app = BUNDLE(exe,
			name='SanPy.app',
			info_plist={
			'NSHighResolutionCapable': 'True'
			},
			icon=None)
			#},
			#icon='assets/icon.icns')
