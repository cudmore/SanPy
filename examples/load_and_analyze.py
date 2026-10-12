"""Load an example ABF recording, detect spikes, and plot the results."""

from pathlib import Path

import matplotlib.pyplot as plt

import sanpy
from sanpy.analysisPlot import bAnalysisPlot

def analyze_folder():

    detection_parameters = sanpy.bDetection().getDetectionDict("Fast Neuron")

    folder_path  = '/Users/cudmore/data/nwb/001261-draft'
    analysis_dir = sanpy.analysisDir(folder_path)

    for row_index in range(analysis_dir.numFiles):
        analysis = analysis_dir.getAnalysis(row_index)
        if analysis is None:
            print(f"Failed to load row {row_index}")
            continue
        # print(analysis)
        analysis.spikeDetect(detection_parameters)

        # debug
        # if row_index == 5:
        #     break

    # save hdf5
    analysis_dir.saveHdf()

def main() -> None:
    """Analyze an example recording and plot detected thresholds and peaks.

    Raises:
        RuntimeError: If SanPy cannot load the recording.
    """
    # Locate the example recording relative to the SanPy repository.
    sanpy_root = Path(__file__).resolve().parents[1]
    abf_path = sanpy_root / "sanpy/user_files/SanPy-User-Files/example-data/19114001.abf"

    # Load the recording into SanPy's main analysis object.
    analysis = sanpy.bAnalysis(str(abf_path))
    if analysis.loadError or analysis.fileLoader is None:
        raise RuntimeError(f"SanPy could not load the ABF file: {abf_path}")

    # Start with the bundled parameters for sinoatrial node recordings.
    detection_parameters = sanpy.bDetection().getDetectionDict("SA Node")

    # Presets are ordinary dictionaries, so individual parameters can be
    # adjusted for a particular experiment. dV/dt is measured in mV/ms.
    detection_parameters["dvdtThreshold"] = 30

    # Detect spikes across every sweep in the recording.
    analysis.spikeDetect(detection_parameters)

    # The analysis summary now includes the number of detected spikes.
    print(analysis)
    print(f"Detection preset: {detection_parameters['detectionName']}")
    print(f"dV/dt threshold: {detection_parameters['dvdtThreshold']} mV/ms")

    # Plot the membrane voltage and overlay each detected threshold and peak.
    plotter = bAnalysisPlot(analysis)
    axes = plotter.plotSpikes(plotThreshold=True, plotPeak=True)
    axes.legend()
    plt.show()


if __name__ == "__main__":
    # main()
    analyze_folder()
