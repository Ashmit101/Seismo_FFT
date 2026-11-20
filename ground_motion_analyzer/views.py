import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.simpledialog import Dialog

from loguru import logger

from . import widgets as w
from .background import BackgroundTask
from .constants import ColumnMode, Events, Palette


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
            developer="By Ashmit Rajaure",
            download_command=self.download_fourier_data,
        )
        self.header.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky=(tk.N + tk.E + tk.W + tk.S),
            pady=(0, 12),
        )
        self.control_panel = ControlPanel(
            self, bg=Palette.BG, on_load_start=self._loading_file
        )
        self.control_panel.grid(row=1, column=0, sticky=(tk.N + tk.S + tk.W))
        self.control_panel.bind(Events.VARIABLES_UPDATED, self._plot)

        self.plot_area = w.PlotArea(self)
        self.plot_area.grid(row=1, column=1, sticky=(tk.N + tk.S + tk.E + tk.W))

    def _loading_file(self):
        self.header.set_download_enabled(False)
        self.plot_area.cancel_pending()

    def _plot(self, *_):
        self.header.set_download_enabled(False)
        self.plot_area.cancel_pending()
        try:
            control_variables = self.control_panel.get()
        except (tk.TclError, ValueError):
            logger.debug("Waiting for valid control values")
            return
        data = control_variables.get("data")

        if data is not None:
            columns = data.columns
            logger.info(f"Columns: {columns}")

            column_mode = control_variables["column_format"]
            if column_mode == ColumnMode.SINGLE:
                motion_data = data[columns[0]]
                time_data = None
            else:
                time_data = data[columns[0]]
                if column_mode == ColumnMode.THREE_COMPONENT:
                    motion_data = data.iloc[:, 1:4]
                else:
                    motion_data = data[columns[1]]

            self.plot_area.plot(
                motion_data=motion_data,
                time_data=time_data,
                time_increment=control_variables["time_increment"],
                filter_params=control_variables["filter"],
                data_unit=control_variables["data_unit"],
                demean=control_variables["demean"],
                detrend=control_variables["detrend"],
                sensitivity=control_variables["sensitivity"],
                on_ready=lambda: self.header.set_download_enabled(True),
            )
        else:
            logger.info("No data file provided")

    def download_fourier_data(self, *_):
        logger.info("Exporting Fourier data")
        MainView._export_data(
            self,
            self.plot_area.get_fourier_data(),
            kind="Fourier",
            filename_suffix="fourier_transform",
            dialog_title="Save Fourier transformed data",
        )

    def download_time_series_data(self, *_):
        logger.info("Exporting time-series data")
        MainView._export_data(
            self,
            self.control_panel.data,
            kind="Time-series",
            filename_suffix="time_series",
            dialog_title="Save time-series data",
        )

    def _export_data(self, data, *, kind, filename_suffix, dialog_title):
        if data is None:
            messagebox.showwarning(
                f"No {kind.lower()} data",
                f"Load a valid signal file before exporting {kind.lower()} data.",
                parent=self,
            )
            return

        data_file = self.control_panel.file_selector.get()["file"]
        source_name = getattr(data_file, "name", None) or str(data_file or "signal")
        initial_name = f"{Path(source_name).stem}_{filename_suffix}.csv"
        output_path = filedialog.asksaveasfilename(
            parent=self,
            title=dialog_title,
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
            data.to_csv(output_path, index=False, sep=separator)
        except (OSError, PermissionError) as error:
            logger.exception("Could not save {} data", kind)
            messagebox.showerror(
                "Save failed",
                f"Could not save the {kind.lower()} data:\n{error}",
                parent=self,
            )
            return

        messagebox.showinfo(
            f"{kind} data saved",
            f"Saved to:\n{output_path}",
            parent=self,
        )


class DataTypeDialog(Dialog):
    def __init__(self, parent, title):
        self.data_types = {
            "Unknown / raw counts": ["unknown", "counts"],
            "Acceleration": ["m/s²", "cm/s²", "g"],
            "Velocity": ["m/s", "cm/s"],
            "Displacement": ["m", "cm"],
        }
        self.data_type = tk.StringVar(master=parent, value=next(iter(self.data_types)))
        self.unit = tk.StringVar(master=parent, value="unknown")
        self.sensitivity = tk.DoubleVar(master=parent, value=0.0)
        super().__init__(parent, title=title)

    def body(self, frame):
        type_combo = ttk.Combobox(
            frame,
            textvariable=self.data_type,
            values=list(self.data_types),
            state="readonly",
            width=15,
        )
        type_combo.grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        type_combo.bind("<<ComboboxSelected>>", self._on_type_change)
        self.unit_combo = ttk.Combobox(
            frame,
            textvariable=self.unit,
            values=self.data_types[self.data_type.get()],
            state="readonly",
            width=12,
        )
        self.unit_combo.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(frame, text="Sensitivity: ").grid(row=1, column=0, sticky=tk.W)

        self.sensitivity_input = ttk.Spinbox(
            frame,
            textvariable=self.sensitivity,
            from_=0.0,
            to=100.0,
            width=12,
        )
        self.sensitivity_input.grid(row=1, column=1, sticky=tk.W)
        return type_combo

    def _on_type_change(self, _event=None):
        units = self.data_types[self.data_type.get()]
        self.unit_combo["values"] = units
        self.unit.set(units[0])

    def apply(self):
        self.result = (self.unit.get(), self.sensitivity.get())


class ControlPanel(tk.Frame):
    """Control panel"""

    def __init__(self, parent, *args, on_load_start=None, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.control_variables = {}
        self.data = None
        self._on_load_start = on_load_start
        self._file_task = BackgroundTask(self, self._file_loaded, self._file_failed)
        self.loading = ttk.Label(self, text="Loading file...")
        self.loading.grid(row=0, column=0, sticky=tk.W)
        self.loading.grid_remove()

        # File Selector
        self.file_selector = w.FileSelector(self)
        self.file_selector.grid(row=1, column=0, sticky=(tk.W + tk.E))
        self.file_selector.bind(Events.FILE_SELECTED, self._handle_new_file)

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
        self.double_col_params.grid(row=5, column=0, sticky=(tk.W + tk.E))
        self.double_col_params.grid_remove()
        self.double_col_params.bind(
            Events.CONTROL_VALUE_UPDATED, self._emit_values_change
        )

        # Detrend and Demean
        self.demean_detrend_options = w.Demean(self)
        self.demean_detrend_options.grid(row=6, sticky=(tk.W + tk.E))
        self.demean_detrend_options.bind(
            Events.CONTROL_VALUE_UPDATED, self._emit_values_change
        )

        self.filtering = w.Filtering(self)
        self.filtering.grid(row=7, column=0, sticky=(tk.W + tk.E))
        self.filtering.bind(Events.FILTER_PARAMS_UPDATED, self._emit_values_change)

        self.statistics = w.Statistics(self, {})
        self.statistics.grid(row=8, column=0, sticky=(tk.W + tk.E))

    def _handle_new_file(self, *_):
        new_file = self.file_selector.get()["file"]
        if not new_file:
            logger.warning("No new file selected")
            return

        self.data = None
        if self._on_load_start is not None:
            self._on_load_start()
        self.loading.grid()
        self._file_task.submit(self._read_file, new_file)

    @staticmethod
    def _read_file(path):
        from .data_loading import detect_column_mode, read_signal_data

        data = read_signal_data(path)
        return data, detect_column_mode(data)

    def _file_loaded(self, result):
        self.data, column_mode = result
        self.column_format.set(column_mode)
        self.statistics.set_file_info(
            self.data.attrs.get("metadata", {}),
            sample_count=len(self.data),
            component_count=3 if column_mode == ColumnMode.THREE_COMPONENT else 1,
            data_unit=self.file_selector.get().get("data_unit"),
        )
        self.loading.grid_remove()
        self._emit_values_change()

    def _file_failed(self, error):
        self.loading.grid_remove()
        messagebox.showerror("Load failed", str(error), parent=self)

    def _emit_values_change(self, *_):
        logger.info("Variables updated!")
        self.event_generate(Events.VARIABLES_UPDATED)

    def _show_options_for_mode(self, column_mode: ColumnMode):
        if column_mode == ColumnMode.SINGLE:
            self.double_col_params.grid_remove()
            self.single_col_options.grid()
        else:
            self.single_col_options.grid_remove()
            self.double_col_params.grid()

    def load_new_file(self):
        self.file_selector.load_file()

    def get(self):
        control_variables = {
            "column_format": self.column_format.get(),
            "time_increment": self.single_col_options.get(),
            "filter": self.filtering.get(),
            "data": self.data,
            **self.demean_detrend_options.get(),
            **self.file_selector.get(),
        }
        return control_variables
