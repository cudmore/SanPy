
- Set priminence to 1.8 or 2.0
- set roi rect left to 100 (to skip bleaching)

20250527

1) shift roi to remove transient (bleaching) in control.
    Will shift roi same amount in Ivab and Thap

2) rerun detection, less aggressive prominence.
    First run was 1.0, second run was 1.8 (too aggressive)

3) Are you 100% confident that your rois were made in the same order?
    I will write code to show each to visually verify.

4) *** Add kym image/roi to browser, make pdf folder

5) finish implementing picker for line plot

6) Come up with a simple metric to validate control kymograph

7) script to generate pdf reports for ALL cells, one pdf per roi
    - normalize to f0
    
8) add legend to mpl browser
