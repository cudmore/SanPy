"""Run a small stochastic Myokit current-step experiment and save it for SanPy.

See:
https://github.com/MichaelClerx/myokit/blob/main/examples/1-1-simulating-an-action-potential.ipynb

20260910

had to install:
brew install sundials

then check sundials with
uv run python -m myokit sundials
"""
import numpy as np
import pandas as pd

import myokit
import myokit.lib.markov as markov


def run_my_myokit() -> None:
    """Run noisy current-step sweeps and save one ``.sanpy`` file."""
    model_file = "sanpy/models/tentusscher-2006.mmt"
    model, _, _ = myokit.load(model_file)

    # Myokit uses milliseconds. These boundaries make four epochs over 10 s:
    # 0: short fake start, 1: baseline, 2: current step, 3: recovery.
    simulation_duration_ms = 10_000
    epoch_boundaries_ms = (100, 1_000, 9_000, simulation_duration_ms)
    log_interval_ms = 0.1

    # Each command produces one sweep at a reasonable cardiac pacing frequency.
    command_values = [0, 1, 2, 3, 4, 5]
    pacing_frequencies_hz = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

    # A new pulse-timing jitter realization is generated for each sweep.
    rng = np.random.default_rng()
    pulse_duration_ms = 1.5
    pulse_level = 0.5
    pulse_jitter_ms = 50

    output_df = pd.DataFrame()
    plot_data: list[tuple[float, np.ndarray, np.ndarray]] = []

    for sweep_number, (command_value, pacing_frequency_hz) in enumerate(
        zip(command_values, pacing_frequencies_hz)
    ):
        # Schedule brief AP-triggering pulses throughout epoch 2.
        pacing_protocol = myokit.Protocol()
        pulse_period_ms = 1_000 / pacing_frequency_hz
        pulse_times = np.arange(
            epoch_boundaries_ms[1], epoch_boundaries_ms[2], pulse_period_ms
        )
        pulse_times += rng.uniform(-pulse_jitter_ms, pulse_jitter_ms, len(pulse_times))
        pulse_times = np.clip(
            pulse_times,
            epoch_boundaries_ms[1],
            epoch_boundaries_ms[2] - pulse_duration_ms,
        )
        for pulse_time in pulse_times:
            pacing_protocol.schedule(
                pulse_level, float(pulse_time), pulse_duration_ms
            )

        simulation = myokit.Simulation(model, pacing_protocol)
        data = simulation.run(
            simulation_duration_ms,
            log_interval=log_interval_ms,
        )

        time_ms = np.asarray(data["engine.time"])
        voltage_mv = np.asarray(data["membrane.V"])

        # Epoch indices are shared by every sweep and must be contiguous ints.
        epoch_index = np.select(
            [
                time_ms < epoch_boundaries_ms[0],
                time_ms < epoch_boundaries_ms[1],
                time_ms < epoch_boundaries_ms[2],
            ],
            [0, 1, 2],
            default=3,
        ).astype(int)

        # Export the requested clean integer command, not the injected noise.
        command = np.where(epoch_index == 2, command_value, 0).astype(int)

        if sweep_number == 0:
            output_df["seconds"] = time_ms / 1_000
            output_df["epoch_index"] = epoch_index
        output_df[f"mv_{sweep_number}"] = voltage_mv
        output_df[f"cmd_{sweep_number}"] = command
        plot_data.append((pacing_frequency_hz, time_ms, voltage_mv))

    save_file = "tentusscher.sanpy"
    print("saving:", save_file)
    print(output_df.head())
    output_df.to_csv(save_file, index=False)

    import matplotlib.pyplot as plt

    # Display every sweep so the effects of command amplitude and noise can be
    # inspected before loading the exported recording in SanPy.
    plt.figure()
    for pacing_frequency_hz, time_ms, voltage_mv in plot_data:
        plt.plot(time_ms / 1_000, voltage_mv, label=f"{pacing_frequency_hz} Hz")
    plt.xlabel("Time (s)")
    plt.ylabel("Membrane potential (mV)")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    run_my_myokit()
