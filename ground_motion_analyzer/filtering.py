"""Reusable signal-filtering utilities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt

FILTER_TYPES = {"lowpass", "highpass", "bandpass", "bandstop"}


def filter_signal(
    data: Sequence[float] | np.ndarray | pd.Series,
    filter_params: Mapping[str, Any],
    *,
    sampling_rate: float,
) -> np.ndarray | pd.Series:
    """Return a zero-phase Butterworth-filtered copy of one-dimensional data.

    ``filter_params`` accepts the dictionary produced by
    :meth:`ground_motion_analyzer.widgets.Filtering.get`::

        {
            "is_filter_on": True,
            "filter_type": "bandpass",
            "cutoff_frequency": [0.5, 20.0],
            "order": 4,
        }

    The sampling rate is expressed in samples per second (Hz). When filtering is
    disabled, a copy is returned without designing a filter.
    """
    values = np.asarray(data, dtype=float)
    if values.ndim != 1:
        raise ValueError("Signal data must be one-dimensional.")

    if not filter_params.get("is_filter_on", False):
        return _restore_data_type(values.copy(), data)

    if len(values) < 2:
        raise ValueError("At least two samples are required for filtering.")
    if not np.isfinite(values).all():
        raise ValueError("Signal data must contain only finite values.")
    if not np.isfinite(sampling_rate) or sampling_rate <= 0:
        raise ValueError("Sampling rate must be a positive finite value.")

    filter_type = str(filter_params.get("filter_type", "")).lower()
    if filter_type not in FILTER_TYPES:
        choices = ", ".join(sorted(FILTER_TYPES))
        raise ValueError(f"Filter type must be one of: {choices}.")

    order = filter_params.get("order")
    if isinstance(order, bool) or not isinstance(order, (int, np.integer)) or order < 1:
        raise ValueError("Filter order must be a positive integer.")

    cutoff = _validate_cutoff(
        filter_params.get("cutoff_frequency"),
        filter_type=filter_type,
        nyquist=sampling_rate / 2.0,
    )
    sections = butter(
        int(order),
        cutoff,
        btype=filter_type,
        fs=sampling_rate,
        output="sos",
    )

    try:
        filtered = sosfiltfilt(sections, values)
    except ValueError as error:
        raise ValueError(
            "Signal is too short for zero-phase filtering with the selected order."
        ) from error

    return _restore_data_type(filtered, data)


def _validate_cutoff(
    cutoff: Any,
    *,
    filter_type: str,
    nyquist: float,
) -> float | tuple[float, float]:
    if filter_type in {"bandpass", "bandstop"}:
        if isinstance(cutoff, (str, bytes)):
            raise ValueError(f"{filter_type} requires low and high cutoff frequencies.")
        try:
            frequencies = np.asarray(cutoff, dtype=float)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{filter_type} requires low and high cutoff frequencies."
            ) from error
        if frequencies.shape != (2,):
            raise ValueError(f"{filter_type} requires exactly two cutoff frequencies.")
        low, high = frequencies
        if not np.isfinite([low, high]).all() or not 0 < low < high < nyquist:
            raise ValueError(
                f"Cutoffs must satisfy 0 < low < high < Nyquist ({nyquist:g} Hz)."
            )
        return low, high

    try:
        frequency = float(cutoff)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{filter_type} requires one numeric cutoff frequency."
        ) from error
    if not np.isfinite(frequency) or not 0 < frequency < nyquist:
        raise ValueError(f"Cutoff must satisfy 0 < cutoff < Nyquist ({nyquist:g} Hz).")
    return frequency


def _restore_data_type(
    values: np.ndarray,
    original: Sequence[float] | np.ndarray | pd.Series,
) -> np.ndarray | pd.Series:
    if isinstance(original, pd.Series):
        return pd.Series(values, index=original.index, name=original.name)
    return values
