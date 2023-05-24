## How to extend the analysis of SanPy with user specified analysis

The core analysis algorithm of SanPy can be easily extended by the user.

 - Derive a class from [sanpy.user_analysis.baseUserAnalysis](userAnalysis/baseUserAnalysis.md)
 - In the member function `defineUserStats()`, define the name of your new analysis with addUserStat()
 - In the member function `run()`, for each spike in the analysis,
    calculate your new stat and set the value with `setSpikeValue()`.

Here is a simple example to get you started.

```python
class exampleUserAnalysis(baseUserAnalysis):
    """
    An example user defined analysis.

    We will add 'User Time To Peak (ms)', defines as:
        For each AP, the time interval between spike threshold and peak

    We need to define the behavior of two inherited functions

    1) defineUserStats()
        add any numner of user stats with
            addUserStat(human_name, internal_name)

    2) run()
        Run the analysis you want to compute.
        Add the value for each spike with
            setSpikeValue(spike_index, internal_name, new_value)
    """

    def defineUserStats(self):
        """Add your user stats here."""
        self.addUserStat("User Time To Peak (ms)", "user_timeToPeak_ms")

    def run(self):
        """This is the user code to create and then fill in
            a new name/value for each spike."""

        # get filtered vm for the entire trace
        # filteredVm = self.getFilteredVm()

        for spikeIdx, spikeDict in enumerate(self.ba.spikeDict):
            
            # add time to peak
            thresholdSec = spikeDict["thresholdSec"]
            peakSecond = spikeDict["peakSec"]
            timeToPeak_ms = (peakSecond - thresholdSec) * 1000

            # assign to underlying bAnalysis
            self.setSpikeValue(spikeIdx, "user_timeToPeak_ms", timeToPeak_ms)
```