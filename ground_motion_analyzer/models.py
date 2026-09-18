"""Data models produced by the ground-motion analysis."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy.signal import detrend as scipy_detrend


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
) -> pd.DataFrame:
    """Return the one-sided FFT magnitudes used by the spectrum plots."""
    signal_values = np.asarray(values, dtype=float)
    if signal_values.ndim == 1:
        signal_values = signal_values[:, np.newaxis]
    if signal_values.ndim != 2 or len(signal_values) < 2:
        raise ValueError("At least two signal samples are required for the FFT.")
    if signal_values.shape[1] != len(component_names):
        raise ValueError("Each signal component must have a name.")
    if not np.isfinite(time_increment) or time_increment <= 0:
        raise ValueError("Time increment must be a positive finite value.")

    sample_count = len(signal_values)
    frequencies = np.fft.rfftfreq(sample_count, d=time_increment)
    magnitudes = np.abs(np.fft.rfft(signal_values, axis=0)) / sample_count

    columns = {"Frequency (Hz)": frequencies}
    for index, component_name in enumerate(component_names):
        columns[f"{component_name} FFT Magnitude"] = magnitudes[:, index]
    return pd.DataFrame(columns)
