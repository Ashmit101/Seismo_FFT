import unittest

import numpy as np

from ground_motion_analyzer.models import create_fourier_data, preprocess_signal


class PreprocessSignalTests(unittest.TestCase):
    def test_demean_removes_each_component_mean(self):
        values = np.array([[1.0, 10.0], [2.0, 20.0], [6.0, 30.0]])

        result = preprocess_signal(values, demean=True, detrend=False)

        np.testing.assert_allclose(result.mean(axis=0), [0.0, 0.0], atol=1e-12)
        np.testing.assert_array_equal(values, [[1.0, 10.0], [2.0, 20.0], [6.0, 30.0]])

    def test_detrend_removes_linear_trend(self):
        samples = np.arange(8, dtype=float)
        values = np.column_stack((2.0 * samples + 3.0, -samples + 5.0))

        result = preprocess_signal(values, demean=False, detrend=True)

        np.testing.assert_allclose(result, 0.0, atol=1e-12)

    def test_disabled_options_leave_values_unchanged(self):
        values = np.array([1.0, 3.0, 2.0])

        result = preprocess_signal(values, demean=False, detrend=False)

        np.testing.assert_array_equal(result, values)
        self.assertIsNot(result, values)


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

    def test_full_resolution_matches_numpy_for_odd_three_component_signal(self):
        values = np.random.default_rng(42).normal(size=(1001, 3))
        result = create_fourier_data(
            values, time_increment=0.01, component_names=["X", "Y", "Z"]
        )
        np.testing.assert_allclose(
            result.iloc[:, 1:],
            np.abs(np.fft.rfft(values, axis=0)) / len(values),
            atol=1e-14,
        )
        self.assertEqual(len(result), 501)

    def test_preview_reduces_nyquist_and_suppresses_aliasing(self):
        time = np.arange(10_000) * 0.001
        values = np.sin(2 * np.pi * 10 * time) + np.sin(2 * np.pi * 190 * time)
        result = create_fourier_data(
            values, time_increment=0.001, component_names=["X"], max_samples=1000
        )
        frequencies = result.iloc[:, 0].to_numpy()
        magnitude = result.iloc[:, 1].to_numpy()
        self.assertEqual(len(result), 501)
        self.assertAlmostEqual(frequencies[-1], 50.0)
        self.assertAlmostEqual(frequencies[magnitude.argmax()], 10.0)
        self.assertAlmostEqual(magnitude.max(), 0.5, delta=0.01)

    def test_preview_limit_requires_integer_at_least_two(self):
        for limit in (True, 1, 2.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                create_fourier_data(
                    np.ones(10),
                    time_increment=0.01,
                    component_names=["X"],
                    max_samples=limit,
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
