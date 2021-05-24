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

## Detection Errors

When we encounter errors during spike detection, they are stored for each spike in ['errors']. Each error has a name like 'dvdtPercent' as follows

- dvdtPercent: Error searching for percent (10%) of dvdt max. When this occurs, the TOP (mV) of a spike will be more depolarized than it should be.
- preMin: Error searching for spike pre min, the MDP before a spike. This can occur on the first spike if it is close to the beginning of the recording.
- postMin:
- fitEDD: Error while fitting slope of EDD.
- preSpikeDvDt: Error while searching for peak in max ap upstroke (dV/dt) between spike threshold (TOP) and the peak in the first derivative of Vm (dV/dt).
- cycleLength: Usually occurs on last spike when looking for next MDP.
- spikeWidth: Error finding a particular spike with (AP_Dur). Usually occurs when spikes are too broad, can increase detection parameter `hwWindow_ms`.
