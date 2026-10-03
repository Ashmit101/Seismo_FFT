from enum import StrEnum


class Palette(StrEnum):
    """Black-and-white colour palette for the UI."""

    BG = "#FFFFFF"
    PANEL = "#FFFFFF"
    ACCENT = "#000000"
    ACCENT2 = "#000000"
    TEXT = "#000000"
    SUBTEXT = "#000000"
    ENTRY_BG = "#FFFFFF"
    BTN_BG = "#FFFFFF"
    BTN_HOV = "#000000"
    SUCCESS = "#000000"
    WARNING = "#FFFFFF"
    BORDER = "#000000"
    PLOT_BG = "#FFFFFF"


class Events(StrEnum):
    FILE_SELECTED = "<<FileSelected>>"
    VARIABLES_UPDATED = "<<VariablesUpdated>>"
    CONTROL_VALUE_UPDATED = "<<ControlValueUpdated>>"
    FILTER_PARAMS_UPDATED = "<<FilterParamsUpdated>>"


class ColumnMode(StrEnum):
    """The column format in the signal data file"""

    SINGLE = "single"
    DOUBLE = "double"
    THREE_COMPONENT = "three_component"
