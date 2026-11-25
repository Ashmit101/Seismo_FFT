from enum import StrEnum
from pathlib import Path

import pandas as pd
from loguru import logger


class ExportFileType(StrEnum):
    CSV = "CSV"


file_type_separator_map = {ExportFileType.CSV: ","}


def export_data(data: pd.DataFrame, file_type: ExportFileType, output_file_path: Path):
    """Signal data exporter."""
    try:
        data.to_csv(
            output_file_path, index=False, sep=file_type_separator_map[file_type]
        )
    except (OSError, PermissionError):
        logger.exception("Could not export data")
