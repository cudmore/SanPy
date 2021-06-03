SanPy will run on:

 - macOS
 - Microsoft Windows
 - Linux
 - In the cloud.

We are following the [FAIR][fair] principles of software development to promote: **(F)**indability, **(A)**ccessibility, **(I)**nteroperability, and **(R)**eusability.

With this, our software is designed to be flexible in how it is used.

- From a desktop
- As a downloaded app
- On an existing cloud server
- Deployed by our users as their own cloud server

## Installing on your own computer

Assuming you have the following

 - [Python 3.7.x][python3]
 - [pip][pip]
 - [git][git] (optional)

[python3]: https://www.python.org/downloads/
[pip]: https://pip.pypa.io/en/stable/
[git]: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git
[fair]: https://en.wikipedia.org/wiki/FAIR_data

### Install the desktop application

#### Option 1) Install using ./install

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

#### Option 2) Install manually

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

#### Option 1) Using ./run

```
cd SanPy
./run
```

#### Option 2) Manually

```
# activate the virtual environment in sanpy_env/
cd SanPy
source sanpy_env/bin/activate

# run the desktop application
python sanpy/sanpy_app.py
```
