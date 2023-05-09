
## Detection Parameters

To detect action potentials, SanPy uses a number of parameters. These can all be configured using the [detection parameter plugin](../plugins/#detection-parameters) or programmatically with the API [sanpy/detectionParams](../api/bDetection).

Note: To update this table use sanpy/bDetection.py

|    | Parameter          | Default Value        | Units   | Human Readable                          | Description                                                                                            |
|---:|:-------------------|:---------------------|:--------|:----------------------------------------|:-------------------------------------------------------------------------------------------------------|
|  0 | dvdtThreshold      | 100                  | dVdt    | dV/dt Threshold                         | dV/dt threshold for a spike, will be backed up to dvdt_percentOfMax and have xxx error when this fails |
|  1 | mvThreshold        | -20                  | mV      | mV Threshold                            | mV threshold for spike AND minimum spike mV when detecting with dV/dt                                  |
|  2 | dvdt_percentOfMax  | 0.1                  | Percent | dV/dt Percent of max                    | For dV/dt detection, the final TOP is when dV/dt drops to this percent from dV/dt AP peak              |
|  3 | onlyPeaksAbove_mV  |                      | mV      | Accept Peaks Above (mV)                 | For dV/dt detection, only accept APs above this value (mV)                                             |
|  4 | doBackupSpikeVm    | True                 | Boolean | Backup Vm Spikes                        | If true, APs detected with just mV will be backed up until Vm falls to xxx                             |
|  5 | refractory_ms      | 170                  | ms      | Minimum AP interval (ms)                | APs with interval (with respect to previous AP) less than this will be removed                         |
|  6 | peakWindow_ms      | 100                  | ms      | Peak Window (ms)                        | Window after TOP (ms) to seach for AP peak (mV)                                                        |
|  7 | dvdtPreWindow_ms   | 10                   | ms      | dV/dt Pre Window (ms)                   | Window (ms) to search before each TOP for real threshold crossing                                      |
|  8 | mdp_ms             | 250                  | ms      | Pre AP MDP window (ms)                  | Window (ms) before an AP to look for MDP                                                               |
|  9 | avgWindow_ms       | 5                    | ms      |                                         | Window (ms) to calculate MDP (mV) as a mean rather than mV at single point for MDP                     |
| 10 | halfHeights        | [10, 20, 50, 80, 90] |         | AP Durations (%)                        | AP Durations as percent of AP height (AP Peak (mV) - TOP (mV))                                         |
| 11 | halfWidthWindow_ms | 200                  | ms      | Half Width Window (ms)                  | Window (ms) after TOP to look for AP Durations                                                         |
| 12 | medianFilter       | 0                    | points  | Median Filter Points                    | Number of points in median filter, must be odd, 0 for no filter                                        |
| 13 | SavitzkyGolay_pnts | 5                    | points  | SavitzkyGolay Filter Points             | Number of points in SavitzkyGolay filter, must be odd, 0 for no filter                                 |
| 14 | SavitzkyGolay_poly | 2                    |         | Savitzky-Golay Filter Polynomial Degree | The degree of the polynomial for Savitzky-Golay filter                                                 |
| 15 | spikeClipWidth_ms  | 500                  | ms      | AP Clip Width (ms)                      | The width/duration of generated AP clips                                                               |

## Detection Errors

When SanPy encounters errors during spike detection, they are stored for each spike in ['errors']. Each error has a name like 'dvdtPercent' as follows

- **dvdtPercent**: Error searching for percent (10%) of dvdt max. When this occurs, the TOP (mV) of a spike will be more depolarized than it should be.
- **preMin**: Error searching for spike pre min, the MDP before a spike. This can occur on the first spike if it is close to the beginning of the recording.
- **postMin**:
- **fitEDD**: Error while fitting slope of EDD.
- **preSpikeDvDt**: Error while searching for peak in max ap upstroke (dV/dt) between spike threshold (TOP) and the peak in the first derivative of Vm (dV/dt).
- **cycleLength**: Usually occurs on last spike when looking for next MDP.
- **spikeWidth**: Error finding a particular spike with (AP_Dur). Usually occurs when spikes are too broad, can increase detection parameter `hwWindow_ms`.

# Analysis results

Once spike are detected, SanPy has the following analysis results.

|    | Stat                              | name                       | units   | yStat                      | yStatUnits   | xStat                  | xStatUnits   |
|---:|:----------------------------------|:---------------------------|:--------|:---------------------------|:-------------|:-----------------------|:-------------|
|  0 | Take Off Potential (s)            | thresholdSec               | s       | thresholdVal               | mV           | thresholdSec           | s            |
|  1 | Take Off Potential (mV)           | thresholdVal               | mV      | thresholdVal               | mV           | thresholdPnt           | Points       |
|  2 | Spike Frequency (Hz)              | spikeFreq_hz               | Hz      | spikeFreq_hz               | Hz           | thresholdPnt           | Points       |
|  3 | Cycle Length (ms)                 | cycleLength_ms             | ms      | cycleLength_ms             | ms           | thresholdPnt           | Points       |
|  4 | AP Peak (mV)                      | peakVal                    | mV      | peakVal                    | mV           | peakPnt                | Points       |
|  5 | AP Height (mV)                    | peakHeight                 | mV      | peakHeight                 | mV           | peakPnt                | Points       |
|  6 | Pre AP Min (mV)                   | preMinVal                  | mV      | preMinVal                  | mV           | preMinPnt              | Points       |
|  7 | Post AP Min (mV)                  | postMinVal                 | mV      | postMinVal                 | mV           | postMinPnt             | Points       |
|  8 | Early Diastolic Depol Rate (dV/s) | earlyDiastolicDurationRate | dV/s    | earlyDiastolicDurationRate | dV/s         |                        |              |
|  9 | Early Diastolic Duration (ms)     | earlyDiastolicDuration_ms  | ms      | earlyDiastolicDuration_ms  | dV/s         | thresholdPnt           | Points       |
| 10 | Diastolic Duration (ms)           | diastolicDuration_ms       | ms      | diastolicDuration_ms       | dV/s         | thresholdPnt           | Points       |
| 11 | Max AP Upstroke (mV)              | preSpike_dvdt_max_val      | mV      | preSpike_dvdt_max_val      | dV/s         | preSpike_dvdt_max_pnt  | Points       |
| 12 | Max AP Upstroke (dV/dt)           | preSpike_dvdt_max_val2     | dV/dt   | preSpike_dvdt_max_val2     | dV/dt        | preSpike_dvdt_max_pnt  | Points       |
| 13 | Max AP Repolarization (mV)        | postSpike_dvdt_min_val     | mV      | postSpike_dvdt_min_val     | mV           | postSpike_dvdt_min_pnt | Points       |
| 14 | AP Duration (ms)                  | apDuration_ms              | ms      | apDuration_ms              | ms           | thresholdPnt           | Points       |
| 15 | Half Width 10 (ms)                | nan                        | nan     | widths_10                  | ms           |                        |              |
| 16 | Half Width 20 (ms)                | nan                        | nan     | widths_20                  | ms           |                        |              |
| 17 | Half Width 50 (ms)                | nan                        | nan     | widths_50                  | ms           |                        |              |
| 18 | Half Width 80 (ms)                | nan                        | nan     | widths_80                  | ms           |                        |              |
| 19 | Half Width 90 (ms)                | nan                        | nan     | widths_90                  | ms           |                        |              |
| 20 | Ca++ Delay (s)                    | nan                        | nan     | caDelay_sec                | s            |                        |              |
| 21 | Ca++ Width (ms)                   | nan                        | nan     | caWidth_ms                 | ms           |                        |              |

# Analysis results (full)

<!-- <iframe src="../static/analysis-output-full.html" width="800" height="800" style="border: 0" seamless></iframe> -->

Generated 2023-03-24 with sanpy.analysisVersion 20230324a

Note: To update this table use sanpy/bAnalysisResults.py

<table border="1" class="dataframe" style="width:600">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Name</th>
      <th>type</th>
      <th>default</th>
      <th>units</th>
      <th>depends on detection</th>
      <th>error</th>
      <th>description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>analysisDate</td>
      <td>str</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>Date of analysis in yyyymmdd format.</td>
    </tr>
    <tr>
      <th>1</th>
      <td>analysisTime</td>
      <td>str</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>Time of analysis in hh:mm:ss 24 hours format.</td>
    </tr>
    <tr>
      <th>2</th>
      <td>modDate</td>
      <td>str</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>Modification date if AP is modified after detection.</td>
    </tr>
    <tr>
      <th>3</th>
      <td>modTime</td>
      <td>str</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>Modification time if AP is modified after detection.</td>
    </tr>
    <tr>
      <th>4</th>
      <td>analysisVersion</td>
      <td>str</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>Analysis version when analysis was run. See sanpy.analysisVersion</td>
    </tr>
    <tr>
      <th>5</th>
      <td>interfaceVersion</td>
      <td>str</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>Interface version string when analysis was run. See sanpy.interfaceVersion</td>
    </tr>
    <tr>
      <th>6</th>
      <td>file</td>
      <td>str</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>Name of raw data file analyzed</td>
    </tr>
    <tr>
      <th>7</th>
      <td>detectionType</td>
      <td></td>
      <td>None</td>
      <td></td>
      <td></td>
      <td></td>
      <td>Type of detection, either vm or dvdt. See enum sanpy.bDetection.detectionTypes</td>
    </tr>
    <tr>
      <th>8</th>
      <td>cellType</td>
      <td>str</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>User specified cell type</td>
    </tr>
    <tr>
      <th>9</th>
      <td>sex</td>
      <td>str</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>User specified sex</td>
    </tr>
    <tr>
      <th>10</th>
      <td>condition</td>
      <td>str</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td>User specified condition</td>
    </tr>
    <tr>
      <th>11</th>
      <td>sweep</td>
      <td>int</td>
      <td>0</td>
      <td></td>
      <td></td>
      <td></td>
      <td>Sweep number of analyzed sweep. Zero based.</td>
    </tr>
    <tr>
      <th>12</th>
      <td>epoch</td>
      <td>int</td>
      <td>NaN</td>
      <td></td>
      <td></td>
      <td></td>
      <td>Stimulus epoch number the spike occured in. Zero based.</td>
    </tr>
    <tr>
      <th>13</th>
      <td>epochLevel</td>
      <td>float</td>
      <td>NaN</td>
      <td></td>
      <td></td>
      <td></td>
      <td>Epoch level (DAC) stimulus during the spike.</td>
    </tr>
    <tr>
      <th>14</th>
      <td>sweepSpikeNumber</td>
      <td>int</td>
      <td>None</td>
      <td></td>
      <td></td>
      <td></td>
      <td>Spike number within the sweep. Zero based.</td>
    </tr>
    <tr>
      <th>15</th>
      <td>spikeNumber</td>
      <td>int</td>
      <td>None</td>
      <td></td>
      <td></td>
      <td></td>
      <td>Spike number across all sweeps. Zero based.</td>
    </tr>
    <tr>
      <th>16</th>
      <td>include</td>
      <td>bool</td>
      <td>True</td>
      <td></td>
      <td></td>
      <td></td>
      <td>Boolean indication include or not. Can be set by user/programmatically  after analysis.</td>
    </tr>
    <tr>
      <th>17</th>
      <td>userType</td>
      <td>int</td>
      <td>0</td>
      <td></td>
      <td></td>
      <td></td>
      <td>Integer indication user type. Can be set by user/programmatically  after analysis.</td>
    </tr>
    <tr>
      <th>18</th>
      <td>errors</td>
      <td>list</td>
      <td>[]</td>
      <td></td>
      <td></td>
      <td></td>
      <td>List of dictionary to hold detection errors for this spike</td>
    </tr>
    <tr>
      <th>19</th>
      <td>dvdtThreshold</td>
      <td>float</td>
      <td>NaN</td>
      <td>dvdt</td>
      <td>dvdtThreshold</td>
      <td></td>
      <td>AP Threshold in derivative dv/dt</td>
    </tr>
    <tr>
      <th>20</th>
      <td>mvThreshold</td>
      <td>float</td>
      <td>NaN</td>
      <td>mV</td>
      <td>mvThreshold</td>
      <td></td>
      <td>AP Threshold in primary recording mV</td>
    </tr>
    <tr>
      <th>21</th>
      <td>medianFilter</td>
      <td>int</td>
      <td>0</td>
      <td></td>
      <td>medianFilter</td>
      <td></td>
      <td>Median filter to generate filtered vm and dvdt. Value 0 indicates no filter.</td>
    </tr>
    <tr>
      <th>22</th>
      <td>halfHeights</td>
      <td>list</td>
      <td>[]</td>
      <td></td>
      <td>halfHeights</td>
      <td></td>
      <td>List of int to specify half-heights like [10, 20, 50, 80, 90].</td>
    </tr>
    <tr>
      <th>23</th>
      <td>thresholdPnt</td>
      <td>int</td>
      <td>NaN</td>
      <td>point</td>
      <td></td>
      <td></td>
      <td>AP threshold point</td>
    </tr>
    <tr>
      <th>24</th>
      <td>thresholdSec</td>
      <td>float</td>
      <td>NaN</td>
      <td>sec</td>
      <td></td>
      <td></td>
      <td>AP threshold seconds</td>
    </tr>
    <tr>
      <th>25</th>
      <td>thresholdVal</td>
      <td>float</td>
      <td>NaN</td>
      <td>mV</td>
      <td></td>
      <td></td>
      <td>Value of Vm at AP threshold point.</td>
    </tr>
    <tr>
      <th>26</th>
      <td>thresholdVal_dvdt</td>
      <td>float</td>
      <td>NaN</td>
      <td>dvdt</td>
      <td></td>
      <td></td>
      <td>Value of dvdt at AP threshold point.</td>
    </tr>
    <tr>
      <th>27</th>
      <td>dacCommand</td>
      <td>float</td>
      <td>NaN</td>
      <td>mV</td>
      <td></td>
      <td></td>
      <td>Value of DAC command at AP threshold point.</td>
    </tr>
    <tr>
      <th>28</th>
      <td>peakPnt</td>
      <td>int</td>
      <td>NaN</td>
      <td>point</td>
      <td>(onlyPeaksAbove_mV, peakWindow_ms)</td>
      <td></td>
      <td>AP peak point.</td>
    </tr>
    <tr>
      <th>29</th>
      <td>peakSec</td>
      <td>float</td>
      <td>NaN</td>
      <td>sec</td>
      <td></td>
      <td></td>
      <td>AP peak seconds.</td>
    </tr>
    <tr>
      <th>30</th>
      <td>peakVal</td>
      <td>float</td>
      <td>NaN</td>
      <td>mV</td>
      <td></td>
      <td></td>
      <td>Value of Vm at AP peak point.</td>
    </tr>
    <tr>
      <th>31</th>
      <td>peakHeight</td>
      <td>float</td>
      <td>NaN</td>
      <td>mV</td>
      <td></td>
      <td></td>
      <td>Difference between peakVal minus thresholdVal.</td>
    </tr>
    <tr>
      <th>32</th>
      <td>timeToPeak_ms</td>
      <td>float</td>
      <td>NaN</td>
      <td>ms</td>
      <td></td>
      <td></td>
      <td>Time to peak (ms) after TOP.</td>
    </tr>
    <tr>
      <th>33</th>
      <td>preMinPnt</td>
      <td>int</td>
      <td>NaN</td>
      <td>point</td>
      <td>mdp_ms</td>
      <td></td>
      <td>Minimum before an AP taken from predefined window.</td>
    </tr>
    <tr>
      <th>34</th>
      <td>preMinVal</td>
      <td>float</td>
      <td>NaN</td>
      <td>mV</td>
      <td></td>
      <td></td>
      <td>Minimum before an AP taken from predefined window.</td>
    </tr>
    <tr>
      <th>35</th>
      <td>preLinearFitPnt0</td>
      <td>int</td>
      <td>NaN</td>
      <td>point</td>
      <td></td>
      <td></td>
      <td>Point where pre linear fit starts. Used for EDD Rate</td>
    </tr>
    <tr>
      <th>36</th>
      <td>preLinearFitPnt1</td>
      <td>int</td>
      <td>NaN</td>
      <td>point</td>
      <td></td>
      <td></td>
      <td>Point where pre linear fit stops. Used for EDD Rate</td>
    </tr>
    <tr>
      <th>37</th>
      <td>earlyDiastolicDuration_ms</td>
      <td>float</td>
      <td>NaN</td>
      <td>ms</td>
      <td></td>
      <td></td>
      <td>Time (ms) between start/stop of EDD.</td>
    </tr>
    <tr>
      <th>38</th>
      <td>preLinearFitVal0</td>
      <td>float</td>
      <td>NaN</td>
      <td>mv</td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <th>39</th>
      <td>preLinearFitVal1</td>
      <td>float</td>
      <td>NaN</td>
      <td>mv</td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <th>40</th>
      <td>earlyDiastolicDurationRate</td>
      <td>float</td>
      <td>NaN</td>
      <td>mv/S</td>
      <td></td>
      <td></td>
      <td>Early diastolic duration rate, the slope of the linear fit between start/stop of EDD.</td>
    </tr>
    <tr>
      <th>41</th>
      <td>lateDiastolicDuration</td>
      <td>float</td>
      <td>NaN</td>
      <td></td>
      <td></td>
      <td></td>
      <td>Depreciated</td>
    </tr>
    <tr>
      <th>42</th>
      <td>preSpike_dvdt_max_pnt</td>
      <td>int</td>
      <td>NaN</td>
      <td>point</td>
      <td></td>
      <td></td>
      <td>Point corresponding to peak in dv/dt before an AP.</td>
    </tr>
    <tr>
      <th>43</th>
      <td>preSpike_dvdt_max_val</td>
      <td>float</td>
      <td>NaN</td>
      <td>mV</td>
      <td></td>
      <td></td>
      <td>Value of Vm at peak of dv/dt before an AP.</td>
    </tr>
    <tr>
      <th>44</th>
      <td>preSpike_dvdt_max_val2</td>
      <td>float</td>
      <td>NaN</td>
      <td>dv/dt</td>
      <td></td>
      <td></td>
      <td>Value of dv/dt at peak of dv/dt before an AP.</td>
    </tr>
    <tr>
      <th>45</th>
      <td>postSpike_dvdt_min_pnt</td>
      <td>int</td>
      <td>NaN</td>
      <td>point</td>
      <td>dvdtPostWindow_ms</td>
      <td></td>
      <td>Point corresponding to min in dv/dt after an AP.</td>
    </tr>
    <tr>
      <th>46</th>
      <td>postSpike_dvdt_min_val</td>
      <td>float</td>
      <td>NaN</td>
      <td>mV</td>
      <td></td>
      <td></td>
      <td>Value of Vm at minimum of dv/dt after an AP.</td>
    </tr>
    <tr>
      <th>47</th>
      <td>postSpike_dvdt_min_val2</td>
      <td>float</td>
      <td>NaN</td>
      <td>dvdt</td>
      <td></td>
      <td></td>
      <td>Value of dv/dt at minimum of dv/dt after an AP.</td>
    </tr>
    <tr>
      <th>48</th>
      <td>isi_pnts</td>
      <td>int</td>
      <td>NaN</td>
      <td>point</td>
      <td>refractory_ms</td>
      <td></td>
      <td>Inter-Spike-Interval (points) with respect to previous AP.</td>
    </tr>
    <tr>
      <th>49</th>
      <td>isi_ms</td>
      <td>float</td>
      <td>NaN</td>
      <td>ms</td>
      <td></td>
      <td></td>
      <td>Inter-Spike-Interval (ms) with respect to previous AP.</td>
    </tr>
    <tr>
      <th>50</th>
      <td>spikeFreq_hz</td>
      <td>float</td>
      <td>NaN</td>
      <td>Hz</td>
      <td></td>
      <td></td>
      <td>AP frequency with respect to previous AP.</td>
    </tr>
    <tr>
      <th>51</th>
      <td>cycleLength_pnts</td>
      <td>int</td>
      <td>NaN</td>
      <td>point</td>
      <td></td>
      <td></td>
      <td>Points between APs with respect to previous AP.</td>
    </tr>
    <tr>
      <th>52</th>
      <td>cycleLength_ms</td>
      <td>int</td>
      <td>NaN</td>
      <td>point</td>
      <td></td>
      <td></td>
      <td>Time (ms) between APs with respect to previous AP.</td>
    </tr>
    <tr>
      <th>53</th>
      <td>diastolicDuration_ms</td>
      <td>float</td>
      <td>NaN</td>
      <td>ms</td>
      <td></td>
      <td></td>
      <td>Time (ms) between minimum before AP (preMinPnt) and AP time (thresholdPnt).</td>
    </tr>
    <tr>
      <th>54</th>
      <td>widths</td>
      <td>list</td>
      <td>[]</td>
      <td></td>
      <td></td>
      <td></td>
      <td>A list of dict to hold half-height information for each half-height in detection halfHeights.</td>
    </tr>
    <tr>
      <th>55</th>
      <td>widths_10</td>
      <td>int</td>
      <td>NaN</td>
      <td>percent</td>
      <td>halfWidthWindow_ms</td>
      <td></td>
      <td>Width (ms) at half-height 10 %.</td>
    </tr>
    <tr>
      <th>56</th>
      <td>widths_20</td>
      <td>int</td>
      <td>NaN</td>
      <td>percent</td>
      <td>halfWidthWindow_ms</td>
      <td></td>
      <td>Width (ms) at half-height 20 %.</td>
    </tr>
    <tr>
      <th>57</th>
      <td>widths_50</td>
      <td>int</td>
      <td>NaN</td>
      <td>percent</td>
      <td>halfWidthWindow_ms</td>
      <td></td>
      <td>Width (ms) at half-height 50 %.</td>
    </tr>
    <tr>
      <th>58</th>
      <td>widths_80</td>
      <td>int</td>
      <td>NaN</td>
      <td>percent</td>
      <td>halfWidthWindow_ms</td>
      <td></td>
      <td>Width (ms) at half-height 80 %.</td>
    </tr>
    <tr>
      <th>59</th>
      <td>widths_90</td>
      <td>int</td>
      <td>NaN</td>
      <td>percent</td>
      <td>halfWidthWindow_ms</td>
      <td></td>
      <td>Width (ms) at half-height 90 %.</td>
    </tr>
  </tbody>
</table>
<br>

# What spike parameters are detected?

For cardiac myocyte analysis, SanPy follows the nomenclature from this paper:

[Larson, et al (2013) Depressed pacemaker activity of sinoatrial node
myocytes contributes to the age-dependent decline in maximum heart rate. PNAS 110(44):18011-18016][larson et al 2013]

- MDP and Vmax were defined as the most negative and positive membrane potentials, respectively
- Take-off potential (TOP) was defined as the membrane potential when the first derivative of voltage with respect to time (dV/dt) reached 10% of its maximum value
- Cycle length was defined as the interval between MDPs in successive APs
- The maximum rates of the AP upstroke and repolarization were taken as the maximum and minimum values of the first derivative (dV/dtmax and dV/dtmin, respectively)
- [[[REMOVED 20210501]]] Action potential duration (APD) was defined as the interval between the TOP and the subsequent MDP
- APD_50 and APD_90 were defined as the interval between the TOP and 50% and 90% repolarization, respectively
- The diastolic duration was defined as the interval between MDP and TOP
- The early diastolic depolarization rate was estimated as the slope of a linear fit between 10% and 50% of the diastolic duration and the early diastolic duration was the corresponding time interval
- The nonlinear late diastolic depolarization phase was estimated as the duration between 1% and 10% dV/dt

[larson et al 2013]: https://www.ncbi.nlm.nih.gov/pubmed/24128759

