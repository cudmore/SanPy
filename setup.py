from setuptools import setup, find_packages

VERSION = "0.1.3"

setup(
    name='sanpy',
    version=VERSION,
    description='Whole cell current clamp analysis.',
    url='http://github.com/cudmore/SanPy',
    author='Robert H Cudmore',
    author_email='robert.cudmore@gmail.com',
    license='GNU General Public License, Version 3',
    # this is CRITICAL to import submodule like sanpy.userAnalysis
    packages=find_packages(include=['sanpy', 'sanpy.*', 'sanpy.interface', 'sanpy.fileloaders']),
    #packages=['sanpy', 'sanpy.userAnalysis'],
    install_requires=[
        'numpy',
        'pandas',
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
        'tables',  # this fails on arm64, neeed 'conda install pytables'
        'scikit-image',
        'pyqtgraph==0.12.4',
        'qdarkstyle',
        'PyQt5==5.15.6',  # this fail on arm64, need 'conda install pyqt'
        'h5py',
    ],
    extras_require={
        'dev': [
            'mkdocs',
            'mkdocs-material',
            'mkdocs-jupyter',
            'mkdocstrings',
            'tornado', # needed for pyinstaller
            'pyinstaller',
            'ipython',
        ],
        'test':["pytest", "pytest-cov", 'flake8', "pooch"],
    },
    python_requires=">=3.7",
    entry_points={
        'console_scripts': [
            'sanpy=sanpy.interface.sanpy_app:main',
        ]
    },
)
