"""Run a deterministic IKr treatment experiment with the Ten Tusscher model."""

from pathlib import Path

import myokit
import numpy as np
import pandas as pd


def run_treatment() -> None:
    """Run four IKr conductance sweeps and save one SanPy recording."""
    model_file = Path(__file__).with_name("tentusscher-2006.mmt")
    output_dir = Path(__file__).with_name("data")
    output_file = output_dir / "tentusscher-treatment.sanpy"

    # Myokit uses milliseconds. The four epochs span 0.1, 0.9, 8, and 1 s.
    simulation_duration_ms = 10_000
    epoch_boundaries_ms = (100, 1_000, 9_000, simulation_duration_ms)
    log_interval_ms = 0.1

    # Every sweep receives the same deterministic 2 Hz pacing train.
    pacing_frequency_hz = 2.0
    pulse_period_ms = 1_000 / pacing_frequency_hz
    pulse_duration_ms = 1.5
    pulse_level = 0.5

    # IKr conductance represents increasing treatment concentration.
    conductance_fractions = [1.0, 0.9, 0.8, 0.7]
    output_df = pd.DataFrame()
    plot_data: list[tuple[int, np.ndarray, np.ndarray]] = []

    for sweep_number, conductance_fraction in enumerate(conductance_fractions):
        # A fresh model gives every sweep the same initial state.
        model, _, _ = myokit.load(model_file)

        # Replace gKr with the requested fraction of its control value.
        gkr = model.get("ikr.gKr")
        control_gkr = gkr.eval()
        gkr.set_rhs(myokit.Number(control_gkr * conductance_fraction, gkr.unit()))

        # Schedule identical brief AP-triggering pulses throughout epoch 2.
        pacing_protocol = myokit.Protocol()
        pulse_times = np.arange(
            epoch_boundaries_ms[1], epoch_boundaries_ms[2], pulse_period_ms
        )
        for pulse_time in pulse_times:
            pacing_protocol.schedule(pulse_level, float(pulse_time), pulse_duration_ms)

        simulation = myokit.Simulation(model, pacing_protocol)
        data = simulation.run(simulation_duration_ms, log_interval=log_interval_ms)
        time_ms = np.asarray(data["engine.time"])
        voltage_mv = np.asarray(data["membrane.V"])

        # Epoch indices are shared by all sweeps and are contiguous integers.
        epoch_index = np.select(
            [
                time_ms < epoch_boundaries_ms[0],
                time_ms < epoch_boundaries_ms[1],
                time_ms < epoch_boundaries_ms[2],
            ],
            [0, 1, 2],
            default=3,
        ).astype(int)

        # SanPy requires a constant command within each epoch. Store the
        # identical 2 Hz condition rather than the individual pulse edges.
        command = np.where(epoch_index == 2, int(pacing_frequency_hz), 0)

        if sweep_number == 0:
            output_df["seconds"] = time_ms / 1_000
            output_df["epoch_index"] = epoch_index
        output_df[f"mv_{sweep_number}"] = voltage_mv
        output_df[f"cmd_{sweep_number}"] = command
        plot_data.append((int(conductance_fraction * 100), time_ms, voltage_mv))

    # Save before showing the plot so the new file is immediately available.
    output_dir.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_file, index=False)
    print(f"saved: {output_file}")

    import matplotlib.pyplot as plt

    plt.figure()
    for conductance_percent, time_ms, voltage_mv in plot_data:
        plt.plot(
            time_ms / 1_000,
            voltage_mv,
            label=f"IKr conductance {conductance_percent}%",
        )
    plt.xlabel("Time (s)")
    plt.ylabel("Membrane potential (mV)")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    run_treatment()
