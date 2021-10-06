"""
Quick and dirty functions to load files from Amazon AWS.

I really don't want to use this but should provide support for users.
"""

import sys, io
import boto3
import sanpy

def fetchFileList(bucketName, folder='.', s3=None):
	"""
	Return a list of keys for a given s3 and a bucket.

	Args:
		s3 (boto3.resource): boto3.resource('s3')
		bucketName (str): 'sanpy-data'
		folder (str): ('.', 'data/fft')
	"""
	if s3 is None:
		s3 = boto3.resource('s3')

	print('fetchFileList() bucketName:', bucketName, 'folder:', folder)

	myBucket = s3.Bucket(bucketName)

	numFiles = 0
	maxNumFiles = 1
	keyList = []
	for myBucketObject in myBucket.objects.all():
		if numFiles > maxNumFiles:
			break
		key = myBucketObject.key
		depth = key.count('/') # depth of 1 is 'root', e.g. '.'
		if folder=='.' and depth>1:
			continue
		if key.endswith('.abf'):
			keyList.append(key)
			numFiles += 1
	#
	print(f'  found {len(keyList)} abf files')
	return keyList

def getConnection():
	s3 = boto3.resource('s3')
	return s3

def loadOneFile(bucket, key, s3=None):
	ba = None
	if s3 is None:
		s3 = boto3.resource('s3')
	file_stream = io.BytesIO()

	try:
		s3.Object(bucket, key).download_fileobj(file_stream)
	except (boto3.exceptions.botocore.exceptions.ClientError) as e:
		print(e)
		#raise
	except (boto3.exceptions.botocore.exceptions.EndpointConnectionError) as e:
		print(e)
		#raise
	else:
		ba = sanpy.bAnalysis(byteStream=file_stream)
		print('  loadOneFile() loaded key:', key, 'ba:', ba)
	#
	return ba

def run():

	# create client assuming ~/.aws/xxx has been defined
	s3 = boto3.resource('s3')

	myBucketName = 'sanpy-data'
	keyList = fetchFileList(myBucketName, s3=s3)

	print(f'loading {len(keyList)} keys/files')
	for key in keyList:
		file_stream = io.BytesIO()
		# works with boto3.client('s3')
		#s3Client.download_fileobj(myBucketName, key, file_stream)
		s3.Object(myBucketName, key).download_fileobj(file_stream)
		ba = sanpy.bAnalysis(byteStream=file_stream)
		print('  loaded key:', key, 'ba:', ba)

	# download one file
	'''
	BUCKET_NAME = 'sanpy-data'
	OBJECT_NAME = 'data/19221014.abf'
	file_stream = io.BytesIO()
	s3.download_fileobj(BUCKET_NAME, OBJECT_NAME, file_stream)
	print('  download_fileobj() filled in file_stream:', type(file_stream))
	ba1 = sanpy.bAnalysis(byteStream=file_stream)
	print('  ba1:', ba1)
	'''

if __name__ == '__main__':
	#run()
	bucket = 'sanpy-data'
	keyList = fetchFileList(bucket, folder='.', s3=None)
	for key in keyList:
		ba = loadOneFile(bucket, key)
