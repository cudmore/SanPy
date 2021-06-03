## What spike parameters are detected?

We are following the cardiac myocyte nomenclature from this paper:

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

## Detection Parameters

To detect action potentials, we use a number of parameters. These can all be configured using the default setting using [sanpy/detectionParams](../api/detectionParams).

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

When we encounter errors during spike detection, they are stored for each spike in ['errors']. Each error has a name like 'dvdtPercent' as follows

- dvdtPercent: Error searching for percent (10%) of dvdt max. When this occurs, the TOP (mV) of a spike will be more depolarized than it should be.
- preMin: Error searching for spike pre min, the MDP before a spike. This can occur on the first spike if it is close to the beginning of the recording.
- postMin:
- fitEDD: Error while fitting slope of EDD.
- preSpikeDvDt: Error while searching for peak in max ap upstroke (dV/dt) between spike threshold (TOP) and the peak in the first derivative of Vm (dV/dt).
- cycleLength: Usually occurs on last spike when looking for next MDP.
- spikeWidth: Error finding a particular spike with (AP_Dur). Usually occurs when spikes are too broad, can increase detection parameter `hwWindow_ms`.
