import os
import sys
from setuptools import setup, find_packages

# manually keep in sync with sanpy/version.py
#VERSION = "0.1.11"

# with open(os.path.join('sanpy', 'VERSION')) as version_file:
#     VERSION = version_file.read().strip()

# load the readme
_thisPath = os.path.abspath(os.path.dirname(__file__))
with open(os.path.abspath(_thisPath+"/README.md")) as f:
    long_description = f.read()

"""
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
        #'mplcursors',
        'seaborn',
        'requests', #  to load from the cloud (for now github)
        'tables',  # aka pytables for hdf5.
        # used for line profile in kym analysis
        # 0.20.0 introduces pyinstaller bug because of lazy import
        'scikit-image==0.19.3', 
        'h5py',
    ],
"""

setup(
    name='sanpy-ephys',  # the package name (on PyPi), still use 'import sanpy'
    #version=VERSION,
    description='Whole cell current-clamp analysis.',
    long_description=long_description,
    long_description_content_type = 'text/markdown',
    url='http://github.com/cudmore/SanPy',
    author='Robert H Cudmore',
    author_email='rhcudmore@ucdavis.edu',
    license='GNU General Public License, Version 3',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],

    # this is CRITICAL to import submodule like sanpy.userAnalysis
    packages=find_packages(include=['sanpy', 'sanpy.*', 'sanpy.interface', 'sanpy.fileloaders']),
    
    use_scm_version=True,
    setup_requires=['setuptools_scm'],

    # for conda based pyinstaller, we had to remove all installs
    # please install with pip install -e '.[gui]'
    install_requires=[],

    extras_require={
        'gui': [
            'numpy==1.23.4',  # 1.24 breaks PyQtGraph with numpy.float error
            'pandas==1.5',  # version 2.0 removes dataframe append
            'scipy',
            'pyabf',
            'tifffile',
            'matplotlib',
            'mplcursors',
            'seaborn',
            'requests', #  to load from the cloud (for now github)
            'tables',  # aka pytable for hdf5. Conflicts with conda install
            # used for line profile in kym analysis
            # 0.20.0 introduces pyinstaller bug because of lazy import
            'scikit-image==0.19.3', 
            'h5py',  # conflicts with conda install

            'qtpy',
            'pyqtgraph',
            'pyqtdarktheme',  # switched to this mar 2023
            'PyQt5',  # only install x86 version, need to use conda install pyqt

            #'setuptools_scm',
        ],
        'dev': [
            'mkdocs',
            'mkdocs-material',
            'mkdocs-jupyter',
            'mkdocstrings',
            'mkdocstrings-python', # resolve erro as of April 30, 2023
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
        'test': [
            'pytest',
            'pytest-cov',
            #'pytest-qt',
            'flake8',
        ]
    },
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'sanpy=sanpy.interface.sanpy_app:main',
        ]
    },
)
