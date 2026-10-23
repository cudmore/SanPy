
2. Updating an Existing NWB File (Without Re-writing Raw Traces)

To append a spike event table to an existing NWB file containing gigabytes of raw data, you must open the file in append mode ("a"). This instructs PyNWB to modify only the file structural index and add your new table metadata onto the end of the HDF5 file layout container without copying, parsing, or altering the large raw data arrays.
Here is the exact code block to handle downstream analysis updates:
python
from pynwb import NWBHDF5IO
from pynwb.core import DynamicTable
from pynwb.misc import TimeSeriesReferenceVectorData

existing_file_path = "ecephys_spike_analysis.nwb"

# 1. Open the file using append mode "a"
with NWBHDF5IO(existing_file_path, mode="a") as io:
    nwbfile = io.read()
    
    # 2. Grab a reference to the existing raw data stream to use for our links
    # For icephys, this might live in nwbfile.acquisition or via your sweep data arrays
    raw_recording = nwbfile.acquisition["raw_ephys_data"]
    
    # 3. Build your new analysis table
    post_hoc_spike_table = DynamicTable(
        name="recalculated_spike_events",
        description="Spike features appended via a secondary post-hoc analysis script."
    )
    post_hoc_spike_table.add_column(name="spike_amplitude_uV", description="Peak amplitude")
    post_hoc_spike_table.add_column(
        name="raw_data_link",
        description="Link to the target TimeSeries using (TimeSeries, start_index, count)",
        cls=TimeSeriesReferenceVectorData
    )
    
    # 4. Add your computed analysis rows
    post_hoc_spike_table.add_row(
        spike_amplitude_uV=-115.8,
        raw_data_link=(raw_recording, 1205, 60)
    )
    
    # 5. Push the new table container into the analysis group
    nwbfile.add_analysis(post_hoc_spike_table)
    
    # 6. Writing in append mode saves only the changes when exiting the context manager block
    io.write(nwbfile)

print(f"Successfully appended 'recalculated_spike_events' to {existing_file_path} efficiently!")