
20210129

Load and plot dual line-scan .tif and whole-cell recording .abf files

Install:
	pip3 install --upgrade -r requirements.txt
	#pip install --upgrade -r requirements.txt

Usage:
	cd dual-analysis
	python3 dualPlot.py

Interface:
	Once a plot is opened, use the keyboard like this:
		1: Toggle Vm plot over kymograph image
		2: Toggle middle Ca plot
		3: Toggle middle Vm plot
		4: Toggle subplot showing lower Vm

		n: go to next file in dual-database.xlsx
		p: go to previous file in dual-database.xlsx

Save:
	to save the entire plot, use the toolbar and
	specify desired file extension from (.svg, .tif, .png, .jpg)

Data:
	- All data is in the 'dual-data' and then a yyyymmdd date folder
	- the 'date folder', 'tif file', and 'abf file' need to be
		specified in the main dual-database.xlsx file

Notes:
	- the imaging starts at a variable time into the abf recording
		get the start time of the .tif wrt the abf with abf.tagTimesSec[0]

	- there are a smaller number of abf.tagTimesSec
		should correspond to the number of line scans (during abf recording) but it does not

	- the interval between abf.tagTimesSec is way to long
		should be the duration of each tif file scan but it is not

Code Notes

	to browse data from dual-database.xls, use
		testTable.py

	in dualAnalysis.py, dualRecord.findSpikePairs()
		assumes dualRecord is loaded and analyzed
		find spike pairs between abf and tif recording

	dualAnalysis.py runOneRecording() will
		use dual-database.xls to analyze and plot ONE dual (tif/abf) recording
		also runs/plot dualRecord.findSpikePairs()

	dualAnalysis.py runPool() will
		use dual-database.xls to analyze all files and make a df
		save df as /Users/cudmore/Desktop/dualAnalysis_db.csv
		to be opened in sanpy/bScatterPlot2.py

Data Notes

how to open in Fiji?
	20210120__0002.oir "galvo frame scan (nucleus). ephys file: 21120 002"

	20210122__0003.oir "galvo image of cell"

	missing e-phys data 000, 001, 002
	Cell 1 - superior cell
	0. galvo LS. ephys file: 21129 000 (mainly LCRs)
	1. galvo LS. ephys file: 21129 001 (depolarized cell towards end of recording)
	Cell 1 - inferior cell
	2. galvo LS. ephys file: 21129 002 (APs)
