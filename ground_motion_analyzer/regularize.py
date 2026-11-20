import numpy as np


def regularize_time_series(time_values, component_data, gap_factor=5.0, rtol=1e-3):
    """
    Return (time_values, component_data, time_increment) on a uniform time grid.

    - Already uniform data is returned unchanged.
    - Burst-sampled data (dense runs separated by large gaps, e.g. 5 samples
      every second) is collapsed to one averaged sample per burst, which gives
      a uniform series at the burst rate.
    - Anything else raises, because interpolating across gaps would invent data.
    """
    time_values = np.asarray(time_values, dtype=float)
    steps = np.diff(time_values)
    if len(steps) == 0 or np.any(steps <= 0):
        raise ValueError("Time values must be strictly increasing.")

    dt = float(np.median(steps))
    if np.allclose(steps, dt, rtol=rtol, atol=1e-12):
        return time_values, component_data, dt

    # Split into bursts wherever the step is much larger than the typical step
    burst_id = np.concatenate([[0], np.cumsum(steps > gap_factor * dt)])
    if burst_id[-1] == 0:
        raise ValueError(
            "Filtering and FFT require uniformly sampled data "
            "(irregular steps, no clear burst structure)."
        )

    cols = list(component_data.columns)
    df = component_data.reset_index(drop=True).copy()
    df["_burst"] = burst_id
    df["_t"] = time_values
    g = df.groupby("_burst")

    t_b = g["_t"].first().to_numpy(dtype=float)  # burst start time
    data_b = g[cols].mean().reset_index(drop=True)  # one averaged row per burst

    period_steps = np.diff(t_b)
    period = float(np.median(period_steps))
    if not np.allclose(period_steps, period, rtol=rtol, atol=1e-12):
        raise ValueError("Bursts are not evenly spaced; cannot build a uniform series.")

    return t_b, data_b, period
