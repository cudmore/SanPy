import sys
from PyQt5 import QtCore, QtGui, QtWidgets
import sanpy
import sanpy.interface

def runFFT(sanpyWindow):
	logger.info('')
	sanpyWindow.tableView._onLeftClick(0)
	sanpyWindow.myDetectionWidget.setAxis(2.1,156.8)

	ba = sanpyWindow.get_bAnalysis()
	pluginName = 'FFT'
	fftPlugin = sanpyWindow.myPlugins.runPlugin(pluginName, ba)
	resultsStr = fftPlugin.getResultStr()

	print('BINGO')
	print(resultsStr)

	sanpyWindow.tableView._onLeftClick(1)
	sanpyWindow.myDetectionWidget.setAxis(0, 103.7)
	resultsStr = fftPlugin.getResultStr()

	sanpyWindow.tableView._onLeftClick(2)
	sanpyWindow.myDetectionWidget.setAxis(16.4, 28.7)
	resultsStr = fftPlugin.getResultStr()

	print('BINGO')
	print(resultsStr)

'''
0	2020_07_30_0001.abf	2.101	156.795	0.391	-0.692	0.019	733097.683	Maybe

1	2020_08_27_0000.abf	0	103.782	0.391	-7.297	0.067	212452.573	No

2	2020_07_07_0000.abf	0.623	14.727	0.781	-7.181	1.276	18398.972	Yes
2	2020_07_07_0000.abf	16.386	28.996	1.172	-1.581	1.11	23812.62	Yes
2*	2020_07_07_0000.abf	63.342	85.077	4.492	-1.928	5.889	34645.676	No

3	2020_10_20_0000.abf	0.549	39.622	0.391	-9.657	0.102	63602.951	Maybe

4	2020_07_28_0002.abf	9.47	275.512	0.195	-6.778	0.011	1929743.374	Maybe

5	2020_07_28_0001.abf	31.494	254.605	0.195	-0.987	0.013	1750217.564	Maybe

6	2020_07_16_0000.abf	18.964	53.389	0.195	-2.16	0.32	50860.361	No

7	2020_07_16_0001.abf	0	203.776	0.195	-0.494	0.01	3216683.756	No

8	2020_07_01_0000.abf	72.828	143.56	8.203	-6.34	8.087	64906.549	No	High Freq 8Hz oscillation

9	2020_07_23_0005.abf	0.714	25.964	2.539	-4.897	0.158	42092.002	Yes
'''
if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)

	path = '/Users/cudmore/Sites/SanPy/data/fft'
	ad = sanpy.analysisDir(path)

	realIdx = 0
	for idx in range(len(ad)):
		# seed
		ba = ad.getAnalysis(idx)
		if ba.loadError:
			print('  file error:', fileName)
			continue
		fileName = ba.getFileName()
		if fileName == '2020_07_30_0001.abf':
			startStop = [2.1,156.8]
		elif fileName == '2020_08_27_0000.abf':
			startStop = [0, 103.78]
		elif fileName == '2020_07_07_0000.abf':
			#startStop = [0.6, 14.7]
			startStop = [16.386, 28.996]
		# 2020_10_20_0000.abf	0.549	39.622
		elif fileName == '2020_10_20_0000.abf':
			startStop = [0.549, 29]
		# 2020_07_28_0002.abf	9.47	275.512	0.195
		elif fileName == '2020_07_28_0002.abf':
			startStop = [9.47, 275.512]
		# 2020_07_28_0001.abf	31.494	254.605	0.195
		elif fileName == '2020_07_28_0001.abf':
			startStop = [31.494, 254.605]
		# 2020_07_16_0000.abf	18.964	53.389
		elif fileName == '2020_07_16_0000.abf':
			startStop = [18.964, 53.389]
		# 2020_07_16_0001.abf	0	203.776
		elif fileName == '2020_07_16_0001.abf':
			startStop = [0, 203.776]
		# 2020_07_01_0000.abf	72.828	143.56
		elif fileName == '2020_07_01_0000.abf':
			startStop = [72.828, 143.56]
		# 2020_07_23_0005.abf	0.714	25.964
		elif fileName == '2020_07_23_0005.abf':
			startStop = [0.714, 25.964]
		# no-cell.csv	9.256	18.895
		elif fileName == 'no-cell.csv':
			startStop = [9.256, 18.895]
		else:
			print('  file not specified:', fileName)
			continue

		if realIdx == 0:
			fftPlugin = sanpy.interface.plugins.fftPlugin(ba=ba, startStop=startStop)
		else:
			fftPlugin.slot_switchFile2(ba, startStop)

		input('Press Enter To Go To Next File!')
		realIdx += 1

	resultsStr = fftPlugin.getResultStr()
	print('BINGO!')
	print(resultsStr)


	sys.exit(app.exec_())
