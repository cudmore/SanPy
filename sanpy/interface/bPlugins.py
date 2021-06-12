# 20210610

import os, sys, pathlib, glob, importlib

import sanpy

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class bPlugins():
	def __init__(self):
		#import inspect
		#tmpList = inspect.getmembers('sanpy.interface.plugins')
		#print('tmpList:', tmpList)

		'''
		import sys, inspect
		for name, obj in inspect.getmembers(sys.modules[__name__]):
			if 1 or inspect.isclass(obj):
				print('jjjj:', obj)
		'''
		
		if 0:
			for k,v in sys.modules.items():
				print(k, '\n', '  ', v)
			tmpList = dir('sanpy.interface.plugins')
			print('tmpList:', tmpList)

		error = False
		userPath = pathlib.Path.home()
		pluginFolder = os.path.join(userPath, 'sanpy_plugins')
		if not os.path.isdir(pluginFolder):
			error = True
			logger.error(f'Did not find pluginFolder "{pluginFolder}"')

		self.pluginFolder = pluginFolder
		self.pluginDict = {}

		if not error:
			sys.path.append(self.pluginFolder)
			self.loadPlugins()

	def loadPlugins(self):
		self.pluginDict = {}

		pluginFolder = self.pluginFolder
		files = glob.glob(os.path.join(pluginFolder, '*.py'))
		for file in files:
			if file.endswith('__init__.py'):
				continue
			logger.info(f'loading plugin: "{file}"')

			moduleName = os.path.split(file)[1]
			moduleName = os.path.splitext(moduleName)[0]
			fullModuleName = 'sanpy.interface.plugins2.' + moduleName

			loadedModule = self._module_from_file(fullModuleName, file)
			#print('loadedModule:', type(loadedModule), loadedModule)

			oneConstructor = getattr(loadedModule, moduleName)
			#print('  oneConstructor:', type(oneConstructor), oneConstructor)

			pluginDict = {
				#'pluginName': moduleName,
				'module': fullModuleName,
				'path': file,
				'constructor': oneConstructor,
			}

			# assuming file name is unique
			self.pluginDict[moduleName] = pluginDict

	def runPlugin(self, pluginName, ba):
		"""
		Run one plugin with given ba (bAnalysis)

		Args:
			pluginName (str):
			ba (bAnalysis): object
		"""
		self.pluginDict[pluginName]['constructor'](ba)

	def pluginList(self):
		"""Get list of names of loaded plugins"""
		retList = []
		for k,v in self.pluginDict.items():
			retList.append(k)
		return retList

	def _module_from_file(self, module_name, file_path):
	    spec = importlib.util.spec_from_file_location(module_name, file_path)
	    module = importlib.util.module_from_spec(spec)
	    spec.loader.exec_module(module)
	    return module

if __name__ == '__main__':
	bp = bPlugins()

	pluginList = bp.pluginList()
	print('pluginList:', pluginList)

	abfPath = '/Users/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(abfPath)

	bp.runPlugin('plotRecording3', ba)
