from loguru import logger
import pandas as pd
import tkinter as tk
from tkinter import ttk

from . import widgets as w
from .constants import ColumnMode, Events, Palette


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
        logger.info(f"control variables: {control_variables}")

        if data_file := control_variables.get("file"):
            data = pd.read_csv(data_file)
            columns = data.columns
            logger.info(f"Columns: {columns}")

            if control_variables["column_format"] == ColumnMode.SINGLE:
                motion_data = data[columns[0]]
                time_data = None
            else:
                time_data = data[columns[0]]
                motion_data = data[columns[1]]

            self.plot_area.plot(motion_data=motion_data,
                                time_data=time_data,
                                time_increment=control_variables["time_increment"])
        else:
            logger.info("No data file provided")
        
        
