"""Signal-file loading and column-layout detection."""

from __future__ import annotations

import re
from os import PathLike
from pathlib import Path
from typing import IO

import pandas as pd
from loguru import logger
from obspy import read

from .constants import ColumnMode


def read_signal_data(source: str | PathLike[str] | IO[str]) -> pd.DataFrame | None:
    """Read signal samples while preserving any metadata preamble."""
    if isinstance(source, (str, PathLike)):
        if _is_mseed_file(source):
            return _read_mseed_file(source)
        if Path(source).suffix.lower() in {".sac", ".sacxy"}:
            return _read_sac_file(source)
        with open(source, encoding="utf-8") as stream:
            return _read_signal_stream(stream)

    try:
        return _read_signal_stream(source)
    finally:
        source.seek(0)


def _is_mseed_file(source):
    file_path = Path(source)
    return file_path.suffix.lower() == ".mseed"


def _read_signal_stream(stream: IO[str]) -> pd.DataFrame:
    stream.seek(0)
    lines = stream.readlines()
    numeric_row_index, column_count = _find_first_numeric_row(lines)

    header_index = numeric_row_index
    has_header = False
    previous_index = _previous_nonempty_line(lines, numeric_row_index)
    if previous_index is not None:
        candidate_separator = _detect_separator(lines[previous_index])
        candidate_fields = _split_fields(lines[previous_index], candidate_separator)
        if len(candidate_fields) == column_count and not _all_numeric(candidate_fields):
            header_index = previous_index
            has_header = True

    reference_line = lines[header_index]
    separator = _detect_separator(reference_line)
    metadata = _parse_metadata(lines[:header_index])

    # Detect headers using the full row width, but load only the supported
    # time + three-component layout when the file includes extra columns.
    loaded_column_count = min(column_count, 4)
    if column_count > loaded_column_count:
        logger.warning(
            "Ignoring columns {} through {}; loading only the first four columns.",
            loaded_column_count + 1,
            column_count,
        )

    engine = "python" if separator == r"\s+" else "c"
    stream.seek(0)
    data = pd.read_csv(
        stream,
        sep=separator,
        engine=engine,
        skiprows=header_index,
        header=0 if has_header else None,
        usecols=range(loaded_column_count),
    )
    if not has_header:
        data.columns = [
            f"Component {index + 1}" for index in range(loaded_column_count)
        ]
    data.attrs["metadata"] = metadata
    data.attrs["header_row"] = header_index + 1 if has_header else None
    return data


def _read_mseed_file(source: str | PathLike[str]) -> pd.DataFrame | None:
    """Read signal samples from mseed file"""
    logger.info("Reading mseed file.")
    streams = read(source, format="MSEED")
    streams.merge(method=1, fill_value=0)

    if len(streams) > 1:
        # TODO: Handle multiple channels
        raise RuntimeError("MSEED file with multiple channels is not supported yet!")
    else:
        trace = streams[0]
        dataframe = pd.DataFrame(
            {"time": trace.times("timestamp"), "amplitude": trace.data}
        )
        return dataframe


def _read_sac_file(source: str | PathLike[str]) -> pd.DataFrame:
    """Read one evenly sampled SAC time history without rescaling amplitudes."""
    import numpy as np
    from obspy.io.sac import SACTrace
    from obspy.io.sac.util import SacIOError

    logger.info("Reading SAC file.")
    with open(source, "rb") as stream:
        try:
            sac = SACTrace.read(stream)
        except (SacIOError, ValueError):
            stream.seek(0)
            try:
                sac = SACTrace.read(stream, ascii=True)
            except (SacIOError, ValueError) as error:
                raise ValueError(
                    "Could not read a valid binary or ASCII SAC file."
                ) from error

    if sac.iftype != "itime" or sac.leven is not True:
        raise ValueError("Only evenly sampled SAC time-series files are supported.")
    if sac.delta is None or not np.isfinite(sac.delta) or sac.delta <= 0:
        raise ValueError("SAC sample interval (delta) must be positive and finite.")
    if sac.data is None or len(sac.data) < 2:
        raise ValueError("At least two signal samples are required in the SAC file.")
    if not np.isfinite(sac.data).all():
        raise ValueError("SAC signal samples must be finite.")

    begin = sac.b if sac.b is not None else 0.0
    if not np.isfinite(begin):
        raise ValueError("SAC begin time (b) must be finite.")
    time = begin + np.arange(len(sac.data), dtype=float) * sac.delta
    # pandas needs native byte order.
    amplitudes = np.asarray(sac.data, dtype=np.float32)
    data = pd.DataFrame({"time": time, "amplitude": amplitudes})
    data.attrs["metadata"] = {
        "format": "SAC",
        "sampling_rate": 1.0 / sac.delta,
        "time_increment": sac.delta,
        "begin_time": begin,
        "station": sac.kstnm or "",
        "network": sac.knetwk or "",
        "channel": sac.kcmpnm or "",
    }
    return data


def _find_first_numeric_row(lines: list[str]) -> tuple[int, int]:
    for index, line in enumerate(lines):
        fields = re.split(r"[\s,;]+", line.strip()) if line.strip() else []
        if (len(fields) in {1, 2} or len(fields) >= 4) and _all_numeric(fields[:4]):
            return index, len(fields)
    raise ValueError("No numeric signal samples were found in the selected file.")


def _previous_nonempty_line(lines: list[str], before: int) -> int | None:
    for index in range(before - 1, -1, -1):
        if lines[index].strip():
            return index
    return None


def _detect_separator(line: str) -> str:
    if "\t" in line:
        return "\t"
    if re.search(r"\s{2,}", line):
        return r"\s+"
    if ";" in line:
        return ";"
    if "," in line:
        return ","
    if len(line.split()) > 1:
        return r"\s+"
    return ","


def _split_fields(line: str, separator: str) -> list[str]:
    if separator == r"\s+":
        return re.split(r"\s+", line.strip())
    return [field.strip() for field in line.strip().split(separator)]


def _all_numeric(fields: list[str]) -> bool:
    if not fields:
        return False
    try:
        for field in fields:
            float(field)
    except ValueError:
        return False
    return True


def _parse_metadata(lines: list[str]) -> dict[str, str | float]:
    metadata: dict[str, str | float] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        parts = re.split(r"(?:\t+|\s{2,}|,|;)", stripped, maxsplit=1)
        if len(parts) != 2:
            continue
        key, value = (part.strip() for part in parts)
        try:
            parsed_value: str | float = float(value)
        except ValueError:
            parsed_value = value
        metadata[key] = parsed_value
    return metadata


def detect_column_mode(data: pd.DataFrame) -> ColumnMode:
    """Map supported file column counts to their signal layout."""
    column_count = len(data.columns)
    modes = {
        1: ColumnMode.SINGLE,
        2: ColumnMode.DOUBLE,
        4: ColumnMode.THREE_COMPONENT,
    }
    try:
        return modes[column_count]
    except KeyError as error:
        raise ValueError(
            "Signal files must contain 1 column (data), 2 columns "
            "(time + data), or 4 columns (time + 3 components)."
        ) from error
