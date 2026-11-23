"""Headless regressions for display-only linear, log–log, and Y-log scales."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import numpy as np
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg

from ground_motion_analyzer.widgets import PlotArea


class SpectrumScaleTests(unittest.TestCase):
    def prepare(self, values, **kwargs):
        """Exercise the real FFT/plot worker without creating any Tk objects."""
        with (
            patch(
                "ground_motion_analyzer.widgets.tk.Tk",
                side_effect=AssertionError("Unexpected Tk root"),
            ),
            patch(
                "matplotlib.backends.backend_tkagg.FigureCanvasTkAgg",
                side_effect=AssertionError("Unexpected Tk canvas"),
            ),
            patch(
                "matplotlib.backends.backend_tkagg.NavigationToolbar2Tk",
                side_effect=AssertionError("Unexpected Tk toolbar"),
            ),
        ):
            result = PlotArea._prepare_plot(values, demean=False, **kwargs)
        self.assertEqual(len(result), 3)
        figure, spectrum, time_series = result

        def clear_figure():
            # Matplotlib clears shared axes one at a time; linearize them first
            # so clearing cannot temporarily propagate zero limits to log axes.
            for axis in figure.axes:
                axis.set_xscale("linear")
                axis.set_yscale("linear")
            figure.clear()

        self.addCleanup(clear_figure)
        canvas = FigureCanvasAgg(figure)
        canvas.draw()
        return figure, canvas, spectrum, time_series

    def assert_positive_magnitude_limits(self, axis):
        limits = axis.get_ylim()
        self.assertTrue(np.isfinite(limits).all(), limits)
        self.assertGreater(limits[0], 0, limits)
        self.assertGreater(limits[1], limits[0], limits)
        magnitudes = np.concatenate([line.get_ydata() for line in axis.lines])
        visible = np.isfinite(magnitudes) & (magnitudes > 0)
        if axis.get_xscale() == "log":
            frequencies = np.concatenate([line.get_xdata() for line in axis.lines])
            visible &= np.isfinite(frequencies) & (frequencies > 0)
        positive = magnitudes[visible]
        if positive.size:
            self.assertLessEqual(limits[0], positive.min())
            self.assertGreaterEqual(limits[1], positive.max())

    def assert_nonpositive_magnitudes_masked(self, axis):
        # Inspect the actual transform: clipping to a tiny positive number is
        # not equivalent to masking nonpositive magnitudes out of the plot.
        transformed = np.ma.asarray(
            axis.yaxis.get_transform().transform(np.array([-1.0, 0.0, 1.0, 10.0]))
        )
        excluded = np.ma.getmaskarray(transformed) | ~np.isfinite(
            np.ma.filled(transformed, np.nan)
        )
        np.testing.assert_array_equal(excluded, [True, True, False, False])
        np.testing.assert_allclose(transformed[2:], [0.0, 1.0])

    def assert_log_frequencies(self, axis):
        self.assertEqual(axis.get_xscale(), "log")
        limits = axis.get_xlim()
        self.assertTrue(np.isfinite(limits).all(), limits)
        self.assertGreater(limits[0], 0, limits)
        self.assertGreater(limits[1], limits[0], limits)
        transformed = np.ma.asarray(
            axis.xaxis.get_transform().transform(np.array([-1.0, 0.0, 1.0, 10.0]))
        )
        excluded = np.ma.getmaskarray(transformed) | ~np.isfinite(
            np.ma.filled(transformed, np.nan)
        )
        np.testing.assert_array_equal(excluded, [True, True, False, False])
        np.testing.assert_allclose(transformed[2:], [0.0, 1.0])

    def assert_linear_frequencies(self, axis):
        self.assertEqual(axis.get_xscale(), "linear")
        # Frequency remains linear, including DC, in linear and Y-only log modes.
        frequencies = np.array([-1.0, 0.0, 0.1, 1.0, 10.0])
        transformed = np.ma.asarray(axis.xaxis.get_transform().transform(frequencies))
        self.assertFalse(np.ma.getmaskarray(transformed).any())
        np.testing.assert_array_equal(transformed, frequencies)

    def assert_linear_magnitudes(self, axis):
        self.assertEqual(axis.get_yscale(), "linear")
        magnitudes = np.array([-1.0, 0.0, 0.1, 1.0, 10.0])
        transformed = np.ma.asarray(axis.yaxis.get_transform().transform(magnitudes))
        self.assertFalse(np.ma.getmaskarray(transformed).any())
        np.testing.assert_array_equal(transformed, magnitudes)

    def assert_empty_annotation(self, axis, *, visible):
        notices = [
            text for text in axis.texts if text.get_gid() == "empty-log-spectrum"
        ]
        self.assertLessEqual(len(notices), 1)
        self.assertEqual(any(text.get_visible() for text in notices), visible)
        for text in notices:
            self.assertEqual(text.get_text(), "No positive spectrum values")

    def test_prepare_remains_linear_and_returns_full_fft_for_one_and_three_components(
        self,
    ):
        values = np.array([1.0, -2.0, 4.0, 0.5, -3.0, 2.0, 5.0, -1.0])
        for component_count in (1, 3):
            with self.subTest(components=component_count):
                columns = ["North", "East", "Vertical"][:component_count]
                samples = np.column_stack(
                    [values * (index + 1) for index in range(component_count)]
                )
                figure, _, spectrum, time_series = self.prepare(
                    pd.DataFrame(samples, columns=columns), time_increment=0.125
                )
                self.assertEqual(len(figure.axes), 2 * component_count)
                for axis in figure.axes:
                    self.assertEqual(axis.get_xscale(), "linear")
                    self.assertEqual(axis.get_yscale(), "linear")
                    self.assertTrue(
                        all(fill.get_visible() for fill in axis.collections)
                    )
                self.assertEqual(
                    spectrum.shape, (len(values) // 2 + 1, component_count + 1)
                )
                np.testing.assert_allclose(
                    spectrum.iloc[:, 0], np.fft.rfftfreq(len(values), 0.125)
                )
                np.testing.assert_allclose(
                    spectrum.iloc[:, 1:],
                    np.abs(np.fft.rfft(samples, axis=0)) / len(values),
                )
                np.testing.assert_array_equal(time_series.iloc[:, 1:], samples)

    def test_roundtrip_changes_only_spectrum_display_and_preserves_time_zoom(self):
        for component_count in (1, 3):
            with self.subTest(components=component_count):
                samples = np.arange(64, dtype=float)
                values = pd.DataFrame(
                    {
                        f"Component {index + 1}": np.sin(samples * (index + 1) * 0.37)
                        + index
                        for index in range(component_count)
                    }
                )
                figure, canvas, spectrum, time_series = self.prepare(values)
                original_spectrum = spectrum.copy(deep=True)
                original_time_series = time_series.copy(deep=True)
                original_input = values.copy(deep=True)
                time_axes, spectrum_axes = figure.axes[::2], figure.axes[1::2]
                for index, axis in enumerate(time_axes):
                    axis.set_xlim(0.12, 0.41)
                    axis.set_ylim(-0.4 + index, 0.6 + index)
                canvas.draw()
                time_limits = [(axis.get_xlim(), axis.get_ylim()) for axis in time_axes]
                frequency_limits = [axis.get_xlim() for axis in spectrum_axes]
                line_data = [
                    (line, line.get_xdata().copy(), line.get_ydata().copy())
                    for axis in figure.axes
                    for line in axis.lines
                ]
                time_fill_visibility = [
                    fill.get_visible()
                    for axis in time_axes
                    for fill in axis.collections
                ]
                spectrum_fills = [
                    fill for axis in spectrum_axes for fill in axis.collections
                ]
                self.assertTrue(spectrum_fills)

                # Multiple switches must reuse artists, not accumulate new plots.
                artist_counts = [
                    (len(axis.lines), len(axis.collections)) for axis in figure.axes
                ]
                # Covers every directed transition among the three modes.
                for scale in ("log", "linear", "loglog", "log", "loglog", "linear"):
                    PlotArea._set_spectrum_scale(figure, scale)
                    canvas.draw()  # A valid scale must also survive real rendering.
                    for axis, xlim in zip(spectrum_axes, frequency_limits):
                        if scale == "loglog":
                            self.assert_log_frequencies(axis)
                        else:
                            self.assert_linear_frequencies(axis)
                            self.assertEqual(axis.get_xlim(), xlim)
                        self.assertEqual(
                            axis.get_yscale(), "linear" if scale == "linear" else "log"
                        )
                        self.assert_empty_annotation(axis, visible=False)
                        if scale != "linear":
                            self.assert_positive_magnitude_limits(axis)
                            self.assert_nonpositive_magnitudes_masked(axis)
                        else:
                            self.assert_linear_magnitudes(axis)
                            self.assertLessEqual(axis.get_ylim()[0], 0)
                        self.assertEqual(
                            axis.lines[0].get_marker(),
                            "None" if scale == "linear" else ".",
                        )
                    self.assertEqual(
                        [fill.get_visible() for fill in spectrum_fills],
                        [scale == "linear"] * len(spectrum_fills),
                    )
                    for axis, (xlim, ylim) in zip(time_axes, time_limits):
                        self.assertEqual(axis.get_xscale(), "linear")
                        self.assertEqual(axis.get_yscale(), "linear")
                        self.assertEqual(axis.get_xlim(), xlim)
                        self.assertEqual(axis.get_ylim(), ylim)
                    self.assertEqual(
                        [
                            fill.get_visible()
                            for axis in time_axes
                            for fill in axis.collections
                        ],
                        time_fill_visibility,
                    )
                    self.assertEqual(
                        [
                            (len(axis.lines), len(axis.collections))
                            for axis in figure.axes
                        ],
                        artist_counts,
                    )
                    for line, x, y in line_data:
                        np.testing.assert_array_equal(line.get_xdata(), x)
                        np.testing.assert_array_equal(line.get_ydata(), y)
                    pd.testing.assert_frame_equal(spectrum, original_spectrum)
                    pd.testing.assert_frame_equal(time_series, original_time_series)
                    pd.testing.assert_frame_equal(values, original_input)

    def test_frequency_x_zoom_is_preserved_when_toggling_from_either_magnitude_scale(
        self,
    ):
        for component_count in (1, 3):
            with self.subTest(components=component_count):
                samples = np.arange(32, dtype=float)
                values = pd.DataFrame(
                    {
                        f"Component {index + 1}": np.sin(samples * (index + 1) * 0.37)
                        for index in range(component_count)
                    }
                )
                figure, canvas, _, _ = self.prepare(values)
                spectrum_axes = figure.axes[1::2]
                for starting_scale in ("linear", "log"):
                    for zoom in ((0.0, 12.5), (-1.0, 8.0), (4.0, 15.0)):
                        with self.subTest(starting_scale=starting_scale, zoom=zoom):
                            PlotArea._set_spectrum_scale(figure, starting_scale)
                            for axis in spectrum_axes:
                                axis.set_xlim(*zoom)
                            canvas.draw()
                            for scale in ("log", "linear", "log", "linear"):
                                PlotArea._set_spectrum_scale(figure, scale)
                                canvas.draw()
                                for axis in spectrum_axes:
                                    self.assert_linear_frequencies(axis)
                                    self.assertEqual(axis.get_yscale(), scale)
                                    self.assertEqual(axis.get_xlim(), zoom)
                                    self.assertFalse(axis.get_autoscalex_on())

    def test_zero_and_dc_only_spectra_render_with_annotation_only_for_empty_log(
        self,
    ):
        for length in (2, 32):
            for constant in (0.0, 7.0):
                for component_count in (1, 3):
                    with self.subTest(
                        length=length, constant=constant, components=component_count
                    ):
                        values = pd.DataFrame(
                            np.full((length, component_count), constant)
                        )
                        figure, canvas, spectrum, _ = self.prepare(values)
                        original_spectrum = spectrum.copy(deep=True)
                        np.testing.assert_array_equal(spectrum.iloc[1:, 1:], 0)
                        spectrum_axes = figure.axes[1::2]
                        frequency_limits = [axis.get_xlim() for axis in spectrum_axes]
                        for scale in ("log", "linear", "log", "linear"):
                            PlotArea._set_spectrum_scale(figure, scale)
                            canvas.draw()
                            for axis, xlim in zip(spectrum_axes, frequency_limits):
                                self.assert_linear_frequencies(axis)
                                self.assertEqual(axis.get_yscale(), scale)
                                self.assertEqual(axis.get_xlim(), xlim)
                                self.assertLessEqual(xlim[0], 0)
                                self.assert_empty_annotation(
                                    axis, visible=scale == "log" and constant == 0
                                )
                                if scale == "log":
                                    self.assert_positive_magnitude_limits(axis)
                                    self.assert_nonpositive_magnitudes_masked(axis)
                                    if constant > 0:
                                        # A positive DC value remains renderable at 0 Hz.
                                        dc = axis.lines[0].get_xydata()[0]
                                        np.testing.assert_array_equal(dc, [0, constant])
                                        self.assertTrue(
                                            np.isfinite(
                                                axis.transData.transform(dc)
                                            ).all()
                                        )
                                        self.assertLess(axis.get_ylim()[0], constant)
                                        self.assertGreater(axis.get_ylim()[1], constant)
                                else:
                                    self.assert_linear_magnitudes(axis)
                                    self.assertLessEqual(axis.get_ylim()[0], 0)
                                self.assertEqual(
                                    axis.lines[0].get_marker(),
                                    "None" if scale == "linear" else ".",
                                )
                                self.assertTrue(axis.collections)
                                self.assertEqual(
                                    [fill.get_visible() for fill in axis.collections],
                                    [scale == "linear"] * len(axis.collections),
                                )
                        pd.testing.assert_frame_equal(spectrum, original_spectrum)

    def test_two_sample_singleton_positive_bin_gets_nonsingular_log_limits(self):
        for component_count in (1, 3):
            with self.subTest(components=component_count):
                values = pd.DataFrame(
                    np.array([[1.0, 2.0, 3.0], [-1.0, -2.0, -3.0]])[:, :component_count]
                )
                figure, canvas, spectrum, _ = self.prepare(values, time_increment=0.25)
                spectrum_axes = figure.axes[1::2]
                frequency_limits = [axis.get_xlim() for axis in spectrum_axes]
                original_spectrum = spectrum.copy(deep=True)
                # Start with the real two-sample FFT, then test display-only data
                # containing invalid magnitudes. Only finite positives set bounds.
                for invalid_dc in (0.0, -1.0, np.nan, np.inf, -np.inf):
                    with self.subTest(invalid_dc=invalid_dc):
                        for index, axis in enumerate(spectrum_axes):
                            magnitude = spectrum.iloc[1, index + 1]
                            axis.lines[0].set_ydata([invalid_dc, magnitude])
                        PlotArea._set_spectrum_scale(figure, "log")
                        canvas.draw()
                        for index, (axis, xlim) in enumerate(
                            zip(spectrum_axes, frequency_limits)
                        ):
                            magnitude = spectrum.iloc[1, index + 1]
                            self.assert_linear_frequencies(axis)
                            self.assertEqual(axis.get_yscale(), "log")
                            self.assert_positive_magnitude_limits(axis)
                            self.assert_nonpositive_magnitudes_masked(axis)
                            self.assertEqual(axis.get_xlim(), xlim)
                            self.assert_empty_annotation(axis, visible=False)
                            self.assertLess(axis.get_ylim()[0], magnitude)
                            self.assertGreater(axis.get_ylim()[1], magnitude)
                            self.assertEqual(axis.lines[0].get_marker(), ".")
                            np.testing.assert_array_equal(
                                axis.lines[0].get_ydata(), [invalid_dc, magnitude]
                            )
                pd.testing.assert_frame_equal(spectrum, original_spectrum)

    def test_zero_dc_and_signal_components_keep_frequency_limits_and_independent_notices(
        self,
    ):
        values = pd.DataFrame(
            {
                "Zero": np.zeros(32),
                "DC": np.ones(32),
                "Signal": np.tile([1.0, -1.0], 16),
            }
        )
        figure, canvas, spectrum, _ = self.prepare(values)
        spectrum_axes = figure.axes[1::2]
        frequency_limits = [axis.get_xlim() for axis in spectrum_axes]
        for scale in ("log", "linear", "log", "linear"):
            PlotArea._set_spectrum_scale(figure, scale)
            canvas.draw()
            for index, (axis, xlim) in enumerate(zip(spectrum_axes, frequency_limits)):
                self.assert_linear_frequencies(axis)
                self.assertEqual(axis.get_xlim(), xlim)
                self.assertEqual(axis.get_xlim(), figure.axes[1].get_xlim())
                self.assertLessEqual(xlim[0], 0)
                self.assertGreaterEqual(xlim[1], spectrum.iloc[-1, 0])
                self.assertEqual(axis.get_yscale(), scale)
                if scale == "log":
                    self.assert_positive_magnitude_limits(axis)
                else:
                    self.assert_linear_magnitudes(axis)
                self.assert_empty_annotation(
                    axis, visible=scale == "log" and index == 0
                )
                self.assertTrue(axis.collections)
                self.assertEqual(
                    [fill.get_visible() for fill in axis.collections],
                    [scale == "linear"] * len(axis.collections),
                )

    def test_leaving_loglog_resets_shared_frequency_zoom_to_include_dc(self):
        for component_count in (1, 3):
            values = pd.DataFrame(np.tile([[1.0], [-1.0]], (16, component_count)))
            figure, canvas, spectrum, _ = self.prepare(values)
            spectrum_axes = figure.axes[1::2]
            for target in ("linear", "log"):
                with self.subTest(components=component_count, target=target):
                    PlotArea._set_spectrum_scale(figure, "loglog")
                    for axis in spectrum_axes:
                        axis.set_xlim(8, 12)
                    canvas.draw()
                    PlotArea._set_spectrum_scale(figure, target)
                    canvas.draw()
                    for axis in spectrum_axes:
                        self.assert_linear_frequencies(axis)
                        self.assertLessEqual(axis.get_xlim()[0], 0)
                        self.assertGreaterEqual(
                            axis.get_xlim()[1], spectrum.iloc[-1, 0]
                        )
                        self.assertEqual(axis.get_xlim(), spectrum_axes[0].get_xlim())

    def test_loglog_zero_dc_and_singleton_bins_have_independent_notices(self):
        for length in (2, 32):
            signals = {
                "Zero": np.zeros(length),
                "DC": np.full(length, 7.0),
                "Signal": np.tile([1.0, -1.0], length // 2),
            }
            for names in (("Zero",), ("DC",), ("Signal",), tuple(signals)):
                with self.subTest(length=length, components=names):
                    figure, canvas, _, _ = self.prepare(
                        pd.DataFrame({name: signals[name] for name in names})
                    )
                    for scale in ("loglog", "log", "loglog", "linear"):
                        PlotArea._set_spectrum_scale(figure, scale)
                        canvas.draw()
                        for name, axis in zip(names, figure.axes[1::2]):
                            if scale == "loglog":
                                self.assert_log_frequencies(axis)
                                self.assertFalse(
                                    np.isfinite(axis.transData.transform([0, 7])).all()
                                )
                            else:
                                self.assert_linear_frequencies(axis)
                                self.assertLessEqual(axis.get_xlim()[0], 0)
                            self.assert_empty_annotation(
                                axis,
                                visible=scale != "linear"
                                and (
                                    name == "Zero"
                                    or (scale == "loglog" and name == "DC")
                                ),
                            )
                            if scale == "linear":
                                self.assert_linear_magnitudes(axis)
                                self.assertLessEqual(axis.get_ylim()[0], 0)
                            else:
                                self.assert_positive_magnitude_limits(axis)
                                self.assert_nonpositive_magnitudes_masked(axis)
                                if scale == "log" and name == "DC":
                                    self.assertTrue(
                                        np.isfinite(
                                            axis.transData.transform([0, 7])
                                        ).all()
                                    )
                            self.assertEqual(
                                axis.lines[0].get_marker(),
                                "None" if scale == "linear" else ".",
                            )
                            self.assertTrue(axis.collections)
                            self.assertEqual(
                                [fill.get_visible() for fill in axis.collections],
                                [scale == "linear"] * len(axis.collections),
                            )

    def test_loglog_bounds_use_global_frequencies_and_paired_visible_magnitudes(self):
        figure, canvas, _, _ = self.prepare(pd.DataFrame(np.ones((8, 3))))
        spectrum_axes = figure.axes[1::2]
        # Simulate differently reduced component spectra. Even frequencies paired
        # with invalid/zero magnitudes contribute to the global shared X extent.
        displayed = (
            (
                [0, -1, np.nan, np.inf, 0.125, 4, 100],
                [1e12, 1e-12, 1e15, 1e-15, 2, 3, 0],
            ),
            ([0, 0.25, 8, 200], [1e12, 5, 6, np.nan]),
            ([0, 1, 32], [1e12, 7, 9]),
        )
        for axis, (x, y) in zip(spectrum_axes, displayed):
            axis.lines[0].set_data(x, y)
        PlotArea._set_spectrum_scale(figure, "loglog")
        canvas.draw()
        for axis, (x, y) in zip(spectrum_axes, displayed):
            self.assert_log_frequencies(axis)
            self.assertLessEqual(axis.get_xlim()[0], 0.125)
            self.assertGreaterEqual(axis.get_xlim()[1], 200)
            self.assertEqual(axis.get_xlim(), spectrum_axes[0].get_xlim())
            self.assert_positive_magnitude_limits(axis)
            self.assertGreater(axis.get_ylim()[0], 1)
            self.assertLess(axis.get_ylim()[1], 10)
            self.assert_empty_annotation(axis, visible=False)
            np.testing.assert_array_equal(axis.lines[0].get_xdata(), x)
            np.testing.assert_array_equal(axis.lines[0].get_ydata(), y)

    def test_loglog_empty_or_invalid_display_data_gets_finite_fallbacks(self):
        figure, canvas, _, _ = self.prepare(pd.DataFrame(np.ones((2, 3))))
        cases = (
            ([], []),
            ([0, -1, np.nan, np.inf], [7, 1, 2, 3]),
            ([0, 1, 2, 3, 4], [7, 0, -1, np.nan, np.inf]),
        )
        for x, y in cases:
            with self.subTest(frequencies=x):
                for axis in figure.axes[1::2]:
                    axis.lines[0].set_data(x, y)
                PlotArea._set_spectrum_scale(figure, "loglog")
                canvas.draw()
                for axis in figure.axes[1::2]:
                    self.assert_log_frequencies(axis)
                    self.assert_positive_magnitude_limits(axis)
                    self.assert_empty_annotation(axis, visible=True)
                # A subsequent positive singleton must clear an existing notice.
                for axis in figure.axes[1::2]:
                    axis.lines[0].set_data([0, 2], [7, 1])
                PlotArea._set_spectrum_scale(figure, "loglog")
                canvas.draw()
                for axis in figure.axes[1::2]:
                    self.assert_log_frequencies(axis)
                    self.assertLess(axis.get_xlim()[0], 2)
                    self.assertGreater(axis.get_xlim()[1], 2)
                    self.assert_positive_magnitude_limits(axis)
                    self.assert_empty_annotation(axis, visible=False)

    def test_switch_reuses_reduced_line_data_without_recalculating_or_mutating_exports(
        self,
    ):
        samples = np.arange(12017, dtype=float)
        values = pd.Series(np.sin(samples * 0.17) + 2.0, name="Vertical")
        figure, canvas, spectrum, time_series = self.prepare(values)
        holder = SimpleNamespace(_fourier_data=spectrum, _time_series_data=time_series)
        spectrum_before = PlotArea.get_fourier_data(holder)
        time_before = PlotArea.get_time_series_data(holder)
        line = figure.axes[1].lines[0]
        self.assertLess(len(line.get_xdata()), len(spectrum))
        x_before, y_before = line.get_xdata().copy(), line.get_ydata().copy()
        with (
            patch.object(
                PlotArea, "_prepare_plot", side_effect=AssertionError("Rebuilt plot")
            ),
            patch.object(
                PlotArea,
                "_display_data",
                side_effect=AssertionError("Rebuilt display data"),
            ),
            patch(
                "ground_motion_analyzer.models.create_fourier_data",
                side_effect=AssertionError("Recomputed FFT"),
            ),
            patch("numpy.fft.rfft", side_effect=AssertionError("Recomputed FFT")),
        ):
            for scale in ("log", "linear", "loglog", "log", "loglog", "linear"):
                PlotArea._set_spectrum_scale(figure, scale)
                canvas.draw()
                self.assertIs(figure.axes[1].lines[0], line)
                np.testing.assert_array_equal(line.get_xdata(), x_before)
                np.testing.assert_array_equal(line.get_ydata(), y_before)
                pd.testing.assert_frame_equal(
                    PlotArea.get_fourier_data(holder), spectrum_before
                )
                pd.testing.assert_frame_equal(
                    PlotArea.get_time_series_data(holder), time_before
                )

    def test_callback_updates_existing_figure_toolbar_and_canvas_without_background_work(
        self,
    ):
        figure, canvas, spectrum, time_series = self.prepare([1.0, -2.0, 3.0, -4.0])
        for scale in ("loglog", "log", "linear"):
            with (
                self.subTest(scale=scale),
                patch.object(
                    PlotArea, "_set_spectrum_scale", wraps=PlotArea._set_spectrum_scale
                ) as set_scale,
                patch.object(canvas, "draw_idle", wraps=canvas.draw_idle) as draw_idle,
            ):
                holder = SimpleNamespace(
                    fig=figure,
                    canvas=canvas,
                    toolbar=Mock(),
                    spectrum_scale=Mock(),
                    _set_spectrum_scale=set_scale,
                    _task=Mock(),
                    _fourier_data=spectrum,
                    _time_series_data=time_series,
                )
                holder.spectrum_scale.get.return_value = scale
                holder._task.submit.side_effect = AssertionError(
                    "Queued background task"
                )
                toolbar_calls = Mock()
                toolbar_calls.attach_mock(holder.toolbar.update, "update")
                toolbar_calls.attach_mock(holder.toolbar.push_current, "push_current")
                with patch.object(
                    PlotArea,
                    "_prepare_plot",
                    side_effect=AssertionError("Rebuilt plot"),
                ):
                    PlotArea._change_spectrum_scale(holder)
                holder.spectrum_scale.get.assert_called_once_with()
                set_scale.assert_called_once_with(figure, scale)
                self.assertEqual(
                    toolbar_calls.mock_calls, [call.update(), call.push_current()]
                )
                draw_idle.assert_called_once_with()
                self.assertEqual(holder._task.mock_calls, [])
                self.assertIs(holder.fig, figure)
                self.assertIs(holder._fourier_data, spectrum)
                self.assertIs(holder._time_series_data, time_series)
                if scale == "loglog":
                    self.assert_log_frequencies(figure.axes[1])
                else:
                    self.assert_linear_frequencies(figure.axes[1])
                self.assertEqual(
                    figure.axes[1].get_yscale(),
                    "linear" if scale == "linear" else "log",
                )
                if scale != "linear":
                    self.assert_positive_magnitude_limits(figure.axes[1])
                    self.assert_nonpositive_magnitudes_masked(figure.axes[1])
                else:
                    self.assert_linear_magnitudes(figure.axes[1])

    def test_callback_without_figure_is_a_noop(self):
        with patch.object(PlotArea, "_set_spectrum_scale") as set_scale:
            holder = SimpleNamespace(
                fig=None,
                canvas=Mock(),
                toolbar=Mock(),
                spectrum_scale=Mock(),
                _set_spectrum_scale=set_scale,
                _task=Mock(),
            )
            PlotArea._change_spectrum_scale(holder)
            set_scale.assert_not_called()
            self.assertEqual(holder.canvas.mock_calls, [])
            self.assertEqual(holder.toolbar.mock_calls, [])
            self.assertEqual(holder._task.mock_calls, [])


if __name__ == "__main__":
    unittest.main()
