
## Making a macOS app with pyinstaller

Each SanPy.app is specific to the exact OS. We have working version for macOS Catalina and Big Sur. Both Microsoft windows and Ubuntu versions are in the works.

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

Compressing h5 files requires `ptrepack` binary and callable from command line

```
/opt/miniconda3/envs/sanpy-env/bin/ptrepack
```

Use the [dev] option in main SanPy installer to install pyinstaller and its dependencies. In particular, pyinstaller requires `pip install tornado` but does not install tornado itself?

```
cd SanPy
source sanpy_env/bin/activate
pip install -e .[dev]
# in zsh, need to escape brackets
pip install -e .\[dev\]
```

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

## Finally, build the app using

```
./build-macos.sh
```

If there are no errors, the app will be in `dist/SanPy.app`.

Good luck !

## Troubleshooting

Running the .app was giving a Segmentation Fault. The following worked after removing PyQt 5.15.4 (QApplication was giving segmentation fault)

Using
```
PyQt5==5.15.2
PyQt5-sip==12.9.0
```
