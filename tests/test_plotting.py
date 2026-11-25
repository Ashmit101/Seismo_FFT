"""Pure plotting regressions: no Tk root, GUI canvas, or display is required."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt
from scipy.signal import detrend as scipy_detrend

from ground_motion_analyzer.widgets import PlotArea


class DisplayDataTests(unittest.TestCase):
    def test_short_and_exact_limit_data_are_not_reduced(self):
        for length in (0, 1, 17, 4998):
            with self.subTest(length=length):
                x = np.arange(length, dtype=float)
                y = np.sin(x)
                display_x, display_y = PlotArea._display_data(x, y)
                np.testing.assert_array_equal(display_x, x)
                np.testing.assert_array_equal(display_y, y)

    def test_default_cap_preserves_endpoints_extrema_and_sample_order(self):
        for length in (4999, 10001, 120017):
            with self.subTest(length=length):
                x = np.arange(length, dtype=float) * 0.01
                y = np.sin(np.arange(length))
                y[113] = -123.0
                y[-3] = 456.0
                original = y.copy()
                display_x, display_y = PlotArea._display_data(x, y)

                self.assertLessEqual(len(display_x), 4998)
                self.assertEqual(len(display_x), len(display_y))
                self.assertEqual(display_x[0], x[0])
                self.assertEqual(display_x[-1], x[-1])
                self.assertTrue(np.all(np.diff(display_x) > 0))
                self.assertEqual(display_y.min(), y.min())
                self.assertEqual(display_y.max(), y.max())
                indices = np.searchsorted(x, display_x)
                np.testing.assert_array_equal(display_y, y[indices])
                np.testing.assert_array_equal(y, original)

    def test_each_bin_and_partial_tail_keep_both_extrema(self):
        # At this cap/length the implementation uses seven bins of width 15,
        # the last partial bin containing 13 samples. Peaks are deliberately
        # between uniform-stride positions, including inside the final tail.
        length, max_points, bin_size = 103, 18, 15
        x = np.arange(length, dtype=float)
        y = np.zeros(length)
        expected_indices = {0, length - 1}
        for start in range(0, length, bin_size):
            stop = min(start + bin_size, length)
            low, high = start + 2, stop - 3
            y[low] = -(start + 1)
            y[high] = start + 2
            expected_indices.update((low, high))

        display_x, display_y = PlotArea._display_data(x, y, max_points=max_points)

        self.assertLessEqual(len(display_x), max_points)
        self.assertTrue(expected_indices.issubset(set(display_x)))
        np.testing.assert_array_equal(display_y, y[display_x.astype(int)])


class PreparePlotTests(unittest.TestCase):
    def prepare(self, *args, **kwargs):
        # Fail immediately if this supposedly pure worker path creates Tk or
        # attaches a GUI canvas. Matplotlib's plain Figure is safe headlessly.
        with (
            patch(
                "ground_motion_analyzer.widgets.tk.Tk",
                side_effect=AssertionError("Tk root"),
            ),
            patch(
                "matplotlib.backends.backend_tkagg.FigureCanvasTkAgg",
                side_effect=AssertionError("Tk canvas"),
            ),
            patch(
                "matplotlib.backends.backend_tkagg.NavigationToolbar2Tk",
                side_effect=AssertionError("Tk toolbar"),
            ),
        ):
            figure, spectrum, time_series = PlotArea._prepare_plot(*args, **kwargs)
        self.addCleanup(figure.clear)
        return figure, spectrum, time_series

    def assert_time_series(self, time_series, time, values, names):
        values = np.asarray(values)
        if values.ndim == 1:
            values = values[:, None]
        self.assertIsInstance(time_series, pd.DataFrame)
        self.assertEqual(time_series.shape, (len(time), len(names) + 1))
        self.assertEqual(time_series.columns.tolist(), ["Time (s)"] + names)
        self.assertTrue(np.isfinite(time_series.to_numpy()).all())
        np.testing.assert_array_equal(time_series.iloc[:, 0], time)
        np.testing.assert_allclose(
            time_series.iloc[:, 1:], values, rtol=1e-10, atol=1e-12
        )

    def assert_full_fft(self, spectrum, values, dt, names):
        values = np.asarray(values)
        if values.ndim == 1:
            values = values[:, None]
        self.assertEqual(spectrum.shape, (len(values) // 2 + 1, len(names) + 1))
        self.assertEqual(
            spectrum.columns.tolist(),
            ["Frequency (Hz)"] + [f"{name} FFT Magnitude" for name in names],
        )
        np.testing.assert_allclose(
            spectrum.iloc[:, 0], np.fft.rfftfreq(len(values), d=dt)
        )
        np.testing.assert_allclose(
            spectrum.iloc[:, 1:],
            np.abs(np.fft.rfft(values, axis=0)) / len(values),
            rtol=1e-10,
            atol=1e-12,
        )

    def test_one_component_builds_detached_figure_and_full_scaled_fft(self):
        values = np.array([1.0, 3.0, -2.0, 5.0, 4.0, -1.0, 2.0, 0.0])
        series = pd.Series(values, name="Vertical")
        figure, spectrum, time_series = self.prepare(
            series,
            time_increment=0.125,
            sensitivity=0.4,
            demean=False,
            detrend=False,
            data_unit="m/s²",
        )

        self.assertEqual(len(figure.axes), 2)
        time_axis, fft_axis = figure.axes
        self.assertEqual(time_axis.get_title(), "Time History")
        self.assertEqual(fft_axis.get_title(), "Fourier Spectrum")
        self.assertEqual(time_axis.get_xlabel(), "Time (s)")
        self.assertEqual(fft_axis.get_xlabel(), "Frequency (Hz)")
        self.assertEqual(time_axis.get_ylabel(), "Amplitude (m/s²)")
        np.testing.assert_array_equal(
            time_axis.lines[0].get_xdata(), np.arange(8) * 0.125
        )
        np.testing.assert_array_equal(time_axis.lines[0].get_ydata(), values * 2.5)
        self.assert_full_fft(spectrum, values * 2.5, 0.125, ["Vertical"])
        self.assert_time_series(
            time_series, np.arange(8) * 0.125, values * 2.5, ["Vertical"]
        )
        np.testing.assert_array_equal(series, values)

    def test_three_components_use_explicit_time_and_independent_demeaning(self):
        time = 12.0 + np.arange(32) * 0.125
        values = np.column_stack((np.sin(time), np.cos(time) + 7, 2 * np.sin(time) - 4))
        names = ["North", "East", "Vertical"]
        frame = pd.DataFrame(values, columns=names)
        figure, spectrum, time_series = self.prepare(frame, time_data=time, demean=True)
        expected = values - values.mean(axis=0)

        self.assertEqual(len(figure.axes), 6)
        for index, name in enumerate(names):
            time_axis, fft_axis = figure.axes[2 * index : 2 * index + 2]
            self.assertEqual(time_axis.get_title(), f"{name}: Time History")
            self.assertEqual(fft_axis.get_title(), f"{name}: Fourier Spectrum")
            np.testing.assert_array_equal(time_axis.lines[0].get_xdata(), time)
            np.testing.assert_allclose(
                time_axis.lines[0].get_ydata(), expected[:, index]
            )
        self.assert_full_fft(spectrum, expected, 0.125, names)
        self.assert_time_series(time_series, time, expected, names)
        np.testing.assert_array_equal(frame, values)

    def test_large_one_and_three_component_figures_bound_lines_and_fill_vertices(self):
        length = 120017
        samples = np.arange(length, dtype=float)
        for component_count in (1, 3):
            with self.subTest(components=component_count):
                values = np.column_stack(
                    [
                        np.sin(samples * (index + 1) * 0.031)
                        for index in range(component_count)
                    ]
                )
                for index in range(component_count):
                    values[137 + index, index] = -100.0 - index
                    values[-3 - index, index] = 200.0 + index
                names = [f"Component {index + 1}" for index in range(component_count)]
                figure, spectrum, time_series = self.prepare(
                    pd.DataFrame(values, columns=names),
                    time_increment=0.01,
                    demean=False,
                )
                self.assertEqual(len(figure.axes), 2 * component_count)
                self.assert_full_fft(spectrum, values, 0.01, names)
                self.assert_time_series(time_series, samples * 0.01, values, names)
                for index in range(component_count):
                    time_axis, fft_axis = figure.axes[2 * index : 2 * index + 2]
                    for axis, full_y in (
                        (time_axis, values[:, index]),
                        (fft_axis, spectrum.iloc[:, index + 1].to_numpy()),
                    ):
                        displayed = axis.lines[0].get_ydata()
                        self.assertLessEqual(len(displayed), 4998)
                        self.assertEqual(displayed.min(), full_y.min())
                        self.assertEqual(displayed.max(), full_y.max())
                        self.assertEqual(len(axis.collections), 1)
                        collection = axis.collections[0]
                        self.assertTrue(collection.get_rasterized())
                        vertex_count = sum(
                            len(path.vertices) for path in collection.get_paths()
                        )
                        self.assertLess(vertex_count, 10000)
                        self.assertGreater(vertex_count, 0)

                # The export accessor must return all bins, not the display
                # envelope, and must isolate cached results from callers.
                holder = SimpleNamespace(_fourier_data=spectrum)
                exported = PlotArea.get_fourier_data(holder)
                pd.testing.assert_frame_equal(exported, spectrum)
                exported.iloc[0, 1] = -999.0
                self.assertNotEqual(spectrum.iloc[0, 1], -999.0)

                holder = SimpleNamespace(_time_series_data=time_series)
                exported_time = PlotArea.get_time_series_data(holder)
                pd.testing.assert_frame_equal(exported_time, time_series)
                self.assertEqual(len(exported_time), length)
                exported_time.iloc[0, :] = -999.0
                self.assert_time_series(time_series, samples * 0.01, values, names)

    def test_combined_processing_exports_filtered_values_for_each_component(self):
        time = 4.0 + np.arange(512) * 0.01
        filter_params = {
            "is_filter_on": True,
            "filter_type": "bandpass",
            "order": 3,
            "cutoff_frequency": (2.0, 12.0),
        }
        original_params = filter_params.copy()
        for component_count in (1, 3):
            with self.subTest(components=component_count):
                names = ["North", "East", "Vertical"][:component_count]
                values = np.column_stack(
                    [
                        10 * (index + 1)
                        + (index + 2) * time
                        + np.sin(2 * np.pi * (index + 4) * time)
                        + 0.5 * np.cos(2 * np.pi * 30 * time)
                        for index in range(component_count)
                    ]
                )
                frame = pd.DataFrame(values, columns=names, index=np.arange(512) + 20)
                original_frame = frame.copy(deep=True)
                explicit_time = pd.Series(time, name="Recorded time")
                original_time = explicit_time.copy(deep=True)
                figure, spectrum, time_series = self.prepare(
                    frame,
                    time_data=explicit_time,
                    time_increment=0.2,  # Explicit times determine the filter rate.
                    sensitivity=2.5,
                    demean=True,
                    detrend=True,
                    filter_params=filter_params,
                )
                scaled = values / 2.5
                baseline_corrected = scipy_detrend(
                    scaled - scaled.mean(axis=0), axis=0, type="linear"
                )
                dt = np.median(np.diff(time))
                sections = butter(
                    3, (2.0, 12.0), btype="bandpass", fs=1.0 / dt, output="sos"
                )
                expected = sosfiltfilt(sections, baseline_corrected, axis=0)

                self.assertFalse(np.allclose(expected, baseline_corrected))
                self.assert_time_series(time_series, time, expected, names)
                self.assert_full_fft(spectrum, expected, dt, names)
                for index in range(component_count):
                    np.testing.assert_allclose(
                        figure.axes[2 * index].lines[0].get_ydata(),
                        expected[:, index],
                        atol=1e-12,
                    )
                pd.testing.assert_frame_equal(frame, original_frame)
                pd.testing.assert_series_equal(explicit_time, original_time)
                self.assertEqual(filter_params, original_params)

                # Exported values must not alias the caller's input arrays.
                time_series.iloc[0, :] = -999.0
                pd.testing.assert_frame_equal(frame, original_frame)
                pd.testing.assert_series_equal(explicit_time, original_time)

    def test_cleaned_samples_get_generated_times_and_original_component_name(self):
        series = pd.Series(
            ["1.5", "invalid", "-2.0", None, "4.0"],
            name="Vertical raw",
            index=[10, 20, 30, 40, 50],
        )
        original = series.copy(deep=True)
        _, spectrum, time_series = self.prepare(
            series, time_increment=0.25, demean=False
        )
        expected = np.array([1.5, -2.0, 4.0])

        self.assert_time_series(
            time_series, np.arange(3) * 0.25, expected, ["Vertical raw"]
        )
        self.assert_full_fft(spectrum, expected, 0.25, ["Vertical raw"])
        pd.testing.assert_series_equal(series, original)

    def test_explicit_times_and_components_are_cleaned_with_same_row_mask(self):
        names = ["North", "East", "Vertical"]
        frame = pd.DataFrame(
            [[1, 2, 3], [9, 8, 7], [4, 5, 6], [7, "bad", 9], [10, 11, 12]],
            columns=names,
            index=[10, 20, 30, 40, 50],
        )
        time = pd.Series(["5.0", "bad", "5.5", "5.75", "6.0"])
        original_frame, original_time = frame.copy(deep=True), time.copy(deep=True)
        _, spectrum, time_series = self.prepare(frame, time_data=time, demean=False)
        expected = np.array([[1, 2, 3], [4, 5, 6], [10, 11, 12]], dtype=float)

        self.assert_time_series(time_series, [5.0, 5.5, 6.0], expected, names)
        self.assert_full_fft(spectrum, expected, 0.5, names)
        pd.testing.assert_frame_equal(frame, original_frame)
        pd.testing.assert_series_equal(time, original_time)

    def test_burst_data_exports_regularized_times_and_processed_burst_means(self):
        time = np.array([10.0, 10.01, 10.02, 11.0, 11.01, 11.02, 12.0, 12.01, 12.02])
        names = ["North", "East", "Vertical"]
        values = np.arange(27, dtype=float).reshape(9, 3) ** 2
        frame = pd.DataFrame(values, columns=names)
        original_time = time.copy()
        _, spectrum, time_series = self.prepare(
            frame, time_data=time, sensitivity=2.0, demean=True
        )
        expected = values.reshape(3, 3, 3).mean(axis=1) / 2.0
        expected -= expected.mean(axis=0)

        self.assert_time_series(time_series, [10.0, 11.0, 12.0], expected, names)
        self.assert_full_fft(spectrum, expected, 1.0, names)
        np.testing.assert_array_equal(frame, values)
        np.testing.assert_array_equal(time, original_time)

    def test_jittered_uniform_timestamps_are_accepted(self):
        # Sensor CSVs (e.g. scientific-notation exports) often have slight
        # sampling-interval jitter around a constant rate without real gaps.
        steps = np.array(
            [0.008008, 0.007990, 0.008015, 0.007996, 0.008004, 0.008002] * 4
        )
        time = np.concatenate([[0.020893245], 0.020893245 + np.cumsum(steps)])
        names = ["x", "y", "z"]
        values = np.column_stack(
            [np.sin(2 * np.pi * (index + 1) * time) for index in range(3)]
        )
        frame = pd.DataFrame(values, columns=names)

        figure, spectrum, time_series = self.prepare(
            frame,
            time_data=pd.Series(time, name="Time (s)"),
            demean=False,
        )

        dt = float(np.median(steps))
        self.assertEqual(len(figure.axes), 6)
        self.assert_time_series(time_series, time, values, names)
        self.assert_full_fft(spectrum, values, dt, names)

    def test_scientific_notation_sample_csv_plots_successfully(self):
        from pathlib import Path

        from ground_motion_analyzer.data_loading import read_signal_data

        sample_path = (
            Path(__file__).resolve().parents[1]
            / "notebooks"
            / "samples"
            / "scientific_notation.csv"
        )
        data = read_signal_data(sample_path)
        figure, spectrum, time_series = self.prepare(
            data.iloc[:, 1:4],
            time_data=data.iloc[:, 0],
        )

        self.assertEqual(len(figure.axes), 6)
        self.assertEqual(len(time_series), len(data))
        self.assertEqual(len(spectrum), len(data) // 2 + 1)

    def test_time_series_accessor_returns_none_when_no_result_is_cached(self):
        holder = SimpleNamespace(_time_series_data=None)
        self.assertIsNone(PlotArea.get_time_series_data(holder))

    def test_time_series_accessor_returns_independent_copies_of_cached_result(self):
        cached = pd.DataFrame({"Time (s)": [2.0, 2.5], "Vertical": [1.0, -1.0]})
        original = cached.copy(deep=True)
        holder = SimpleNamespace(_time_series_data=cached)
        first = PlotArea.get_time_series_data(holder)
        second = PlotArea.get_time_series_data(holder)

        self.assertIsNot(first, cached)
        self.assertIsNot(first, second)
        pd.testing.assert_frame_equal(first, original)
        first.iloc[0, 0] = 99.0
        first.iloc[1, 1] = 99.0
        first.rename(columns={"Vertical": "Changed"}, inplace=True)
        pd.testing.assert_frame_equal(cached, original)
        pd.testing.assert_frame_equal(second, original)
        pd.testing.assert_frame_equal(PlotArea.get_time_series_data(holder), original)

    def test_invalid_requests_raise_without_creating_a_gui(self):
        cases = [
            ({"motion_data": [1.0]}, "At least two"),
            ({"motion_data": [1.0, 2.0], "time_increment": 0}, "greater than zero"),
            ({"motion_data": [1.0, 2.0], "time_data": [0.0]}, "equal lengths"),
            (
                {"motion_data": [1.0, 2.0], "time_data": [1.0, 0.0]},
                "strictly increasing",
            ),
            (
                {"motion_data": [1.0, 2.0, 3.0], "time_data": [0.0, 0.1, 0.3]},
                "uniformly",
            ),
            ({"motion_data": pd.DataFrame(np.ones((8, 2)))}, "one or three"),
        ]
        for kwargs, message in cases:
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(ValueError, message),
            ):
                self.prepare(**kwargs)


if __name__ == "__main__":
    unittest.main()
