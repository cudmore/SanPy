## Kymograph analysis (Aug 6, 2023)

For each original tif file, we save two text files with the analysis (using the csv extension).

**Please note**, both these text files start with a one line header. If you import into a plotting program, make sure you skip the header.

For example, original tif file `cell 05_C002T001.tif` yields two files:

### 1) Peak Analysis File
 - `cell 05_C002T001.csv`: The **peak analysis**, similar to action potential analysis. One row per peak (action potential).

 
Each row in the csv represents the analysis for one detected peak (e.g. action potential). Please note, I have normalized the sum intensity for each line scan, these are not actual intensity values. In general the intensity is monotonically decreasing presumably due to bleaching. We can discuss this. 

Useful columns are as follows:

    thresholdSec. Time of take off for the peak (s).

    thresholdVal. Intensity value at take off (normalized).
    
    peakVal. Maximum intensity of the peak (normalized).

    peakHeight. Height of the peak between peak threshold and peakVal.

    widths_50. Half width of the peak (ms).

#### Additional columns analyzing diameter change after the AP

    k_diam_foot. Baseline diameter, just befor start of AP (um).
        
    k_diam_foot_sec. Time of foot measurement (s).
    
    k_diam_peak. Peak diameter after the AP (um).
        
    k_diam_peak_sec. Time of peak diameter (s).
    
    k_diam_time_to_peak_sec.
        Time to peak diameter change, k_diam_peak_sec  - thresholdSec (s).
    
    k_diam_amp.
        Difference between k_diam_foot and k_diam_peak (um).
    
    k_diam_percent.
        Percent change in diamter between k_diam_foot and k_diam_peak (%).
    
### 2) Diameter Analysis File
 - `cell 05_C002T001-diam.csv`: The Kymograph **diameter analysis**. One row per line scan in the kymograph.

Each row in the csv file corresponds to one line scan in the Kymograph. If you scanned 10,0000 lines, this file will have 10,000 rows of analysis.

The final values in this file are calculated by using the rectangular ROI that was drawn on the kymograph image during analysis in SanPy.

If you want to plot the sum intensity and the diameter for each kymograph, this is what you want!

Useful columns are as follows:
 
    time_sec. Time of the line scan (s).

    sumintensity_raw. Raw sum intensity of the line scan.

    sumintensity. Sum intensity normalized to maximum (range is 0 to 1).
    
    sumintensity_filt. Filtered sumintensity after median filter.

    diameter_um. Diameter estimate for the line scan (um).

    diameter_um_filt.
        Filtered diameter estimate for the line scan after median filter (um).

    minInt. Minimum intensity in the analyzed line scan.

    maxInt. Maximum intensity in the analyzed line scan.

    rangeInt.
        Range of intensities in the analyzed line scan (if low then low SNR).