import tkinter as tk
from tkinter import ttk

from .views import MainView


class Application(tk.Tk):
    """Root application"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.main_view = MainView(self)
        self.main_view.grid(row=0, padx=10,
                            sticky=(tk.W + tk.E)
                            )
        
        
    
