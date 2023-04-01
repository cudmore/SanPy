
## PyInstaller Workflow, Mar 30, 2023

1) Create and activate a fresh conda environment

This is required because if you use an old and bloated conda environment then the size of the built application gets huge. On macOS Monteray, my built app is ~366 MB.

```
conda create -y -n sanpy-env-pyinstaller python=3.9
conda activate sanpy-env-pyinstaller    
```

2) install pyinstaller

```
pip install pyinstaller
```

3) Clone and install SanPy from source

```
git clone git@github.com:cudmore/SanPy.git
```

If that does not work, try

```
git clone https://github.com/cudmore/SanPy.git
```

```
cd SanPy
pip install .[gui]
```

On newer macOS, zsh shell in general, you need some quotes

```
pip install ".[gui]"
```

4) Run SanPy to make sure it works.

This is critical because if it fails here, it will not work when bundled.

You should click around in the interface a bit, open some plugins, etc.

Try and 'Load Folder' from the included `Sanpy/data`.

```
sanpy
```

5) Build with a modified pyinstaller spec file

I am using a hand modified spec file, `mocos-monterey-arm64.spec`.

```
pyinstaller --noconfirm --clean macos-monterey-arm64.spec
```

For Windows, make a copy of this spec file and tailor it to windows. In that new file, you have to get the windows paths correct, like this

```
/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/libblosc2.dylib
```

6) First run of bundled app or exe

I first run the app from the macOS app folder (use 'show package contents'). This way I get a command prompt with the logs and is easy to troubleshoot.

If the app in general fails to run, you need to figure out how to run it and be able to see the console logging output on Windows.

## Using create-dmg

Got this working but when I put it in a GitHub Release and then download the dmg, I get

```
... is damaged and can't be opened. You should move it to the Trash.
```

I can easily fix this with the following ... but the whole point of making an app or a dmg was so the end user would not have to use the command line. Uggghhhh.

```
xattr -cr /Applications/SanPy-Monterey.app
```

Monterey is macOS 12.4

Need to use codesign, how to pay to become a macOS developer?

https://github.com/create-dmg/create-dmg

General usage is

```
create-dmg [options ...] <output_name.dmg> <source_folder>
```

See my script that seems to work `build-dmg.sh`

See a tutorial here:
    https://www.pythonguis.com/tutorials/packaging-pyqt5-applications-pyinstaller-macos-dmg/


Still is corrupt after putting up on GitHub release?

## How do we codesign or notarize an app and a dmg ???

Briefcase has a pretty good recipe on codesign

https://briefcase.readthedocs.io/en/stable/how-to/code-signing/macOS.html


### Test the dmg

```
(base) cudmore pyinstaller:spctl -a -vvv /Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.dmg

/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.dmg: rejected
source=no usable signature
```

Test the app installed from the dmg

```
(base) cudmore pyinstaller:spctl -a -v /Applications/SanPy-Monterey.app
/Applications/SanPy-Monterey.app: code has no resources but signature indicates they must be present
```

```
(base) cudmore pyinstaller:spctl -a -t open --context context:primary-signature -v /Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.dmg

/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.dmg: rejected
source=no usable signature
```

```
spctl -a -t open --context context:primary-signature -v /Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.dmg

# yields
/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-Monterey.dmg: rejected
source=no usable signature
```

## Trying to use codesign

```
codesign -f -o runtime --timestamp -s "robert.cudmore@gmail.com: Robert Cudmore" /Applications/SanPy-Monterey.app
```

```
codesign -dv -r- /Applications/SanPy-Monterey.app

# gives
(base) cudmore pyinstaller:codesign -dv -r- /Applications/SanPy-Monterey.app

Executable=/Applications/SanPy-Monterey.app/Contents/MacOS/SanPy-Monterey
Identifier=SanPy-Monterey-555549441f738c84b5623e6891857c4a489d2a4f
Format=app bundle with Mach-O thin (x86_64)
CodeDirectory v=20400 size=115024 flags=0x2(adhoc) hashes=3588+2 location=embedded
Signature=adhoc
Info.plist=not bound
TeamIdentifier=not set
Sealed Resources=none
# designated => cdhash H"35dd62ef6d0dcc8411bcf7ba2d4af88c7d310db0"
```

## 20230316

On M1 macOS laptop (Monteray, 12.4), build from a premade spec `macos-monterey-arm64.spec`.

```
conda create -y -n sanpy-env-pyinstaller python=3.9
conda activate sanpy-env-pyinstaller

pip install -e .

cd pyinstaller
./build-from-spec.sh
```

Having problems with tables package. pyinstaller is not bundling libblosc2.dylib

Solved by manually copying this file into bundled macos app

/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/libblosc2.dylib

added this to my macos-arm.spec

```
    datas=[
            #('/Users/cudmore/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/pyqtgraph/colors', 'pyqtgraph/colors'),
            ('/Users/cudmore/opt/miniconda3/envs/sanpy-env-pyinstaller/lib/python3.9/site-packages/tables/libblosc2.dylib, 'tables'),
            ('../sanpy/_userFiles', '_userFiles')],
```

Now is failing with skimage

"Cannot load imports from non-existent stub", problem was introduces with skimage 0.20.0


## Making a macOS app with pyinstaller

Each SanPy.app is specific to the exact OS. We have working version for macOS Catalina and Big Sur. Both Microsoft windows and Ubuntu versions are in the works.

pyinstaller is very particular about how Python and its packages are installed. On macOS it does not work with Python downloaded from `python.org` and seems to be difficult with Python installed with `pyenv`. Solution is to use conda.

### Install SanPy from source code (use git clone).

```
git clone git@github.com:cudmore/SanPy.git

conda create -y -n sanpy-env python=3.9
conda activate sanpy-env

pip install --upgrade pip setuptools

#setuptools 61.2.0 -->> 62.4.0
#pip 21.2.4 -->> 22.1.2 (???)

# PyQt on a Mac M1 (arm64) chip does not install with pip install PyQt5
# thus, need to use conda
# not PyQt5 like with pip
conda install pyqt 

# this would be 'pip install tables' but fails on aMac M1 (arm64)
conda install pytables

# see setup.py for definitions of [gui] and [dev]
# they basically install different packages, e.g. [gui] install pyqtgraph
pip install -e .
pip install -e .\[gui\]
pip install -e .\[dev\]
```

### Run SanPy from command line to make sure it works

```
python Sanpy/sanpy/interface/sanpy_app.py
```

### pyinstaller script

Make a script (.sh on macOS, .bat on Windows)

The location matters, here it is in `/SanPy/pyinstaller/build-macos-laptop.sh`. This script contains  the following ...

```
pyinstaller \
	--noconfirm \
	--clean \
	--onedir \
	--windowed \
	--icon ../sanpy/interface/icons/sanpy_transparent.icns \
	--path /Users/cudmore/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/ \
	--name SanPy \
	--hidden-import tables \
    --add-data "/Users/cudmore/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/pyqtgraph/colors:pyqtgraph/colors" \
	../sanpy/interface/sanpy_app.py
```

Need to modify both `--path` and `--add-data` to what just got installed above.

This script will generate a new file `SanPy/pyinstaller/SanPy.spec`. Have a look at it. Another way to use pyinstaller is to run it from this script (change its name so it does not get over-written).

Look carefully at the output, look for WARNING and ERROR and adjust the script as neccessary.

The warnings are also written to `/SanPy/pyinstaller/build/SanPy/warn-SanPy.txt`

I get the following WARNING(s) but they don't seem to kill the built SanPy.app.

Moving forward it is probably best to adjust the install script to remove these. They may break code for some users some of the time?

```
58 WARNING: Failed to collect submodules for 'pkg_resources._vendor.pyparsing.diagram' because importing 'pkg_resources._vendor.pyparsing.diagram' raised: ModuleNotFoundError: No module named 'railroad'
56469 WARNING: Hidden import "pkg_resources.py2_warn" not found!
56469 WARNING: Hidden import "pkg_resources.markers" not found!
94 WARNING: Failed to collect submodules for 'setuptools._vendor.pyparsing.diagram' because importing 'setuptools._vendor.pyparsing.diagram' raised: ModuleNotFoundError: No module named 'railroad'
74393 WARNING: Library user32 required via ctypes not found
74421 WARNING: Library msvcrt required via ctypes not found
32701 WARNING: Cannot find path /Applications/Postgres.app/Contents/Versions/9.6/lib/libpq.5.dylib (needed by /Users/cudmore/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages/PyQt5/Qt5/plugins/sqldrivers/libqsqlpsql.dylib)
```

I was not able to fix some warnings using a naive approach like add the following to install script ...

```
	--hidden-import pkg_resources.py2_warn \
	--hidden-import pkg_resources.markers \
```

### Once app is built, run it and see if it crashes

Important to do this on the machine used to build plus ANOTHER machine.

The app on macOS is in `dist/SanPy.app`, I guess on windows it will be `dist/SanPy.exe`

On macOS, `SanPy.app` is actually a special kind of folder that can be revealed with right-click `Show Contents`. Not sure if there is equivalent on Windows?

The `SanPy.app` is actually run from `SanPy.app/Contents/MacOS/SanPy`. Running that file directly from a command prompt allows you to see a terminal with feedback warnings/errors logged by theSanPy code as it runs.

On Windows have to figure out a way to see these logs in a terminal? Double-clicking SanPy.exe probably will not show a terminal (like double-click of SanPy.app). 

## Notes

See this repo for building Napari (similar) https://github.com/tlambert03/napari-pyinstaller

When using conda, site-packages is in

```
/opt/miniconda3/envs/sanpy-env/lib/python3.9/site-packages
```

Build is in

```
/Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy-App.app/Contents/MacOS/SanPy-App
```

For pyqtgraph, we already have a folder but need to copy 'colors' folder into it

```
FileNotFoundError: [Errno 2] No such file or directory: '/Users/cudmore/Desktop/SanPy-App.app/Contents/MacOS/pyqtgraph/colors/maps/CET-L18'
```

Use the [dev] option in main SanPy installer to install pyinstaller and its dependencies. In particular, pyinstaller requires `pip install tornado` but does not install tornado itself?

```
cd SanPy
source sanpy_env/bin/activate
pip install -e .[dev]
# in zsh, need to escape brackets
pip install -e .\[dev\]
```

### Attempting to configure pyenv to play nice with pyinstaller

Need to install pyenv python with framework/shared libraries activated (always forget this).

```
# on mac os, use framework
env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.7.9
pyenv global 3.7.9

# linux/windows, use shared (not tested)
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.7.9
# activate as global
pyenv global 3.7.9
```

Otherwise, will get pyinstaller error

```
* On Debian/Ubuntu, you would need to install Python development packages
  * apt-get install python3-dev
  * apt-get install python-dev
* If you're building Python by yourself, please rebuild your Python with `--enable-shared` (or, `--enable-framework` on Darwin)
```

### setuptools

To check version of Python setuptools (it is a package).

```
import setuptools
print(setuptools.__version__)
```

My laptop had 56.0.0, after upgrade got 62.4.0

To upgrade setuptools

```
pip install --upgrade setuptools
```

## Finally, build the app using

```
./build-macos.sh
```

If there are no errors, the app will be in `dist/SanPy.app`.

Good luck !

## Troubleshooting

[[Ignore, do not do this, use current version of PyQt5]] Running the .app was giving a Segmentation Fault. The following worked after removing PyQt 5.15.4 (QApplication was giving segmentation fault)

Using
```
PyQt5==5.15.2
PyQt5-sip==12.9.0
```

[[Fixed in source code]] Compressing h5 files requires `ptrepack` binary and callable from command line. I was able to fix this in source code. `ptrepack` is a python script (not an actual binary), took it apart and handled in source.

```
/opt/miniconda3/envs/sanpy-env/bin/ptrepack
```
