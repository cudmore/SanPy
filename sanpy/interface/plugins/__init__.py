#from . import *

from .sanpyPlugin import *

# TODO: Fix this so I do not need to add each
from .plotRecording import plotRecording
from .sanpyLog import sanpyLog
from .plotTool import plotTool
from .plotScatter import plotScatter
from .detectionErrors import detectionErrors
from .spikeClips import spikeClips
from .resultsTable import resultsTable
from .analysisSummary import analysisSummary

# see: https://stackoverflow.com/questions/1057431/how-to-load-all-modules-in-a-folder
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

# see:
# https://stackoverflow.com/questions/1057431/how-to-load-all-modules-in-a-folder
# does not work in pyinstaller
# dirname(__file__) becomes
# /Users/cudmore/Sites/SanPy/pyinstaller/dist/SanPy.app/Contents/MacOS/sanpy/interface/plugins
'''
from os.path import dirname, basename, isfile, join
import glob
print('  dirname(__file__):', dirname(__file__))
modules = glob.glob(join(dirname(__file__), "*.py"))
print('  modules:', modules)
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]
print('  __all__:', __all__)
from . import *
'''

'''
import os, sys
print('  sys.executable:', sys.executable)
print('  os.path.dirname(sys.executable):', os.path.dirname(sys.executable))
sys.path.append(os.path.dirname(sys.executable))
print('  sys.path:', sys.path)
'''


'''
import importlib
modulename = 'plotRecording'
#module = importlib.import_module("plugins." + modulename, 'sanpy.interface.plugins')
module = importlib.import_module("." + modulename, 'sanpy.interface.plugins')
print('  module:', module)
#from . import *
'''

# works
'''
import sys, importlib.util

def module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

moduleName = 'sanpy.interface.plugins.plotRecording2'
srcPath = '/Users/cudmore/sanpy_plugins/plotRecording2.py'
sys.modules[moduleName] = module_from_file(moduleName, srcPath)
print('sys.modules[moduleName]:', sys.modules[moduleName])
'''
#baz = module_from_file(moduleName, srcPath)
#baz = module_from_file('.plotRecording2', srcPath)
#print(baz)
#print(dir(baz))
# ??? available as
# sanpy.interface.plugins.baz.plotRecording2()

# in code
#path = '/Users/cudmore/Sites/SanPy/data/19114001.abf'
#ba = sanpy.bAnalysis(path)
#ba.spikeDetect()
#tmpMod = sanpy.interface.plugins.module_from_file('xxx', '/Users/cudmore/sanpy_plugins/plotRecording2.py')
#tmpMod.plotRecording2(ba)

if 0:
	import os, sys, importlib, pathlib
	userPath = pathlib.Path.home()
	pluginPath = os.path.join(userPath, 'sanpy_plugins')
	print('  pluginPath:', pluginPath)
	sys.path.append(pluginPath)
	modulename = 'plotRecording2' # todo get list of all .py and strip .py
	modulePath = os.path.join(pluginPath, modulename)
	#module = importlib.import_module(modulePath, 'sanpy.interface.plugins')
	# /Users/cudmore/sanpy_plugins/plotRecording2
	print('  __name__:', __name__)
	print('  modulePath:', modulePath)
	module = importlib.import_module(modulePath)
	#module = importlib.import_module('.' + modulename, __name__)
	print('  module:', module)
	#from module import *
	importlib.invalidate_caches()
