from loguru import logger
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter import messagebox
import matplotlib
import pandas as pd
import numpy as np

matplotlib.use("TkAgg")
matplotlib.rcParams["path.simplify"] = True
matplotlib.rcParams["path.simplify_threshold"] = 1.0
matplotlib.rcParams["agg.path.chunksize"] = 10000

from matplotlib.axes import Axes
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from .constants import ColumnMode, Palette, Events
from .data_loading import detect_column_mode, read_signal_data
from .filtering import filter_signal


class Header(tk.Frame):
    """Header displaying the name of project."""

    def __init__(self, parent, title, developer):
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
            fg=Palette.ACCENT2,
            font=("Consolas", 18, "bold"),
            ).grid(row=1,column=0)
        

class ColumnFormatDisplay(tk.LabelFrame):
    """Display the column layout detected from the selected file."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, text="Detected Format", *args, **kwargs)

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
        super().__init__(parent, text="Single Column Options", *args, **kwargs)

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


class DoubleColumnParams(tk.LabelFrame):
    """Parameters for Double Column Format"""

    def __init__(self, parent, *args, **kwargs):
        """Double Column Params Initializer"""
        super().__init__(parent, text="Component Options", *args, **kwargs)

        self.factor_var = tk.StringVar(value="")

        tk.Label(self,
                 text="Scale Factor (leave blank = 1.0)"
                 ).grid(row=1, column=0)
        tk.Entry(self,
                 textvariable=self.factor_var
                 ).grid(row=2, column=0)
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

    filter_types = ["lowpass", "highpass", "bandpass", "bandstop"]

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text="Filtering", **kwargs)

        self.filter_on = tk.BooleanVar(value=False)
        self.filter_type = tk.StringVar(value=self.filter_types[0])
        self.cutoff_frequency = tk.DoubleVar(value=10.0)   # used for lowpass/highpass, and as LOW cutoff for band*
        self.cutoff_frequency_high = tk.DoubleVar(value=20.0)  # used as HIGH cutoff for bandpass/bandstop
        self.filter_order = tk.IntVar(value=4)

        # --- Enable filter ---
        ttk.Checkbutton(
            self,
            variable=self.filter_on,
            text="Filter"
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=2)

        # --- Filter type ---
        ttk.Label(self, text="Type:").grid(row=1, column=0, sticky="w", padx=4)
        self.filter_type_combo = ttk.Combobox(
            self,
            textvariable=self.filter_type,
            values=self.filter_types,
            state="readonly",
            width=10
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
            width=10
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
            width=10
        )
        # gridded/hidden dynamically in _on_type_change

        # --- Filter order ---
        ttk.Label(self, text="Order:").grid(row=4, column=0, sticky="w", padx=4)
        ttk.Spinbox(
            self,
            textvariable=self.filter_order,
            from_=1,
            to=10,
            increment=1,
            width=10
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
            pass                # widget destroyed or not ready yet

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

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, text="File", *args, **kwargs)

        self.data_file = None
        tk.Button(self,
                  text="Select File",
                  command=self._load_file,
                  ).grid(row=0,
                         column=0)

    def _load_file(self):
        signal_data = filedialog.askopenfile(
            title="Select signal data file",
            filetypes=[
                ("Signal data", "*.csv *.txt"),
                ("CSV", "*.csv"),
                ("Text", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if signal_data:
            self.data_file = signal_data
            self.event_generate(Events.FILE_SELECTED)
      
    def get_file(self):
        return self.data_file

class Statistics(tk.LabelFrame):
    """Statistics of data"""
    def __init__(self, parent, stats: dict, *args, **kwargs):
        super().__init__(parent, text="Statistics", *args, **kwargs)
        
        self.textbox = tk.Text(self,
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
    ):
        lines = [
            f"Samples: {sample_count}",
            f"Components: {component_count}",
        ]
        lines.extend(
            f"{key.replace('_', ' ')}: {value:g}"
            if isinstance(value, float)
            else f"{key.replace('_', ' ')}: {value}"
            for key, value in metadata.items()
        )

        self.textbox.config(state=tk.NORMAL)
        self.textbox.delete("1.0", tk.END)
        self.textbox.insert("1.0", "\n".join(lines))
        self.textbox.config(state=tk.DISABLED)
    

class ControlPanel(tk.Frame):
    """Control panel"""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.control_variables = {}

        # File Selector
        self.file_selector = FileSelector(self)
        self.file_selector.grid(row=1, column=0, sticky=(tk.W + tk.E))
        self.file_selector.bind(Events.FILE_SELECTED, self._file_selected)

        self.column_format = ColumnFormatDisplay(self)
        self.column_format.grid(row=2, column=0, sticky=(tk.W + tk.E))

        self.single_col_options = SingleColumnParams(self)
        self.single_col_options.grid(row=3,
                                     column=0, sticky=(tk.W + tk.E))
        self.single_col_options.grid_remove()
        self.single_col_options.bind(
            Events.CONTROL_VALUE_UPDATED, self._emit_values_change
        )

        # Double Column Params
        self.double_col_params = DoubleColumnParams(self)
        self.double_col_params.grid(row=4, column=0, sticky=(tk.W + tk.E))
        self.double_col_params.grid_remove()
        self.double_col_params.bind(
            Events.CONTROL_VALUE_UPDATED, self._emit_values_change
        )
        
        self.filtering = Filtering(self)
        self.filtering.grid(row=5, column=0, sticky=(tk.W + tk.E))
        self.filtering.bind(Events.FILTER_PARAMS_UPDATED, self._emit_values_change)

        self.statistics = Statistics(self, {})
        self.statistics.grid(row=6, column=0, sticky=(tk.W + tk.E))


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
            "filter": self.filtering.get(),
            }
        return control_variables
        

class PlotArea(tk.Frame):
    """The plots of the signal data"""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        plt.style.use("dark_background")
        self.fig = Figure(figsize=(8, 6), dpi=100, facecolor=Palette.BG)
        self.fig.subplots_adjust(
            hspace=0.45, left=0.1, right=0.96, top=0.93, bottom=0.1
            )

        self.ax_time = self.fig.add_subplot(211)
        self.ax_fourier = self.fig.add_subplot(212)

        self._create_plot_area(self.ax_time,
                               "Time vs Ground Motion",
                               "Time (s)",
                               "Amplitude"
                               )
        self._create_plot_area(self.ax_fourier,
                               "Fourier Spectrum",
                               "Frequency (Hz)",
                               "Amplitude"
                               )

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        widget = self.canvas.get_tk_widget()
        widget.grid(row=0, column=0, sticky=(tk.N + tk.E + tk.S + tk.W))

        toolbar_frame = tk.Frame(self, bg=Palette.PANEL)
        toolbar_frame.grid(row=1, column=0, sticky=(tk.S + tk.W + tk.E))
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.config(bg=Palette.PANEL)
        toolbar.update()

        
    def _create_plot_area(self, subplot: Axes, title: str, xlabel: str, ylabel: str):
        subplot.set_facecolor(Palette.PANEL)
        for spine in subplot.spines.values():
            spine.set_edgecolor(Palette.BORDER)
        subplot.tick_params(colors=Palette.SUBTEXT, labelsize=8)
        subplot.grid(True, color=Palette.BORDER, linewidth=0.5, linestyle="--", alpha=0.6)

        subplot.set_title(
            title,
            color=Palette.TEXT,
            fontsize=10,
            fontfamily="monospace",
            pad=8
            )
        subplot.set_xlabel(xlabel, color=Palette.SUBTEXT, fontsize=8)
        subplot.set_ylabel(ylabel, color=Palette.SUBTEXT, fontsize=8)
        subplot.text(
            0.5,
            0.5,
            "Load a file to begin",
            ha="center",
            va="center",
            color=Palette.BORDER,
            fontsize=12,
            fontfamily="monospace",
            )

    def plot(
        self,
        motion_data,
        *,
        time_data=None,
        time_increment=0.01,
        filter_params=None,
        scale_factor=1.0,
    ):
        """Plot one or three signal components in time and frequency domains."""
        logger.info(f"Plotting {len(motion_data)} data points")

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

        self.fig.clear()
        if component_count == 1:
            axes = self.fig.subplots(2, 1, squeeze=False)
            time_axes = [axes[0, 0]]
            fourier_axes = [axes[1, 0]]
        else:
            axes = self.fig.subplots(3, 2, squeeze=False, sharex="col")
            time_axes = list(axes[:, 0])
            fourier_axes = list(axes[:, 1])

        self.ax_time = time_axes[0]
        self.ax_fourier = fourier_axes[0]
        colours = (Palette.ACCENT2, Palette.ACCENT, Palette.SUCCESS)
        sample_count = len(values)
        frequencies = np.fft.rfftfreq(sample_count, d=time_increment)

        for index, component_name in enumerate(component_data.columns):
            signal = values[:, index]
            colour = colours[index]
            time_axis = time_axes[index]
            fourier_axis = fourier_axes[index]

            time_axis.plot(
                time_values, signal, color=colour, linewidth=0.9, alpha=0.9
            )
            time_axis.fill_between(time_values, signal, alpha=0.12, color=colour)
            time_axis.axhline(
                0, color=Palette.BORDER, linewidth=0.7, linestyle="--"
            )

            fft_values = np.abs(np.fft.rfft(signal)) / sample_count
            fourier_axis.plot(
                frequencies, fft_values, color=colour, linewidth=0.9
            )
            fourier_axis.fill_between(
                frequencies, fft_values, alpha=0.16, color=colour
            )

            if component_count == 1:
                time_title = f"{component_name}: Time vs Ground Motion"
                fourier_title = f"{component_name}: Fourier Spectrum"
            else:
                time_title = f"{component_name}: Time History"
                fourier_title = f"{component_name}: Fourier Spectrum"

            self._style_axis(time_axis, time_title, "Time (s)", "Amplitude")
            self._style_axis(
                fourier_axis, fourier_title, "Frequency (Hz)", "Amplitude"
            )

            if component_count == 3 and index < component_count - 1:
                time_axis.set_xlabel("")
                fourier_axis.set_xlabel("")

        self.fig.tight_layout(rect=[0, 0, 1, 1], h_pad=2.0, w_pad=2.0)
        logger.debug("Drawing the canvas")
        self.canvas.draw_idle()

    def _style_axis(self, axis: Axes, title: str, xlabel: str, ylabel: str):
        axis.set_facecolor(Palette.PANEL)
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
