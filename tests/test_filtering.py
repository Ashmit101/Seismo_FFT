import unittest

import numpy as np
import pandas as pd

from ground_motion_analyzer.filtering import filter_signal


class FilterSignalTests(unittest.TestCase):
    def setUp(self):
        self.sampling_rate = 200.0
        self.time = np.arange(0.0, 2.0, 1.0 / self.sampling_rate)
        self.low_frequency = np.sin(2 * np.pi * 5 * self.time)
        self.high_frequency = 0.5 * np.sin(2 * np.pi * 60 * self.time)
        self.mixed_signal = self.low_frequency + self.high_frequency

    def test_disabled_filter_returns_copy_and_preserves_series_metadata(self):
        source = pd.Series(self.mixed_signal, name="acceleration")

        result = filter_signal(
            source,
            {"is_filter_on": False},
            sampling_rate=self.sampling_rate,
        )

        self.assertIsInstance(result, pd.Series)
        self.assertEqual(result.name, source.name)
        self.assertTrue(result.index.equals(source.index))
        np.testing.assert_array_equal(result.to_numpy(), source.to_numpy())
        self.assertIsNot(result, source)

    def test_lowpass_rejects_high_frequency_component(self):
        result = filter_signal(
            self.mixed_signal,
            {
                "is_filter_on": True,
                "filter_type": "lowpass",
                "cutoff_frequency": 15.0,
                "order": 4,
            },
            sampling_rate=self.sampling_rate,
        )

        middle = slice(50, -50)
        error = result[middle] - self.low_frequency[middle]
        self.assertLess(np.sqrt(np.mean(error**2)), 0.02)

    def test_band_cutoffs_must_be_ordered_and_below_nyquist(self):
        with self.assertRaisesRegex(ValueError, "Nyquist"):
            filter_signal(
                self.mixed_signal,
                {
                    "is_filter_on": True,
                    "filter_type": "bandpass",
                    "cutoff_frequency": [30.0, 120.0],
                    "order": 4,
                },
                sampling_rate=self.sampling_rate,
            )


if __name__ == "__main__":
    unittest.main()
