import tkinter as tk
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ground_motion_analyzer.constants import ColumnMode, Events
from ground_motion_analyzer.views import ControlPanel, DataTypeDialog, MainView


class MainViewTests(unittest.TestCase):
    def test_invalid_control_edit_invalidates_pending_plot_before_reading_values(self):
        for error in (tk.TclError("empty numeric value"), ValueError("invalid value")):
            with self.subTest(error=error):
                calls = []
                view = SimpleNamespace(
                    header=SimpleNamespace(set_download_enabled=Mock()),
                    plot_area=SimpleNamespace(
                        cancel_pending=Mock(
                            side_effect=lambda calls=calls: calls.append("cancel")
                        )
                    ),
                    control_panel=SimpleNamespace(get=Mock()),
                )

                def get(calls=calls, error=error):
                    calls.append("get")
                    raise error

                view.control_panel.get.side_effect = get
                MainView._plot(view)
                self.assertEqual(calls, ["cancel", "get"])
                view.header.set_download_enabled.assert_called_once_with(False)


class SensitivityControlTests(unittest.TestCase):
    def setUp(self):
        # Use real Tcl variables/traces without requiring a graphical desktop.
        self.interpreter = tk.Tcl()
        self.sensitivity = tk.DoubleVar(master=self.interpreter, value=0.0)
        self.panel = ControlPanel.__new__(ControlPanel)
        self.panel.event_generate = Mock()
        with ExitStack() as stack:
            stack.enter_context(patch("ground_motion_analyzer.views.tk.Frame.__init__"))
            variable = stack.enter_context(
                patch(
                    "ground_motion_analyzer.views.tk.DoubleVar",
                    return_value=self.sensitivity,
                )
            )
            for name in (
                "BackgroundTask",
                "ttk.Label",
                "ttk.LabelFrame",
                "ttk.Spinbox",
                "w.FileSelector",
                "w.ColumnFormatDisplay",
                "w.SingleColumnParams",
                "w.DoubleColumnParams",
                "w.Demean",
                "w.Filtering",
                "w.Statistics",
            ):
                stack.enter_context(patch(f"ground_motion_analyzer.views.{name}"))
            ControlPanel.__init__(self.panel, None)
            variable.assert_called_once_with(master=self.panel, value=0.0)

        self.panel.file_selector.get.return_value = {
            "file": "signal.csv",
            "data_unit": "g",
        }
        self.panel.demean_detrend_options.get.return_value = {
            "demean": True,
            "detrend": False,
        }

    def test_default_and_edited_sensitivity_are_available_in_every_mode(self):
        self.assertEqual(self.panel.get()["sensitivity"], 0.0)
        for mode in (ColumnMode.SINGLE, ColumnMode.DOUBLE, ColumnMode.THREE_COMPONENT):
            with self.subTest(mode=mode):
                self.panel.column_format.get.return_value = mode
                self.panel.event_generate.reset_mock()
                self.sensitivity.set(2.5)
                self.assertEqual(self.panel.get()["sensitivity"], 2.5)
                self.panel.event_generate.assert_called_once_with(
                    Events.VARIABLES_UPDATED
                )

    def test_loading_a_file_keeps_panel_sensitivity(self):
        self.sensitivity.set(4.0)
        self.panel._handle_new_file()
        self.panel._file_task.submit.assert_called_once_with(
            self.panel._read_file, "signal.csv"
        )
        self.assertEqual(self.panel.get()["sensitivity"], 4.0)

    def test_invalid_edit_is_rejected_until_a_number_is_entered(self):
        self.interpreter.setvar(str(self.sensitivity), "")
        with self.assertRaises(tk.TclError):
            self.panel.get()
        self.sensitivity.set(0.4)
        self.assertEqual(self.panel.get()["sensitivity"], 0.4)

    def test_units_dialog_returns_only_units(self):
        dialog = SimpleNamespace(unit=Mock(get=Mock(return_value="m/s²")))
        DataTypeDialog.apply(dialog)
        self.assertEqual(dialog.result, "m/s²")


if __name__ == "__main__":
    unittest.main()
