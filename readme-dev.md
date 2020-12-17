
## Updates 20201109
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

## pyinstaller

python -m venv sanpy_env

eval "$(pyenv init -)"

pyinstaller --windowed bTestPrint.spec

```
# this never finished ?
#env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.7.0

env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.7.0
```

### build with PyInstall

Tried with the python3 default from Catalina, does not work OSError:
```
Python library not found: libpython3.7.dylib, libpython3.7m.dylib, Python, .Python
```

Install pyenv

```
git clone https://github.com/pyenv/pyenv.git ~/.pyenv
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile
```

Use pyenv to install python

```
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.7.3
```

activate python
```
# activate local python
pyenv local 3.7.3
```

Install SanPy

```
pip install -r requirements
pip install -e .
```

```
which python
/Users/cudmore/.pyenv/shims/python
```

Need to run PyInstaller like this (not directly on command line)

When I do this it complains apout torndao, so

```
pip install tornado
```

```
python -m PyInstaller --windowed sanpy/sanpy_app.py
```
then

```
python -m PyInstaller --windowed sanpy_app.spec
```

```
```
