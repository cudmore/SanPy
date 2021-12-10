# pyABF
[![](https://img.shields.io/azure-devops/build/swharden/swharden/6?label=Build&logo=azure%20pipelines)](https://dev.azure.com/swharden/swharden/_build/latest?definitionId=6&branchName=master)
[![](https://img.shields.io/azure-devops/tests/swharden/swharden/6?label=Tests&logo=azure%20pipelines)](https://dev.azure.com/swharden/swharden/_build/latest?definitionId=6&branchName=master)
[![](https://img.shields.io/pypi/dm/pyabf?label=Pip%20Installs&logo=python&logoColor=white)](https://pypi.org/project/pyabf/)
[![](https://img.shields.io/pypi/v/pyabf?label=pyabf&logo=python&logoColor=white)](https://pypi.org/project/pyabf/)

### Changes

This fork has been modified to load .abf files as an io.BytesIO stream. This is useful when running on a web server and a .abf file is dragged and dropped into the browser.

Made changes to __init__() and _loadAndScaleData().

In _loadAndScaleData() simply switched

```
raw = np.fromfile(fb, dtype=self._dtype,
			  count=self.dataPointCount)
```

to

```
raw = np.frombuffer(fb.read(), dtype=self._dtype,
				count=self.dataPointCount)
```

Where fb is type '_io.BytesIO' and made from an Octet Stream (octetStream) with:

```
decoded = base64.b64decode(octetStream)
fb = io.BytesIO(decoded)
```

To install this fork, you need to use the following because setup.py is in a sub folder named 'src':

```
pip install "git+https://github.com/cudmore/pyABF#egg=pyabf&subdirectory=src"
```

I also removed docs, data, and dev folders to make my pip install from git+https relatively faster.


I will eventually try and merge this with the master...

**pyABF is a Python library for reading electrophysiology data from Axon Binary Format (ABF) files.** It was created with the goal of providing a Pythonic API to access the content of ABF files which is so intuitive to use (with a predictive IDE) that documentation is largely unnecessary. Flip through the **[pyABF Tutorial](https://swharden.com/pyabf/tutorial)** and you'll be analyzing data from your ABF files in minutes!

<p align="center">
<img src='docs/graphics/2017-11-06-aps.png'>
</p>

### Installation
```bash
pip install --upgrade pyabf
```

### Quickstart
```python
import pyabf
abf = pyabf.ABF("demo.abf")
abf.setSweep(3)
print(abf.sweepY) # displays sweep data (ADC)
print(abf.sweepX) # displays sweep times (seconds)
print(abf.sweepC) # displays command waveform (DAC)
```

### Resources
* [pyABF Website](http://swharden.com/pyabf/)
* [pyABF Tutorial](https://swharden.com/pyabf/tutorial)
* [Advanced Examples](https://swharden.com/pyabf/advanced)
* [ABF File Format](https://swharden.com/pyabf/abf2-file-format)

<p align="center">
<img src='docs/getting-started/source/advanced_08b_using_plot_module.jpg'>
</p>
