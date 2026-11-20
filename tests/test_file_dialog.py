import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ground_motion_analyzer.widgets import FileSelector


class FileDialogTests(unittest.TestCase):
    def setUp(self):
        self.previous_directory = FileSelector._last_directory
        FileSelector._last_directory = None
        self.selector = FileSelector.__new__(FileSelector)
        self.selector.winfo_exists = Mock(return_value=True)
        self.selector.winfo_viewable = Mock(return_value=True)
        self.selector.selected_file_name = Mock()
        self.selector.event_generate = Mock()
        self.selector.data_file = "previous.csv"
        self.selector.data_unit = "g"

    def tearDown(self):
        FileSelector._last_directory = self.previous_directory

    def test_initial_directory_and_filters_and_directory_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            selected = str(Path(directory) / "signal.csv")
            with (
                patch(
                    "ground_motion_analyzer.widgets.filedialog.askopenfilename",
                    return_value=selected,
                ) as dialog,
                patch("ground_motion_analyzer.views.DataTypeDialog") as units,
            ):
                units.return_value.result = "m/s²"
                self.selector._load_file()
                options = dialog.call_args.kwargs
                self.assertTrue(Path(options["initialdir"]).is_dir())
                self.assertIs(options["parent"], self.selector)
                self.assertIn("*.mseed", options["filetypes"][0][1])
                self.assertIn("*.sac", options["filetypes"][0][1])
                self.assertIn("*.SAC", options["filetypes"][0][1])
                self.assertIn(
                    ("SAC", "*.sac *.SAC *.sacxy *.SACXY"), options["filetypes"]
                )
                self.assertEqual(self.selector.data_file, selected)
                self.selector.event_generate.assert_called_once()
                self.assertEqual(FileSelector._initial_directory(), Path(directory))

    def test_cancel_file_or_units_preserves_selection(self):
        for filename in ("", "/tmp/new_signal.csv"):
            with (
                self.subTest(filename=filename),
                patch(
                    "ground_motion_analyzer.widgets.filedialog.askopenfilename",
                    return_value=filename,
                ),
                patch("ground_motion_analyzer.views.DataTypeDialog") as units,
            ):
                units.return_value.result = None
                self.selector._load_file()
                self.assertEqual(self.selector.data_file, "previous.csv")
                self.assertEqual(self.selector.data_unit, "g")
                self.selector.event_generate.assert_not_called()

    def test_dialog_is_deferred_before_window_is_visible(self):
        self.selector.winfo_viewable.return_value = False
        root = Mock()
        self.selector.winfo_toplevel = Mock(return_value=root)
        with patch(
            "ground_motion_analyzer.widgets.filedialog.askopenfilename"
        ) as dialog:
            self.selector._load_file()
            root.after.assert_called_once_with(100, self.selector._open_dialog)
            dialog.assert_not_called()
            self.selector.winfo_exists.return_value = False
            self.selector._open_dialog()
            dialog.assert_not_called()

    def test_missing_last_directory_falls_back_to_documents_or_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            FileSelector._last_directory = home / "missing"
            with patch("ground_motion_analyzer.widgets.Path.home", return_value=home):
                self.assertEqual(FileSelector._initial_directory(), Path.cwd())
                (home / "Documents").mkdir()
                self.assertEqual(FileSelector._initial_directory(), home / "Documents")


if __name__ == "__main__":
    unittest.main()
