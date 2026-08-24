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
        

class ColumnFormatRadioButton(tk.LabelFrame):

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, text="Column Format", *args, **kwargs)

        self.column_mode = tk.StringVar(value=ColumnMode.SINGLE)

        # Single column
        for index, (val, label) in enumerate([
            (ColumnMode.SINGLE, "Single Column  (data only)"),
            (ColumnMode.DOUBLE, "Double Column  (time + data)"),
        ]):
            rb = ttk.Radiobutton(
                self,
                text=label,
                variable=self.column_mode,
                value=val,
                command=self._on_mode_change,
            )
            rb.grid(row=index+1,
                    column=0,
                    sticky=(tk.W))

    def _on_mode_change(self):
        self.event_generate(Events.COLUMN_FORMAT_UPDATED)

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

    def get(self):
        return self.dt_var.get()


class DoubleColumnParams(tk.LabelFrame):
    """Parameters for Double Column Format"""

    def __init__(self, parent, *args, **kwargs):
        """Double Column Params Initializer"""
        super().__init__(parent, text="Double Column Params", *args, **kwargs)

        self.factor_var = tk.StringVar(value="")

        tk.Label(self,
                 text="Scale Factor (leave blank = 1.0)"
                 ).grid(row=1, column=0)
        tk.Entry(self,
                 textvariable=self.factor_var
                 ).grid(row=2, column=0)

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
        signal_data = filedialog.askopenfile(title="Select signal data file", filetypes=[("CSV", "*.csv")])

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
    

class ControlPanel(tk.Frame):
    """Control panel"""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.control_variables = {}

        self.column_format = ColumnFormatRadioButton(self)
        self.column_format.grid(row=1, column=0, sticky=(tk.W + tk.E))
        self.column_format.bind(Events.COLUMN_FORMAT_UPDATED, self._column_format_updated)

        self.single_col_options = SingleColumnParams(self)
        self.single_col_options.grid(row=2,
                                     column=0, sticky=(tk.W + tk.E))

        # Double Column Params
        self.double_col_params = DoubleColumnParams(self)
        self.double_col_params.grid(row=3, column=0, sticky=(tk.W + tk.E))
        self.double_col_params.grid_remove()
        
        # File Selector
        self.file_selector = FileSelector(self)
        self.file_selector.grid(row=4, column=0, sticky=(tk.W + tk.E))
        self.file_selector.bind(Events.FILE_SELECTED, self._file_selected)

        self.filtering = Filtering(self)
        self.filtering.grid(row=5, column=0, sticky=(tk.W + tk.E))
        self.filtering.bind(Events.FILTER_PARAMS_UPDATED, self._emit_values_change)

        self.statitics = Statistics(self, {})
        self.statitics.grid(row=6, column=0, sticky=(tk.W + tk.E))


    def _emit_values_change(self, *_):
        self.event_generate(Events.VARIABLES_UPDATED)

    def _file_selected(self, *_):
        self.control_variables["signal_data_file"] = self.file_selector.get_file()
        self._emit_values_change()
        self.event_generate(Events.FILE_SELECTED)

    def _column_format_updated(self, *_):
        column_mode = self.column_format.get()
        self.control_variables["column_format"] = column_mode

        if column_mode == ColumnMode.SINGLE:
            self.double_col_params.grid_remove()
            self.single_col_options.grid()
            self.control_variables["time_increment"] = self.single_col_options.get()
        else:
            self.single_col_options.grid_remove()
            self.double_col_params.grid()
            self.control_variables["scale_factor"] = self.double_col_params.get()

        self._emit_values_change()

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
        toolbar_frame.grid(sticky=(tk.S + tk.W + tk.E))
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

    def plot(self, motion_data, *, time_data = None, time_increment = 0.01):
        """Plot the given data"""
        logger.info(f"Plotting {len(motion_data)} data points")

        motion_data = pd.to_numeric(motion_data, errors='coerce')
        motion_data = motion_data.dropna()
        motion_data = motion_data.to_numpy()
        
        self.ax_time.cla()
        self.ax_time.set_facecolor(Palette.PANEL)
        self.ax_time.tick_params(colors=Palette.SUBTEXT, labelsize=8)
        for sp in self.ax_time.spines.values():
            sp.set_edgecolor(Palette.BORDER)

        if time_data is None:
            logger.info("Calculating time series")
            t0 = 0.0
            time_data = np.array([t0 + i * time_increment for i in range(len(motion_data))])
            logger.info("Time series calcution completed")

        self.ax_time.plot(time_data, motion_data,
                          color=Palette.ACCENT2,
                          linewidth=0.9,
                          alpha=0.9)
        self.ax_time.fill_between(time_data, motion_data, alpha=0.15, color=Palette.ACCENT2)
        self.ax_time.axhline(0, color=Palette.BORDER, linewidth=0.7, linestyle="--")

        self.ax_time.set_title(
            "Time vs Ground Motion",
            color=Palette.TEXT,
            fontsize=10,
            fontfamily="monospace",
            pad=8,
        )
        self.ax_time.set_xlabel("Time (s)", color=Palette.SUBTEXT, fontsize=8)
        self.ax_time.set_ylabel("Amplitude", color=Palette.SUBTEXT, fontsize=8)
        self.ax_time.grid(True, color=Palette.BORDER, linewidth=0.5, linestyle="--", alpha=0.6)
        logger.debug("Title labels and grid done")
        
        # self.fig.tight_layout(rect=[0, 0, 1, 1], h_pad=3.0)
        logger.debug("Drawing the canvas")

        # ── Fourier spectrum
        self.ax_fourier.cla()
        self.ax_fourier.set_facecolor(Palette.PANEL)
        self.ax_fourier.tick_params(colors=Palette.SUBTEXT, labelsize=8)
        for sp in self.ax_fourier.spines.values():
            sp.set_edgecolor(Palette.BORDER)

        n = len(motion_data)
        fft_vals = np.abs(np.fft.rfft(motion_data)) / n
        freqs = np.fft.rfftfreq(n, d=time_increment)

        self.ax_fourier.plot(freqs, fft_vals, color=Palette.ACCENT, linewidth=0.9)
        self.ax_fourier.fill_between(freqs, fft_vals, alpha=0.2, color=Palette.ACCENT)

        self.ax_fourier.set_title(
            "Fourier Spectrum", color=Palette.TEXT, fontsize=10, fontfamily="monospace", pad=8
        )
        self.ax_fourier.set_xlabel("Frequency (Hz)", color=Palette.SUBTEXT, fontsize=8)
        self.ax_fourier.set_ylabel("Amplitude", color=Palette.SUBTEXT, fontsize=8)
        self.ax_fourier.grid(
            True, color=Palette.BORDER, linewidth=0.5, linestyle="--", alpha=0.6
        )

        self.fig.tight_layout(rect=[0, 0, 1, 1], h_pad=3.0)


        self.canvas.draw_idle()
