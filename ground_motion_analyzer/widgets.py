import tkinter as tk
from tkinter import ttk

from .constants import Palette


class Header(tk.Frame):
    """Header displaying the name of project."""

    def __init__(self, parent, title, developer):
        super().__init__(parent, bg=Palette.BG, pady=10)

        tk.Label(
            self,
            text=title,
            bg=Palette.BG,
            fg=Palette.ACCENT2,
            font=("Consolas", 32, "bold"),
            ).grid(row=0, column=0)

        tk.Label(
            self,
            text=developer,
            bg=Palette.BG,
            fg=Palette.ACCENT2,
            font=("Consolas", 18, "bold"),
            ).grid(row=1,column=0)


class SectionHeader(tk.Frame):

    def __init__(self, title, *args, **kwargs):
        super().__init__(*args, **kwargs)

        label = tk.Label(self,
                         text=f"▸ {title}",
                         bg=Palette.BG,
                         fg=Palette.ACCENT,
                         font=("Consolas", 12, "bold")
                         )
        label.grid(row=0,
                   column=0,
                   padx=16
                   )
        

class ControlPanel(tk.Frame):
    """Control panel"""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Column Mode
        self.column_mode_header = SectionHeader("Column Format")
        self.column_mode_header.grid(row=0,
                                     column=0
                                     )
    
