"""Auto-closing real-Tk smoke/profile run; requires a graphical desktop.

Run: uv run python -m cProfile -o profile_after_gui.prof tests/gui_performance_probe.py
The native file dialog is mocked, not timed. CSV reading and plots are real.
"""

import csv
import math
import sys
import tempfile
import threading
import time
from itertools import pairwise
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ground_motion_analyzer.app import Application
from ground_motion_analyzer.background import BackgroundTask


def main():
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "signal.csv"
        with source.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Time", "X", "Y", "Z"])
            for index in range(200_000):
                t = index * 0.01
                writer.writerow([t, math.sin(t), math.cos(t), math.sin(3 * t)])

        started = time.perf_counter()
        app = Application()
        print(f"GUI_CONSTRUCTION_SECONDS {time.perf_counter() - started:.6f}")
        assert not (
            set(sys.modules) & {"numpy", "pandas", "scipy", "matplotlib", "obspy"}
        )
        area = app.main_view.plot_area
        selector = app.main_view.control_panel.file_selector
        main_thread = threading.get_ident()
        errors = []
        beats = []
        completed = []
        original_show = area._task.on_result
        original_run = BackgroundTask._run
        worker_calls = []
        draws = []

        def run(results, request):
            worker_calls.append((request[1].__name__, threading.get_ident()))
            original_run(results, request)

        def show(result):
            assert threading.get_ident() == main_thread
            original_show(result)
            completed.append(time.perf_counter())
            assert len(area._fourier_data) == 100_001
            assert len(area.fig.axes) == (6 if len(completed) == 1 else 2)
            if len(completed) == 1:
                original_draw = area.canvas.draw

                def draw():
                    draws.append(threading.get_ident())
                    assert threading.get_ident() == main_thread
                    return original_draw()

                area.canvas.draw = draw
                area.toolbar.pan()
                assert area.canvas.widgetlock.isowner(area.toolbar)
                # Exercise figure replacement and the rebuilt navigation toolbar.
                app.after(
                    200,
                    lambda: area.plot(
                        app.main_view.control_panel.data.iloc[:, 1],
                        time_increment=0.01,
                    ),
                )
            else:
                area.toolbar.home()
                assert not area.canvas.widgetlock.locked()
                area.toolbar.pan()
                assert area.canvas.widgetlock.isowner(area.toolbar)
                area.toolbar.pan()
                assert not area.canvas.widgetlock.locked()
                app.after(200, app.destroy)

        def failed(error):
            errors.append(str(error))
            app.destroy()

        def heartbeat():
            beats.append(time.perf_counter())
            app.after(10, heartbeat)

        def select_file():
            with (
                patch(
                    "ground_motion_analyzer.widgets.filedialog.askopenfilename",
                    return_value=str(source),
                ),
                patch("ground_motion_analyzer.views.DataTypeDialog") as units,
            ):
                units.return_value.result = "g"
                selector._load_file()

        def callback_exception(kind, error, traceback):
            failed(f"{kind.__name__}: {error}")

        area._task.on_result = show
        area._task.on_error = failed
        app.main_view.control_panel._file_task.on_error = failed
        app.report_callback_exception = callback_exception
        app.after(10, heartbeat)
        app.after(100, select_file)
        app.after(60_000, lambda: failed("GUI smoke test timed out"))
        with patch.object(BackgroundTask, "_run", staticmethod(run)):
            app.mainloop()
        assert draws and all(thread == main_thread for thread in draws)
        assert len(worker_calls) == 3, worker_calls
        assert all(thread != main_thread for _, thread in worker_calls)
        print("GUI_WORKER_AND_CANVAS_THREAD_AFFINITY PASS", worker_calls)
        if errors:
            raise AssertionError(errors)
        assert len(completed) == 2, completed
        gaps = [b - a for a, b in pairwise(beats)]
        print(f"GUI_PLOTS_COMPLETED {len(completed)}")
        print(f"GUI_HEARTBEATS {len(beats)}")
        print(f"GUI_MAX_HEARTBEAT_GAP_SECONDS {max(gaps):.6f}")
        print("GUI_FILE_LOAD_FFT_EXPORT_TOOLBAR_REPLACEMENT PASS")


if __name__ == "__main__":
    main()
