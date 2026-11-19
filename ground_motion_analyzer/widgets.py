from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING, ClassVar

from loguru import logger

from .background import BackgroundTask
from .constants import ColumnMode, Events, Palette

if TYPE_CHECKING:
    from matplotlib.axes import Axes


class Header(tk.Frame):
    """Header displaying the name of project."""

    def __init__(self, parent, title, developer, download_command=None):
        super().__init__(parent, bg=Palette.BG, pady=10)
        self.grid_columnconfigure(0, weight=1)

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
            fg=Palette.SUBTEXT,
            font=("Consolas", 18, "bold"),
        ).grid(row=1, column=0, sticky=tk.E, padx=16)

        self.download_button = tk.Button(
            self,
            text="Download FFT Data",
            command=download_command,
            state=tk.DISABLED,
            bg=Palette.BTN_BG,
            fg=Palette.TEXT,
            activebackground=Palette.BTN_HOV,
            activeforeground=Palette.BG,
            relief=tk.FLAT,
            padx=12,
            pady=7,
            cursor="hand2",
        )
        self.download_button.place(relx=1.0, x=-16, y=4, anchor=tk.NE)

    def set_download_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.download_button.configure(state=state)


class ColumnFormatDisplay(tk.LabelFrame):
    """Display the column layout detected from the selected file."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text="Detected Format", **kwargs)

        self.column_mode = tk.StringVar(value=ColumnMode.SINGLE)
        self.description = tk.StringVar(value="Select a file to detect its format")
        ttk.Label(self, textvariable=self.description).grid(
            row=0, column=0, sticky=tk.W, padx=4, pady=4
        )

    def set(self, mode: ColumnMode):
        descriptions = {
            ColumnMode.SINGLE: "1 column: component data",
            ColumnMode.DOUBLE: "2 columns: time + 1 component",
            ColumnMode.THREE_COMPONENT: "4 columns: time + 3 components",
        }
        self.column_mode.set(mode)
        self.description.set(descriptions[mode])

    def get(self):
        return self.column_mode.get()


class SingleColumnParams(tk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text="Single Column Options", **kwargs)

        tk.Label(
            self,
            text="Time Increment (dt)  [s]",
        ).grid(row=1, column=0)

        self.dt_var = tk.DoubleVar(value=0.01)
        self.dt_entry = tk.Spinbox(
            self,
            textvariable=self.dt_var,
            from_=0,
            to=100,
            increment=0.01,
        )
        self.dt_entry.grid(row=2, column=0)
        self.dt_var.trace_add("write", self._emit_change)

    def _emit_change(self, *_):
        try:
            self.event_generate(Events.CONTROL_VALUE_UPDATED, when="tail")
        except tk.TclError:
            pass

    def get(self):
        return self.dt_var.get()

    def set(self, time_increment: float):
        self.dt_var.set(time_increment)


class ScalingFactor(tk.LabelFrame):
    """Scaling factor for the data"""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text="Scaling Factor", **kwargs)
        self.scaling_factor = tk.DoubleVar(value=1.0)

        tk.Label(self, text="Scaling factor: ").grid(row=0, column=0)
        ttk.Spinbox(
            self,
            from_=0.1,
            to=100.0,
            increment=0.01,
            textvariable=self.scaling_factor,
        ).grid(row=0, column=1)

        self.scaling_factor.trace_add("write", self._on_data_change)

    def get(self):
        return self.scaling_factor.get()

    def _on_data_change(self, *_):
        logger.info("Scaling factor updated")
        self.event_generate(Events.CONTROL_VALUE_UPDATED, when="tail")


class DoubleColumnParams(tk.LabelFrame):
    """Parameters for Double Column Format"""

    def __init__(self, parent, *args, **kwargs):
        """Double Column Params Initializer"""
        super().__init__(parent, *args, text="Component Options", **kwargs)

        self.factor_var = tk.StringVar(value="")

        tk.Label(self, text="Scale Factor (leave blank = 1.0)").grid(row=1, column=0)
        tk.Entry(self, textvariable=self.factor_var).grid(row=2, column=0)
        self.factor_var.trace_add("write", self._emit_change)

    def _emit_change(self, *_):
        try:
            self.event_generate(Events.CONTROL_VALUE_UPDATED, when="tail")
        except tk.TclError:
            pass

    def get(self):
        return self.factor_var.get()


class Filtering(tk.LabelFrame):
    """Parameters for filtering"""

    filter_types: ClassVar[tuple[str, ...]] = (
        "lowpass",
        "highpass",
        "bandpass",
        "bandstop",
    )

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text="Filtering", **kwargs)

        self.filter_on = tk.BooleanVar(value=False)
        self.filter_type = tk.StringVar(value=self.filter_types[0])
        self.cutoff_frequency = tk.DoubleVar(
            value=10.0
        )  # used for lowpass/highpass, and as LOW cutoff for band*
        self.cutoff_frequency_high = tk.DoubleVar(
            value=20.0
        )  # used as HIGH cutoff for bandpass/bandstop
        self.filter_order = tk.IntVar(value=4)

        # --- Enable filter ---
        ttk.Checkbutton(self, variable=self.filter_on, text="Filter").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=4, pady=2
        )

        # --- Filter type ---
        ttk.Label(self, text="Type:").grid(row=1, column=0, sticky="w", padx=4)
        self.filter_type_combo = ttk.Combobox(
            self,
            textvariable=self.filter_type,
            values=self.filter_types,
            state="readonly",
            width=10,
        )
        self.filter_type_combo.grid(row=1, column=1, padx=4, pady=2)
        self.filter_type_combo.bind("<<ComboboxSelected>>", self._on_type_change)

        # --- Low / primary cutoff ---
        self.cutoff_label = ttk.Label(self, text="Cutoff (Hz):")
        self.cutoff_label.grid(row=2, column=0, sticky="w", padx=4)
        self.cutoff_spin = ttk.Spinbox(
            self,
            textvariable=self.cutoff_frequency,
            from_=0.01,
            to=100.0,
            increment=0.1,
            width=10,
        )
        self.cutoff_spin.grid(row=2, column=1, padx=4, pady=2)

        # --- High cutoff (only for bandpass/bandstop) ---
        self.cutoff_high_label = ttk.Label(self, text="High cutoff (Hz):")
        self.cutoff_high_spin = ttk.Spinbox(
            self,
            textvariable=self.cutoff_frequency_high,
            from_=0.01,
            to=100.0,
            increment=0.1,
            width=10,
        )
        # gridded/hidden dynamically in _on_type_change

        # --- Filter order ---
        ttk.Label(self, text="Order:").grid(row=4, column=0, sticky="w", padx=4)
        ttk.Spinbox(
            self, textvariable=self.filter_order, from_=1, to=10, increment=1, width=10
        ).grid(row=4, column=1, padx=4, pady=2)

        self._on_type_change()  # set initial visibility state
        self._bind_change_events()

    def _bind_change_events(self):
        """Attach trace callbacks so any parameter change emits CHANGE_EVENT."""
        for var in (
            self.filter_on,
            self.filter_type,
            self.cutoff_frequency,
            self.cutoff_frequency_high,
            self.filter_order,
        ):
            var.trace_add("write", self._emit_change)

    def _emit_change(self, *_):
        try:
            self.event_generate(Events.FILTER_PARAMS_UPDATED, when="tail")
            logger.info("Filter params updated")
        except tk.TclError:
            pass  # widget destroyed or not ready yet

    def _on_type_change(self, event=None):
        """Show/hide the high-cutoff field depending on filter type."""
        needs_band = self.filter_type.get() in ("bandpass", "bandstop")

        if needs_band:
            self.cutoff_label.config(text="Low cutoff (Hz):")
            self.cutoff_high_label.grid(row=3, column=0, sticky="w", padx=4)
            self.cutoff_high_spin.grid(row=3, column=1, padx=4, pady=2)
        else:
            self.cutoff_label.config(text="Cutoff (Hz):")
            self.cutoff_high_label.grid_remove()
            self.cutoff_high_spin.grid_remove()

    def get(self):
        filter_type = self.filter_type.get()
        params = {
            "is_filter_on": self.filter_on.get(),
            "filter_type": filter_type,
            "order": self.filter_order.get(),
        }

        if filter_type in ("bandpass", "bandstop"):
            params["cutoff_frequency"] = [
                self.cutoff_frequency.get(),
                self.cutoff_frequency_high.get(),
            ]
        else:
            params["cutoff_frequency"] = self.cutoff_frequency.get()

        return params


class FileSelector(tk.LabelFrame):
    """Button to open dialog that selects file"""

    _last_directory: ClassVar[Path | None] = None

    @classmethod
    def _initial_directory(cls):
        if cls._last_directory is not None and cls._last_directory.is_dir():
            return cls._last_directory
        documents = Path.home() / "Documents"
        return documents if documents.is_dir() else Path.cwd()

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text="File", **kwargs)

        self.data_file = None
        self.data_unit = ""
        self.selected_file_name = tk.StringVar(value="No file selected")
        self.sensitivity = 0.0

        tk.Button(
            self,
            text="Select File",
            command=self._load_file,
        ).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(
            self,
            textvariable=self.selected_file_name,
            wraplength=220,
            justify=tk.LEFT,
        ).grid(row=1, column=0, sticky=tk.W, padx=4, pady=(4, 0))

    def _load_file(self):
        if not self.winfo_viewable():
            self.winfo_toplevel().after(100, self._open_dialog)
            return
        self._open_dialog()

    def _open_dialog(self):
        if not self.winfo_exists():
            return
        signal_filepath = filedialog.askopenfilename(
            parent=self,
            title="Select signal data file",
            initialdir=str(self._initial_directory()),
            filetypes=[
                (
                    "Signal data",
                    "*.csv *.txt *.tsv *.mseed *.MSEED *.sac *.SAC *.sacxy *.SACXY",
                ),
                ("CSV", "*.csv"),
                ("Text", "*.txt"),
                ("MSEED", "*.mseed *.MSEED"),
                ("SAC", "*.sac *.SAC *.sacxy *.SACXY"),
                ("All files", "*.*"),
            ],
        )

        if signal_filepath:
            type(self)._last_directory = Path(signal_filepath).parent
            from ground_motion_analyzer.views import DataTypeDialog

            data_type_dialog = DataTypeDialog(self, title="Data units")
            data_unit, sensitivity = data_type_dialog.result
            if data_unit is None:
                return
            self.data_file = signal_filepath
            self.data_unit = data_unit
            self.sensitivity = sensitivity

            self.selected_file_name.set(Path(signal_filepath).name)
            self.event_generate(Events.FILE_SELECTED)

    def get_file(self):
        return self.data_file

    def get_unit(self):
        return self.data_unit


class Statistics(tk.LabelFrame):
    """Statistics of data"""

    def __init__(self, parent, stats: dict, *args, **kwargs):
        super().__init__(parent, *args, text="Statistics", **kwargs)

        self.textbox = tk.Text(
            self,
            bg=Palette.ENTRY_BG,
            fg=Palette.SUBTEXT,
            relief=tk.FLAT,
            width=30,
            height=7,
            state=tk.DISABLED,
            highlightthickness=0,
        )
        self.textbox.grid(row=0, column=0)

    def set_file_info(
        self,
        metadata: dict[str, str | float],
        *,
        sample_count: int,
        component_count: int,
        data_unit: str,
    ):
        lines = [
            f"Samples: {sample_count}",
            f"Components: {component_count}",
            f"Data unit: {data_unit}",
        ]
        lines.extend(
            (
                f"{key.replace('_', ' ')}: {value:g}"
                if isinstance(value, float)
                else f"{key.replace('_', ' ')}: {value}"
            )
            for key, value in metadata.items()
        )

        self.textbox.config(state=tk.NORMAL)
        self.textbox.delete("1.0", tk.END)
        self.textbox.insert("1.0", "\n".join(lines))
        self.textbox.config(state=tk.DISABLED)


class Demean(tk.LabelFrame):
    """Option to demean and detrend plots."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text="Demean & Detrend", **kwargs)

        self._demean = tk.BooleanVar(value=True)
        self._detrend = tk.BooleanVar(value=False)

        tk.Checkbutton(
            self, variable=self._demean, text="Demean", command=self._emit_change
        ).grid(row=0)
        tk.Checkbutton(
            self, variable=self._detrend, text="Detrend", command=self._emit_change
        ).grid(row=1)

    def _emit_change(self):
        self.event_generate(Events.CONTROL_VALUE_UPDATED)

    def get(self):
        return {"demean": self._demean.get(), "detrend": self._detrend.get()}


class PlotArea(tk.Frame):
    """The plots of the signal data"""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._fourier_data = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.canvas = None
        self.fig = None
        self.toolbar = None
        self._on_ready = None
        self.loading = ttk.Label(self, text="Load a file to begin")
        self.loading.grid(row=0, column=0)
        self._task = BackgroundTask(self, self._show_plot, self._plot_failed)

    def _show_plot(self, result):
        """Show a finished plot."""
        from matplotlib.backends.backend_tkagg import (
            FigureCanvasTkAgg,
            NavigationToolbar2Tk,
        )

        figure, fourier_data = result
        if self.canvas is None:
            self.canvas = FigureCanvasTkAgg(figure, master=self)
            self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
            self.toolbar_frame = tk.Frame(self, bg=Palette.PANEL)
            self.toolbar_frame.grid(row=1, column=0, sticky="sew")
        else:
            if self.canvas.widgetlock.isowner(self.toolbar):
                self.canvas.widgetlock.release(self.toolbar)
            self.toolbar.destroy()
            self.fig.set_canvas(None)
            self.canvas.figure = figure
            figure.set_canvas(self.canvas)
            width = self.canvas.get_tk_widget().winfo_width()
            height = self.canvas.get_tk_widget().winfo_height()
            if width > 1 and height > 1:
                figure.set_size_inches(
                    width / figure.dpi, height / figure.dpi, forward=False
                )
        self.fig = figure
        self.ax_time, self.ax_fourier = figure.axes[:2]
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
        self.toolbar.config(bg=Palette.PANEL)
        self.toolbar.update()
        self._fourier_data = fourier_data
        self.canvas.draw_idle()
        self.loading.grid_remove()
        if self._on_ready is not None:
            self._on_ready()

    def _plot_failed(self, error):
        self._fourier_data = None
        self.loading.grid_remove()
        messagebox.showerror("Plot failed", str(error), parent=self)

    def cancel_pending(self):
        """Drop old plot work."""
        self._task.invalidate()
        self._fourier_data = None
        self._on_ready = None
        self.loading.grid_remove()

    def plot(self, motion_data, *, on_ready=None, **kwargs):
        """Queue a plot."""
        self._fourier_data = None
        self._on_ready = on_ready
        self.loading.configure(text="Loading...")
        self.loading.grid()
        self.loading.lift()
        self._task.submit(self._prepare_plot, motion_data, **kwargs)

    @staticmethod
    def _prepare_plot(
        motion_data,
        *,
        time_data=None,
        time_increment=0.01,
        filter_params=None,
        scale_factor=1.0,
        data_unit="",
        demean=True,
        detrend=False,
    ):
        """Build the plot and FFT."""
        import numpy as np
        import pandas as pd
        from matplotlib.figure import Figure

        from .filtering import filter_signal
        from .models import create_fourier_data, preprocess_signal

        if isinstance(motion_data, pd.DataFrame):
            component_data = motion_data.apply(pd.to_numeric, errors="coerce")
        else:
            component_name = getattr(motion_data, "name", None) or "Component"
            component_data = pd.DataFrame(
                {component_name: pd.to_numeric(motion_data, errors="coerce")}
            )
        component_data = component_data.reset_index(drop=True)

        if time_data is None:
            component_data = component_data.dropna()
            time_values = None
        else:
            time_values = pd.Series(
                pd.to_numeric(time_data, errors="coerce")
            ).reset_index(drop=True)
            if len(time_values) != len(component_data):
                raise ValueError("Time and component columns must have equal lengths.")

            valid = time_values.notna() & component_data.notna().all(axis=1)
            component_data = component_data.loc[valid]
            time_values = time_values.loc[valid].to_numpy(dtype=float)

            time_steps = np.diff(time_values)
            if len(time_steps) == 0 or np.any(time_steps <= 0):
                raise ValueError("Time values must be strictly increasing.")
            time_increment = float(np.median(time_steps))
            if not np.allclose(time_steps, time_increment, rtol=1e-3, atol=1e-12):
                raise ValueError("Filtering and FFT require uniformly sampled data.")

        if time_increment <= 0:
            raise ValueError("Time increment must be greater than zero.")

        values = component_data.to_numpy(dtype=float) * scale_factor
        if len(values) < 2:
            raise ValueError("At least two valid signal samples are required.")

        values = preprocess_signal(values, demean=demean, detrend=detrend)

        if filter_params is not None:
            for column_index in range(values.shape[1]):
                values[:, column_index] = filter_signal(
                    values[:, column_index],
                    filter_params,
                    sampling_rate=1.0 / time_increment,
                )

        if time_values is None:
            logger.info("Calculating time series")
            time_values = np.arange(len(values), dtype=float) * time_increment
            logger.info("Time series calcution completed")

        component_count = values.shape[1]
        if component_count not in {1, 3}:
            raise ValueError("Plotting supports either one or three components.")

        figure = Figure(figsize=(8, 6), dpi=100, facecolor=Palette.BG)
        figure.subplots_adjust(
            left=0.10, right=0.96, bottom=0.10, top=0.93, hspace=0.60, wspace=0.35
        )
        if component_count == 1:
            axes = figure.subplots(2, 1, squeeze=False)
            time_axes = [axes[0, 0]]
            fourier_axes = [axes[1, 0]]
        else:
            axes = figure.subplots(3, 2, squeeze=False, sharex="col")
            time_axes = list(axes[:, 0])
            fourier_axes = list(axes[:, 1])

        colours = (Palette.ACCENT2, Palette.ACCENT, Palette.SUCCESS)
        amplitude_label = f"Amplitude ({data_unit})" if data_unit else "Amplitude"
        fourier_data = create_fourier_data(
            values,
            time_increment=time_increment,
            component_names=component_data.columns,
        )
        frequencies = fourier_data.iloc[:, 0].to_numpy()

        for index, component_name in enumerate(component_data.columns):
            signal = values[:, index]
            colour = colours[index]
            time_axis = time_axes[index]
            fourier_axis = fourier_axes[index]

            display_time, display_signal = PlotArea._display_data(time_values, signal)
            time_axis.plot(
                display_time, display_signal, color=colour, linewidth=0.9, alpha=0.9
            )
            time_axis.fill_between(
                display_time, display_signal, alpha=0.12, color=colour, rasterized=True
            )
            time_axis.axhline(0, color=Palette.BORDER, linewidth=0.7, linestyle="--")
            time_axis.margins(x=0)

            fft_values = fourier_data.iloc[:, index + 1].to_numpy()
            display_freq, display_fft = PlotArea._display_data(frequencies, fft_values)
            fourier_axis.plot(display_freq, display_fft, color=colour, linewidth=0.9)
            fourier_axis.fill_between(
                display_freq, display_fft, alpha=0.16, color=colour, rasterized=True
            )
            fourier_axis.margins(x=0)

            if component_count == 1:
                time_title = "Time History"
                fourier_title = "Fourier Spectrum"
            else:
                time_title = f"{component_name}: Time History"
                fourier_title = f"{component_name}: Fourier Spectrum"

            PlotArea._style_axis(time_axis, time_title, "Time (s)", amplitude_label)
            PlotArea._style_axis(
                fourier_axis,
                fourier_title,
                "Frequency (Hz)",
                amplitude_label,
            )

            if component_count == 3 and index < component_count - 1:
                time_axis.set_xlabel("")
                fourier_axis.set_xlabel("")

        return figure, fourier_data

    @staticmethod
    def _display_data(x, y, max_points=4998):
        """Reduce points for display while keeping peaks."""
        import numpy as np

        if len(y) <= max_points:
            return x, y
        bin_size = int(np.ceil(len(y) / ((max_points - 4) // 2)))
        full_bins = len(y) // bin_size
        bins = y[: full_bins * bin_size].reshape(full_bins, bin_size)
        offsets = np.arange(full_bins) * bin_size
        indices = np.concatenate(
            (
                [0],
                offsets + bins.argmin(axis=1),
                offsets + bins.argmax(axis=1),
                [len(y) - 1],
            )
        )
        if full_bins * bin_size < len(y):
            remainder = y[full_bins * bin_size :]
            indices = np.concatenate(
                (
                    indices,
                    [
                        full_bins * bin_size + remainder.argmin(),
                        full_bins * bin_size + remainder.argmax(),
                    ],
                )
            )
        indices = np.unique(indices)
        return x[indices], y[indices]

    def get_fourier_data(self):
        """Return a copy of the spectrum currently displayed, if available."""
        if self._fourier_data is None:
            return None
        return self._fourier_data.copy()

    @staticmethod
    def _style_axis(axis: Axes, title: str, xlabel: str, ylabel: str):
        axis.set_facecolor(Palette.PLOT_BG)
        for spine in axis.spines.values():
            spine.set_edgecolor(Palette.BORDER)
        axis.tick_params(colors=Palette.SUBTEXT, labelsize=8)
        axis.grid(
            True,
            color=Palette.BORDER,
            linewidth=0.5,
            linestyle="--",
            alpha=0.6,
        )
        axis.set_title(
            title,
            color=Palette.TEXT,
            fontsize=10,
            fontfamily="monospace",
            pad=8,
        )
        axis.set_xlabel(xlabel, color=Palette.SUBTEXT, fontsize=8)
        axis.set_ylabel(ylabel, color=Palette.SUBTEXT, fontsize=8)
        axis.tick_params(axis="both", which="major", labelsize=10)
