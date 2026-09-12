## How to write a SanPy plugin.

!!! note
    Runtime loading of external Python plugins is currently disabled (SanPy 2.5, September 2026). The
    example below is retained as a developer reference in
    `examples/user_extensions/plugins/exampleUserPlugin1.py`.

1) Derive a class from [sanpy.interface.plugins.sanpyPlugin](interface/plugins/sanpyPlugin.md)

2) Give you plugin a name by defining the static property `myHumanName = 'Nice name for your plugin`.

3) Build your user interface in a `plot()` member function.

4) Have your plugin respond to the main interface by reploting in a `replot()` member function.
    This is to enable your plugin to respond to different pre-defined interface changes, see below.

Here is a template retained for future extension development.

```python
from sanpy.interface.plugins import sanpyPlugin

class exampleUserPlugin1(sanpyPlugin):
    """
    Plot x/y statistics as a scatter
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
