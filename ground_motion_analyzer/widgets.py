import tkinter as tk
from tkinter import ttk
import matplotlib
from matplotlib.font_manager import font_scalings


matplotlib.use("TkAgg")
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from .constants import Palette


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

        self.column_mode = tk.StringVar(value="single")

        # Single column
        for index, (val, label) in enumerate([
            ("single", "Single Column  (data only)"),
            ("double", "Double Column  (time + data)"),
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
        # Emit signal
        print("Column format changed")

        
class SingleColumnParams(tk.LabelFrame):

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, text="Single Column Options", *args, **kwargs)

        tk.Label(
            self,
            text="Time Increment (dt)  [s]",
        ).grid(row=1, column=0)
        
        self.dt_var = tk.StringVar(value="0.01")
        self.dt_entry = tk.Entry(
            self,
            textvariable=self.dt_var,
        )
        self.dt_entry.grid(row=2, column=0)


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


class FileSelector(tk.LabelFrame):
    """Button to open dialog that selects file"""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, text="File", *args, **kwargs)

        tk.Button(self,
                  text="Select File",
                  command=self._load_file,
                  ).grid(row=0,
                         column=0)

    def _load_file(self):
        print("Loading file")
        

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

        self.column_format = ColumnFormatRadioButton(self)
        self.column_format.grid(row=1, column=0, sticky=(tk.W + tk.E))

        self.single_col_options = SingleColumnParams(self)
        self.single_col_options.grid(row=2,
                                     column=0, sticky=(tk.W + tk.E))

        # Double Column Params
        self.double_col_params = DoubleColumnParams(self)
        self.double_col_params.grid(row=3, column=0, sticky=(tk.W + tk.E))

        # File Selector
        self.file_selector = FileSelector(self)
        self.file_selector.grid(row=4, column=0, sticky=(tk.W + tk.E))

        self.statitics = Statistics(self, {})
        self.statitics.grid(row=5, column=0, sticky=(tk.W + tk.E))


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
