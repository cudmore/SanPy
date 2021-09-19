import os, json
import io
from datetime import datetime
import gzip
import zlib

import numpy as np

import flask
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
					'courses': 'xxx was COURSES'})

@app.route('/getxy/<row_idx>', methods=['GET'])
def getxy(row_idx=0):
	"""
	Get X/Y of a file
	TODO: for now, just getting first file
	"""
	row_idx = int(row_idx)
	print('flask app.py getxy() row_idx:', row_idx)

	#ret = baList[row_idx]['ba'].api_getRecording()
	ba = baList.getAnalysis(row_idx)
	ret = ba.api_getRecording()

	# object of type bytes is not json serializable
	'''
	ret = {
		'sweepX': ba.sweepX2.tobytes(),
		'sweepY': ba.sweepY2.tobytes(),
	}
	'''
	# was this
	content = gzip.compress(json.dumps(ret).encode('utf8'), 5)
	print('content:', type(content))
	response = make_response(content)
	response.headers['Content-length'] = len(content)
	response.headers['Content-Encoding'] = 'gzip'
	#return jsonify(ret)
	return response

# application/octet-stream
@app.route('/getxy2/<row_idx>', methods=['GET'])
def getxy2(row_idx=0):
	"""
	Get X/Y of a file
	TODO: for now, just getting first file
	"""
	row_idx = int(row_idx)
	print('flask app.py getxy() row_idx:', row_idx)

	#ret = baList[row_idx]['ba'].api_getRecording()
	ba = baList.getAnalysis(row_idx)
	#ret = ba.api_getRecording()

	sweepX = ba.sweepX2
	sweepY = ba.sweepY2

	'''
	import zipfile
	zipBuffer = io.BytesIO() #create our buffer
	with zipfile.ZipFile(zipBuffer, 'w') as myZipFile:
		myZipFile.writestr('sweepX', sweepX.tobytes(), compress_type=zipfile.ZIP_DEFLATED)
		myZipFile.writestr('sweepY', sweepY.tobytes(), compress_type=zipfile.ZIP_DEFLATED)
	#zipF.write(sweepY.tobytes(), compress_type=zipfile.ZIP_DEFLATED)
	zipBuffer.seek(0)
	print('len(zipBuffer):', zipBuffer.getbuffer().nbytes, type(zipBuffer));
	'''

	'''
	import zlib
	zipBuffer = zlib.compress(sweepX.tobytes())

	#return flask.send_file(zipBuffer, attachment_filename='capsule.zip', as_attachment=True)

	response = flask.make_response(zipBuffer)
	'''
	
	#response.headers['Content-length'] = len(zipBuffer)
	#response.headers['Content-Encoding'] = 'zip'
	#response.headers['Content-Encoding'] = 'application/octet-stream'

	# works
	#response = flask.make_response(sweepX.tobytes())
	#response.headers.set('Content-Type', 'application/octet-stream')
	
	#response.headers['Content-length'] = len(content)
	#response.headers['Content-Encoding'] = 'gzip'
	# response.headers.set('Content-Disposition', 'attachment', filename='np-array.bin')
	
	import struct
	# struct.pack("f", value)

	numWaves = 2
	waveLength = sweepX.shape[0]
	numWaves = struct.pack("f", float(numWaves))
	waveLength = struct.pack("f", float(waveLength))

	print('sweepX:', sweepX[:].shape)
	
	myBytes = numWaves
	myBytes += waveLength
	myBytes += sweepX[:].astype(np.float32).tobytes()
	myBytes += sweepY[:].astype(np.float32).tobytes()

	tmpCompress = gzip.compress(myBytes, 5)
	# print('tmpCompress:', len(tmpCompress))

	response = flask.make_response(tmpCompress)
	response.headers['Content-length'] = len(tmpCompress)
	response.headers['Content-Encoding'] = 'gzip'  # 'application/octet-stream'

	return response

@app.route('/filelist', methods=['GET'])
def filelist():
	print('flask filelist()')
	#headerList = [x['header'] for x in baList]
	headerList = baList.api_getFileHeaders()
	ret = {
		'status': 'success',
		'fileList': headerList
		}
	print('--- flask app filelist() ret:')
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

#path = '../../data'
path = '/Users/cudmore/Sites/SanPy/data'
#baList = loadSanPyDir(path)
baList = sanpy.analysisDir(path)
print('baList:', baList)
#for baFile in baList:
#	print(baFile)

#
if __name__ == '__main__':
	app.run()
