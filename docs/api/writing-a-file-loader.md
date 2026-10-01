## How to write a custom SanPy file loader.

!!! note
    Runtime loading of external Python file loaders is currently disabled (SanPy 2.5, September 2026).
    Built-in file loaders continue to work normally.

1) Derive a new class from [sanpy.fileloaders.fileLoader_base](fileloader/fileLoader_base.md).

2) Specify the file extension you want to load with `loadFileType = 'your_file_extension'`

3) In a `loadFile()` member function, load your raw data file

4) Call `self.setLoadedData(...)` with the results. 

Here is some sample code based on the built-in SanPy CSV file loader
[fileLoader_csv](fileloader/fileLoader_csv.md).

```python
import sanpy.fileloaders.fileLoader_base as fileLoader_base

class fileLoader_csv(fileLoader_base):
    loadFileType = 'csv'
    
    def loadFile(self):
        """Load file and call setLoadedData().
        
        Use self.filepath for the file path to load
        """
```

The function signature for `setLoadedData` is as follows. There are only two required parameters and a number of optional parameters.

```python
    def setLoadedData(self,
        sweepX : np.ndarray,
        sweepY : np.ndarray,
        sweepC : Optional[np.ndarray] = None,
        recordingMode : recordingModes = recordingModes.iclamp,
        xLabel : str = '',
        yLabel : str = ''):
        
        """
        Parameters
        ----------
        sweepX : np.ndarray
            Time values
        sweepY : np.ndarray
            Recording values, mV or pA
        sweepC : np.ndarray
            (optional) DAC stimulus, pA or mV
        recordingMode : recordingModes
            (optional) Defaults to recordingModes.iclamp)
        xLabel : str
            (optional) str for x-axis label
        yLabel : str
            (optional) str for y-axis label
        """
```
