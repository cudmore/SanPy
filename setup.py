from setuptools import setup#, find_packages

#exec (open('bimpy/version.py').read())

setup(
    name='sanpy',
    version='0.1.1',
    description='Cardiac Myocyte Current Clamp Analysis',
    url='http://github.com/cudmore/SanPy',
    author='Robert H Cudmore',
    author_email='robert.cudmore@gmail.com',
    license='GNU GPLv3',
    install_requires=[
        'numpy',
        'scipy',
        'pandas',
        'pyqtgraph',
        'matplotlib',
        'pyabf',
        'XlsxWriter',
        'PyQt5==5.13.0',
		'qdarkstyle',
    ]
)
