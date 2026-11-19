# Seismo FFT

Seismology signal analysis with FFT (Fast Fourier Transform): directional components, frequency-domain plots, and interactive exploration via a Marimo notebook.

## Requirements

- **Python** 3.12+
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip

## Installation

Clone the repo and install dependencies with uv:

```bash
git clone https://github.com/YOUR_USERNAME/Seismo_FFT.git
cd Seismo_FFT
uv sync
```

Or with pip:

```bash
pip install -e .
```

## Usage

### Interactive app (Marimo)

Run the Marimo notebook for interactive signal upload, column mapping, and FFT visualization:

```bash
uv run marimo edit seismo_signal.py
```

- Upload a tab-delimited (`.txt`) or CSV file.
- Choose columns for time, vertical, east–west, and north–south.
- View time-series and frequency-domain plots.

**Static export (e.g. for GitHub Pages):**

```bash
uv run marimo export html-wasm seismo_signal.py -o seismo_fft_page --mode run
```

Then serve or open the generated files in `seismo_fft_page/`.

### Command-line script

Run the directional FFT analysis script (expects a data file in the project root):

```bash
uv run python main.py
```

**Data format:** `main.py` looks for **`new_data.txt`** in the project root, tab-delimited, with columns:

- `Time (s)` — time in seconds
- `V` — vertical component
- `E-W` — east–west component
- `N-S` — north–south component

Results are shown as matplotlib figures and optionally written to `directional_components.csv`.

## Project structure

| Path | Description |
|------|-------------|
| `seismo_signal.py` | Marimo app: interactive signal upload, column mapping, FFT plots |
| `main.py` | Script: load data, directional FFT analysis, matplotlib plots |
| `plot_signal.py`, `plot_fft.py` | Plotting helpers |


# Graphical User Interface

The application is named "Ground Motion Analyzer" and its source code is inside `ground_motion_analyzer`. The GUI is built entirely with [Tkinter](https://docs.python.org/3/library/tkinter.html).

To run the GUI from source:

```bash
uv run python -m ground_motion_analyzer
```

### Supported GUI input files

Use **Select File** to open CSV/text, MiniSEED, or **SAC** recordings. The SAC
filter accepts `.sac` / `.SAC` and `.sacxy` / `.SACXY`; the loader handles binary
SAC in either byte order and SAC ASCII (alphanumeric) files.

SAC support is for a single, evenly sampled time-history component per file.
The time axis uses the SAC begin offset (`b`) and sample interval (`delta`), in
seconds relative to the SAC reference time. Amplitudes are read unchanged; the
existing unit-selection dialog still applies, and no instrument-response or
physical-unit conversion is performed automatically. Filtering, plotting, FFT,
and FFT CSV export use the same background processing path as other inputs.
Spectral/XY SAC files, unevenly sampled records, invalid sample intervals, and
nonfinite samples are rejected with an error rather than misinterpreted.

### Building the GUI

To build a standalone executable for your current operating system:

```bash
uv run pyinstaller --clean --noconfirm ground_motion_analyzer.spec
```

Use the spec file so the executable includes ObsPy's reader plugins, dependency
metadata, native libraries, and version-file handling. Building directly from
`ground_motion_analyzer/__main__.py` bypasses these settings.

Run the executable on macOS or Linux:

```bash
./dist/ground_motion_analyzer
```

On Windows, run `dist\ground_motion_analyzer.exe`.

### Matplotlib font cache in standalone builds

The frozen app uses a persistent, per-user font cache rather than PyInstaller's
new temporary cache on every launch:

- macOS: `~/Library/Caches/Seismo_FFT/matplotlib`
- Windows: `%LOCALAPPDATA%\Seismo_FFT\matplotlib`
- Linux: `$XDG_CACHE_HOME/Seismo_FFT/matplotlib` (default `~/.cache/Seismo_FFT/matplotlib`)

The first plot can still report **"Matplotlib is building the font cache"**.
Subsequent launches reuse that index; deleting the cache or a Matplotlib cache
format change can require another rebuild. This does not remove PyInstaller's
separate one-file extraction time. Rebuild the executable using the command
above to include this fix; existing executables do not update automatically.

For a custom writable location, set `SEISMO_FFT_MPLCONFIGDIR` before launching the
executable. Ordinary `MPLCONFIGDIR` is overwritten by PyInstaller's runtime hook,
so the frozen app uses this app-specific override. Source runs retain Matplotlib's
normal `MPLCONFIGDIR` behavior. If the persistent directory is not writable, the
app logs a warning and retains PyInstaller's temporary-cache fallback.

To build a Python wheel and source distribution instead:

```bash
uv build
```
