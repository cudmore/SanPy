
1. Handling the Protocol "Epoch Table" in Intracellular Ephys

For intracellular electrophysiology (icephys), NWB provides a dedicated set of tables to organize sequential sweeps, including the sweep_table and the IntracellularElectrodesTable / SimultaneousRecordingsTable hierarchy.
To keep your design clean and KISS, you have two solid architectural choices for your protocol metadata:

Option A: Direct Columns in the sweep_table (Simplest if epochs are uniform)

If every sweep has a fixed sequence of epochs (e.g., Epoch 1 is always a baseline, Epoch 2 is always a step, Epoch 3 is recovery), you can append custom columns directly to NWB's native sweep_table.
python
# Assuming you have a standard icephys setup
nwbfile.sweep_table.add_column(name='epoch_2_level_pA', description='Current step amplitude for epoch 2')
nwbfile.sweep_table.add_column(name='epoch_2_duration_pnts', description='Duration of epoch 2')
Use code with caution.

Option B: A Secondary DynamicTable mapped to Sweeps (Recommended for varying epochs)

If your sweeps have a variable number of epochs (e.g., Sweep 1 has 3 epochs, Sweep 2 has a multi-step ramp with 5 epochs), create a dedicated DynamicTable in the analysis or stimulus group. You can link each epoch row back to its parent sweep number.
python
from pynwb.core import DynamicTable

# Create an explicit protocol description table
protocol_table = DynamicTable(
    name="stimulus_protocol_epochs",
    description="Describes the programmatic protocol sequence generating the stimulus output."
)

# Define your columns
protocol_table.add_column(name="sweep_number", description="The sequential sweep ID (0-indexed)")
protocol_table.add_column(name="epoch_index", description="The ordered position of the epoch within this sweep")
protocol_table.add_column(name="epoch_start_pnt", description="Starting sample point index")
protocol_table.add_column(name="epoch_stop_pnt", description="Stopping sample point index")
protocol_table.add_column(name="epoch_level", description="Target command level (nA or Amps)")
protocol_table.add_column(name="epoch_type", description="Type of waveform ('dc', 'ramp', 'sin')")

# Example: Adding 2 epochs belonging to Sweep 0
protocol_table.add_row(sweep_number=0, epoch_index=0, epoch_start_pnt=0, epoch_stop_pnt=3000, epoch_level=0.0, epoch_type="dc")
protocol_table.add_row(sweep_number=0, epoch_index=1, epoch_start_pnt=3000, epoch_stop_pnt=15000, epoch_level=0.250, epoch_type="dc")

nwbfile.add_analysis(protocol_table)
