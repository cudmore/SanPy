import os, json
from datetime import datetime
import gzip

from flask import Flask, jsonify, make_response
from flask_cors import CORS

import sanpy

# configuration
DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)

CORS(app, resources={r'/*': {'origins': '*'}})

def loadSanPyDir(path):
	"""
	Load folder of .abf

	Ret:
		list: list of dict
	"""
	print('app.py loadSanPyDir() path:', path)
	retList = []
	for file in os.listdir(path):
		if file.startswith('.'):
			continue
		if file.endswith('.abf'):
			#print('  loadSanPyDir() file: ', file)
			filePath = os.path.join(path, file)
			ba = sanpy.bAnalysis(filePath)
			headerDict = ba.api_getHeader()

			item = {
				'header': headerDict,
				'ba': ba
			}
			retList.append(item)
	#
	return retList

'''
def loadSanPy(path):
	"""
	Load one file
	"""
	ba = sanpy.bAnalysis(path)

	dDict = ba.getDefaultDetection()
	#dDict['dvdtThreshold'] = None # detect using just Vm
	ba.spikeDetect(dDict)
	#ba.errorReport()
	return  ba
'''

'''
def getHeader(ba):
	headerDict = ba.api_getHeader()
	#print('--- headerDictheaderDict')
	#for k,v in headerDict.items():
	#	print('  ', k,v)
	return headerDict
'''

"""
@app.errorhandler(404)
def resource_not_found(e):
	return jsonify(error=str(e)), 404
"""

@app.route('/', methods=['GET'])
def index():
	return jsonify({
					'status': 'success',
					'courses': COURSES})

@app.route('/getxy/<row_idx>', methods=['GET'])
def getxy(row_idx=0):
	"""
	Get X/Y of a file
	TODO: for now, just getting first file
	"""
	row_idx = int(row_idx)
	print('flask app.py getxy() row_idx:', row_idx)

	#ret = baList[row_idx]['ba'].api_getRecording()
	item = baList.getFromIndex(row_idx, type='ba')
	ret = item.api_getRecording()

	content = gzip.compress(json.dumps(ret).encode('utf8'), 5)
	response = make_response(content)
	response.headers['Content-length'] = len(content)
	response.headers['Content-Encoding'] = 'gzip'
	#return jsonify(ret)
	return response

@app.route('/filelist', methods=['GET'])
def filelist():
	print('flask filelist()')
	#headerList = [x['header'] for x in baList]
	headerList = baList.getHeaderList()
	ret = {
		'status': 'success',
		'fileList': headerList
		}
	print('--- filelist ret:')
	print(ret)
	return jsonify(ret)

'''
@app.route('/header')
def header():
	headerDict = getHeader(ba)
	return jsonify(headerDict)
'''

@app.route('/ping', methods=['GET'])
def ping_pong():
	#headerDict = getHeader(ba)
	#return jsonify(headerDict)
	now = datetime.now()
	dateTimeStr = now.strftime("%Y/%m/%d %H:%M:%S")
	return jsonify(f'pong! xxx could be any json !!! {dateTimeStr}')

# assuming we are running in 'SanPy/flask-vue' folder
'''
path = '../../data/19114001.abf'
path = '../../data/19221014.abf'
path = '../../data/19612002.abf'
ba = loadSanPy(path)
'''

path = '../../data'
#baList = loadSanPyDir(path)
baList = sanpy.bAnalysisDir(path)
#for baFile in baList:
#	print(baFile)

#
if __name__ == '__main__':
	app.run()
