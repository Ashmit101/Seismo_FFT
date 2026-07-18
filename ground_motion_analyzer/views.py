import tkinter as tk
from tkinter import ttk

from . import widgets as w
from .constants import Palette


class MainView(tk.Frame):
    """Main view of the application"""
    
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.grid_columnconfigure(0, weight=1)

        w.Header(
            self,
            title="Ground Motion Analyzer",
            developer="Ashmit Rajaure"
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        
        w.ControlPanel(self, bg=Palette.BG).grid(row=1, column=0, sticky="nw")
