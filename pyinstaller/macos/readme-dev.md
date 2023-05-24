Hopefully the final version of pyinstaller scripts.

Activate a conda environment

    conda activate sanpy-env-pyinstaller

    or

    conda activate sanpy-env-pyinstaller-i386

Run `python macos_build.py`

Depending on the architecture of the activated conda environments, their will be an app and zip in `dist_x86` or `dist_arm`.

The build script should have final output like

```
2023-04-11 10:28:47,096 - root - INFO -   subprocess.run codesign ...
dist_x86/SanPy.app: replacing existing signature
dist_x86/SanPy.app: signed app bundle with Mach-O thin (x86_64) [SanPy]
2023-04-11 10:29:30,846 - root - INFO - codesign verify dist_x86/SanPy.app ...
dist_x86/SanPy.app: valid on disk
dist_x86/SanPy.app: satisfies its Designated Requirement
```

# Making a conda virtual environment

## 1. Make a platform specific conda environment

### Arm

    CONDA_SUBDIR=osx-arm64 conda create -y -n sanpy-pyinstaller-arm python=3.9
    conda activate sanpy-pyinstaller-arm
    conda env config vars set CONDA_SUBDIR=osx-arm64

    # NEED TO REACTIVATE ENV !!!
    conda deactivate
    conda activate sanpy-pyinstaller-arm

    pip install --upgrade pip

### x86

    # v1
    conda create -y -n sanpy-pyinstaller-i386 python=3.9
    conda activate sanpy-pyinstaller-i386

    # v2
    CONDA_SUBDIR=osx-64 conda create -y -n sanpy-pyinstaller-i386 python=3.9
    conda activate sanpy-pyinstaller-i386
    conda env config vars set CONDA_SUBDIR=osx-64

    conda deactivate
    conda activate sanpy-pyinstaller-i386

    pip install --upgrade pip

## 2. Conda install everything manually

Note: May 12, I am now using pip install for all x86 packages.

This is all for SanPy on arm64

conda install -y numpy pandas==1.5.3 scipy scikit-image==0.19.3 tifffile h5py requests matplotlib seaborn pyqt qtpy pyqtgraph pytables

```
conda install -y numpy
conda install -y pandas==1.5.3
conda install -y scipy
conda install -y scikit-image==0.19.3
conda install -y tifffile
conda install -y h5py
conda install -y requests

conda install -y matplotlib
conda install -y seaborn

conda install -y pyqt
conda install -y qtpy
conda install -y pyqtgraph

# in python 3.11
#conda install -y -c anaconda pytables
# in python 3.9
#conda install -y pytables

#conda install -y -c conda-forge mplcursors

pip install pyabf
pip install pyqtdarktheme
```

## 3. Install modified version of SanPy

I modified SanPy/setup.py to install no dependencies. For normal install we have to use `pip install -e ".[gui]"`

Use this to not install dependencies (we installed above with conda)

May 11, after starting to use setuptools_scm. We now need to pip install from the PyPi archive!
The local version does not pick up the correct version via a tag
but the pip install (from PyPi) does????
This is all very confusing!

```
### arm

pip install -e '../../.'

### x86

pip install -e '../../.[gui]'
```

# Check which arch the python kernel is running in

python -c 'import platform; print(platform.platform())'
python -c 'import sanpy; print(sanpy.__version__)'

import platform
_platform = platform.machine()
# arm64
# x86_64

```
# arm
macOS-12.4-arm64-arm-64bit

# x86
# macOS-10.16-x86_64-i386-64bit
```

# install my branch of pyinstaller

This branch removes DS_Store so codesign and notarize work

```
pip install -e ~/Sites/pyinstaller/.
```

Results in:

```
Successfully installed altgraph-0.17.3 macholib-1.16.2 pyinstaller-5.9.0 pyinstaller-hooks-contrib-2023.3
```

# Run pyinstaller script

```
python macos_build.py
```

# New Errors, April 28, 2023

```
INTEL MKL ERROR: dlopen(/Users/cudmore/Sites/SanPy/pyinstaller/macos/dist_x86/SanPy.app/Contents/MacOS/libmkl_intel_thread.1.dylib, 0x0009): Library not loaded: @rpath/libiomp5.dylib
  Referenced from: <F8EB4FC6-5255-330A-90E0-90B2F3E5F7E1> /Users/cudmore/Sites/SanPy/pyinstaller/macos/dist_x86/SanPy.app/Contents/Resources/libmkl_intel_thread.1.dylib
  Reason: tried: '/usr/lib/libiomp5.dylib' (no such file, not in dyld cache).
Intel MKL FATAL ERROR: Cannot load libmkl_intel_thread.1.dylib.
```

Fixed: This error does not occur in Python 3.9.

Nope, not fixed. We need to specify the conda env platform. On x86 we need to use pip (which does not grab arm by mistake). On arm64 we need to use conda install.

# Next steps

## Verify codesign

```
codesign --verify --verbose dist_x86/SanPy.app
codesign --verify --verbose dist_arm/SanPy.app
```

Try this as well
```
codesign -vvv --deep --strict dist_x86/SanPy.app
codesign -vvv --deep --strict dist_arm/SanPy.app
```

## Notarize

This will upload to apple and tell us when it is done uploading. Once on the apple server, it will email with pass/fail results.

The bundle-id seems to have rules? No '_' and no numbers?

We are now using `notarizeSanpy.py`. This includes local _secrets.app_specific_password

x86

    xcrun altool --verbose --notarize-app -t osx -f dist_x86/SanPy-intel.zip \
        --primary-bundle-id "intel" -u "<apple_id_eamil>" --password "<app_specific_password>"

arm

    xcrun altool --verbose --notarize-app -t osx -f dist_arm/SanPy-arm.zip \
        --primary-bundle-id "arm" -u "<apple_id_eamil>" --password "<app_specific_password>"

Check progress, all my notarize requested organized by RequestUUID

    xcrun altool --notarization-history 0 -u "<apple_id_eamil>" -p "<app_specific_password>"

```
Date                      RequestUUID                          Status        Status Code Status Message   
------------------------- ------------------------------------ ------------- ----------- ---------------- 
2023-04-11 17:51:55 +0000 ee097dd3-112f-493f-ac2b-63e2bd2bd9b2 in progress                                
```

## grab the log, that long sting is the RequestUUID

This will return a url with json list of errors

    xcrun altool --notarization-info 153f1da8-3ca4-409c-a57f-f10e53deca24 -u "<apple_id_eamil>" -p "<app_specific_password>"

That url tells me that none of the Contents/Resources binaries are signed or timestamp(ed). See `Manually codesigning` below.

```
    {
      "severity": "error",
      "code": null,
      "path": "SanPy-intel.zip/SanPy.app/Contents/Resources/libquadmath.dylib",
      "message": "The binary is not signed.",
      "docUrl": "https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution/resolving_common_notarization_issues#3087721",
      "architecture": "x86_64"
    },
    {
      "severity": "error",
      "code": null,
      "path": "SanPy-intel.zip/SanPy.app/Contents/Resources/libquadmath.dylib",
      "message": "The signature does not include a secure timestamp.",
      "docUrl": "https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution/resolving_common_notarization_issues#3087733",
      "architecture": "x86_64"
    },
```

## Staple

After submitting to apple for notarization using `xcrun altool`, they wil send an email if it passed.

Remember, once we staple, we need to remake the zip from the app.

```
xcrun stapler staple "dist_x86/SanPy.app"
xcrun stapler staple "dist_arm/SanPy.app"
```

```
Processing: /Users/cudmore/Sites/SanPy/pyinstaller/macos/dist_x86/SanPy.app
Processing: /Users/cudmore/Sites/SanPy/pyinstaller/macos/dist_x86/SanPy.app
The staple and validate action worked!
```

Check the staple

```
spctl -vvv --assess --type exec dist_x86/SanPy.app
spctl -vvv --assess --type exec dist_arm/SanPy.app
```

```
dist_x86/SanPy.app: accepted
source=Notarized Developer ID
origin=Developer ID Application: first_name last_name (app_specific_password)
```

