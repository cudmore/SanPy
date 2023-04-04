#!/bin/sh

# usage
# create-dmg [options ...] <output_name.dmg> <source_folder>

# Create a folder (named dmg) to prepare our DMG in (if it doesn't already exist).
mkdir -p dist/dmg
# Empty the dmg folder.
rm -r dist/dmg/*
# Copy the app bundle to the dmg folder.
cp -r "dist/SanPy-Monterey.app" dist/dmg
# If the DMG already exists, delete it.
test -f "dist/SanPy-Monterey.dmg" && rm "dist/SanPy-Monterey.dmg"
create-dmg \
  --volname "SanPy-Monterey" \
  --volicon "sanpy_transparent.icns" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 100 \
  --icon "SanPy-Monterey.app" 175 120 \
  --hide-extension "SanPy-Monterey.app" \
  --app-drop-link 425 120 \
  --notarize tmp_profile_name_for_dmg \
  "dist/SanPy-Monterey.dmg" \
  "dist/dmg/"

  # Options
# --volname <name>: set volume name (displayed in the Finder sidebar and window title)
# --volicon <icon.icns>: set volume icon
# --background <pic.png>: set folder background image (provide png, gif, jpg)
# --window-pos <x> <y>: set position the folder window
# --window-size <width> <height>: set size of the folder window
# --text-size <text_size>: set window text size (10-16)
# --icon-size <icon_size>: set window icons size (up to 128)
# --icon <file_name> <x> <y>: set position of the file's icon
# --hide-extension <file_name>: hide the extension of file
# --custom-icon <file_name|custom_icon|sample_file> <x> <y>: set position and -tom icon
# --app-drop-link <x> <y>: make a drop link to Applications, at location x, y
# --ql-drop-link <x> <y>: make a drop link to /Library/QuickLook, at location x, y
# --eula <eula_file>: attach a license file to the dmg
# --rez <rez_path>: specify custom path to Rez tool used to include license file
# --no-internet-enable: disable automatic mount&copy
# --format: specify the final image format (UDZO|UDBZ|ULFO|ULMO) (default is UDZO)
# --filesystem: specify the image filesystem (HFS+|APFS) (default is HFS+, APFS supports macOS 10.13 or newer)
# --add-file <target_name> <file|folder> <x> <y>: add additional file or folder (can be used multiple times)
# --disk-image-size <x>: set the disk image size manually to x MB
# --hdiutil-verbose: execute hdiutil in verbose mode
# --hdiutil-quiet: execute hdiutil in quiet mode
# --bless: bless the mount folder (deprecated, needs macOS 12.2.1 or older, #127)
# --codesign <signature>: codesign the disk image with the specified signature
# --notarize <credentials>: notarize the disk image (waits and staples) with the keychain stored credentials For more information check Apple's documentation
# --skip-jenkins: skip Finder-prettifying AppleScript, useful in Sandbox and non-GUI environments, #72
# --sandbox-safe: hdiutil with sandbox compatibility, do not bless and do not execute the cosmetic AppleScript (not supported for APFS disk images)
# --version: show tool version number
# -h, --help: display the help
