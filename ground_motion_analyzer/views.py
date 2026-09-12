import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.simpledialog import Dialog

import pandas as pd
from loguru import logger

from . import widgets as w
from .constants import ColumnMode, Events, Palette
from .data_loading import detect_column_mode, read_signal_data


class MainView(tk.Frame):
    """Main view of the application"""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header = w.Header(
            self,
            title="Ground Motion Analyzer",
            developer="Ashmit Rajaure",
            download_command=self._download_fourier_data,
        )
        self.header.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky=(tk.N + tk.E + tk.W + tk.S),
            pady=(0, 12),
        )
        self.control_panel = ControlPanel(self, bg=Palette.BG)
        self.control_panel.grid(row=1, column=0, sticky=(tk.N + tk.S + tk.W))
        self.control_panel.bind(Events.VARIABLES_UPDATED, self._plot)

        self.plot_area = w.PlotArea(self)
        self.plot_area.grid(row=1, column=1, sticky=(tk.N + tk.S + tk.E + tk.W))

    def _plot(self, *_):
        self.header.set_download_enabled(False)
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
                data_unit=control_variables["data_unit"],
                demean=control_variables["demean"],
                detrend=control_variables["detrend"],
            )
            self.header.set_download_enabled(True)
        else:
            logger.info("No data file provided")

    def _download_fourier_data(self):
        fourier_data = self.plot_area.get_fourier_data()
        if fourier_data is None:
            messagebox.showwarning(
                "No Fourier data",
                "Load a valid signal file before downloading Fourier data.",
                parent=self,
            )
            return

        data_file = self.control_panel.file_selector.get_file()
        source_name = getattr(data_file, "name", "signal")
        initial_name = f"{Path(source_name).stem}_fourier_transform.csv"
        output_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Fourier transformed data",
            initialfile=initial_name,
            defaultextension=".csv",
            filetypes=[
                ("CSV file", "*.csv"),
                ("Tab-delimited text", "*.tsv *.txt"),
                ("All files", "*.*"),
            ],
        )
        if not output_path:
            return

        separator = (
            "\t" if Path(output_path).suffix.lower() in {".tsv", ".txt"} else ","
        )
        try:
            fourier_data.to_csv(output_path, index=False, sep=separator)
        except (OSError, PermissionError) as error:
            logger.exception("Could not save Fourier data")
            messagebox.showerror(
                "Save failed",
                f"Could not save the Fourier data:\n{error}",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Fourier data saved",
            f"Saved to:\n{output_path}",
            parent=self,
        )


class DataTypeDialog(Dialog):
    """A dialog that asks for data type and unit."""

    def __init__(self, parent, title):
        self.data_types = {
            "Acceleration": ["m/s²", "cm/s²", "g"],
            "Velocity": ["m/s", "cm/s"],
        }
        self.data_type = tk.StringVar(value=next(iter(self.data_types)))
        self.unit = tk.StringVar(value=self.data_types[self.data_type.get()][0])
        super().__init__(parent, title=title)

    def body(self, frame):
        ttk.Label(frame, text="Provide unit for signal").grid(row=0)

        type_combo = ttk.Combobox(
            frame,
            textvariable=self.data_type,
            values=list(self.data_types),
        )
        type_combo.grid()
        type_combo.bind("<<ComboboxSelected>>", self._on_type_change)

        self.unit_combo = ttk.Combobox(
            frame,
            textvariable=self.unit,
            values=self.data_types[self.data_type.get()],
        )
        self.unit_combo.grid()
        return type_combo

    def _on_type_change(self, _event=None):
        units = self.data_types[self.data_type.get()]
        self.unit_combo["values"] = units
        self.unit.set(units[0])

    def apply(self):
        self.result = self.unit.get()


class ControlPanel(tk.Frame):
    """Control panel"""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.control_variables = {}

        # File Selector
        self.file_selector = w.FileSelector(self)
        self.file_selector.grid(row=1, column=0, sticky=(tk.W + tk.E))
        self.file_selector.bind(Events.FILE_SELECTED, self._file_selected)

        self.column_format = w.ColumnFormatDisplay(self)
        self.column_format.grid(row=2, column=0, sticky=(tk.W + tk.E))

        self.single_col_options = w.SingleColumnParams(self)
        self.single_col_options.grid(row=3, column=0, sticky=(tk.W + tk.E))
        self.single_col_options.grid_remove()
        self.single_col_options.bind(
            Events.CONTROL_VALUE_UPDATED, self._emit_values_change
        )

        # Double Column Params
        self.double_col_params = w.DoubleColumnParams(self)
        self.double_col_params.grid(row=4, column=0, sticky=(tk.W + tk.E))
        self.double_col_params.grid_remove()
        self.double_col_params.bind(
            Events.CONTROL_VALUE_UPDATED, self._emit_values_change
        )

        # Detrend and Demean
        self.demean_detrend_options = w.Demean(self)
        self.demean_detrend_options.grid(row=5, sticky=(tk.W + tk.E))
        self.demean_detrend_options.bind(
            Events.CONTROL_VALUE_UPDATED, self._emit_values_change
        )

        self.filtering = w.Filtering(self)
        self.filtering.grid(row=6, column=0, sticky=(tk.W + tk.E))
        self.filtering.bind(Events.FILTER_PARAMS_UPDATED, self._emit_values_change)

        self.statistics = w.Statistics(self, {})
        self.statistics.grid(row=7, column=0, sticky=(tk.W + tk.E))

    def _emit_values_change(self, *_):
        self.event_generate(Events.VARIABLES_UPDATED)

    def _file_selected(self, *_):
        data_file = self.file_selector.get_file()
        try:
            data = read_signal_data(data_file)
            mode = detect_column_mode(data)
        except (OSError, UnicodeError, ValueError, pd.errors.ParserError) as error:
            messagebox.showerror("Unsupported signal file", str(error))
            return

        metadata = data.attrs.get("metadata", {})
        if mode == ColumnMode.SINGLE:
            sampling_rate = metadata.get("Sampling_rate")
            if isinstance(sampling_rate, (int, float)) and sampling_rate > 0:
                self.single_col_options.set(1.0 / sampling_rate)

        component_count = 3 if mode == ColumnMode.THREE_COMPONENT else 1
        self.statistics.set_file_info(
            metadata,
            sample_count=len(data),
            component_count=component_count,
            data_unit=self.file_selector.get_unit(),
        )
        self.control_variables["signal_data_file"] = data_file
        self.column_format.set(mode)
        self._show_options_for_mode(mode)
        self._emit_values_change()
        self.event_generate(Events.FILE_SELECTED)

    def _show_options_for_mode(self, column_mode: ColumnMode):
        if column_mode == ColumnMode.SINGLE:
            self.double_col_params.grid_remove()
            self.single_col_options.grid()
        else:
            self.single_col_options.grid_remove()
            self.double_col_params.grid()

    def get(self):
        control_variables = {
            "column_format": self.column_format.get(),
            "time_increment": self.single_col_options.get(),
            "scale_factor": self.double_col_params.get(),
            "file": self.file_selector.get_file(),
            "data_unit": self.file_selector.get_unit(),
            "filter": self.filtering.get(),
            **self.demean_detrend_options.get(),
        }
        return control_variables
