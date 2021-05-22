"""
load and save files from/to a box folder

this is a really tricky interface

requires

pip instal boxsdk
"""

import os, sys, time, io
import numpy as np

#import matplotlib.pyplot as plt
import contextlib

from boxsdk import OAuth2, Client
from boxsdk.object.collaboration import CollaborationRole
import boxsdk.exception

import sanpy

import logging

# turn off most logging, sanpy was causing this to start logging everything
logging.getLogger('boxsdk').setLevel(logging.CRITICAL)

# TODO: put this back in
#shared_link_password = None

#def my_store_tokens_callback(access_token, refresh_token):
#	# store the tokens at secure storage (e.g. Keychain)
#	print('** my_store_tokens_callback()', access_token, refresh_token)

# TODO: Remove this !!!!
'''
developerToken = 'k3UCplWbjcnNkENtKMyYYzIXUs8Z2SPZ' # expires 60 min
clientID = 'rbzxgzx8g8khweib17idk6e4iengrts0'
clientSecret = 'sj5HbZ9eCiObv4U8Rzdx4AroUUuAeM5h'

auth = OAuth2(
	client_id = clientID,
	client_secret = clientSecret,
	access_token = developerToken,
	#store_tokens=my_store_tokens_callback,
	#access_token=persisted_access_token,
	#refresh_token=persisted_refresh_token,
)
'''

def boxException(name, e):
	print('=== boxException:', name)
	print('  message:', e.message)
	print('  status:', e.status)
	print('  code:', e.code)

def upload():
	"""
	upload files to Box
	"""
	developerToken = 'T61RQcoh1StFYi6U93hy3FeCBGkGGc0V' # expires 60 min
	clientID = 'rbzxgzx8g8khweib17idk6e4iengrts0'
	clientSecret = 'sj5HbZ9eCiObv4U8Rzdx4AroUUuAeM5h'

	auth = OAuth2(
		client_id = clientID,
		client_secret = clientSecret,
		access_token = developerToken,
		#store_tokens=my_store_tokens_callback,
		#access_token=persisted_access_token,
		#refresh_token=persisted_refresh_token,
	)

	client = Client(auth) # boxsdk.client.client.Client

	# check the client we just opened
	user = client.user().get()
	print('  opening boxsdk.Client()')
	print('  user:', user)
	print('  user.id', user.id)

	# find the SanPy-Cloud-Data-Folder
	items = client.folder('0').get_items()
	for item in items:
		print(item.type, item.id, item.name)
		if item.name == 'SanPy-Cloud-Data':
			sharedFolderId = item.id

	# make analysis folder
	analysisFolder = 'sanpy-analysis'
	try:
		analysisFolder = client.folder(folder_id=sharedFolderId).create_subfolder(analysisFolder)
		print('analysisFolder:', analysisFolder, type(analysisFolder))
	except (boxsdk.exception.BoxAPIException) as e:
		boxException('create_subfolder', e)
		existingId = e.context_info['conflicts'][0]['id']
		analysisFolder = client.folder(folder_id=existingId)

	# test upload file
	try:
		uploaded_file = analysisFolder.upload('/Users/cudmore/Desktop/test.png')
	except (boxsdk.exception.BoxAPIException) as e:
		boxException('upload', e)


def download(sharedLinkToFolder):
	"""
	download files from box

	see this to download with urllib
	    https://stackoverflow.com/questions/50145101/download-files-from-a-box-location-using-api
	"""
	print('myBox.download() sharedLinkToFolder:', sharedLinkToFolder)

	# SanPy app to read/write
	'''
	developerToken = 'T61RQcoh1StFYi6U93hy3FeCBGkGGc0V' # expires 60 min
	clientID = 'rbzxgzx8g8khweib17idk6e4iengrts0'
	clientSecret = 'sj5HbZ9eCiObv4U8Rzdx4AroUUuAeM5h'
	'''

	# with this we only have READ priveledge !!!!
	# SanPy-View app to read (from robert.cudmore@gmail.com)
	clientID = 'dytfu05fqfah7p6q7ct8s1zyrjep4m03'
	clientSecret = ['NOTHING DEFINED HERE']
	access_token = 'kNugpRS4xUCYNjKEP8SG2CkaeYTqNmIG' # primary access token, expires in 60 days

	'''
	def my_store_tokens_callback(access_token, refresh_token):
		# store the tokens at secure storage (e.g. Keychain)
		print('========== store_tokens()')
	'''

	try:
		print('  creatinig OAuth2() with:')
		print('    clientID:', clientID)
		print('    clientSecret:', clientSecret)
		print('    access_token (SECRET):', access_token)
		auth = OAuth2(
			client_id = clientID,
			client_secret = clientSecret,
			access_token = access_token, # secret

			#store_tokens=my_store_tokens_callback,
			#access_token=persisted_access_token,
			#refresh_token=persisted_refresh_token,
		)
	except (boxsdk.exception.BoxOAuthException) as e:
		boxException('download() client', e)
		return

	try:
		client = Client(auth) # boxsdk.client.client.Client
	except (boxsdk.exception.BoxAPIException) as e:
		boxException('creating client', e)
		return
	except (boxsdk.exception.BoxOAuthException) as e:
		boxException('creating client 2', e)
		return

	# see: https://stackoverflow.com/questions/50145101/download-files-from-a-box-location-using-api

	print('  client.calling get_shared_item() from shared link:', sharedLinkToFolder)
	try:
		shared_folder = client.get_shared_item(sharedLinkToFolder) # use password parameter
	except (boxsdk.exception.BoxAPIException) as e:
		boxException('download() client.get_shared_item', e)
		return
	except (boxsdk.exception.BoxOAuthException) as e:
		boxException('  download() client.get_shared_item 2', e)
		return

	#print('  shared_folder:', shared_folder)
	#print('  type(shared_folder):', type(shared_folder)) # boxsdk.object.folder.Folder
	#print('  shared_folder.id:', shared_folder.id) # the name of the folder
	print('    shared_folder.name:', shared_folder.name) # the name of the folder
	print('    shared folder is owned by', shared_folder.owned_by['login'])

	print('    shared folder contents are:')
	items = client.with_shared_link(sharedLinkToFolder, shared_link_password=None).folder(shared_folder.id).get_items()
	for item in items:
	    print('      item type:{0} id:{1} name:"{2}"'.format(item.type, item.id, item.name))

	goodExtensions = '.abf'

	#for idx, item in enumerate(shared_folder.get_items(limit=1000)):
	numItems = 'xxx'
	for idx, item in enumerate(shared_folder.get_items(limit=1000)):
		print('  item idx:', idx, 'of', numItems)
		print('    item.name:', item.name)
		print('    item.id:', item.id, type(item.id))
		print('    item.type:', item.type)
		if item.type == 'file' and item.name.endswith(goodExtensions):
			# Operations on the item are allowed using client.get_shared_item() or client.with_shared_link()
			# using context: client.with_shared_link(sharedLinkToFolder, None)
			# Get file contents into memory
			#file = client.with_shared_link(sharedLinkToFolder, None).file(item.id)
			file = client.with_shared_link(sharedLinkToFolder, shared_link_password=None).file(item.id)

			with stopwatch('   downloading file'):
				fileContent = file.content()
			print('   len(fileContent):', len(fileContent))
			print('   type(fileContent):', type(fileContent))

			#decoded = base64.b64decode(fileContentStr)
			fileLikeObject = io.BytesIO(fileContent)

			ba = sanpy.bAnalysis(byteStream=fileLikeObject)
			print('   sweepY:', np.min(ba._abf.sweepY), np.max(ba._abf.sweepY))

			# loading seemms to work
			#plt.plot(ba._abf.sweepX, ba._abf.sweepY)
			#plt.show()

			# download link with urllib
			#download_url = client.file(file_id=item.id).get_shared_link_download_url()
			#print('  download_url:', download_url)
			#your_local_file_name = item.name
			#urllib.urlretrieve(download_url , your_local_file_name)

			# Or download to file
			#client.file(file_id=item.id).download_to(item.name)

@contextlib.contextmanager
def stopwatch(message):
    """Context manager to print how long a block of code took."""
    t0 = time.time()
    try:
        yield
    finally:
        t1 = time.time()
        print('%s took %.3f seconds' % (message, t1 - t0))

if __name__ == '__main__':
	# works
	#upload()

	#
	# both these shared links work !!!!
	# link from robert.cudmore@gmail.com
	sharedLinkToFolder = 'https://app.box.com/s/x1f83d23yutcoeccup2ojs74g61z3p28'
	# link from ucdavis box
	sharedLinkToFolder = 'https://ucdavis.box.com/s/euw0u55voypvz899d7kiyzctlfckllv3'

	download(sharedLinkToFolder)
