import unittest

import numpy as np

from ground_motion_analyzer.models import create_fourier_data


class CreateFourierDataTests(unittest.TestCase):
    def test_exports_frequency_and_magnitude_for_each_component(self):
        time_increment = 0.125
        time = np.arange(8) * time_increment
        values = np.column_stack(
            (
                np.sin(2 * np.pi * time),
                np.cos(2 * np.pi * 2 * time),
            )
        )

        result = create_fourier_data(
            values,
            time_increment=time_increment,
            component_names=["North", "Vertical"],
        )

        self.assertEqual(
            result.columns.tolist(),
            [
                "Frequency (Hz)",
                "North FFT Magnitude",
                "Vertical FFT Magnitude",
            ],
        )
        np.testing.assert_allclose(
            result["Frequency (Hz)"],
            np.fft.rfftfreq(len(values), d=time_increment),
        )
        np.testing.assert_allclose(
            result.iloc[:, 1:].to_numpy(),
            np.abs(np.fft.rfft(values, axis=0)) / len(values),
        )

    def test_requires_one_name_per_component(self):
        with self.assertRaisesRegex(ValueError, "must have a name"):
            create_fourier_data(
                np.ones((4, 2)),
                time_increment=0.1,
                component_names=["Only one"],
            )


if __name__ == "__main__":
    unittest.main()
