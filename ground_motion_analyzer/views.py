import tkinter as tk
from tkinter import ttk

from . import widgets as w
from .constants import Events, Palette


class MainView(tk.Frame):
    """Main view of the application"""
    
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        w.Header(
            self,
            title="Ground Motion Analyzer",
            developer="Ashmit Rajaure"
        ).grid(row=0, column=0, columnspan=2, sticky=(tk.N + tk.E + tk.W + tk.S), pady=(0, 12))
        self.control_panel = w.ControlPanel(self, bg=Palette.BG)
        self.control_panel.grid(row=1, column=0, sticky=(tk.N + tk.S + tk.W))
        self.control_panel.bind(Events.VARIABLES_UPDATED, self._plot)

        
        self.plot_area = w.PlotArea(self)
        self.plot_area.grid(row=1, column=1, sticky=(tk.N + tk.S + tk.E + tk.W))

        
    def _plot(self, *_):
        control_variables = self.control_panel.get()
        print(f"control variables: {control_variables}")
        
        
