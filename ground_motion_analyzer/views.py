from loguru import logger
import tkinter as tk

from . import widgets as w
from .constants import ColumnMode, Events, Palette
from .data_loading import read_signal_data


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
        try:
            control_variables = self.control_panel.get()
        except tk.TclError:
            # A numeric field can be briefly incomplete while the user types.
            return
        logger.info(f"control variables: {control_variables}")

        if data_file := control_variables.get("file"):
            data = read_signal_data(data_file)
            columns = data.columns
            logger.info(f"Columns: {columns}")

            column_mode = control_variables["column_format"]
            if column_mode == ColumnMode.SINGLE:
                motion_data = data[columns[0]]
                time_data = None
                scale_factor = 1.0
            else:
                time_data = data[columns[0]]
                if column_mode == ColumnMode.THREE_COMPONENT:
                    motion_data = data.iloc[:, 1:4]
                else:
                    motion_data = data[columns[1]]
                scale_factor_text = control_variables["scale_factor"].strip()
                try:
                    scale_factor = float(scale_factor_text or 1.0)
                except ValueError:
                    return

            self.plot_area.plot(
                motion_data=motion_data,
                time_data=time_data,
                time_increment=control_variables["time_increment"],
                filter_params=control_variables["filter"],
                scale_factor=scale_factor,
            )
        else:
            logger.info("No data file provided")
        
        
