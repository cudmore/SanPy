from setuptools import setup, find_packages

VERSION = "0.1.6"

setup(
    name='sanpy-ephys',  # thepackage name (on PyPi), still use 'import sanpy'
    version=VERSION,
    description='Whole cell current clamp analysis.',
    url='http://github.com/cudmore/SanPy',
    author='Robert H Cudmore',
    author_email='robert.cudmore@gmail.com',
    license='GNU General Public License, Version 3',
    # this is CRITICAL to import submodule like sanpy.userAnalysis
    packages=find_packages(include=['sanpy', 'sanpy.*', 'sanpy.interface', 'sanpy.fileloaders']),
    install_requires=[
        'numpy',
        'pandas==1.5',
        'scipy',
        'pyabf',
        'tifffile',
        #'XlsxWriter',
        #'xlrd', #  for loading excel files in examples/reanalyze.py
        #'openpyxl',
        'matplotlib',
        'mplcursors',
        'seaborn',
        'requests', #  to load from the cloud (for now github)
        'tables',  # aka pytable for hdf5.
        # used for line profile in kym analysis
        # 0.20.0 introduces pyinstaller bug because of lazy import
        'scikit-image==0.19.3', 
        'h5py',
    ],
    extras_require={
        'gui': [
            'qtpy',
            #'pyqtgraph==0.12.4',
            'pyqtgraph',
            #'qdarkstyle',  # v1
            'pyqtdarktheme',  # switched to this mar 2023
            #'PyQt5==5.15.6',  #
            'PyQt5',  #
        ],
        'dev': [
            'mkdocs',
            'mkdocs-material',
            'mkdocs-jupyter',
            'mkdocstrings',
            'tornado', # needed for pyinstaller
            'pyinstaller',
            'ipython',
            'tox',
            'pytest',
            'pytest-cov',
            'pytest-qt',
            'flake8',
            'jupyter',
            'pooch'  # what is this for?
        ],
        #"test": ["pytest", "pytest-cov", "scikit-image", "pooch"],
        'test': [
            'pytest',
            'pytest-cov',
            #'pytest-qt',
            'flake8',
        ]
    },
    python_requires=">=3.7",
    entry_points={
        'console_scripts': [
            'sanpy=sanpy.interface.sanpy_app:main',
        ]
    },
)
