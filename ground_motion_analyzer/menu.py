import tkinter as tk

from ground_motion_analyzer.constants import Events


class MainMenu(tk.Menu):
    """Main menu of the application."""

    def _event(self, event: Events):

        def callback(*_):
            root = self.master.winfo_toplevel()
            root.event_generate(event)

        return callback

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # File menu
        file_menu = tk.Menu(self, tearoff=False)
        file_menu.add_command(
            label="Export FFT...",
            command=self._event(Events.EXPORT_FFT_DATA),
        )
        file_menu.add_command(
            label="Export time series...",
            command=self._event(Events.EXPORT_TIME_SERIES_DATA),
        )

        self.add_cascade(label="File", menu=file_menu)
