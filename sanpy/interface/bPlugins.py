# 20210610

import os, sys, pathlib, glob, importlib, inspect

import sanpy
import sanpy.interface.plugins

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

class bPlugins():
	"""
	Generate a list of plugins.

	Looking in
		- sanpy.interface.plugins
		- <user>/sanpy_plugins
	"""
	def __init__(self, sanpyApp=None):
		self._sanpyApp = sanpyApp

		error = False
		userPath = pathlib.Path.home()
		pluginFolder = os.path.join(userPath, 'sanpy_plugins')
		if not os.path.isdir(pluginFolder):
			error = True
			logger.error(f'Did not find pluginFolder "{pluginFolder}"')

		self.pluginFolder = pluginFolder
		self.pluginDict = {}

		"""set of open plugins"""
		self._openSet = set()

		if not error:
			sys.path.append(self.pluginFolder)
			self.loadPlugins()

	def getSanPyApp(self):
		"""
		Get the underlying SanPy app
		"""
		return self._sanpyApp

	def loadPlugins(self):
		"""
		Load plugins from both:
		 - sanpy.interface.plugins
		 - <user>/sanpy_plugins
		"""
		self.pluginDict = {}

		ignoreModuleList = ['sanpyPlugin', 'myWidget']

		#
		# system plugins from sanpy.interface.plugins
		for moduleName, obj in inspect.getmembers(sanpy.interface.plugins):
			print('moduleName:', moduleName, 'obj:', obj)
			if inspect.isclass(obj):
				print('  class')
				if moduleName in ignoreModuleList:
					# our base plugin class
					continue
				#print('sys plugin:', moduleName, ':', obj)
				fullModuleName = 'sanpy.interface.plugins.' + moduleName
				humanName = obj.myHumanName
				pluginDict = {
					'pluginClass': moduleName,
					'type': 'system',
					'module': fullModuleName,
					'path': '',
					'constructor': obj,
					'humanName': humanName
				}
				#if moduleName in self.pluginDict.keys():
				if humanName in self.pluginDict.keys():
					logger.warning(f'Plugin already added "{moduleName}" humanName:"{humanName}"')
				else:
					self.pluginDict[humanName] = pluginDict

		#
		# user plugins from files in folder <user>/sanpy_plugins
		pluginFolder = self.pluginFolder
		files = glob.glob(os.path.join(pluginFolder, '*.py'))
		for file in files:
			if file.endswith('__init__.py'):
				continue

			moduleName = os.path.split(file)[1]
			moduleName = os.path.splitext(moduleName)[0]
			fullModuleName = 'sanpy.interface.plugins.' + moduleName

			loadedModule = self._module_from_file(fullModuleName, file)

			try:
				oneConstructor = getattr(loadedModule, moduleName)
			except (AttributeError) as e:
				logger.error(f'Make sure filename and class are the same file:"{moduleName0}"')
			else:
				humanName = oneConstructor.myHumanName
				pluginDict = {
					'pluginClass': moduleName,
					'type': 'user',
					'module': fullModuleName,
					'path': file,
					'constructor': oneConstructor,
					'humanName': humanName
					}
				# assuming moduleName is unique
				#if moduleName in self.pluginDict.keys():
				if humanName in self.pluginDict.keys():
					logger.warning(f'Plugin already added "{moduleName}" humanName:"{humanName}"')
				else:
					logger.info(f'loading plugin: "{file}"')
					#self.pluginDict[moduleName] = pluginDict
					self.pluginDict[humanName] = pluginDict

	def runPlugin(self, pluginName, ba):
		"""
		Run one plugin with given ba (bAnalysis)

		Args:
			pluginName (str):
			ba (bAnalysis): object
		"""
		if not pluginName in self.pluginDict.keys():
			logger.error(f'Did not find plugin: "{pluginName}"')
			return
		else:
			humanName = self.pluginDict[pluginName]['constructor'].myHumanName
			logger.info(f'Running plugin: "{pluginName}" {humanName}')
			# TODO: to open PyQt windows, we need to keep a local (persistent) variable
			newPlugin = \
					self.pluginDict[pluginName]['constructor'](ba=ba, bPlugin=self)
			self._openSet.add(newPlugin)

	def getType(self, pluginName):
		"""
		returns one of ('system', 'user')
		"""
		if not pluginName in self.pluginDict.keys():
			logger.error(f'Did not find plugin: "{pluginName}"')
			return None
		else:
			theRet = self.pluginDict[pluginName]['type']
			return theRet

	def pluginList(self):
		"""Get list of names of loaded plugins"""
		retList = []
		for k,v in self.pluginDict.items():
			retList.append(k)
		return retList

	def getHumanNames(self):
		retList = []
		for k,v in self.pluginDict.items():
			myHumanName = v['myHumanName']
			retList.append(myHumanName)
		return retList

	def _module_from_file(self, module_name, file_path):
		spec = importlib.util.spec_from_file_location(module_name, file_path)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		return module

	def slot_closeWindow(self, pluginObj):
		"""
		close named plugin window

		Args:
			id (int): The running plugin .id()
			"""
		logger.info(pluginObj)
		try:
			self._openSet.remove(pluginObj)
		except (KeyError) as e:
			logger.exception(e)

	def slot_selectSpike(self, sDict):
		"""
		On user selection of spike in a plugin

		Tell main app to select a spike everywhere
		"""
		logger.info(sDict)
		app = self.getSanPyApp()
		if app is not None:
			spikeNumber = sDict['spikeNumber']
			doZoom = sDict['doZoom']
			app.selectSpike(spikeNumber, doZoom=False)

def test_print_classes():
	"""testing"""
	print('__name__:', __name__)
	for name, obj in inspect.getmembers(sys.modules[__name__]):
		if inspect.isclass(obj):
			print(name, ':', obj)

	print('===')
	for name, obj in inspect.getmembers(sanpy.interface.plugins):
		if inspect.isclass(obj):
			print(name, ':', obj)

if __name__ == '__main__':
	#print_classes()
	#sys.exit(1)

	bp = bPlugins()

	pluginList = bp.pluginList()
	print('pluginList:', pluginList)

	abfPath = '/Users/cudmore/Sites/SanPy/data/19114001.abf'
	ba = sanpy.bAnalysis(abfPath)

	bp.runPlugin('plotRecording', ba)
	#bp.runPlugin('plotRecording3', ba)
