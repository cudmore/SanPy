SanPy is designed to run on: macOS, Microsoft Windows, and Linux.

## Download the SanPy app.

We are building apps so users can download a single SanPy.app and get working with just a double-click. This does not require anything special on our users end. No programming, no installing Python, and no command line.

Check back for more info on this.

## Manual install from the command line

Assuming you have the following

 - [Python > 3.7][python3]
 - [pip][pip]
 - [git][git]

[python3]: https://www.python.org/downloads/
[pip]: https://pip.pypa.io/en/stable/
[git]: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git

1) Clone the repository

```
git clone git@github.com:cudmore/SanPy.git
cd SanPy
```

2) Create and activate a virtual environment with either `conda` or `venv`

2.1) With `conda`

```
conda create -y -n sanpy-env python=3.9
conda activate sanpy-env
```

2.2) With `venv`

```
python -m venv sanpy-env
source sanpy-env/bin/activate
```

3) Install SanPy including the desktop GUI

```
pip install -e .[gui]
```

Note, on newer macOS machines or if using the zsh shell in general, you need some extra quotes

```
pip install -e ".[gui]"
```

4) Run `sanpy`

```
sanpy
```

5) Have fun