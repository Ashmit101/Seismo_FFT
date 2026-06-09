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

## Dependencies

Key libraries: **marimo**, **obspy**, **numpy**, **pandas**, **scipy**, **matplotlib**, **plotly**. See `pyproject.toml` for full list.

## License

See repository settings or a `LICENSE` file in the repo.
