"""
Ground Motion File Loader & Analyzer
Supports single-column (with dt) and two-column (time, data) formats.
Plots: Time vs Ground Motion, Frequency vs Fourier Spectrum
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import os

# ─── Color Palette ────────────────────────────────────────────────────────────
BG = "#F2EAE3"  # Linen – light warm background
PANEL = "#EBDED1"  # Sandstone – slightly darker panel
ACCENT = "#C07D58"  # Clay – warm terracotta accent
ACCENT2 = "#8A4E35"  # Sage-complementary warm rust
TEXT = "#3B2A1A"  # Deep espresso-brown text
SUBTEXT = "#734F3A"  # Chestnut – muted subtext
ENTRY_BG = "#D8C3A6"  # Warm Beige – input field background
BTN_BG = "#B56B46"  # Terracotta – primary button
BTN_HOV = "#994D2C"  # Burnt Sienna – button hover
SUCCESS = "#5D573B"  # Moss – success state
WARNING = "#C4B195"  # Oat – soft warning tone
BORDER = "#8D8961"  # Olive – subtle border


# ─── Main Application ──────────────────────────────────────────────────────────
class GroundMotionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            dpi = self.winfo_fpixels('1i')  # pixels per inch
            scale = dpi / 96.0
            self.tk.call('tk', 'scaling', scale)
        except Exception:
            pass
        self.title("Ground Motion Analyzer")
        self.geometry("1200x780")
        self.configure(bg=BG)
        self.resizable(True, True)

        # State
        self.time_data = None
        self.motion_data = None
        self.filepath = None
        self.column_mode = tk.StringVar(value="single")

        self._build_ui()
        self._style_ttk()

    # ── TTK Styling ─────────────────────────────────────────────────────────
    def _style_ttk(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "TRadiobutton",
            background=PANEL,
            foreground=TEXT,
            font=("Consolas", 10),
            focuscolor=PANEL,
        )
        style.configure(
            "TLabel", background=PANEL, foreground=TEXT, font=("Consolas", 10)
        )
        style.configure(
            "Header.TLabel",
            background=BG,
            foreground=ACCENT2,
            font=("Consolas", 13, "bold"),
        )
        style.configure(
            "Sub.TLabel", background=PANEL, foreground=SUBTEXT, font=("Consolas", 9)
        )
        style.configure(
            "TEntry",
            fieldbackground=ENTRY_BG,
            foreground=TEXT,
            insertcolor=TEXT,
            borderwidth=1,
        )
        style.configure("TFrame", background=PANEL)
        style.configure("BG.TFrame", background=BG)
        style.configure("TSeparator", background=BORDER)

    # ── UI Layout ────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Top header bar
        header = tk.Frame(self, bg=BG, pady=10)
        header.pack(fill=tk.X, padx=20)

        tk.Label(
            header,
            text="GROUND MOTION ANALYZER",
            bg=BG,
            fg=ACCENT2,
            font=("Consolas", 16, "bold"),
        ).pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="No file loaded")
        tk.Label(
            header,
            textvariable=self.status_var,
            bg=BG,
            fg=SUBTEXT,
            font=("Consolas", 9),
        ).pack(side=tk.RIGHT, padx=10)

        # ── Main horizontal split
        main = tk.Frame(self, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # Left control panel
        self._build_control_panel(main)

        # Right plot area
        self._build_plot_area(main)

    def _build_control_panel(self, parent):
        panel = tk.Frame(
            parent,
            bg=PANEL,
            width=300,
            bd=0,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12), pady=0)
        panel.pack_propagate(False)

        def section(title):
            tk.Label(
                panel, text=title, bg=PANEL, fg=ACCENT, font=("Consolas", 10, "bold")
            ).pack(anchor=tk.W, padx=16, pady=(14, 4))
            tk.Frame(panel, bg=BORDER, height=1).pack(fill=tk.X, padx=16)

        # ── Section 1: Column Mode
        section("▸ COLUMN FORMAT")

        for val, label in [
            ("single", "Single Column  (data only)"),
            ("double", "Double Column  (time + data)"),
        ]:
            rb = ttk.Radiobutton(
                panel,
                text=label,
                variable=self.column_mode,
                value=val,
                command=self._on_mode_change,
            )
            rb.pack(anchor=tk.W, padx=20, pady=3)

        # ── Section 2: Parameters (single mode)
        section("▸ SINGLE-COLUMN PARAMS")

        self.single_frame = tk.Frame(panel, bg=PANEL)
        self.single_frame.pack(fill=tk.X, padx=16, pady=4)

        tk.Label(
            self.single_frame,
            text="Time Increment (dt)  [s]",
            bg=PANEL,
            fg=SUBTEXT,
            font=("Consolas", 9),
        ).pack(anchor=tk.W)
        self.dt_var = tk.StringVar(value="0.01")
        self.dt_entry = tk.Entry(
            self.single_frame,
            textvariable=self.dt_var,
            bg=ENTRY_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            font=("Consolas", 10),
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self.dt_entry.pack(fill=tk.X, pady=(2, 0), ipady=5)

        # ── Section 3: Parameters (double mode)
        section("▸ DOUBLE-COLUMN PARAMS")

        self.double_frame = tk.Frame(panel, bg=PANEL)
        self.double_frame.pack(fill=tk.X, padx=16, pady=4)

        tk.Label(
            self.double_frame,
            text="Scale Factor  (leave blank = 1.0)",
            bg=PANEL,
            fg=SUBTEXT,
            font=("Consolas", 9),
        ).pack(anchor=tk.W)
        self.factor_var = tk.StringVar(value="")
        self.factor_entry = tk.Entry(
            self.double_frame,
            textvariable=self.factor_var,
            bg=ENTRY_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            font=("Consolas", 10),
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self.factor_entry.pack(fill=tk.X, pady=(2, 0), ipady=5)
        tk.Label(
            self.double_frame,
            text="Col 1 = time  |  Col 2 = data",
            bg=PANEL,
            fg=SUBTEXT,
            font=("Consolas", 8, "italic"),
        ).pack(anchor=tk.W, pady=(3, 0))

        # ── Section 4: File
        section("▸ FILE")

        self.file_label = tk.Label(
            panel,
            text="No file selected",
            bg=PANEL,
            fg=SUBTEXT,
            font=("Consolas", 8),
            wraplength=260,
            justify=tk.LEFT,
        )
        self.file_label.pack(anchor=tk.W, padx=16, pady=(6, 2))

        self._btn(panel, "📂  Load File", self._load_file, BTN_BG).pack(
            fill=tk.X, padx=16, pady=(4, 8), ipady=7
        )

        # ── Section 5: Actions
        section("▸ PLOT")

        self._btn(
            panel, "〜  Time-Domain Plot", lambda: self._plot("time"), "#1b5e20"
        ).pack(fill=tk.X, padx=16, pady=(6, 3), ipady=6)
        self._btn(
            panel, "∿  Fourier Spectrum", lambda: self._plot("fourier"), "#0d47a1"
        ).pack(fill=tk.X, padx=16, pady=3, ipady=6)
        self._btn(panel, "◈  Both Plots", lambda: self._plot("both"), "#4a148c").pack(
            fill=tk.X, padx=16, pady=3, ipady=6
        )

        # ── Section 6: Stats
        section("▸ STATISTICS")

        self.stats_text = tk.Text(
            panel,
            bg=ENTRY_BG,
            fg=SUBTEXT,
            font=("Consolas", 8),
            relief=tk.FLAT,
            height=7,
            state=tk.DISABLED,
            highlightthickness=0,
        )
        self.stats_text.pack(fill=tk.X, padx=16, pady=6)

        # Init mode visibility
        self._on_mode_change()

    def _btn(self, parent, text, cmd, bg=BTN_BG):
        """Flat styled button with hover effect."""
        b = tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=bg,
            fg=TEXT,
            relief=tk.FLAT,
            cursor="hand2",
            font=("Consolas", 10, "bold"),
            activebackground=BTN_HOV,
            activeforeground=TEXT,
            bd=0,
        )

        def on_enter(e):
            b.config(bg=BTN_HOV)

        def on_leave(e):
            b.config(bg=bg)

        b.bind("<Enter>", on_enter)
        b.bind("<Leave>", on_leave)
        return b

    def _build_plot_area(self, parent):
        plot_frame = tk.Frame(parent, bg=BG)
        plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create matplotlib figure with dark theme
        plt.style.use("dark_background")
        self.fig = Figure(figsize=(8, 6), dpi=100, facecolor=BG)
        self.fig.subplots_adjust(
            hspace=0.45, left=0.1, right=0.96, top=0.93, bottom=0.1
        )

        self.ax_time = self.fig.add_subplot(211)
        self.ax_fourier = self.fig.add_subplot(212)

        for ax in [self.ax_time, self.ax_fourier]:
            ax.set_facecolor(PANEL)
            for spine in ax.spines.values():
                spine.set_edgecolor(BORDER)
            ax.tick_params(colors=SUBTEXT, labelsize=8)
            ax.grid(True, color=BORDER, linewidth=0.5, linestyle="--", alpha=0.6)

        self.ax_time.set_title(
            "Time vs Ground Motion",
            color=TEXT,
            fontsize=10,
            fontfamily="monospace",
            pad=8,
        )
        self.ax_time.set_xlabel("Time (s)", color=SUBTEXT, fontsize=8)
        self.ax_time.set_ylabel("Amplitude", color=SUBTEXT, fontsize=8)
        self.ax_time.text(
            0.5,
            0.5,
            "Load a file to begin",
            transform=self.ax_time.transAxes,
            ha="center",
            va="center",
            color=BORDER,
            fontsize=12,
            fontfamily="monospace",
        )

        self.ax_fourier.set_title(
            "Fourier Spectrum", color=TEXT, fontsize=10, fontfamily="monospace", pad=8
        )
        self.ax_fourier.set_xlabel("Frequency (Hz)", color=SUBTEXT, fontsize=8)
        self.ax_fourier.set_ylabel("Amplitude", color=SUBTEXT, fontsize=8)
        self.ax_fourier.text(
            0.5,
            0.5,
            "Load a file to begin",
            transform=self.ax_fourier.transAxes,
            ha="center",
            va="center",
            color=BORDER,
            fontsize=12,
            fontfamily="monospace",
        )

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar_frame = tk.Frame(plot_frame, bg=PANEL)
        toolbar_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.config(bg=PANEL)
        toolbar.update()

    # ── Mode toggle ─────────────────────────────────────────────────────────
    def _on_mode_change(self):
        mode = self.column_mode.get()
        for w in self.single_frame.winfo_children():
            w.config(state=tk.NORMAL if mode == "single" else tk.DISABLED)
        for w in self.double_frame.winfo_children():
            w.config(state=tk.NORMAL if mode == "double" else tk.DISABLED)

    # ── File Loading ─────────────────────────────────────────────────────────
    def _load_file(self):
        path = filedialog.askopenfilename(
            title="Select Ground Motion File",
            filetypes=[
                ("Text / Data files", "*.txt *.dat *.csv *.asc"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        self.filepath = path
        fname = os.path.basename(path)
        self.file_label.config(text=f"📄 {fname}", fg=SUCCESS)
        self.status_var.set(f"Loaded: {fname}")

        try:
            mode = self.column_mode.get()
            raw = np.loadtxt(path, comments=("#", "%", "!"))

            if mode == "single":
                self._process_single(raw)
            else:
                self._process_double(raw)

            self._update_stats()
            self._plot("both")

        except Exception as exc:
            messagebox.showerror("Load Error", f"Could not parse file:\n{exc}")
            self.status_var.set("Error loading file")

    def _process_single(self, raw):
        """Single-column: build time axis from dt."""
        if raw.ndim != 1:
            # If file is multi-col, flatten first column
            raw = raw[:, 0]

        try:
            dt = float(self.dt_var.get())
            if dt <= 0:
                raise ValueError("dt must be positive")
        except ValueError as e:
            messagebox.showerror("Invalid dt", str(e))
            return

        n = len(raw)
        t0 = 0.0
        self.time_data = np.array([t0 + i * dt for i in range(n)])
        self.motion_data = raw.copy()

    def _process_double(self, raw):
        """Two-column: time in col 0, data in col 1, optionally scaled."""
        if raw.ndim == 1 or raw.shape[1] < 2:
            messagebox.showerror(
                "Format Error",
                "File must have at least two columns for double-column mode.",
            )
            return

        self.time_data = raw[:, 0]

        factor_str = self.factor_var.get().strip()
        if factor_str == "":
            factor = 1.0
        else:
            try:
                factor = float(factor_str)
            except ValueError:
                messagebox.showerror("Invalid Factor", "Scale factor must be a number.")
                return

        self.motion_data = raw[:, 1] * factor

    # ── Statistics ───────────────────────────────────────────────────────────
    def _update_stats(self):
        if self.motion_data is None:
            return
        d = self.motion_data
        lines = [
            f"  Points   : {len(d)}",
            f"  Min      : {d.min():.4g}",
            f"  Max      : {d.max():.4g}",
            f"  Mean     : {d.mean():.4g}",
            f"  Std Dev  : {d.std():.4g}",
            f"  PGA      : {np.abs(d).max():.4g}",
            f"  Duration : {self.time_data[-1] - self.time_data[0]:.4g} s",
        ]
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert(tk.END, "\n".join(lines))
        self.stats_text.config(state=tk.DISABLED)

    # ── Plotting ─────────────────────────────────────────────────────────────
    def _plot(self, which="both"):
        if self.time_data is None or self.motion_data is None:
            messagebox.showwarning("No Data", "Please load a file first.")
            return

        t = self.time_data
        x = self.motion_data
        dt = t[1] - t[0] if len(t) > 1 else 0.01

        # ── Time domain
        self.ax_time.cla()
        self.ax_time.set_facecolor(PANEL)
        self.ax_time.tick_params(colors=SUBTEXT, labelsize=8)
        for sp in self.ax_time.spines.values():
            sp.set_edgecolor(BORDER)

        if which in ("time", "both"):
            self.ax_time.plot(t, x, color=ACCENT2, linewidth=0.9, alpha=0.9)
            self.ax_time.fill_between(t, x, alpha=0.15, color=ACCENT2)
            self.ax_time.axhline(0, color=BORDER, linewidth=0.7, linestyle="--")

        self.ax_time.set_title(
            "Time vs Ground Motion",
            color=TEXT,
            fontsize=10,
            fontfamily="monospace",
            pad=8,
        )
        self.ax_time.set_xlabel("Time (s)", color=SUBTEXT, fontsize=8)
        self.ax_time.set_ylabel("Amplitude", color=SUBTEXT, fontsize=8)
        self.ax_time.grid(True, color=BORDER, linewidth=0.5, linestyle="--", alpha=0.6)

        # ── Fourier spectrum
        self.ax_fourier.cla()
        self.ax_fourier.set_facecolor(PANEL)
        self.ax_fourier.tick_params(colors=SUBTEXT, labelsize=8)
        for sp in self.ax_fourier.spines.values():
            sp.set_edgecolor(BORDER)

        if which in ("fourier", "both"):
            n = len(x)
            fft_vals = np.abs(np.fft.rfft(x)) / n
            freqs = np.fft.rfftfreq(n, d=dt)

            self.ax_fourier.plot(freqs, fft_vals, color=ACCENT, linewidth=0.9)
            self.ax_fourier.fill_between(freqs, fft_vals, alpha=0.2, color=ACCENT)

        self.ax_fourier.set_title(
            "Fourier Spectrum", color=TEXT, fontsize=10, fontfamily="monospace", pad=8
        )
        self.ax_fourier.set_xlabel("Frequency (Hz)", color=SUBTEXT, fontsize=8)
        self.ax_fourier.set_ylabel("Amplitude", color=SUBTEXT, fontsize=8)
        self.ax_fourier.grid(
            True, color=BORDER, linewidth=0.5, linestyle="--", alpha=0.6
        )

        self.fig.tight_layout(rect=[0, 0, 1, 1], h_pad=3.0)
        self.canvas.draw()


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = GroundMotionApp()
    app.mainloop()
