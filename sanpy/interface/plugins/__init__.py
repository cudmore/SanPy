'''
import os
for module in os.listdir(os.path.dirname(__file__)):
	if module == '__init__.py' or module[-3:] != '.py' or module.startswith('.'):
		continue
	print('module:', module)
	moduleName = module[:-3]
	__import__(moduleName, locals(), globals())
del module
'''

from os.path import dirname, basename, isfile, join
import glob
modules = glob.glob(join(dirname(__file__), "*.py"))
print('modules:', modules)
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]
print('__all__:', __all__)
#from . import *
