import os
import tkinter as tk

from .views import MainView


class Application(tk.Tk):
    """Root application"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._configure_window()
        self._configure_scaling()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_view = MainView(self)
        self.main_view.grid(row=0, ipadx=10, ipady=10, sticky="nsew")


    def _configure_window(self):
        self.title("Ground Motion Analyzer")
        self.geometry("1280x800")

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
        except Exception:
            self.tk.call("tk", "scaling", 1.25)
