# 20210609
import numpy as np
import scipy.signal

import matplotlib.pyplot as plt

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

import sanpy

class aPlugin():
	"""
	TODO: plugin should recieve slot() when
		(1) detection is run
		(2) spike is selected
		(3) file is changed
	"""
	def __init__(self, ba):
		self._ba = ba

		self.fig = None
		self.ax = None

	@property
	def ba(self):
		return self._ba

	def plot(self):
		pass

	def slot_updateAnalysis(self):
		pass

	def slot_selectSpike(self, spikeNumber, doZoom):
		pass

if __name__ == '__main__':
	#testPlot()
	pass
