import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from ground_motion_analyzer.views import MainView


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


if __name__ == "__main__":
    unittest.main()
