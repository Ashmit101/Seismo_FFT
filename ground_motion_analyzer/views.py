import tkinter as tk
from tkinter import ttk

from . import widgets as w


class MainView(tk.Frame):
    """Main view of the application"""
    
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        w.Header(self,
                 title="Ground Motion Analyzer",
                 developer="Ashmit Rajaure"
                 ).grid(row=0, column=0)
        
        w.ControlPanel(self).grid(row=1, column=0)
