import tempfile
import unittest
from pathlib import Path

import numpy as np
from obspy.io.sac import SACTrace

from ground_motion_analyzer.constants import ColumnMode
from ground_motion_analyzer.data_loading import detect_column_mode, read_signal_data
from ground_motion_analyzer.views import ControlPanel
from ground_motion_analyzer.widgets import PlotArea


class SacLoadingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.values = np.sin(np.arange(1000) * 2 * np.pi / 100).astype(np.float32)

    def make_trace(self, **kwargs):
        headers = {
            "delta": 0.01,
            "b": -2.5,
            "kstnm": "TEST",
            "knetwk": "XX",
            "kcmpnm": "BHZ",
            "nzyear": 2026,
            "nzjday": 100,
        }
        headers.update(kwargs)
        return SACTrace(data=self.values.copy(), **headers)

    def test_binary_byte_orders_and_case_insensitive_extensions(self):
        for byteorder, extension in (
            ("little", ".sac"),
            ("big", ".SAC"),
            ("little", ".Sac"),
        ):
            with self.subTest(byteorder=byteorder, extension=extension):
                path = self.directory / f"signal{extension}"
                sac = self.make_trace()
                sac.write(str(path), byteorder=byteorder)
                data = read_signal_data(path)
                self.assertEqual(list(data.columns), ["time", "amplitude"])
                self.assertEqual(detect_column_mode(data), ColumnMode.DOUBLE)
                np.testing.assert_array_equal(data["amplitude"], self.values)
                self.assertTrue(data["amplitude"].dtype.isnative)
                np.testing.assert_allclose(
                    data["time"],
                    sac.b + np.arange(len(self.values)) * sac.delta,
                )
                self.assertEqual(data.attrs["metadata"]["station"], "TEST")
                self.assertEqual(data.attrs["metadata"]["channel"], "BHZ")
                self.assertAlmostEqual(
                    data.attrs["metadata"]["sampling_rate"], 100, places=5
                )

    def test_ascii_sac_and_sacxy_extensions(self):
        for extension in (".sac", ".sacxy", ".SACXY"):
            with self.subTest(extension=extension):
                path = self.directory / f"ascii{extension}"
                sac = self.make_trace()
                sac.write(str(path), ascii=True)
                data = read_signal_data(str(path))
                np.testing.assert_allclose(data["amplitude"], self.values, atol=1e-7)
                np.testing.assert_allclose(np.diff(data["time"]), sac.delta)

    def test_invalid_or_unsupported_sac_headers_are_rejected(self):
        for headers, message in (
            ({"iftype": "irlim"}, "evenly sampled SAC time-series"),
            ({"leven": False}, "evenly sampled SAC time-series"),
            ({"delta": 0}, "sample interval"),
            ({"delta": float("nan")}, "sample interval"),
            ({"b": float("nan")}, "begin time"),
        ):
            with self.subTest(headers=headers):
                path = self.directory / "invalid.sac"
                self.make_trace(**headers).write(str(path))
                with self.assertRaisesRegex(ValueError, message):
                    read_signal_data(path)

    def test_short_and_nonfinite_signals_are_rejected(self):
        for values, message in (
            (np.array([1.0], dtype=np.float32), "At least two"),
            (np.array([1.0, np.nan, 2.0], dtype=np.float32), "must be finite"),
        ):
            with self.subTest(message=message):
                path = self.directory / "invalid_samples.sac"
                sac = self.make_trace()
                sac.data = values
                sac.write(str(path))
                with self.assertRaisesRegex(ValueError, message):
                    read_signal_data(path)

    def test_corrupt_sac_reports_read_error(self):
        path = self.directory / "corrupt.sac"
        path.write_bytes(b"This is not a SAC file.")
        with self.assertRaisesRegex(ValueError, "valid binary or ASCII SAC"):
            read_signal_data(path)

    def test_loaded_sac_uses_header_timing_for_plot_and_full_fft(self):
        path = self.directory / "waveform.sac"
        sac = self.make_trace(delta=0.0001)
        sac.write(str(path), byteorder="big")
        data, mode = ControlPanel._read_file(str(path))
        self.assertEqual(mode, ColumnMode.DOUBLE)
        figure, spectrum = PlotArea._prepare_plot(
            data["amplitude"],
            time_data=data["time"],
            demean=False,
            data_unit="m/s²",
        )
        self.addCleanup(figure.clear)
        self.assertEqual(len(figure.axes), 2)
        np.testing.assert_allclose(figure.axes[0].lines[0].get_xdata(), data["time"])
        np.testing.assert_allclose(
            spectrum.iloc[:, 0],
            np.fft.rfftfreq(len(self.values), sac.delta),
        )
        np.testing.assert_allclose(
            spectrum.iloc[:, 1],
            np.abs(np.fft.rfft(self.values.astype(float))) / len(self.values),
            atol=1e-12,
        )
        self.assertEqual(len(spectrum), len(self.values) // 2 + 1)


if __name__ == "__main__":
    unittest.main()
