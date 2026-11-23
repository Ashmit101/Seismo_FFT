# SEISNEP

**Seismic Signal Processing and Analaysis, Nepal**

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

Time-series downloads contain the processed data used for the current plot:
cleaned/regularized samples with sensitivity correction, demeaning, detrending,
and filtering applied according to the selected settings. Exports include a
`Time (s)` column and all signal samples, not just the reduced display points.
Wait for the updated plot to finish before exporting after a settings change.

Use **Spectrum scale** above the plots to choose:

| Option | Frequency (x) axis | Magnitude (y) axis |
| --- | --- | --- |
| Linear | Linear | Linear |
| Log–log | Logarithmic | Logarithmic |
| Y log / X linear | Linear | Logarithmic |

Time histories and their zoom stay unchanged. Switching modes reuses the
existing FFT without changing processing or exported values. Both logarithmic
magnitude modes mask nonpositive magnitudes and hide zero-baseline shading;
Log–log also omits zero frequency. If no samples can be displayed, the spectrum
shows an explanatory message. Returning from Log–log restores the linear
frequency extent, including zero. The selected mode also applies to new plots.

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

## Automated releases

The [build and release workflow](.github/workflows/build-release.yml) runs on pushes
(including merged pull requests) to `main` and `staging`:

- **`staging` — beta:** every push builds Linux, Windows, and macOS executables plus
  a Python wheel and source distribution, then publishes them together as a
  [GitHub prerelease](https://github.com/Ashmit101/Seismo_FFT/releases).
  Versions use `<project-version>b<workflow-run-number>` (for example, `0.1.3b42`),
  with a matching `v0.1.3b42` tag pointing at the pushed commit. The Python package
  version is stamped only in the CI checkout; no version bump needs to be committed.
  Rerunning the same workflow run reuses its beta tag and replaces its assets.
- **`main` — stable:** publishes `v<project-version>` only if that release does not
  already exist. Bump the version in [pyproject.toml](pyproject.toml) for a new stable
  release.

Publishing waits for the Python package and all three executable builds to succeed.
Beta releases are marked **Pre-release** and never replace the latest stable release.
These are unsigned desktop binaries; beta deployment means publishing downloadable
release assets, not updating the Marimo GitHub Pages site.

To enable this, include the workflow on `staging` and allow GitHub Actions to run in
repository settings. Publishing uses the automatic `GITHUB_TOKEN` with
`contents: write` only in the release job; no additional secrets are needed.
Repository or organization policies and tag rules must allow that token to create
release tags. The separate [Pages workflow](.github/workflows/deploy_marimo.yaml)
continues to deploy only from `main`.

## Other tools

Marimo notebook:

```bash
uv run marimo edit seismo_signal.py
```

Old command-line example:

```bash
uv run python main.py
```
