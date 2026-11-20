import io
import unittest

import pandas as pd

from ground_motion_analyzer.constants import ColumnMode
from ground_motion_analyzer.data_loading import detect_column_mode, read_signal_data


class DataLoadingTests(unittest.TestCase):
    def test_reads_delimiter_free_single_column(self):
        data = read_signal_data(io.StringIO("amplitude\n1\n2\n3\n"))

        self.assertEqual(data.shape, (3, 1))
        self.assertEqual(detect_column_mode(data), ColumnMode.SINGLE)

    def test_detects_time_and_one_component(self):
        data = read_signal_data(io.StringIO("time,amplitude\n0,1\n0.01,2\n"))

        self.assertEqual(detect_column_mode(data), ColumnMode.DOUBLE)

    def test_detects_whitespace_delimited_three_components(self):
        data = read_signal_data(io.StringIO("Time N-S E-W V\n0 1 2 3\n0.01 4 5 6\n"))

        self.assertEqual(data.shape, (2, 4))
        self.assertEqual(detect_column_mode(data), ColumnMode.THREE_COMPONENT)

    def test_skips_and_preserves_metadata_preamble(self):
        source = io.StringIO(
            "Station_code    CDG\n"
            "Sampling_rate   100.000000\n"
            "Start_date      04.25.2015\n"
            "Start_time      06:11:30.14\n"
            "Time:sec   N,g    E,g    V,g\n"
            "0\t-1.2e-5\t1.0e-5\t-1.1e-5\n"
            "0.01\t-1.1e-5\t-2.0e-6\t-3.0e-6\n"
        )

        data = read_signal_data(source)

        self.assertEqual(list(data.columns), ["Time:sec", "N,g", "E,g", "V,g"])
        self.assertEqual(data.shape, (2, 4))
        self.assertEqual(data.attrs["metadata"]["Station_code"], "CDG")
        self.assertEqual(data.attrs["metadata"]["Sampling_rate"], 100.0)
        self.assertEqual(data.attrs["header_row"], 5)

    def test_reads_quoted_acceleration_csv_with_extra_column(self):
        source = io.StringIO(
            '"Time (s)","Acceleration x (m/s^2)","Acceleration y (m/s^2)",'
            '"Acceleration z (m/s^2)","Absolute acceleration (m/s^2)"\n'
            "3.867218000E-3,-9.337386489E-2,-5.746084079E-2,9.586383820E0,9.587010752E0\n"
            "5.867764000E-3,-9.097966552E-2,-5.985504389E-2,9.586383820E0,9.587002381E0\n"
        )

        data = read_signal_data(source)

        self.assertEqual(data.shape, (2, 4))
        self.assertEqual(
            list(data.columns),
            [
                "Time (s)",
                "Acceleration x (m/s^2)",
                "Acceleration y (m/s^2)",
                "Acceleration z (m/s^2)",
            ],
        )
        self.assertEqual(data.attrs["header_row"], 1)
        self.assertEqual(data.attrs["metadata"], {})
        self.assertEqual(detect_column_mode(data), ColumnMode.THREE_COMPONENT)
        self.assertAlmostEqual(data.iloc[0, 0], 0.003867218)
        self.assertAlmostEqual(data.iloc[0, 3], 9.586383820)
        self.assertEqual(source.tell(), 0)

    def test_ignores_extra_columns_in_headerless_files(self):
        for separator in (",", ";", "\t", " "):
            for column_count in (5, 6):
                with self.subTest(separator=separator, column_count=column_count):
                    source = io.StringIO(
                        separator.join(str(value) for value in range(column_count))
                        + "\n"
                        + separator.join(
                            str(value + 10) for value in range(column_count)
                        )
                        + "\n"
                    )

                    data = read_signal_data(source)

                    self.assertEqual(data.shape, (2, 4))
                    self.assertEqual(
                        list(data.columns),
                        [f"Component {index + 1}" for index in range(4)],
                    )
                    self.assertEqual(
                        data.values.tolist(), [[0, 1, 2, 3], [10, 11, 12, 13]]
                    )
                    self.assertIsNone(data.attrs["header_row"])
                    self.assertEqual(
                        detect_column_mode(data), ColumnMode.THREE_COMPONENT
                    )

    def test_preserves_metadata_with_extra_columns(self):
        source = io.StringIO(
            "Station_code    CDG\ntime,x,y,z,absolute\n0,1,2,3,4\n0.01,5,6,7,8\n"
        )

        data = read_signal_data(source)

        self.assertEqual(list(data.columns), ["time", "x", "y", "z"])
        self.assertEqual(data.values.tolist(), [[0, 1, 2, 3], [0.01, 5, 6, 7]])
        self.assertEqual(data.attrs["metadata"], {"Station_code": "CDG"})
        self.assertEqual(data.attrs["header_row"], 2)

    def test_rejects_unsupported_column_count(self):
        data = pd.DataFrame(columns=["one", "two", "three"])

        with self.assertRaisesRegex(ValueError, "1 column"):
            detect_column_mode(data)


if __name__ == "__main__":
    unittest.main()
