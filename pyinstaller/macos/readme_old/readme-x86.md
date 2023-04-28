
Sat April 8, 2023

Was able to get x86 app that ran without error

Using conda env `sanpy-env-pyinstaller-i386`

```
pyinstaller --noconfirm --clean macos-x86.spec
```

- conda environment where everything is manually installed with `conda install xxx`.
- installed pyinstaller from my dev fork with `pip install -e .`.
- did not specify codesign_identity

```
codesign_identity=None,  # "Developer ID Application: Robert Cudmore (794C773KDS)",
```

- include the following key in entitlements.plist

```
    <key>com.apple.security.cs.disable-library-validation</key>
	<true/>
```

# Troubleshooting

## to run a file

```
xattr -cr /Applications/SanPy.app
```

## good description of why downloading a zip and then app is currupt

This mentions same zip of a usb stick or file-share is fine

https://help.yoyogames.com/hc/en-us/articles/216753558-Mac-says-apps-damaged-when-downloaded-from-the-internet

## pyinstaller isuue, look into this to make a codesigned app

- This pyinstaller issue from Oct 2022 is super important, @nyavramov

https://github.com/pyinstaller/pyinstaller/issues/7123

Led to this example repo

https://github.com/nyavramov/python_app_mac_app_store


codesign --verify --verbose "dist/SanPy.app"



