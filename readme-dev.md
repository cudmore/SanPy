
## Update 20201230
 - In export window, added X-Tick and Y-Tick major/minor controls (4x controls). To set the tick intervals on the X/Y axis.
 - In export window fixed bug where click or double-click on set value up/down would result in control incrementing over and over (no way to stop it)

## Update 20201218
 - Finalized changes from 20201209
 - Now making zip from local git and distributing as SanPy-20201218a.zip

## Updates 20201209
- Added SanPy program icon
- Now properly sort the file list
- Fixed errors with parsing _db.json when files are added/removed or have abf errors

- Added 'Early Diastolic Depol Rate (dV/s)' to saved Excel report.
- Added checkboxes to toggle dV/dt and Scatter views (like Clips view).
- Added alt+click+drag to set the y-axis of both dV/dt and Vm.
- Added the mean spike clip to the spike clip window. This can now also be exported.
- Fully revamped the export of traces to a file.
	- Toggle the x/y axes on and off.
	- Set the line width.
	- Set the line color.
	- Subsample the trace (to make saved file-size smaller).
	- Median filter the trace (to make it smoother).

- Fixed  errors when an .abf file is corrupt (will keep adding error checking as we find more).
- Removed open file dialog when default path is not found.
- When saving Excel file with 'Save Spike Report' button, we no longer save a .txt file. To also save a .txt file, use Shift+Click.
- Added dark mode.
- Reduced size of interface buttons and lists to maximize the area we use for plotting.


example/reanalyze.py, reanalyze from an excel file giving us threshold and start/stop time

examples/manuscript0.py, plot stat across (condition, region),


## Reduce png file size

install

```
brew install pngquant
```

Compress all png in folder - REPLACES FILES

```
pngquant --ext .png --force docs/docs/img/*.png
```

## Big Sur

This is my recipe for installing Python development environment, including SanPy, on a fresh install of macOS Big Surr.

### Install Brew

This should install XCode

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
```

### Install some packages with Brew

```
#brew install zlib sqlite bzip2 libiconv libzip
brew install openssl readline sqlite3 xz zlib
```

### Install pyenv

```
brew install pyenv
```

pyenv requires the following in `~/.zshrc`

```
if command -v pyenv 1>/dev/null 2>&1; then
  export PYENV_ROOT="$HOME/.pyenv"
  export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init --path)"
  eval "$(pyenv init -)"
fi
```

### Install Python 3.7.9 into pyenv

```
pyenv install 3.7.9
pyenv global 3.7.9
```

And check python is correct

```
python --version
# Python 3.7.9
```

```
which python
# /Users/cudmore/.pyenv/shims/python
```

### Upgrade pip

scipy was failing on pip version 20.1.1 but working on newer pip 21.1.2. We will do this again once in the venv `sanpy_env`.

```
pip install --upgrade pip
```

Original pip version was

```pip 20.1.1 from /Users/cudmore/Sites/SanPy/sanpy_env/lib/python3.7/site-packages/pip (python 3.7)
```

after `pip install --upgrade pip`

```
pip 21.1.2 from /Users/cudmore/Sites/SanPy/sanpy_env/lib/python3.7/site-packages/pip (python 3.7)
```

### Install python in pyenv to work with `pyinstaller`.

When installing pyenv, need shared-libraries for pyinstaller to work. The commands are slightly different on macOS, need to use `--enable-framework`.

If this is not configured properly, pyinstaller will give errors like `Python library not found: libpython3.7.dylib, libpython3.7m.dylib`

```
# on mac os, use framework
env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.7.9
pyenv global 3.7.9

# linux/windows, use shared (not tested)
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.7.9
# activate as global
pyenv global 3.7.9
```

### Clone sanpy

```
git clone https://github.com/cudmore/SanPy.git
cd SanPy
```

### Make a venv for SanPy in folder `sanpy_env`.

```
cd SanPy
python -m venv sanpy_env
# activate (will be different on Windows)
source sanpy_env/bin/activate
```

The sanpy_env needs pip 21.1.2, otherwise SciPy install will fail

```
# in the sanpy_env
pip install --upgrade pip
```

### Install SanPy (from cloned source code)

Because using Zsh shell, need to escape square brackets

```
pip install -e .
pip install -e .\[gui\]
pip install -e .\[dev\]
```

### Run SanPy gui

```
sanpy
```

## Big Sur miscellaneous system configuration

Colorize the command prompt in Zsh shell

```
PROMPT='%F{green}%*%f:%F{green}%~%f %% '
```

My ~/.zshrc looks like

```
# abb style the prompt
PROMPT='%F{green}%n@%m%f:%F{green}%~%f %% '
```
