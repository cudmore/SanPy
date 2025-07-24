"""
Once our macOS app has been created

Submit a zip of the app for notarize

if it is successful then zip the app into the final zip we will distribute.
"""

import os
import sys
import subprocess

from build_utils import getAppPath, makeZip
from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)

from _secrets import email
from _secrets import team_id
from _secrets import app_password

PROD_MACOS_NOTARIZATION_APPLE_ID = email
PROD_MACOS_NOTARIZATION_TEAM_ID = team_id
PROD_MACOS_NOTARIZATION_PWD = app_password

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

def run():
    """
    dist : str
        Either dist_arm or dist_x86
    """

    app_path = getAppPath()  # includes .app

    logger.info(f'zipping app_path: {app_path}')
    
    # this make 'SanPy-pre-notarize.zip'
    zipPath_preNotarize = makeZip(app_path, 'pre-notarize')

    if zipPath_preNotarize is None:
        logger.error(f'Did not find zip file to send to notarize: {zipPath_preNotarize}')
        return
    
    logger.info(f'zipPath_preNotarize: {zipPath_preNotarize}')

    # check that the zip path exists
    if not os.path.isfile(zipPath_preNotarize):
        logger.error(f'Did not find zip file to send to notarize: {zipPath_preNotarize}')
        return
    
    # xcrun notarytool store-credentials "my-notarytool-profile-oct2023" --apple-id "$PROD_MACOS_NOTARIZATION_APPLE_ID" --team-id "$PROD_MACOS_NOTARIZATION_TEAM_ID" --password "$PROD_MACOS_NOTARIZATION_PWD"
    
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
    #         "store-credentials", "my-notarytool-profile-oct2023"
    #         "--apple-id", PROD_MACOS_NOTARIZATION_APPLE_ID,
    #         "--team-id", PROD_MACOS_NOTARIZATION_TEAM_ID,
    #         "--password", PROD_MACOS_NOTARIZATION_PWD,  # app specific password
    #     ],
    # )

    # xcrun notarytool submit "dist_x86/SanPy-pre-notarize.zip" --keychain-profile "my-notarytool-profile" --wait
    logger.info(f'submit to xcrun notarytool ... wait for output of pass/fail')
    logger.info(f'  -->> need to wait ... like 10 minutes')
    # logger.info(f'  --keychain-profile "my-notarytool-profile-oct2023"')

    _result = subprocess.run(
        [
            "xcrun", "notarytool",
            "submit", zipPath_preNotarize,  # like "dist_x86/SanPy-pre-notarize.zip"
            "--keychain-profile", "my-notarytool-profile-oct2025",
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
    
    # if dist == 'dist_arm':
    #     _platform = 'macOS-arm'
    # elif dist == 'dist_x86':
    #     _platform = 'macOS-x86'


    # delete zipPath_preNotarize
    logger.info(f'deleting zipPath_preNotarize: {zipPath_preNotarize}')
    if os.path.exists(zipPath_preNotarize):
        os.remove(zipPath_preNotarize)

    logger.info(f'zipping the app for distribution app_path:{app_path}')
    zipPath = makeZip(app_path, None)
    logger.info(f'Upload this zip to the GitHub release zipPath: {zipPath}')

def _store_credentials():
    """
    This does not work, need to copy and paste to command line.
    Every value has to be copied/pasted to command line with ""

    Like this
    xcrun notarytool store-credentials "my-notarytool-profile-oct2023" --apple-id "my-email" --team-id "my-team-id" --password "my-app-password"
    """
    logger.info(f'Storing credentials in my-notarytool-profile')
    print('  PROD_MACOS_NOTARIZATION_APPLE_ID:', PROD_MACOS_NOTARIZATION_APPLE_ID)
    print('  PROD_MACOS_NOTARIZATION_TEAM_ID:', PROD_MACOS_NOTARIZATION_TEAM_ID)
    print('  PROD_MACOS_NOTARIZATION_PWD:', PROD_MACOS_NOTARIZATION_PWD)
    subprocess.run(
        [
            "xcrun", "notarytool",
            "store-credentials", "my-notarytool-profile-oct2023"
            "--apple-id", "robert.cudmore@gmail.com",
            "--team-id", PROD_MACOS_NOTARIZATION_TEAM_ID,
            "--password", PROD_MACOS_NOTARIZATION_PWD,  # app specific password
        ],
    )

if __name__ == '__main__':
    run()