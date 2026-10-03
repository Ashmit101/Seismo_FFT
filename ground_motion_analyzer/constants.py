from enum import StrEnum


class Palette(StrEnum):
    """Grayscale colour palette for the UI."""

    BG = "#E5E5E5"
    PANEL = "#F2F2F2"
    ACCENT = "#404040"
    ACCENT2 = "#262626"
    TEXT = "#202020"
    SUBTEXT = "#505050"
    ENTRY_BG = "#FAFAFA"
    BTN_BG = "#D0D0D0"
    BTN_HOV = "#606060"
    SUCCESS = "#484848"
    WARNING = "#B0B0B0"
    BORDER = "#888888"
    PLOT_BG = "#F5F5F5"


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
