# Seismo_FFT performance changes

Measured on 2026-11-14: macOS arm64, Python 3.12.16, NumPy 2.2.5,
SciPy 1.17.1, Matplotlib 3.10.1. Existing local edits were preserved.

## Changes

1. **Plotting:** [widgets.py](<ground_motion_analyzer/widgets.py>) prepares a
   detached figure, filtering, and FFT in a daemon worker. Tk/backend attachment,
   toolbar updates, and `draw_idle()` remain on the main thread. No application
   `canvas.draw()` calls remain. A Loading label covers preparation.
   [background.py](<ground_motion_analyzer/background.py>) uses a queue polled
   every 25 ms on Tk, then `after(0, ...)` for delivery; workers never call Tk,
   even `after`. One active job plus one replaceable pending request avoids
   unbounded work. Old results/errors are discarded, including after invalid
   numeric edits or destruction. Toolbar pan/zoom locks are released on replacement.
2. **Display geometry:** min/max envelope reduction retains endpoints and bin
   extrema, with at most 4,998 points per trace and fewer than 10,000 vertices per
   fill polygon. Collections are also rasterized. This bounds actual drawing
   work; `draw_idle()` alone would not make a large draw nonblocking. Fixed
   subplot spacing avoids renderer-dependent layout work in the worker.
3. **FFT:** [models.py](<ground_motion_analyzer/models.py>) uses
   `scipy.fft.rfft(..., axis=0, workers=-1)` and preserves the existing `abs(FFT)/N`
   normalization. Full-frequency GUI analysis and CSV exports retain all samples
   and bins. Optional `max_samples` uses anti-aliased polyphase downsampling and
   adjusts the sample interval. It is deliberately **not enabled by default**:
   a shorter display does not imply that discarding high-frequency seismic data
   is acceptable. Preview downsampling lowers the Nyquist limit.
4. **Files:** explicit parent, file filters, Documents/project fallback directory,
   and a last-used directory remembered for the session. A pre-render request
   is deferred by 100 ms; there is no startup dialog. Cancelling either dialog
   preserves the selection. Parsing now runs in a worker too.
5. **Startup:** [app.py](<ground_motion_analyzer/app.py>) defers the views import;
   [views.py](<ground_motion_analyzer/views.py>) defers data-loader imports.
   Plotting imports NumPy/pandas/SciPy/Matplotlib only on demand. Importing the
   application, widgets, and views loads none of those packages or ObsPy.

**Dependencies:** none added. SciPy 1.17.1 was already declared in
[pyproject.toml](<pyproject.toml>); no `uv add` command or lockfile change was needed.

## Measurements and pstats excerpts

The original interactive [profile.prof](<profile.prof>) was inspected, not
replaced. Its key cumulative times were:

```text
calls   cumtime   function
    4     9.312   collections.py:352(draw)
    4     6.344   models.py:31(create_fourier_data)
    4     6.299   numpy _pocketfft.py:318(rfft)
    1     9.441   filedialog.py:381(askopenfilename)
    1     3.150   app.py:1(<module>)
```

That interaction/input was not reproduced exactly. Do not compare those totals
against a different number of draws or a smaller synthetic signal as a speedup.

### Repeatable synthetic comparison

[performance_probe.py](<tests/performance_probe.py>) uses the same 200,000-sample,
single-component 3 Hz + 17 Hz signal, 0.01 s interval, 800×600 Agg figure, and one
render before/after. Scientific imports are warmed before profiling in both
versions. Baseline uses the original implementation; final uses the new one.

| Measurement | Before | Final |
|---|---:|---:|
| Preparation wall time | 0.1024 s | 0.0228 s |
| Drawing wall time | 0.3384 s | 0.1554 s |
| Preparation + drawing | 0.4408 s | 0.1782 s |
| Collection draw cumulative, 2 calls | 0.2955 s | 0.0497 s |
| Largest fill polygon | 400,003 vertices | 9,885 vertices |
| Exported FFT rows | 100,001 | 100,001 |

This run reduced collection drawing by **83%**, drawing wall time by **54%**,
and total preparation/drawing by **60%**. Single runs are illustrative, not a
statistical guarantee; cache state, render styling/layout, and load affect them.

Key lines from [profile_baseline_synthetic.prof](<profile_baseline_synthetic.prof>)
and [profile_after.prof](<profile_after.prof>):

```text
                           before calls/cumtime    after calls/cumtime
collections.py:352(draw)          2 / 0.295458            2 / 0.049674
create_fourier_data              1 / 0.001591            1 / 0.001660
rfft (NumPy -> SciPy)             1 / 0.001155            1 / 0.001074
```

**FFT speedup was not established on this machine.** Median of seven warmed raw
transforms (axis=0) gave the following milliseconds; the 200k cases were also
checked for NumPy/SciPy numerical agreement:

| Samples × components | NumPy | SciPy, workers=-1 |
|---|---:|---:|
| 200,000 × 1 | 0.622 | 0.624 |
| 200,000 × 3 | 1.521 | 1.499 |
| 1,000,000 × 1 | 3.818 | 3.637 |
| 1,000,000 × 3 | 9.478 | 9.652 |

Workers can parallelize independent component transforms, not necessarily a
single one-dimensional transform. Thread overhead and memory layout matter.
The demonstrated responsiveness improvement is moving FFT off Tk, not claiming
that `workers=-1` always lowers elapsed FFT time.

After Tasks 1, 2, and 3, synthetic preparation+draw totals were respectively
0.142, 0.138, and 0.138 s. After import deferral, a first-use preparation including
scientific imports took 0.988 s, while the warmed Task 4 total was 0.163 s.
Import deferral moves that cost to the worker; it does not eliminate it.

### Startup and real Tk verification

- Fresh-process `import ground_motion_analyzer.app`: **1.414 s → 0.010 s**,
  measured inside Python with `perf_counter` (not process launch/uv overhead).
- Final real-Tk window construction: **0.293 s**; no scientific imports were
  present immediately after construction.
- [gui_performance_probe.py](<tests/gui_performance_probe.py>) loaded an actual
  200,000-row, three-component CSV, displayed it, and replaced it with a
  single-component plot while pan was active. Full FFT rows and replacement
  toolbar operations passed. Explicit thread-ID assertions verified file reads
  and figure/FFT preparation off-main, and canvas drawing/result delivery on-main.
- A 10 ms heartbeat ran 132 times; maximum observed gap was **0.155 s**.
  Drawing still runs on Tk and is not zero-latency.
- [profile_after_gui.prof](<profile_after_gui.prof>): collection draw cumulative
  **0.0673 s / 14 calls**. This interpreter's cProfile run included worker calls
  and overlapping cumulative timings, so thread ownership was verified explicitly
  rather than inferred from the presence/absence of FFT in pstats.

The native file dialog was **mocked** in automation. Its real opening latency
was not measured. The original 9.441 s includes user waiting time; native modal
dialogs must remain on Tk. No claim is made that filtering/initialdir removes
that entire duration or avoids all OS/filesystem delays.

## Verification and reproduction

**39 unittest tests pass**, including previous data/filter tests, numerical FFT
agreement, preview anti-aliasing, bounded plot geometry, thread handoff,
coalescing/invalidation, errors/destruction, dialog options/cancellation, invalid
numeric edits, and lazy imports. The real-Tk probe, focused Ruff checks/formatting,
and `git diff --check` also pass. Import checks passed after each task.

```bash
# Optional writable caches for sandboxed runs:
export UV_CACHE_DIR="$PWD/.uv-cache"
export MPLCONFIGDIR="$PWD/.cache/matplotlib"
export XDG_CACHE_HOME="$PWD/.cache"

uv run python -c "import ground_motion_analyzer.app"
uv run python -m unittest discover -s tests -v
uv run python tests/performance_probe.py --output profile_after.prof
uv run python -m pstats profile_after.prof
# At the prompt: sort cumtime; then stats 20; then quit

# Auto-closing real GUI test (requires a graphical desktop):
uv run python -m cProfile -o profile_after_gui.prof tests/gui_performance_probe.py

# Interactive profiling of your original input/actions, then close the window:
uv run python -m cProfile -o profile_after_interactive.prof -m ground_motion_analyzer
```

During implementation the unchanged environment was used with `uv run --no-sync`.
The originally requested script-path command failed before changes because
[app.py](<ground_motion_analyzer/app.py>) used relative imports. It is a class
module, not the launcher; with deferred imports that command only measures class
module loading. Use the package entry point shown above for interactive profiling.
The baseline synthetic profile was captured before editing the plotting code;
the current probe cannot recreate the old implementation by itself.

## Remaining tradeoffs

- Display zoom and toolbar image/vector saves show the reduced envelope, not
  every original sample. FFT CSV exports remain full resolution.
- Active native work cannot be cancelled midway; obsolete results are discarded
  and only the latest pending request runs next.
- Very large CSV exports and their defensive DataFrame copy remain synchronous,
  as before. Export threading is outside this patch's scope.
- The original slow recording still needs an interactive replay to quantify its
  exact FFT and native-dialog timings. No claim of eliminating every GUI stall.
