"""Reproducible, non-interactive plot/FFT benchmark (not a GUI latency test).

Run with: uv run python tests/performance_probe.py --output profile_after.prof
"""

import argparse
import cProfile
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

# Warm the same scientific imports that the original widgets module imported.
# Keep this steady-state comparison separate from first-use/startup timings.
from ground_motion_analyzer import filtering, models  # noqa: F401
from ground_motion_analyzer.widgets import PlotArea


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="profile_after.prof")
    parser.add_argument("--samples", type=int, default=200_000)
    args = parser.parse_args()
    samples = np.arange(args.samples) * 0.01
    signal = np.sin(2 * np.pi * 3 * samples) + 0.2 * np.cos(2 * np.pi * 17 * samples)
    profile = cProfile.Profile()
    profile.enable()
    started = time.perf_counter()
    if hasattr(PlotArea, "_prepare_plot"):
        figure, fourier_data, _ = PlotArea._prepare_plot(signal)
    else:
        # Compatibility with the original synchronous implementation.
        figure = Figure(figsize=(8, 6), dpi=100)
        area = SimpleNamespace(
            fig=figure, canvas=SimpleNamespace(draw_idle=lambda: None)
        )
        area._style_axis = lambda *args: PlotArea._style_axis(area, *args)
        PlotArea.plot(area, signal)
        fourier_data = area._fourier_data
    prepared = time.perf_counter()
    canvas = FigureCanvasAgg(figure)
    canvas.draw()
    finished = time.perf_counter()
    profile.disable()
    profile.dump_stats(args.output)
    print(
        json.dumps(
            {
                "samples": args.samples,
                "prepare_seconds": prepared - started,
                "draw_seconds": finished - prepared,
                "total_seconds": finished - started,
                "fft_rows": len(fourier_data),
                "max_line_points": max(
                    len(line.get_xdata()) for ax in figure.axes for line in ax.lines
                ),
                "max_collection_vertices": max(
                    len(path.vertices)
                    for ax in figure.axes
                    for collection in ax.collections
                    for path in collection.get_paths()
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
