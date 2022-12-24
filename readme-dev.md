## Development workflow

### Github workflow can run out of memory

```
Error: Process completed with exit code 134.
```

### flake8

```
flake8 ./sanpy --count --select=E9,F63,F7,F82 --show-source --statistics
```

### PyTest

```
pytest tests
```

### xxx

### tox

install

```
python -m pip install --user tox
```

## Writing code 202212

 - Activate drag/drop of a folder from the finder
    see: sanpy.interface.fileListWidget

## Update 202109

- Split FFT plugin into front-end and back-end. Currrently it is all front-end. This includes moving to back end: creation of bessel filter, filtering the signal, calculating FFT/PSD. Once this is done, write example notebook on how to do it programatically with API.

- Fix scaling in main interface. Switching between files is not resetting previous zoom properly

- Re-examine my user of filtering. Am I filtering out fast peaks in dvdt? Test this by turning filtering off. If I am removing fast peaks, expand API to include filtered and non-filter versions of Vm and dvdt.

- merge duplicate copies of stat list, it is defined at least 2x places. Make detection widget read from modified version of bAnalysisUtil. This was will include user defined stats.

1) In bDetection widget (get rid of this list)

```
self.myPlots = [
	{
		'humanName': 'Global Threshold (mV)',
		'x': 'thresholdSec',
		'y': 'thresholdVal',
		'convertx_tosec': False,  # some stats are in points, we need to convert to seconds
		'color': 'r',
		'styleColor': 'color: red',
		'symbol': 'o',
		'plotOn': 'vmGlobal', # which plot to overlay (vm, dvdt)
		'plotIsOn': True,
	},
```

2) expand bAnalysisUtil to include some of above fields, like to turn on/off a plot in detection widget. Also need another boolean to show/hide in detection widget.

Add all this to plotRecording.py plugin (add list widget to show stat ilst) so user can turn on/off

```
statList = OrderedDict()
statList['Spike Time (s)'] = {
	'name': 'thresholdSec',
	'units': 's',
	'yStat': 'thresholdVal',
	'yStatUnits': 'mV',
	'xStat': 'thresholdSec',
	'xStatUnits': 's'
	}
```

- GOTCHA. When filtering with median/golay we are reducing dvdt and thus detection parameter. Using Detection plugin DOES NOT refresh dvdt in main display and can be misleading!

- After detection with detect parameters plugin need to refresh ALL detection widget plot because filtering could have changed.

## Getting amazon aws s3 buckets working

Download and install aws command line

```
https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-mac.html
```

Configure aws command line

```
aws configure
# AWS Access Key ID [None]: <access key>
# AWS Secret Access Key [None]: <secret key>
# Default region name [None]: us-west-1
# Default output format [None]: json
```
From aws cli, list data

```
aws s3 ls s3://sanpy-data/data/
```

## Update 202106

## Timeline

 - I want to have a final draft of a manuscript by July 20th, 2021.
 - I then want to submit an initial version to https://www.biorxiv.org/.
 - Once the biorxiv is up and we get some feedback, I want to submit a manuscript to either PLoS or Frontiers. I am open to others on your suggestions.

I would like some things from you:

- Can you suggest 2-3 labs who would be interested in checking out SanPy? I want to make sure it encompasses their needs.
- A few whole-cell current-clamp recordings of ventricular cells to make sure the analysis yields reasonable results.
- Do you know any labs that use Heka amplifiers? I want to check this kind of file import works.
- We need to create an 'experimental figure' for the manuscript. Ideally this would be detailed AP analysis before/after application of a drug. I think it is fine if we re-use already published data. How about some before/after Iso?

Here is a recap of my work ...

Documentation is at: https://cudmore.github.io/SanPy/
 - A work in progress but critical for final publication. Added benefit is it makes me think in an organized way about a fairly complex system.

Overall:
 - Added runtime logging to file. Users can view logs and send to me to troubleshoot. This is HUGE.

Analysis:
 - Built system to log per-AP errors (when detection goes wrong)
 - Expanded detection parameters to be more controllable beyond dV/dt and mV thresholds to include things like refractory period and time-windows to control searching for spike peak, AP-durations etc. Goal is to have presets for different kinds of cells. For example: SA Node, ventricular, etc. See: https://cudmore.github.io/SanPy/methods.html#detection-parameters

Interface:
 - Expanded detection parameters beyond dV/dt and mV thresholds (see above).
 - Created interface to browse individual APs with automatic zooming, like: 'go to AP', 'next AP', previous AP', etc
 - Can now browse per-AP errors and jump to zoomed view of the problem AP.
 - Implemented 'Plugins', a bit like ImageJ/Fiji. This is SUPER useful to extend the analysis/plotting without having to update the main SanPy program. You just drop in some custom code to do detailed/specific analysis. I've started using this with some good examples that will get others up and running quickly.

Desktop App:
 - Now creating a downloadable app that can be run with one click (no Python or command prompt). This is a huge improvement but pretty technical on my end. I need a computer with actual operating system to build it. I have macOS Catalina and Big Sur working. Next is to get Windows 7 and 10 working.

Cloud App:
 - Created a web based app that runs in the cloud. This is great as it uses all the same code as the main SanPy Desktop app, just a different interface. This is a starting point for the Santana R01 software add on. Do not plan on including this in initial SanPy manuscript, too many details need to be hashed out.

TODO:
 - Make sure spike detect is using all columns in main File Table (imported from folder of csv)
 - bFileTable.pandasModel needs to be split into two classes (file table, error table), put common functions in a base class 'sanpyPandasModel'
 - Move sanpy_app.new_tableClicked() into bDetectionWidget. Requires proper signal to be emitted by detection widget and actions taken in slots
 - Load folder (e.g. switch folder) is buggy and needs to be rock solid. (i) if existinf csv, parse columns inteligently, ensure soft error when abf corrupt, (iii) error check loading txt files, (iv) remove loading kymograph tif. Kymographs are beyond the scope of initial publication.
 - Once we have a folder csv, ensure we can update csv after (i) files removed and (ii) files added
 - add plugins including: detection errors, spike clips
 - expand scatter plugin with option to display spike_i versus spike_i-1
 - When detection yields no spikes -->> now getting exceptions ... fix
 - If plugin is open with no file/detection, need to set title with file on switch file.
 - Add keystrokes to all plugins, to toggle switching on update on file selection and new analysis. We already have a QCheckbox in scatter plugin to do this. Make it a default property

BUGS
 - scatter plugin does not select correct spike when plotting 'chase'
 - scatter plugin does not plot hw (AP dur), need to tweek my master stat list to include predefined hw (10,20,50,80,90).

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
