
SanPy Documentation is available at [https://cudmore.github.io/SanPy/](https://cudmore.github.io/SanPy/)

## 20231201

### New Features
 - Added fast AHP. The fast AHP after a spike. Measured in a window using detection parameter fastAhpWindow_ms
 - Added API documentation for adding a new measurement to the core analysis

### Bug fixes
 - Fixed bug in loading detection-presets when they do not match the default detection presets (missing keys)
 - Fixed bug in loading folder of raw data. Previouslly, the folder would not load if there was an error in one abf file. We are getting abf file errors trying to read abf exported from sutter patch.

