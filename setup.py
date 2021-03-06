from setuptools import setup, find_packages

#exec (open('bimpy/version.py').read())

setup(
    name='sanpy',
    version='0.1.2',
    description='Cardiac Myocyte Current Clamp Analysis',
    url='http://github.com/cudmore/SanPy',
    author='Robert H Cudmore',
    author_email='robert.cudmore@gmail.com',
    license='GNU GPLv3',
	#packages=find_packages(include=['sanpy', 'sanpy.*']),
    packages=['sanpy'],
	install_requires=[
        'numpy',
        'pandas',
        'matplotlib',
        'scipy',
        'pyabf',
        'XlsxWriter',
		'xlrd', #  for loading excel files in examples/reanalyze.py
		'openpyxl',
		'seaborn',
		'tifffile',
		'mplcursors',
		'requests', #  to load from the cloud (for now github)
		'tables'  # to load/save with pandas HDFStore
    ],
    # use pip install .[gui]
    # on Big Sur use pip install .\[gui\]
	extras_require={
        'gui': [
			'pyqtgraph',
			'PyQt5==5.15.2',
			'qdarkstyle',
		],
        'dev': [
			'mkdocs',
			'mkdocs-material',
			'mkdocs-jupyter',
            'mkdocstrings',
            'tornado', # nneded for pyinstaller
            'pyinstaller',
            'ipython',
		],
    },
    entry_points={
        'console_scripts': [
            'sanpy=sanpy.interface.sanpy_app:main',
        ]
    },
)
