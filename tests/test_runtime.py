import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ground_motion_analyzer.runtime import configure_matplotlib_cache


class MatplotlibCacheTests(unittest.TestCase):
    def test_source_run_preserves_explicit_matplotlib_configuration(self):
        with (
            patch.object(sys, "frozen", False, create=True),
            patch.dict(os.environ, {"MPLCONFIGDIR": "/chosen/cache"}, clear=True),
            patch("ground_motion_analyzer.runtime.Path.mkdir") as mkdir,
        ):
            self.assertIsNone(configure_matplotlib_cache())
            self.assertEqual(os.environ["MPLCONFIGDIR"], "/chosen/cache")
            mkdir.assert_not_called()

    def test_frozen_cache_location_is_stable_and_platform_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for platform, expected in (
                ("darwin", home / "Library" / "Caches"),
                ("win32", home / "AppData" / "Local"),
                ("linux", home / ".cache"),
            ):
                with (
                    self.subTest(platform=platform),
                    patch.object(sys, "frozen", True, create=True),
                    patch.object(sys, "platform", platform),
                    patch(
                        "ground_motion_analyzer.runtime.Path.home", return_value=home
                    ),
                    patch.dict(
                        os.environ, {"MPLCONFIGDIR": "/temporary/first"}, clear=True
                    ),
                ):
                    result = configure_matplotlib_cache()
                    self.assertEqual(result, expected / "Seismo_FFT" / "matplotlib")
                    self.assertTrue(result.is_dir())
                    # Simulate PyInstaller choosing a different directory next launch.
                    os.environ["MPLCONFIGDIR"] = "/temporary/second"
                    self.assertEqual(configure_matplotlib_cache(), result)
                    self.assertEqual(os.environ["MPLCONFIGDIR"], str(result))

    def test_frozen_cache_respects_platform_cache_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            for platform, variable in (
                ("linux", "XDG_CACHE_HOME"),
                ("win32", "LOCALAPPDATA"),
            ):
                with (
                    self.subTest(platform=platform),
                    patch.object(sys, "frozen", True, create=True),
                    patch.object(sys, "platform", platform),
                    patch.dict(os.environ, {variable: directory}, clear=True),
                ):
                    self.assertEqual(
                        configure_matplotlib_cache(),
                        Path(directory) / "Seismo_FFT" / "matplotlib",
                    )

    def test_frozen_app_specific_override(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "custom"
            with (
                patch.object(sys, "frozen", True, create=True),
                patch.dict(
                    os.environ, {"SEISMO_FFT_MPLCONFIGDIR": str(target)}, clear=True
                ),
            ):
                self.assertEqual(configure_matplotlib_cache(), target.resolve())
                self.assertEqual(os.environ["MPLCONFIGDIR"], str(target.resolve()))

    def test_unwritable_cache_preserves_pyinstaller_fallback(self):
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.dict(os.environ, {"MPLCONFIGDIR": "/temporary/fallback"}, clear=True),
            patch(
                "ground_motion_analyzer.runtime.Path.mkdir", side_effect=PermissionError
            ),
            self.assertLogs("ground_motion_analyzer.runtime", level="WARNING") as logs,
        ):
            self.assertIsNone(configure_matplotlib_cache())
            self.assertEqual(os.environ["MPLCONFIGDIR"], "/temporary/fallback")
            self.assertIn("keeping temporary cache", logs.output[0])


if __name__ == "__main__":
    unittest.main()
