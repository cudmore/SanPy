
## Updates 20201109

- Added 'Early Diastolic Depol Rate (dV/s)' to saved Excel report
- Removed open file dialog when default path is not found
- When saving Excel file with 'Save Spike Report' button, we no longer save a .txt file. To also save a .txt file, use Shift+Click
- Fixed  errors when an .abf file is corrupt (will keep adding error checking as we find more)
- Added checkboxes to toggle dV/dt and Scatter (Like Clips)

- Added dark mode
- Reduced size of interface buttons and lists to maximize the area we use for plotting
- Export to pdf now uses lines only (no markers)

example/reanalyze.py, reanalyze from an excel file giving us threshold and start/stop time

examples/manuscript0.py, plot stat across (condition, region),
