from enum import StrEnum


class Palette(StrEnum):
    """Colour Palette for the UI"""
    BG = "#F2EAE3"  # Linen – light warm background
    PANEL = "#EBDED1"  # Sandstone – slightly darker panel
    ACCENT = "#C07D58"  # Clay – warm terracotta accent
    ACCENT2 = "#8A4E35"  # Sage-complementary warm rust
    TEXT = "#3B2A1A"  # Deep espresso-brown text
    SUBTEXT = "#734F3A"  # Chestnut – muted subtext
    ENTRY_BG = "#D8C3A6"  # Warm Beige – input field background
    BTN_BG = "#B56B46"  # Terracotta – primary button
    BTN_HOV = "#994D2C"  # Burnt Sienna – button hover
    SUCCESS = "#5D573B"  # Moss – success state
    WARNING = "#C4B195"  # Oat – soft warning tone
    BORDER = "#8D8961"  # Olive – subtle border

    
