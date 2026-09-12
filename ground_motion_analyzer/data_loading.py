"""Signal-file loading and column-layout detection."""

from __future__ import annotations

import re
from os import PathLike
from typing import IO

import pandas as pd

from .constants import ColumnMode


def read_signal_data(source: str | PathLike[str] | IO[str]) -> pd.DataFrame:
    """Read signal samples while preserving any metadata preamble."""
    if isinstance(source, (str, PathLike)):
        with open(source, encoding="utf-8") as stream:
            return _read_signal_stream(stream)

    try:
        return _read_signal_stream(source)
    finally:
        source.seek(0)


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

    engine = "python" if separator == r"\s+" else "c"
    stream.seek(0)
    data = pd.read_csv(
        stream,
        sep=separator,
        engine=engine,
        skiprows=header_index,
        header=0 if has_header else None,
    )
    if not has_header:
        data.columns = [f"Component {index + 1}" for index in range(column_count)]
    data.attrs["metadata"] = metadata
    data.attrs["header_row"] = header_index + 1 if has_header else None
    return data


def _find_first_numeric_row(lines: list[str]) -> tuple[int, int]:
    for index, line in enumerate(lines):
        fields = re.split(r"[\s,;]+", line.strip()) if line.strip() else []
        if len(fields) in {1, 2, 4} and _all_numeric(fields):
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
