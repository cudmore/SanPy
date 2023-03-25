## How to write a SanPy plugin.

1) Derive a class from [sanpy.interface.plugins.sanpyPlugin](interface/plugins/sanpyPlugin.md)

2) Give you plugin a name by defining the static property `myHumanName = 'Nice name for your plugin`.

3) Build your user interface in a `plot()` member function.

4) Have your plugin respond to the main interface by reploting in a `replot()` member function.
    This is to enable your plugin to respond to different pre-defined interface changes, see below.

5) Place you new plugin py file in the `<user>Documents/SanPy/plugins` folder

6) Run SanPy and it will append you plugin to the list of available plugins in the `Plugins Menu`.

**Coming soon.** We will provide unit tests to ensure new plugins is working.

Here is a template to get started. This is the same as gets installed in the User plugin folder file `exampleUserPlugin.py`.

```python
from sanpy.interface.plugins import sanpyPlugin

class exampleUserPlugin1(sanpyPlugin):
    """
    Plot x/y statistics as a scatter

    Get stat names and variables from sanpy.bAnalysisUtil.getStatList()
    """
    myHumanName = 'Example User Plugin 1'

    def plot(self):
        """Create the plot in the widget (called once).
        """
        
        # embed a matplotlib axis (self.axs)
        self.mplWindow2() # assigns (self.fig, self.axs)

        # plot a white line with raw data
        self._lineRaw, = self.axs.plot([], [], '-w', linewidth=0.5)

        # plot red circles with spike threshold
        self._lineDetection, = self.axs.plot([], [], 'ro')

    def replot(self):
        """Replot the widget. Usually when the file is switched
        """
        # get the x/y values from the recording
        sweepX = self.getSweep('x')
        sweepY = self.getSweep('y')

        # update plot of raw data
        self._lineRaw.set_data(sweepX, sweepY)

        # update plot of spike threshold
        thresholdSec = self.ba.getStat('thresholdSec')
        thresholdVal = self.ba.getStat('thresholdVal')
        self._lineDetection.set_data(thresholdSec, thresholdVal)

        # make sure the matplotlib axis auto scale
        self.axs.relim()
        self.axs.autoscale_view(True,True,True)
        
        # plt.draw()
        self.static_canvas.draw()
```

