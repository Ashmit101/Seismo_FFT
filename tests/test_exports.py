import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from ground_motion_analyzer.views import MainView


class ExportCommandTests(unittest.TestCase):
    def make_view(self, *, fourier=None, time_series=None, source="motion.csv"):
        return SimpleNamespace(
            plot_area=SimpleNamespace(
                get_fourier_data=Mock(return_value=fourier),
                get_time_series_data=Mock(return_value=time_series),
            ),
            control_panel=SimpleNamespace(
                data=time_series,
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


if __name__ == "__main__":
    unittest.main()
