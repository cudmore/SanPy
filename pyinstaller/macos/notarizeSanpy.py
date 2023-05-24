"""
Once our macOS app has been created

Submit a zip of the app for notarize

if it is successful then zip the app into the final zip we will distribute.
"""

import logging
import os
import sys
import subprocess
#import argparse

logger = logging.getLogger()

logging.basicConfig(
    # %(filename)s %(funcName)s() line:%(lineno)d
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s %(funcName)s() line:%(lineno)d %(message)s",
    level=logging.INFO,
)

from _secrets import email
from _secrets import team_id
from _secrets import app_password

PROD_MACOS_NOTARIZATION_APPLE_ID = email
PROD_MACOS_NOTARIZATION_TEAM_ID = team_id
PROD_MACOS_NOTARIZATION_PWD = app_password

#app_path = os.path.join('dist_x86', 'SanPy.app')

'''
    Goals
    -----

    1) do this once manually
    xcrun notarytool store-credentials "my-notarytool-profile" --apple-id "$PROD_MACOS_NOTARIZATION_APPLE_ID" --team-id "$PROD_MACOS_NOTARIZATION_TEAM_ID" --password "$PROD_MACOS_NOTARIZATION_PWD"

    ditto -c -k --keepParent "dist_x86/SanPy.app" "dist_x86/SanPy-pre-notarize.zip"

    xcrun notarytool submit "dist_x86/SanPy-pre-notarize.zip" --keychain-profile "my-notarytool-profile" --wait

    xcrun stapler staple "target/mac/Espanso.app"

    # if notarization fails, check  with this
    xcrun notarytool log <RANDOM-ID> --keychain-profile "my-notarytool-profile"
'''

'''
see here: https://developer.apple.com/forums/thread/706894

authKeyPath = '/Users/cudmore/apple-dev-keys-do-not-remove/AuthKey_XRVPNZRAJP.p8'
authKeyID = 'XRVPNZRAJP'
ISSUER_UUID = 'c055ca8c-e5a8-4836-b61d-aa5794eeb3f4'

xcrun notarytool history --key PATH_TO_KEY --key-id KEY_ID -i ISSUER_UUID
'''

def run(dist : str):
    """
    dist : str
        Either dist_arm or dist_x86
    """

    app_path = os.path.join(dist, 'SanPy.app')

    doZip = True
    if doZip:
        # this make 'SanPy-pre-notarize.zip'
        zipPath = makeZip(app_path, 'pre-notarize')
        print('zipPath:', zipPath)
    else:
        zipPath = dist + '/SanPy-pre-notarize.zip'

    logger.info(f'zipPath: {zipPath}')

    # check that the zip path exists
    if not os.path.isfile(zipPath):
        logger.error(f'Did not find zip file to send to notarize: {zipPath}')
        return
    
    # xcrun notarytool store-credentials "my-notarytool-profile" --apple-id "$PROD_MACOS_NOTARIZATION_APPLE_ID" --team-id "$PROD_MACOS_NOTARIZATION_TEAM_ID" --password "$PROD_MACOS_NOTARIZATION_PWD"
    
    #
    # running this manually from the command line worked
    #
    # xcrun notarytool store-credentials "my-notarytool-profile" --apple-id "<apple_id_email>" --team-id "<team_idx>" --password "<app-specific-password>"
    '''
        This process stores your credentials securely in the Keychain. You reference these credentials later using a profile name.

        Validating your credentials...
        Success. Credentials validated.
        Credentials saved to Keychain.
        To use them, specify `--keychain-profile "my-notarytool-profile"`
    '''

    # logger.info(f'Storing credentials in my-notarytool-profile')
    # subprocess.run(
    #     [
    #         "xcrun", "notarytool",
    #         "store-credentials", "my-notarytool-profile"
    #         "--apple-id", PROD_MACOS_NOTARIZATION_APPLE_ID,
    #         "--team-id", PROD_MACOS_NOTARIZATION_TEAM_ID,
    #         "--password", PROD_MACOS_NOTARIZATION_PWD,  # app specific password
    #     ],
    # )

    # xcrun notarytool submit "dist_x86/SanPy-pre-notarize.zip" --keychain-profile "my-notarytool-profile" --wait
    logger.info(f'submit to xcrun notarytool and wait for output of pass/fail ... need to wait ... like 10 minutes')
    logger.info(f'  zipPath:{zipPath}')
    logger.info(f'  --keychain-profile "my-notarytool-profile"')

    _result = subprocess.run(
        [
            "xcrun", "notarytool",
            "submit", zipPath,  # like "dist_x86/SanPy-pre-notarize.zip"
            "--keychain-profile", "my-notarytool-profile",
            "--wait"
        ],
        capture_output=True, text=True
    )

    print('_result', type(_result))
    print(_result)
    
    print('_result.stdout', type(_result.stdout))
    print(_result.stdout)

    print('_result.stderr', type(_result.stdout))
    print(_result.stderr)

    # look for this in _result.stdout 'status: Accepted'
    _notaryAccepted = False
    if 'status: Accepted' in _result.stdout:
        _notaryAccepted = True
        logger.info(f'=== notarization accepted by the Apple server')

    if not _notaryAccepted:
        logger.error(f'notarytool did not except the zip --> aborting !!!')
        return
    
    '''
    After some time, we receive
    ---------------------------
    Conducting pre-submission checks for SanPy-pre-notarize.zip and initiating connection to the Apple notary service...
    Submission ID received
    id: dfa71a26-541e-4bcf-b721-0bc077f3c6e5
    Upload progress: 100.00% (128 MB of 128 MB)   
    Successfully uploaded file
    id: dfa71a26-541e-4bcf-b721-0bc077f3c6e5
    path: /Users/cudmore/Sites/SanPy/pyinstaller/macos/dist_x86/SanPy-pre-notarize.zip
    Waiting for processing to complete.
    Current status: Accepted........................
    Processing complete
    id: dfa71a26-541e-4bcf-b721-0bc077f3c6e5
    status: Accepted
    '''

    # if notary tool passed then staple
    # xcrun stapler staple "target/mac/Espanso.app"
    logger.info(f'=== xcrun stapler staple app_path {app_path}')
    _result = subprocess.run(
        ['xcrun', 'stapler',
         'staple', app_path,
        ]
    )

    # finally, create the final zip to upload to GitHub release
    
    if dist == 'dist_arm':
        _platform = 'macOS-arm'
    elif dist == 'dist_x86':
        _platform = 'macOS-x86'


    zipPath = makeZip(app_path, _platform)
    logger.info(f'Upload this zip to the GitHub release zipPath: {zipPath}')

def makeZip(appPath : str, shortPlatformStr : str):
    """Make a zip file from app.
    
    Parameters
    ----------
    appPath : str
        Relative path to the app we are building. Like 'dist/SanPy.app'
    shortPlatformStr : str
        Append this with hyphen '-' to zip file name.
        From ['intel', 'm1']

    Returns
    -------
    zipPath : str
        The relative path to the zip that we distribute

    """
    zipPath, _ = os.path.splitext(appPath)
    zipPath += '-' + shortPlatformStr + '.zip'
    logger.info(f'ditto is compressing {appPath} to {zipPath} ...')

    # ditto -c -k --keepParent "dist/SanPy-Monterey-arm.app" dist/SanPy-Monterey-arm.zip
    subprocess.run(
        [
            'ditto',
            '-c',
            '-k',
            '--keepParent',
            appPath,
            zipPath
        ]
    )

    return zipPath

if __name__ == '__main__':
    [myFile, dist] = sys.argv
    
    print(sys.argv)

    print('dist:', dist)

    if not dist in ['dist_arm', 'dist_x86']:
        logger.error(f'invalid dist folder. Expecting dist_arm or dist_x86')
    else:
        run(dist)