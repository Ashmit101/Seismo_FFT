import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from ground_motion_analyzer.views import MainView
from ground_motion_analyzer.widgets import PlotArea


class ExportCommandTests(unittest.TestCase):
    def make_view(self, *, fourier=None, time_series=None, source="motion.csv"):
        return SimpleNamespace(
            plot_area=SimpleNamespace(
                get_fourier_data=Mock(return_value=fourier),
                get_time_series_data=Mock(return_value=time_series),
            ),
            control_panel=SimpleNamespace(
                # Loaded raw data must never be used for processed exports.
                data=pd.DataFrame({"raw": [99.0]}),
                file_selector=SimpleNamespace(get=Mock(return_value={"file": source})),
            ),
        )

    def test_fft_export_writes_csv_with_source_based_name(self):
        data = pd.DataFrame({"Frequency (Hz)": [0.0], "X FFT Magnitude": [1.0]})
        view = self.make_view(fourier=data)
        with (
            patch(
                "ground_motion_analyzer.views.filedialog.asksaveasfilename",
                return_value="/tmp/result.csv",
            ) as dialog,
            patch.object(data, "to_csv") as to_csv,
            patch("ground_motion_analyzer.views.messagebox.showinfo"),
        ):
            MainView.download_fourier_data(view)

        self.assertEqual(
            dialog.call_args.kwargs["initialfile"], "motion_fourier_transform.csv"
        )
        to_csv.assert_called_once_with("/tmp/result.csv", index=False, sep=",")

    def test_time_series_export_writes_tab_delimited_data(self):
        data = pd.DataFrame({"Time (s)": [0.0], "X": [1.0]})
        view = self.make_view(time_series=data, source=Path("record.sac"))
        with (
            patch(
                "ground_motion_analyzer.views.filedialog.asksaveasfilename",
                return_value="/tmp/result.tsv",
            ) as dialog,
            patch.object(data, "to_csv") as to_csv,
            patch("ground_motion_analyzer.views.messagebox.showinfo"),
        ):
            MainView.download_time_series_data(view)

        self.assertEqual(
            dialog.call_args.kwargs["initialfile"], "record_time_series.csv"
        )
        to_csv.assert_called_once_with("/tmp/result.tsv", index=False, sep="\t")
        view.plot_area.get_time_series_data.assert_called_once_with()

    def test_missing_data_warns_without_opening_dialog(self):
        view = self.make_view()
        with (
            patch(
                "ground_motion_analyzer.views.filedialog.asksaveasfilename"
            ) as dialog,
            patch("ground_motion_analyzer.views.messagebox.showwarning") as warning,
        ):
            MainView.download_time_series_data(view)

        dialog.assert_not_called()
        warning.assert_called_once()


class ProcessedExportStateTests(unittest.TestCase):
    def make_area(self):
        return SimpleNamespace(
            _fourier_data=pd.DataFrame({"Frequency (Hz)": [0.0]}),
            _time_series_data=pd.DataFrame({"Time (s)": [0.0], "X": [1.0]}),
            _task=Mock(),
            _prepare_plot=Mock(),
            _on_ready=Mock(),
            loading=Mock(),
            canvas=None,
        )

    def assert_exports_unavailable(self, area):
        self.assertIsNone(PlotArea.get_fourier_data(area))
        self.assertIsNone(PlotArea.get_time_series_data(area))

    def test_cancel_discards_cached_exports(self):
        area = self.make_area()
        PlotArea.cancel_pending(area)
        area._task.invalidate.assert_called_once_with()
        self.assertIsNone(area._on_ready)
        self.assert_exports_unavailable(area)

    def test_new_plot_discards_cached_exports_before_submitting(self):
        area = self.make_area()
        area._task.submit.side_effect = lambda *args, **kwargs: (
            self.assert_exports_unavailable(area)
        )
        PlotArea.plot(area, [1.0, 2.0], sensitivity=2.0)
        area._task.submit.assert_called_once_with(
            area._prepare_plot, [1.0, 2.0], sensitivity=2.0
        )
        self.assert_exports_unavailable(area)

    def test_failed_plot_discards_cached_exports(self):
        area = self.make_area()
        with patch("ground_motion_analyzer.widgets.messagebox.showerror"):
            PlotArea._plot_failed(area, ValueError("invalid signal"))
        self.assert_exports_unavailable(area)

    def test_display_publishes_both_exports_before_ready_callback(self):
        area = self.make_area()
        figure = Mock(axes=[Mock(), Mock()])
        spectrum = pd.DataFrame({"Frequency (Hz)": [0.0], "X FFT Magnitude": [2.0]})
        processed = pd.DataFrame({"Time (s)": [0.0, 0.1], "X": [-2.0, 2.0]})

        def on_ready():
            pd.testing.assert_frame_equal(PlotArea.get_fourier_data(area), spectrum)
            pd.testing.assert_frame_equal(
                PlotArea.get_time_series_data(area), processed
            )

        area._on_ready.side_effect = on_ready
        with (
            patch("matplotlib.backends.backend_tkagg.FigureCanvasTkAgg"),
            patch("matplotlib.backends.backend_tkagg.NavigationToolbar2Tk"),
            patch("ground_motion_analyzer.widgets.tk.Frame"),
        ):
            PlotArea._show_plot(area, (figure, spectrum, processed))
        area._on_ready.assert_called_once_with()
        exported = PlotArea.get_time_series_data(area)
        exported.iloc[0, 1] = 999.0
        self.assertEqual(area._time_series_data.iloc[0, 1], -2.0)


if __name__ == "__main__":
    unittest.main()
