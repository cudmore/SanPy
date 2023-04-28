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

Arm

```
CONDA_SUBDIR=osx-arm64 conda create -y -n sanpy-env-pyinstaller python=3.11
conda activate sanpy-env-pyinstaller
conda env config vars set CONDA_SUBDIR=osx-arm64

pip install --upgrade pip
```

x86

```
conda create -y -n sanpy-env-pyinstaller-i386 python=3.11
conda activate sanpy-env-pyinstaller-i386
#conda env config vars set CONDA_SUBDIR=osx-arm64

pip install --upgrade pip
```

## 2. Conda install everything manually


This is all for SanPy

```
conda install -y numpy
conda install -y pandas==1.5.3
conda install -y scipy
conda install -y scikit-image==0.19.3
conda install -y tifffile
conda install -y h5py
conda install -y requests

conda install -y -c anaconda pytables

conda install -y matplotlib
conda install -y -c conda-forge mplcursors
conda install -y seaborn

conda install -y pyqt
conda install -y qtpy
conda install -y pyqtgraph

pip install pyabf
pip install pyqtdarktheme
```

## 3. Install modified version of SanPy

I modified SanPy/setup.py to install no dependencies. For normal operation we have to use `pip install -e ".[gui]"`

```
pip install -e "../../."
```

# Check which arch the python kernel is running in

We don't want any reference to `x86_64` or `i386`.

python -c 'import platform; print(platform.platform())'

```
macOS-12.4-arm64-arm-64bit

# was previously
# macOS-10.16-x86_64-i386-64bit
```

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

x86

```
xcrun altool --verbose --notarize-app -t osx -f dist_x86/SanPy-intel.zip \
    --primary-bundle-id "intel" -u "robert.cudmore@gmail.com" --password "bisd-xacv-hsiv-okrd"
```

arm

```
xcrun altool --verbose --notarize-app -t osx -f dist_arm/SanPy-arm.zip \
    --primary-bundle-id "arm" -u "robert.cudmore@gmail.com" --password "bisd-xacv-hsiv-okrd"
```

Check progress, all my notarize requested organized by RequestUUID

```
xcrun altool --notarization-history 0 -u "robert.cudmore@gmail.com" -p "bisd-xacv-hsiv-okrd"
```

```
Date                      RequestUUID                          Status        Status Code Status Message   
------------------------- ------------------------------------ ------------- ----------- ---------------- 
2023-04-11 17:51:55 +0000 ee097dd3-112f-493f-ac2b-63e2bd2bd9b2 in progress                                
```

## grab the log, that long sting is the RequestUUID

This will return a url with json list of errors

```
xcrun altool --notarization-info 940392b3-6ff8-490f-a3ec-a0ae1137f566 -u "robert.cudmore@gmail.com" -p "bisd-xacv-hsiv-okrd"
```

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
origin=Developer ID Application: Robert Cudmore (794C773KDS)
```

## need to start using notarytool

```
xcrun notarytool submit OvernightTextEditor_11.6.8.zip
                   --keychain-profile "AC_PASSWORD"
                   --wait
                   --webhook "https://example.com/notarization"
```

or

```
xcrun notarytool store-credentials "AC_PASSWORD"
               --apple-id "AC_USERNAME"
               --team-id <WWDRTeamID>
               --password <secret_2FA_password>
```

xcrun altool --notarize-app -t osx -f dist_x86/SanPy-intel.zip \
    --primary-bundle-id "tueaprileleven" -u "robert.cudmore@gmail.com" --password "bisd-xacv-hsiv-okrd"

I don't understand all the parameters here

From my previous readme(s)

```
xcrun notarytool store-credentials
                --apple-id "robert.cudmore@gmail.com"
                --team-id "794C773KDS"
```

had to answer questions,
    like 'app specific password' which is currently "bisd-xacv-hsiv-okrd",
    then I chose the name "tmp_profile_name_for_dmg"

```
To use them, specify `--keychain-profile "tmp_profile_name_for_dmg"`
```


