import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import rfft, rfftfreq


def plot_signal(time_data, motion_data, *, x_label="Time", y_label):
    _fig, ax = plt.subplots()
    ax.plot(time_data, motion_data, linewidth=1.0)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    plt.show()


def plot_fft(motion_data, time_increment, *, y_label):
    motion_spectrum = rfft(motion_data)
    frequencies = rfftfreq(len(motion_data), d=time_increment)
    amplitude = 2 / len(motion_data) * np.abs(motion_spectrum)
    _fig, ax = plt.subplots()
    ax.plot(frequencies, amplitude, linewidth=1.0)

    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel(y_label)
    plt.show()
