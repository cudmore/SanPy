# -*- mode: python -*-

block_cipher = None


a = Analysis(['AnalysisApp.py'],
             pathex=['/Users/cudmore/Sites/bAnalysis/spike-analysis-app/src'],
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
          name='SpikeAnalysis',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False , icon='icons/videoapp.icns')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='SpikeAnalysis')
app = BUNDLE(coll,
             name='SpikeAnalysis.app',
             icon='icons/videoapp.icns',
             bundle_identifier=None)
