import os
import tkinter as tk

from ground_motion_analyzer.constants import Events

from .menu import MainMenu
from .runtime import configure_matplotlib_cache


class Application(tk.Tk):
    """Root application"""

    def __init__(self, *args, **kwargs):
        configure_matplotlib_cache()
        super().__init__(*args, **kwargs)

        self._configure_window()
        self._configure_scaling()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        from .views import MainView

        self.main_view = MainView(self)
        self.main_view.grid(row=0, ipadx=10, ipady=10, sticky="nsew")

        self._bind_events()

    def _configure_window(self):
        self.title("SEISNEP")
        self.geometry("1280x800")

        menu = MainMenu(self)
        self.config(menu=menu)

    def _configure_scaling(self):
        try:
            dpi = self.winfo_fpixels("1i")
            scale = dpi / 96.0

            env_scale = os.environ.get("GDK_SCALE")
            if env_scale:
                try:
                    scale = max(scale, float(env_scale))
                except ValueError:
                    pass

            self.tk.call("tk", "scaling", max(scale, 1.25))
        except tk.TclError:
            self.tk.call("tk", "scaling", 1.25)

    def _bind_events(self):
        event_callback_map = {
            Events.EXPORT_FFT_DATA: self.main_view.download_fourier_data,
            Events.EXPORT_TIME_SERIES_DATA: self.main_view.download_time_series_data,
        }

        for event, callback in event_callback_map.items():
            self.bind(event, callback)
