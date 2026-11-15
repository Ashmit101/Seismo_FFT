"""Data models produced by the ground-motion analysis."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy.fft import rfft, rfftfreq
from scipy.signal import detrend as scipy_detrend
from scipy.signal import resample_poly


def preprocess_signal(
    values: np.ndarray,
    *,
    demean: bool = True,
    detrend: bool = False,
) -> np.ndarray:
    """Return signal values with the selected baseline corrections applied."""
    processed = np.asarray(values, dtype=float).copy()
    if processed.ndim not in {1, 2}:
        raise ValueError("Signal data must be one- or two-dimensional.")

    if demean:
        processed -= np.mean(processed, axis=0)
    if detrend:
        processed = scipy_detrend(processed, axis=0, type="linear")

    return processed


def create_fourier_data(
    values: np.ndarray,
    *,
    time_increment: float,
    component_names: Sequence[object],
    max_samples: int | None = None,
) -> pd.DataFrame:
    """Return one-sided FFT magnitudes, optionally at preview resolution.

    The GUI/export defaults to full resolution to preserve the original Nyquist
    range. Callers requesting a reduced-bandwidth preview may set max_samples.
    """
    signal_values = np.asarray(values, dtype=float)
    if signal_values.ndim == 1:
        signal_values = signal_values[:, np.newaxis]
    if signal_values.ndim != 2 or len(signal_values) < 2:
        raise ValueError("At least two signal samples are required for the FFT.")
    if signal_values.shape[1] != len(component_names):
        raise ValueError("Each signal component must have a name.")
    if not np.isfinite(time_increment) or time_increment <= 0:
        raise ValueError("Time increment must be a positive finite value.")

    if max_samples is not None:
        if (
            isinstance(max_samples, bool)
            or not isinstance(max_samples, (int, np.integer))
            or max_samples < 2
        ):
            raise ValueError("Preview sample limit must be an integer of at least two.")
        if len(signal_values) > max_samples:
            factor = (len(signal_values) + max_samples - 1) // max_samples
            # Anti-alias before decimation; a stride alone would fold high
            # frequencies into the spectrum. This lowers the Nyquist limit and
            # loses high-frequency content, so it is opt-in, never used for export.
            signal_values = resample_poly(signal_values, 1, factor, axis=0)
            time_increment *= factor

    sample_count = len(signal_values)
    frequencies = rfftfreq(sample_count, d=time_increment)
    # Independent component transforms can use all cores. For one component,
    # SciPy may still use one worker; responsiveness comes from the daemon job.
    magnitudes = np.abs(rfft(signal_values, axis=0, workers=-1)) / sample_count

    columns = {"Frequency (Hz)": frequencies}
    for index, component_name in enumerate(component_names):
        columns[f"{component_name} FFT Magnitude"] = magnitudes[:, index]
    return pd.DataFrame(columns)
