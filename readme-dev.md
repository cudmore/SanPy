## 20230726

- file loaders

[ ] errors in loading atf. Added try/except for when pyAbf load atf fails


[x] Added member variable declaration (to None) in base file loader __init__() such that when we get load error, we do not get no variable found

[x] Bug: On clicking next/prev sweep, we are incrementing by two. PRoblem was we did not finish modifying code when we removed first combobox entry 'All'.

[ ] TODO: add file loader errors like we have spike errors. Each file loader will have a _errorList list


## Pushing tags to github

get the current tag

    git describe --tags

```
# make a tag and push the tag
git tag v0.1.25
git push origin v0.1.25

# delete a tag 
git tag -d v0.1.25
git push --delete origin v0.1.25
``` 

## Lock down a version to accompany SanPy manuscript

Working on publishing v0.1.8

## TODO for manuscript march 2023

- [done] Refactor all things having to do with light/dark theme. This is critical as copy paste from the interface cannot be trapped in a dark theme (for printing, manuscripts, etc)

- [done]Finish implementation of setSpikeStat plugin. Make sure it responds to interface changes and actually sets backend data in bAnalysis results.

- Update main sanpy app preferences, add mechanism to

    1) [done] remember if a plugin is in a standalone window or embedded in a toolbar.
    2) [done] Add in show/hide of setSpineStat plugin

- [done] Implement command+w and ctrl+w to close windows

- [done] track down errors in bAnalysis self._spikesPerSweep
    TODO: remove self._spikesPerSweep

- [done] Remove 'I' column from file list. This is supposed to be used for pooling (later versions will include this).

- [done] Preferences need to save/load the window position of external plugins.

- [done] Use spike pre clip ms and spike clip post ms to set zoom on a spike in the main sanpy widnow. Currently my zoom is large (for myocytes) but needs to be 10x smaller for neurons.

- Switch all `from PyQt5` to `from qtpy`. Switch all `QtCore.pyqtSignal` to `QtCore.Signal`

- [done] Get releases on PyPi

- [done] Replace `<user>/Documents/SanPy` with `<user>/SanPy-User-Files`

- Implement markers and colors in main detection widget
    - [done] Symbols will be user type
    - [done] Color will cycle through a number of conditions (use pd df unique()
    
- [done] Add an Error (E) column to main file table

- Fix plot spike clip plugin. Basically make self.ba.getSpikeClips() fetch spike clips for just one sweep and one epoch. Also is a problem with spike time wrt sweep?

- Reactivate limiting spike clips in plugin when user selects the x-axis. In general, my plugins no longer respond to x-axis changes. Turn code back on and just be sure to not select in scatter plugin (that was my original intention)

- Add detection option to not allow spikes within some window of start of an epoch, use like 1-2 ms. Fastest Theanne spikes seem to be out  at like 10 ms.

- Add current step (DAC) to plot recording plugin.

- Fix resultsTable and resultsTable2. They currently display spike based on the x-axis. This was usefull for one sweep but not useful for multiple sweeps.
    Use self.getStat('spikeNumber) which respects the selected sweep and epoch (including all)
    Then prune the main df to just those spikeNumber

- sweep popup is not always updating when i programatically set it.

- depreciate shift+click in favor of double-click to zoom on one spike

- [done] Added keyboard +/- to detection widget and scatter plot plugin to increase/decrease the scatter plot point size.

- [done] revamped crosshairs to show values next to the cursor.

- [done] set usertype marker in detection widget
    - [done] Need to reselect (to change marker) on set user type in set spike plugin. In general, reselect spikes on analysis changed.

- [done] When setting user type in scatter plot, selection seems to update in plugin but not in main detection widget. The opposite does work, changing user type in main interface propogates to scatter plot plugin.

## Bugs

- If user saves h5f and then deleted raw data file (like an abf)
    File still appears in the table but we get runtime exception when clicked.
    To fix, check if abf exists when loading h5f and flag file 'missing' in table

[fixed] Selecting spike in an epoch does not update correctly in Scatter plot widget

[fixed] Selecting spike and setting user type with set spike stat results in incorrect spike symbol being set in plot scatter widget.

[fixed] interface, raw data no longer expands to fit window. Something with detection widget being a toolbar?

### TODO minor

- Single spike selection in table plugin (That sets the sweep) does not also set the spike

- Add simple spike selection (using threshold) to 'plot fi' plugin. Use code in plot scatter plugin.

- [done] The file table needs to be expanded/colapsed by the user, it gets incredibly small. Previously was in a dock and could do this. Got rid of dock because it was getting complicated with show/hide of panels.

## TODO for version 2 (after submit to bioarchive)

- Implement class spikeSelection() and have all signal emit and connected slots use it. This will be a list of spikes [int] to select and will provide some utility functions like getting spikes for a sweep, etc.

- Implement class sanpyTablePlugin(sanpy.interface.plugins.sanpyPlugin) and have all table plugins derive from it. Right now the table plugins leave a lot to be desired, in particular with spike selections. They emit single spike selection (not multiple). They are not responding in a slot to spike selection! Need to implement a sort proxy to get the currect row selection (see PyMapManager for an example sort proxy).

- Create a preferences panel to set sanpy app preferences. Things like raw plot line width, symbol size, font size.

- Add a note to each file. Use keyboard 'n' and popup a dialog

# Random development notes, not really used

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


# Install on m1 arch arm64

Install mini conda from ‘Miniconda3-latest-MacOSX-arm64.pkg’

SHA256 hash: 0cb5165ca751e827d91a4ae6823bfda24d22c398a0b3b01213e57377a2c54226

see: https://docs.conda.io/en/latest/miniconda.html

Using Conda 4.12.0

/opt/miniconda3/bin/python

Python 3.9.12


```
conda create -y -n napari-env python=3.9
conda activate napari-env
conda install pyqt  # not PyQt5 like with pip
pip install napari
```

# install SanPy

```
conda create -y -n sanpy1-env python=3.9
conda activate sanpy1-env

pip install -e .
```

```
pip install --upgrade pip setuptools
```

setuptools 61.2.0 -->> 62.4.0
pip 21.2.4 -->> 22.1.2 (???)

# not PyQt5 like with pip
conda install pyqt 

# this would be 'pip install tables' but fails on arm
conda install pytables

pip install -e .
pip install -e .\[gui\]
pip install -e .\[dev\]

# need to add these to setup.cfg
#pip install pyqtgraph qdarkstyle 


# configure ssh

Three steps

1) https://docs.github.com/en/authentication/connecting-to-github-with-ssh/checking-for-existing-ssh-keys

2) https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent

3) https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account


ls -al ~/.ssh       # might not exists
ssh-keygen -t ed25519 -C “robert.cudmore@gmail.com"
eval "$(ssh-agent -s)"  
open ~/.ssh/config
touch ~/.ssh/config 
pico ~/.ssh/config  

```
Host *
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519
```

ssh-add -K ~/.ssh/id_ed25519    
pbcopy < ~/.ssh/id_ed25519.pub        # copy to clipboard

Follow link (3) above to add the new key to the GitHub website


## Switch an old https local GitHub to new ssh

```
# to see current (Should have https)
git remote -v

git remote set-url origin git@github.com:cudmore/SanPy.git

# verify
git remote -v

## Configure vs code

The vs code outline panel is uselull. I always want to turn off showing Python variables.

In VS Code, open preferences, search for 'outline.showVariables', and turn it off.

##### Option 1) Install using ./install

```
# If you have git installed.
# Clone the github repository (this will create a SanPy/ folder).
git clone https://github.com/cudmore/SanPy.git

# If you do not have git installed you can download the .zip file manually.
# In a browser, go to 'https://github.com/cudmore/SanPy'.
# Click green button 'Clone or download'.
# Select 'Download ZIP'.
# Once downloaded, manually extract the contents of the .zip file and continue following this tutorial.

# Change into the cloned or downloaded 'SanPy/' folder.
cd SanPy

# Install
./install

# Run
./run
```

##### Option 2) Install manually

```
# clone the github repository (this will create a SanPy/ folder)
git clone https://github.com/cudmore/SanPy.git

# change into the cloned SanPy folder
cd SanPy

# create a Python3 virtual environment in 'sanpy_env/' folder
python -m venv sanpy_env

# [OR] if python is bound to Python 2 (check with 'python --version')

python3 -m venv sanpy_env

# activate the virtual environment in sanpy_env/
source sanpy_env/bin/activate

# install the package
pip install .

# [OR] install the required python packages (into the activated virtual environment)
# pip install -r requirements.txt
```

### Running the desktop application

##### Option 1) Using ./run

```
cd SanPy
./run
```

##### Option 2) Manually

```
# activate the virtual environment in sanpy_env/
cd SanPy
source sanpy_env/bin/activate

# run the desktop application
python sanpy/sanpy_app.py
```

## Technologies used

#### Backend

 - [Python][Python]
 - [Pandas][Pandas]
 - [NumPy][NumPy]
 - [pyABF][pyABF] - Package to open Axon Binary Format (ABF) files
 - [XlsxWriter][XlsxWriter]
 -
#### Desktop Application

 - [PyQt][PyQt] - Desktop application interface
 - [PyQtGraph][pyqtgraph] - Derived from PyQt and used to make fast plots
 - [Matplotlib][Matplotlib] - Desktop application plotting

#### Web application

 - [Plotly Python][Plotly]
 - [Plotly Dash][Dash] - Web application interface
 - [Dash Bootstrap components][Dash Bootstrap components]

[Python]: https://www.python.org/
[Pandas]: https://pandas.pydata.org/
[NumPy]: https://www.numpy.org/
[pyABF]: https://github.com/swharden/pyABF
[TkInter]: https://docs.python.org/3/library/tkinter.html
[PyQt]: https://riverbankcomputing.com/software/pyqt/intro
[pyqtgraph]: http://www.pyqtgraph.org/
[XlsxWriter]: https://xlsxwriter.readthedocs.io/
[Matplotlib]: https://matplotlib.org/
[Plotly]: https://plot.ly/python/
[Dash]: https://plot.ly/products/dash/
[Dash Bootstrap components]: https://dash-bootstrap-components.opensource.faculty.ai/

## Other software

 - [ParamAP][ParamAP] - Standardized parameterization of sinoatrial node myocyte action potentials
 - [stimfit][stimfit] - A program for viewing and analyzing electrophysiological data

C++ libraries

 - [biosig][biosig] - A C/C++ library providing reading and writing routines for biosignal data formats
 - [sigviewer][sigviewer] - SigViewer is a viewing application for biosignals.

[ParamAP]: https://github.com/christianrickert/ParamAP
[stimfit]: https://github.com/neurodroid/stimfit
[biosig]: http://biosig.sourceforge.net/projects.html
[sigviewer]: https://github.com/cbrnr/sigviewer

## Advanced

#### Building a stand alone app (macOS)

Install pyinstaller

    pip install pyinstaller

Make the app

    cd SanPy
    ./makeapp

You can find the app in `dist/SanPy.app`.

#### Download the AnalysisApp

**This is not available yet.** We will eventually distribute a precompiled application for macOS, Microsoft Windows, an Linux.

Be sure to download the .zip file by clicking the triple tilde '...' on the top-right of the page and select download.

Once you have the .zip file ...

When you run the app you will see a dialog telling you 'Can't be opened because it is from an unidentified developer'.

You need to go into your 'Apple Menu - System Preferences - Security & Privacy'

Find the part that says "SpikeAnalysis... was blocked from opening because it is not from an identified developer" and click "Open Anyway"

After that, you are good to go!

[python3]: https://www.python.org/downloads/
[pip]: https://pip.pypa.io/en/stable/
[pyabf]: https://github.com/swharden/pyABF
[paramap]: https://github.com/christianrickert/ParamAP
[git]: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git
[virtualenv]: https://virtualenv.pypa.io/en/stable/

## Change log

 - 20190216, Created the code and implemented ap detection
 - 20190518, Started making web application (fairly complete as of 20190601)

## To Do

 - Set from/to (sec) when user zooms by dragging on graph
 - get file table to update when analysis is saved

### 20190326

 - Save analysis csv file and reload when loading folder. Don't always require re-analysis. Will break when format of csv file changes, make sure to include a file version.
 - Implement all stats used by Larson ... Proenza (2013) paper.
 - Show average spike clip in red
 - Export average spike clip
 - Take all stats on average spike clip. Is it different from taking average across all spikes?

### 20190329

Done:
 - 'Save Spike Report' now prompts for a file name
 - Added checkbox option to hide/show spike clips. It was getting too slow to always show spike clips when there are a ton of spikes. When you want to see them, you just turn it on.
 - Excel file column width are now (sanely) wider
 - Added max upstroke and min downstroke dV/dt to excel report
 - Added spike errors to excel report

To Do:
 - Convert ALL reported units to milli-seconds
 - Add new window to plot stats on x/y. For example, peak AP amplitude (mV) versus spike width (ms).

### 20190329
 - Gave new code to Laura that does pure Vm detection
 - New after giving Laura code
 - Meta plot will remember last stat plot when switching files, when first run it defaults to 'Spike Frequency (Hz)'
 - Median filter needs to be odd, if even value is specified we tweek it to odd

) always use ms2pnt() for
	postSpike_pnts = self.dataPointsPerMs * postSpike_ms

2) [done] add new detection param, to specify window to search for min dvdt after spike

	#
	# minima in dv/dt after spike
	#postRange = dvdt[self.spikeTimes[i]:postMinPnt]
	postSpike_ms = 10


3) [done] add a new detection param to flag low edd rate (slope)
units???

	lowestEddRate = 8

4) [done] fix save excel analysis, make sure we dump ALL detection params into sheet tab 'parameters'

5) summary spikes plugin needs to respond to changes in x-axis

6) in summary analysis plugin, turn off key press (we take no action).

7) analysisDir delete row needs to also delete uuid from h5 file

8) working on scatterplotwidget2, this will eventually not depend on sanpy but just a pandas df

- constructor takes statListDict, just use sanpy

9) Allow user to save preset detection parameters

10) mdp is currently looking in a pre TP window. This is not very 'cardiac'.
	- Add second mdp_cardiac to simply look for minimum in Vm between spikes
	- hold off on adding EDD and edd rate for this 'mdp_cardiac' ???

11) Add single spike selection to bDetectionWidget global

12) increase point size of overlay scatter plot in vm and dvdt.
	TODO: add option for user to control this point size

13) add a common QVLayout to all plugins to show: (file, start sec, stop sec, num spikes)
	Do this for: (plot scatter, error summary, summary analysis, ... OTHERS)

14) Modify ALL QTableView to retain blue selection when disabled. Like main file QTableView

15) Look into abf convert
	https://github.com/swharden/AbfConvert
