"""Stochastic Hodgkin-Huxley sweeps with a settable threshold and adaptation.

The ionic currents and subunit noise follow Alan Leggitt's pylab port of
Goldwyn and Shea-Brown (ModelDB accession 144499). Voltage stays in that
paper's frame, where rest is near 0 mV, until the sweep subtracts a baseline
for SanPy.

``ModelRun`` holds the published currents, the sodium-activation shift, the
slow potassium adaptation gate, and the current-clamp protocol. One ``ModelRun``
is integrated at every current amplitude and written to one ``.sanpy`` file.
The next file is a copy of that parameter set with the fields that should
differ replaced, using the same amplitudes.

``m_shift_mv`` defaults to 2.23 mV so a long step with noise off and ``g_w = 0``
first spikes at 5 uA/cm^2 while ``g_k`` stays at the published 36 mS/cm^2.
``tau_w_ms`` defaults to 100 ms. ``g_w = 0`` leaves the published current balance.
``g_d`` is a dendrotoxin-sensitive potassium current that delays the first spike.
It defaults to 0. After each file is written, the sweeps are drawn together on
one figure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def _default_output_dir() -> Path:
    """Return the folder that receives ``.sanpy`` files.

    Returns:
        Desktop path for the September 2026 model runs.
    """

    return Path("/Users/cudmore/Desktop/sanpy-model-data/sept_2026")


@dataclass
class ModelRun:
    """One model configuration and the current-clamp protocol saved with it.

    Build the shared setup once, then ``dataclasses.replace`` the fields that
    change for the next file. Each file keeps ``amplitudes_ua_cm2``.

    Attributes:
        capacitance: Membrane capacitance, uF/cm^2.
        g_na: Maximal sodium conductance, mS/cm^2.
        e_na: Sodium reversal, mV, Hodgkin-Huxley frame.
        g_k: Maximal delayed-rectifier conductance, mS/cm^2.
        e_k: Potassium reversal, mV, Hodgkin-Huxley frame.
        g_l: Leak conductance, mS/cm^2.
        e_l: Leak reversal, mV, Hodgkin-Huxley frame.
        g_w: Spike-frequency adaptation conductance, mS/cm^2. This is not ``g_k``.
            Zero turns adaptation off. Larger values let the slow potassium
            gate ``w`` (``tau_w_ms``) build during a step and slow later spikes.
        tau_w_ms: Adaptation time constant, ms.
        g_d: Dendrotoxin-sensitive potassium conductance, mS/cm^2. This is not
            ``g_k`` or ``g_w``. Zero leaves the first spike undelayed. Larger
            values hold the membrane below threshold until the slow inactivation
            gate has closed, so the first spike comes later.
        tau_d_ms: Activation time constant of ``g_d``, ms.
        d_half_mv: Activation half-voltage of ``g_d``, mV in the Hodgkin-Huxley
            frame. +22 mV here is about -43 mV physiological.
        d_slope_mv: Activation slope of ``g_d``, mV.
        tau_d_inact_ms: Inactivation time constant of ``g_d``, ms.
        d_inact_half_mv: Inactivation half-voltage of ``g_d``, mV in the
            Hodgkin-Huxley frame. -2 mV here is about -67 mV physiological.
        d_inact_slope_mv: Inactivation slope of ``g_d``, mV. Positive values
            close the gate as voltage rises.
        w_half_mv: Adaptation half-activation, mV in the Hodgkin-Huxley frame.
            A physiological M-current near -35 mV is +30 mV in this frame.
        w_slope_mv: Adaptation activation slope, mV.
        m_shift_mv: Sodium-activation shift, mV. Positive values raise rheobase.
        na_channels_per_area: Sodium channels per unit of ``area``.
        k_channels_per_area: Potassium channels per unit of ``area``.
        area: Area scale used by ModelDB 144499 to set channel counts.
        subunit_noise: When True, add Fox-Lu subunit noise on m, h, and n.
        seed: Seed for subunit noise. Unused when ``subunit_noise`` is False.
        duration_sec: Sweep length, seconds.
        sample_rate_hz: Nominal sample rate before the ``myRun2`` divisor, Hz.
        step_start_ms: Current-step onset, milliseconds.
        epoch_zero_ms: End of epoch 0, milliseconds.
        baseline_shift_mv: Subtracted from voltage after the solve, mV.
        amplitudes_ua_cm2: Step currents saved as consecutive sweeps, uA/cm^2.
        output_dir: Directory for the ``.sanpy`` file.
    """

    capacitance: float = 1.0
    g_na: float = 120.0
    e_na: float = 120.0
    g_k: float = 36.0
    e_k: float = -12.0
    g_l: float = 0.3
    e_l: float = 10.6
    g_w: float = 0.0
    tau_w_ms: float = 100.0
    g_d: float = 0.0
    tau_d_ms: float = 1.0
    d_half_mv: float = 22.0
    d_slope_mv: float = 8.0
    tau_d_inact_ms: float = 150.0
    d_inact_half_mv: float = -2.0
    d_inact_slope_mv: float = 6.0
    w_half_mv: float = 30.0
    w_slope_mv: float = 10.0
    m_shift_mv: float = 2.23
    na_channels_per_area: float = 60.0
    k_channels_per_area: float = 18.0
    area: float = 100.0
    subunit_noise: bool = True
    seed: int = 1
    duration_sec: float = 1.0
    sample_rate_hz: float = 10000.0
    step_start_ms: float = 250.0
    epoch_zero_ms: float = 10.0
    baseline_shift_mv: float = 60.0
    # amplitudes_ua_cm2: tuple[float, ...] = (
    #     -2,
    #     -1,
    #     0,
    #     1,
    #     2,
    #     3,
    #     4,
    #     5,
    #     6,
    #     7,
    #     8,
    #     9,
    #     10,
    #     11,
    #     12,
    # )
    amplitudes_ua_cm2: tuple[float, ...] = (
        -2,
        -1,
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
    )
    output_dir: Path = field(default_factory=_default_output_dir)


def _alpha_singularity(driving_mv: float, scale: float, slope_mv: float) -> float:
    """Hodgkin-Huxley forward rate with the removable singularity filled in.

    Args:
        driving_mv: Numerator voltage term, mV. The published rate is singular
            when this is zero.
        scale: Leading coefficient of the rate, 1/ms.
        slope_mv: Exponential slope, mV.

    Returns:
        The forward rate, 1/ms.
    """

    if abs(driving_mv) < 1e-7:
        return scale * slope_mv
    return scale * driving_mv / (math.exp(driving_mv / slope_mv) - 1.0)


def subunit_rates(
    voltage_mv: float, m_shift_mv: float
) -> tuple[float, float, float, float, float, float]:
    """Published Hodgkin-Huxley subunit rates at one voltage.

    Only the sodium activation rates see ``m_shift_mv``. Inactivation and the
    delayed rectifier stay on the published voltage axis.

    Args:
        voltage_mv: Membrane voltage in the Hodgkin-Huxley frame, mV.
        m_shift_mv: Sodium-activation shift, mV.

    Returns:
        ``alpha_m``, ``beta_m``, ``alpha_h``, ``beta_h``, ``alpha_n``, and
        ``beta_n``, each in 1/ms.
    """

    shifted = voltage_mv - m_shift_mv
    alpha_m = _alpha_singularity(25.0 - shifted, 0.1, 10.0)
    beta_m = 4.0 * math.exp(-shifted / 18.0)
    alpha_h = 0.07 * math.exp(-voltage_mv / 20.0)
    beta_h = 1.0 / (math.exp((30.0 - voltage_mv) / 10.0) + 1.0)
    alpha_n = _alpha_singularity(10.0 - voltage_mv, 0.01, 10.0)
    beta_n = 0.125 * math.exp(-voltage_mv / 80.0)
    return alpha_m, beta_m, alpha_h, beta_h, alpha_n, beta_n


def _steady_state(alpha: float, beta: float) -> float:
    """Equilibrium open probability of a two-state gate.

    Args:
        alpha: Opening rate, 1/ms.
        beta: Closing rate, 1/ms.

    Returns:
        ``alpha / (alpha + beta)``.
    """

    return alpha / (alpha + beta)


def w_infinity(voltage_mv: float, run: ModelRun) -> float:
    """Steady-state adaptation-gate activation.

    Args:
        voltage_mv: Membrane voltage in the Hodgkin-Huxley frame, mV.
        run: Parameter set supplying half-activation and slope.

    Returns:
        Activation in ``[0, 1]``.
    """

    exponent = -(voltage_mv - run.w_half_mv) / run.w_slope_mv
    return 1.0 / (1.0 + math.exp(exponent))


def d_infinity(voltage_mv: float, run: ModelRun) -> float:
    """Steady-state activation of the dendrotoxin-sensitive potassium current.

    Args:
        voltage_mv: Membrane voltage in the Hodgkin-Huxley frame, mV.
        run: Parameter set supplying half-activation and slope.

    Returns:
        Activation in ``[0, 1]``. It rises with depolarization.
    """

    exponent = -(voltage_mv - run.d_half_mv) / run.d_slope_mv
    return 1.0 / (1.0 + math.exp(exponent))


def d_inactivation_infinity(voltage_mv: float, run: ModelRun) -> float:
    """Steady-state inactivation of the dendrotoxin-sensitive potassium current.

    Args:
        voltage_mv: Membrane voltage in the Hodgkin-Huxley frame, mV.
        run: Parameter set supplying half-inactivation and slope.

    Returns:
        Availability in ``[0, 1]``. It falls with depolarization.
    """

    exponent = (voltage_mv - run.d_inact_half_mv) / run.d_inact_slope_mv
    return 1.0 / (1.0 + math.exp(exponent))


def _clamp_unit(value: float) -> float:
    """Clamp a gating variable to ``[0, 1]``.

    Args:
        value: Unconstrained gate value.

    Returns:
        The value limited to the unit interval.
    """

    return min(1.0, max(0.0, value))


def _channel_counts(run: ModelRun) -> tuple[int, int]:
    """Count sodium and potassium channels the way ModelDB 144499 does.

    Args:
        run: Parameter set supplying area and channel densities.

    Returns:
        Sodium count and potassium count.

    Raises:
        ValueError: If ``area`` is too small to place at least one channel
            of each kind.
    """

    n_na = int(round(run.area * run.na_channels_per_area))
    n_k = int(round(run.area * run.k_channels_per_area))
    if n_na < 1 or n_k < 1:
        raise ValueError("area is too small to place sodium and potassium channels")
    return n_na, n_k


def time_base_ms(run: ModelRun) -> np.ndarray:
    """Sample times used by ``myStochHH.myRun2``.

    That helper adds 0.01 ms to the duration and divides the sample interval
    by 10. Both choices are kept so epoch times match files from that script.

    Args:
        run: Parameter set supplying duration and nominal sample rate.

    Returns:
        Strictly increasing sample times, milliseconds.
    """

    duration_ms = run.duration_sec * 1000.0 + 0.01
    step_ms = 1000.0 / run.sample_rate_hz / 10.0
    return np.arange(0.0, duration_ms, step_ms)


def step_stop_ms(run: ModelRun) -> float:
    """End of the current step, matching ``myRun2``.

    Args:
        run: Parameter set supplying duration and step onset.

    Returns:
        Step offset, milliseconds.
    """

    return run.duration_sec * 1000.0 + 0.01 - run.step_start_ms


def step_stimulus(
    time_ms: np.ndarray, amplitude_ua_cm2: float, run: ModelRun
) -> tuple[np.ndarray, np.ndarray]:
    """Build the current-clamp step and SanPy epoch index.

    Epoch 2 is the step, matching the index ``myRun2`` writes for plot FI.

    Args:
        time_ms: Sample times, milliseconds.
        amplitude_ua_cm2: Step amplitude, uA/cm^2.
        run: Parameter set supplying step timing and epoch boundaries.

    Returns:
        Injected current, uA/cm^2, and an integer epoch index per sample.
    """

    stop_ms = step_stop_ms(run)
    on_step = (time_ms >= run.step_start_ms) & (time_ms <= stop_ms)
    current = np.zeros(len(time_ms), dtype=float)
    current[on_step] = amplitude_ua_cm2
    epoch = np.ones(len(time_ms), dtype=int)
    epoch[time_ms < run.epoch_zero_ms] = 0
    epoch[on_step] = 2
    epoch[time_ms > stop_ms] = 3
    return current, epoch


def simulate(
    time_ms: np.ndarray,
    input_current: np.ndarray,
    run: ModelRun,
) -> np.ndarray:
    """Integrate one current waveform with forward Euler.

    Subunit noise, when enabled, is the Fox-Lu noise on ``m``, ``h``, and ``n``
    from ModelDB 144499. The adaptation gate and the dendrotoxin-sensitive
    gates are deterministic.

    Args:
        time_ms: Uniform sample times, milliseconds. The step is ``time_ms[1]
            - time_ms[0]``.
        input_current: Injected current at each sample, uA/cm^2.
        run: Ionic parameters, adaptation, sodium shift, and noise settings.

    Returns:
        Membrane voltage in the Hodgkin-Huxley frame, mV. Index 0 is the
        initial rest value and is not integrated.

    Raises:
        ValueError: If the time and current arrays disagree, or if time does
            not increase.
    """

    if len(time_ms) != len(input_current):
        raise ValueError("time_ms and input_current must have the same length")
    if len(time_ms) < 2:
        raise ValueError("time_ms must contain at least two samples")
    dt = float(time_ms[1] - time_ms[0])
    if dt <= 0.0:
        raise ValueError("time_ms must be increasing")

    sqrt_dt = math.sqrt(dt)
    n_na, n_k = _channel_counts(run)
    rng = np.random.default_rng(run.seed)
    voltage = np.zeros(len(time_ms), dtype=float)
    v = 0.0
    alpha_m, beta_m, alpha_h, beta_h, alpha_n, beta_n = subunit_rates(
        v, run.m_shift_mv
    )
    m = _steady_state(alpha_m, beta_m)
    h = _steady_state(alpha_h, beta_h)
    n = _steady_state(alpha_n, beta_n)
    w = w_infinity(v, run)
    d_act = d_infinity(v, run)
    d_inact = d_inactivation_infinity(v, run)

    for index in range(1, len(time_ms)):
        injected = float(input_current[index - 1])
        alpha_m, beta_m, alpha_h, beta_h, alpha_n, beta_n = subunit_rates(
            v, run.m_shift_mv
        )
        m_noise = 0.0
        h_noise = 0.0
        n_noise = 0.0
        if run.subunit_noise:
            m_variance = (alpha_m * (1.0 - m) + beta_m * m) / n_na
            h_variance = (alpha_h * (1.0 - h) + beta_h * h) / n_na
            n_variance = (alpha_n * (1.0 - n) + beta_n * n) / n_k
            m_noise = math.sqrt(max(0.0, m_variance)) * float(rng.standard_normal())
            h_noise = math.sqrt(max(0.0, h_variance)) * float(rng.standard_normal())
            n_noise = math.sqrt(max(0.0, n_variance)) * float(rng.standard_normal())
        m += dt * (alpha_m * (1.0 - m) - beta_m * m) + m_noise * sqrt_dt
        h += dt * (alpha_h * (1.0 - h) - beta_h * h) + h_noise * sqrt_dt
        n += dt * (alpha_n * (1.0 - n) - beta_n * n) + n_noise * sqrt_dt
        w += dt * (w_infinity(v, run) - w) / run.tau_w_ms
        d_act += dt * (d_infinity(v, run) - d_act) / run.tau_d_ms
        d_inact += dt * (d_inactivation_infinity(v, run) - d_inact) / run.tau_d_inact_ms
        m = _clamp_unit(m)
        h = _clamp_unit(h)
        n = _clamp_unit(n)
        w = _clamp_unit(w)
        d_act = _clamp_unit(d_act)
        d_inact = _clamp_unit(d_inact)
        na_open = _clamp_unit(m**3 * h)
        k_open = _clamp_unit(n**4)
        v += (
            dt
            * (
                -run.g_na * na_open * (v - run.e_na)
                - run.g_k * k_open * (v - run.e_k)
                - run.g_w * w * (v - run.e_k)
                - run.g_d * d_act * d_inact * (v - run.e_k)
                - run.g_l * (v - run.e_l)
                + injected
            )
            / run.capacitance
        )
        voltage[index] = v
    return voltage


def amplitude_sweep(run: ModelRun) -> pd.DataFrame:
    """Run every current in ``run`` and stack the SanPy columns.

    Each amplitude restarts the subunit-noise generator from ``run.seed``.
    Ionic parameters stay fixed for the whole table.

    Args:
        run: Model and protocol for this file.

    Returns:
        A table with ``seconds``, ``epoch_index``, and ``mv_i`` / ``cmd_i``
        columns in the same order as ``myStochHH.py``. Voltage is shifted into
        the SanPy frame.
    """

    time_ms = time_base_ms(run)
    frame = pd.DataFrame()
    for index, amplitude in enumerate(run.amplitudes_ua_cm2):
        current, epoch = step_stimulus(time_ms, amplitude, run)
        voltage = simulate(time_ms, current, run)
        print(
            f"  appending mv_{index} amp:{amplitude:g} "
            f"gK:{run.g_k:g} g_w:{run.g_w:g} g_d:{run.g_d:g}"
        )
        if index == 0:
            frame["seconds"] = time_ms / 1000.0
            frame["epoch_index"] = epoch
        frame[f"mv_{index}"] = voltage - run.baseline_shift_mv
        frame[f"cmd_{index}"] = current
    return frame


def output_path(run: ModelRun, when: datetime) -> Path:
    """Path for one parameter set.

    Args:
        run: Parameter set written into the file name.
        when: Timestamp shared by every file from one launch.

    Returns:
        CSV path ending in ``.sanpy``.
    """

    date_str = when.strftime("%Y%m%d")
    time_str = when.strftime("%H%M%S")
    name = (
        f"stoch-hh-gk-{date_str}-{time_str}"
        f"-gK{run.g_k:g}-gw{run.g_w:g}-gd{run.g_d:g}.sanpy"
    )
    return run.output_dir / name


def plot_run(frame: pd.DataFrame, run: ModelRun) -> None:
    """Draw every current step from one model run on a single axes.

    Args:
        frame: Table from ``amplitude_sweep``. Voltage is the SanPy frame.
        run: Parameter set used to label the figure and the current legend.
    """

    import matplotlib.pyplot as plt

    amplitudes = run.amplitudes_ua_cm2
    colors = plt.colormaps["viridis"](np.linspace(0.0, 1.0, len(amplitudes)))
    fig, ax = plt.subplots()
    for index, amplitude in enumerate(amplitudes):
        ax.plot(
            frame["seconds"],
            frame[f"mv_{index}"],
            color=colors[index],
            label=f"{amplitude:g}",
        )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Voltage (mV)")
    ax.set_title(
        f"gK={run.g_k:g}, g_w={run.g_w:g}, g_d={run.g_d:g} mS/cm$^2$"
    )
    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize="x-small",
        title="uA/cm$^2$",
    )
    fig.tight_layout()


def save_sweep(frame: pd.DataFrame, path: Path) -> None:
    """Write one model run, creating the output directory if needed.

    Args:
        frame: Table from ``amplitude_sweep``.
        path: Destination, including the ``.sanpy`` suffix.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    print(f"saving file: {path}")


def main() -> None:
    """Save one file per adaptation conductance and show its sweeps."""

    when = datetime.now()
    base = ModelRun()

    currents = tuple(4 * amp for amp in base.amplitudes_ua_cm2)
    # currents = base.amplitudes_ua_cm2

    # g_w is spike-frequency adaptation, not g_k. g_k is the fast delayed
    # rectifier on each spike. g_w=0 has no adaptation current. g_w=0.5 lets
    # gate w grow over tau_w_ms (100 ms), so firing slows later in the step.
    # g_d delays the first spike. g_d=0 leaves that current off. g_d=2 holds
    # the cell below threshold until the 150 ms inactivation gate closes.
    runs = (
        # replace(base, g_w=0.0),
        # replace(base, g_w=0.5),
        # replace(base, g_w=0.5, amplitudes_ua_cm2=currents),
        # replace(base, g_w=2.0, amplitudes_ua_cm2=currents),
        # replace(base, g_w=0.5, g_d=2.0, amplitudes_ua_cm2=currents),
        replace(base, g_w=1.0, g_d=2.0, amplitudes_ua_cm2=currents),
        replace(base, g_w=2.0, g_d=2.0, amplitudes_ua_cm2=currents),
    )

    _do_plot = False
    _do_save = True

    for run in runs:
        frame = amplitude_sweep(run)
        if _do_save:
            save_sweep(frame, output_path(run, when))
        if _do_plot:
            plot_run(frame, run)
    if _do_plot:
        import matplotlib.pyplot as plt

        plt.show()


if __name__ == "__main__":
    main()
