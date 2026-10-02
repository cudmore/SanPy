"""Load an example ABF recording and plot one voltage sweep."""

from pathlib import Path

import matplotlib.pyplot as plt

import sanpy


def main() -> None:
    """Load an ABF file, print its basic properties, and plot one sweep.

    Raises:
        RuntimeError: If SanPy cannot load the recording.
    """
    # Locate the example recording relative to the SanPy repository.
    sanpy_root = Path(__file__).resolve().parents[1]
    abf_path = sanpy_root / "sanpy/user_files/SanPy-User-Files/example-data/19114000.abf"

    # Load the recording into SanPy's main analysis object.
    analysis = sanpy.bAnalysis(str(abf_path))
    loader = analysis.fileLoader
    if analysis.loadError or loader is None:
        raise RuntimeError(f"SanPy could not load the ABF file: {abf_path}")

    # Printing the analysis gives a concise summary of the loaded recording.
    print(analysis)

    # The recording mode is an enum; its value is the human-readable label.
    print(f"Recording mode: {loader.recordingMode.value}")

    # Select the first sweep. Sweep numbers are zero-based.
    sweep_number = 0

    # All sweeps share the same time axis, expressed in seconds.
    time_seconds = loader.sweepX

    # Retrieve the recorded membrane voltage for the selected sweep.
    membrane_voltage_mv = loader.get_sweep_y(sweep_number)

    # Plot membrane voltage as a function of time.
    figure, axes = plt.subplots(figsize=(10, 4))
    axes.plot(time_seconds, membrane_voltage_mv)
    axes.set_xlabel("Time (seconds)")
    axes.set_ylabel("Membrane voltage (mV)")
    axes.set_title(f"{loader.filename} — sweep {sweep_number}")
    figure.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
