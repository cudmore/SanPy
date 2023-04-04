## Making a Windows executable with pyinstaller
Creates SanPy.exe. Currently working on Windows 10. Have not tested on Windows 11.

##  Install Conda/Python
Install conda to run pyinstaller and its packages. Miniconda works well since it is a smaller base version of conda and does not include unnecessary packages.
You can install it here at: https://docs.conda.io/en/latest/miniconda.html.

## Install SanPy from source code

```
git clone https://github.com/cudmore/SanPy.git
```

## Setup Environment 
```
# This creates environment in location: C:\Users\johns\miniconda3\envs\sanpy-env-pyinstaller 

conda create -y -n sanpy-env-pyinstaller python=3.9

conda activate sanpy-env-pyinstaller

# Cd into Sanpy directory 

cd SanPy

pip install -e .[gui]

# On windows we need the extra step of installing curses
# I believe this is because  linux/mac versions of python automatically 
# have it but windows do not 

pip install windows-curses

```


## .Spec file that is ran to create executable

```
# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['..\\sanpy\\interface\\sanpy_app.py'],
    pathex=['C:\\Users\\johns\\miniconda3\\envs\\sanpy-env-pyinstaller\\Lib\\site-packages\\'],
    binaries=[],
    datas=[('C:\\Users\\johns\\miniconda3\\envs\\sanpy-env-pyinstaller\\Lib\\site-packages\\tables\\libblosc2.dll', 'tables'),
        ('../sanpy/_userFiles','_userFiles')],
    hiddenimports=['tables', 'pkg_resources'],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SanPy',
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
    icon='..\\sanpy\\interface\\icons\\sanpy_transparent.icns',
)

```

Changing the line of ```console=True``` to ```console=False``` inside the script will remove the terminal console that shows errors. For later distribution we will need to set ```console=False``` so that users do not have to see the console.

Modify path lines to include your user directories by replacing "johns" to run this .spec file on your own system

Run command ```pyinstaller --noconfirm --clean pyinstaller-windows10.spec``` in commandline to create the executable

Executable can be found in .../sanpy/pyinstaller/dist/

Executable can be ran by double clicking the .exe or by using the commandline: cd into the directory of the executable and use the command: ```start SanPy.exe```
