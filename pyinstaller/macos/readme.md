This folder contains scripts to build macOS app(s) from Python source code using pyinstaller.

Building a Python app on macOS is by no means simple. The app needs to be properly codesigned, notarized on an Apple server (requires uploading a zip of the app to Apple), waiting for the ok, and then staple(ing) the app with the notarization.

This all requires an Apple Developer Subscription which is $99/year.

**Important.** In what follows, to codesign, notarize, and staple requires additional `secrets` we do not include in the public github repository. These include:

    provisioning_profile = '/Users/cudmore/apple-dev-keys-do-not-remove/mac_app.cer'
    
    app_certificate = "Developer ID Application: first_name last_name (team_id)"
    
    email = 'apple-developer_email_address'
    
    team_id = 'team_id'
    
    app_password = 'app_specific_password'

    # for the notarize step, we manually did this once
    # to save a local copy of "my-notarytool-profile"
    xcrun notarytool store-credentials "my-notarytool-profile" --apple-id "<apple_id_email>" --team-id "<team_idx>" --password "<app-specific-password>"

This has two parallel workflows, one for x86 and the other for arm64.


### arm64
    build_arm.sh
    
### x86
    build_x86.sh

### Each script follows a similar workflow with slight differences between x86 and arm64.

- Create a fresh  conda environment

    All environments are created with conda and are specified as x86 or arm64. This is done with `CONDA_SUBDIR=osx-64` and `CONDA_SUBDIR=osx-arm64`.

- Install requirements for SanPy and install SanPy
    
    For x86, all packages are installed with pip via a normal SanPy install with `pip install ".[gui]"`

    For arm64, most (not all) packages are installed with conda. Pip installed packages include pyabf, pyqtdarktheme, and sanpy itself with `pip install .`

- Create the app with pyinstaller and codesign

    **Important:** This is using a modified version of the [pyinstaller develop repo](https://github.com/cudmore/pyinstaller). Here, we have pyinstaller remove all `.DS_Store` files otherwise codesign fails.

    Creating the app is done in `macos_build.py` which has some logic depending on the x86 or arm64 environment it is called from. This script uses the one `macos.spec` file for both platforms. An example of the platform differences is the x86 version had to include pytables binaries, see logic in the `macos.spec` file.

    Codesign(ing) is also done in `macos_build.py` which detects the platform of the env it was called from and does x86 or arm64 specific stuff. For example, the precise placementent of some `dylib` libraries for the `skimage` package.

- Send the zipped app to Apple to get notarized

    This is the same regardless of platform (phew) and uses the newer `notarytool`.

- On notarize success, staple the app

- Make a final zip of the app and (manually) upload as an asset in a GitHub release.

    All this, send for notarization, staple, and make final zip is done with either `python notarizeSanpy.py dist_arm` or `python notarizeSanpy.py dist_x86`

### Usefull links

A possible complete recipe for running this all as a GitHub action

https://federicoterzi.com/blog/automatic-code-signing-and-notarization-for-macos-apps-using-github-actions/
