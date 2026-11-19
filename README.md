# Seismo FFT

Ground motion viewer and FFT tool.

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/YOUR_USERNAME/Seismo_FFT.git
cd Seismo_FFT
uv sync
```

## Run the GUI

```bash
uv run python -m ground_motion_analyzer
```

Supported files:

- CSV / TXT / TSV
- MiniSEED (`.mseed`)
- SAC binary or ASCII (`.sac`, `.sacxy`)

SAC support is for one evenly sampled component per file.

## Build executable

```bash
uv run pyinstaller --clean --noconfirm ground_motion_analyzer.spec
```

Run it:

```bash
./dist/ground_motion_analyzer       # macOS/Linux
dist\ground_motion_analyzer.exe     # Windows
```

The first plot may build Matplotlib's font cache. Later launches reuse it.

## Other tools

Marimo notebook:

```bash
uv run marimo edit seismo_signal.py
```

Old command-line example:

```bash
uv run python main.py
```
