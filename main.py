import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
import scipy.signal as signal

def load_data(file_path: str):
    data = pd.read_csv(file_path, delimiter='\t')
    return data

def apply_fft(time_series, sampling_rate):
    window = signal.windows.hann(len(time_series))
    windowed_signal = time_series * window

    n = len(time_series)
    fft_result = fft(windowed_signal)

    fft_result = fft_result[:n//2]
    magnitude = np.abs(fft_result)
    magnitude = magnitude / n

    freq = fftfreq(n, 1/sampling_rate)[:n//2]

    return freq, magnitude


def separate_directions(data, sampling_rate, x_orientation, z_orientation):
    time = data['Time (s)'].values
    y_signal = data['V'].values
    x_signal = data['E-W'].values
    z_signal = data['N-S'].values

    freq_y, fft_y = apply_fft(y_signal, sampling_rate)
    freq_x, fft_x = apply_fft(x_signal, sampling_rate)
    freq_z, fft_z = apply_fft(z_signal, sampling_rate)
    
    directions = {
        'vertical': {'signal': y_signal, 'fft': fft_y, 'freq': freq_y},
    }
    
    if x_orientation == 'east-west':
        directions['east'] = {'signal': np.maximum(x_signal, 0), 'freq': freq_x}
        directions['west'] = {'signal': np.maximum(-x_signal, 0), 'freq': freq_x}
        directions['north'] = {'signal': np.maximum(z_signal, 0), 'freq': freq_z}
        directions['south'] = {'signal': np.maximum(-z_signal, 0), 'freq': freq_z}
    else:  # x_orientation == 'north-south'
        directions['north'] = {'signal': np.maximum(x_signal, 0), 'freq': freq_x}
        directions['south'] = {'signal': np.maximum(-x_signal, 0), 'freq': freq_x}
        directions['east'] = {'signal': np.maximum(z_signal, 0), 'freq': freq_z}
        directions['west'] = {'signal': np.maximum(-z_signal, 0), 'freq': freq_z}
    
    for direction in ['east', 'west', 'north', 'south']:
        _, directions[direction]['fft'] = apply_fft(directions[direction]['signal'], sampling_rate)
    
    return directions, time


def plot_directional_analysis(directions, time):
    # Create figure for time domain plots
    plt.figure(figsize=(15, 10))
    
    # Plot time domain signals
    plt.subplot(3, 1, 1)
    plt.plot(time, directions['vertical']['signal'])
    plt.title('Vertical Component')
    plt.xlabel('Time')
    plt.ylabel('Amplitude')
    
    plt.subplot(3, 1, 2)
    plt.plot(time, directions['east']['signal'], 'r', label='East')
    plt.plot(time, directions['west']['signal'], 'b', label='West')
    plt.title('East-West Components')
    plt.xlabel('Time')
    plt.ylabel('Amplitude')
    plt.legend()
    
    plt.subplot(3, 1, 3)
    plt.plot(time, directions['north']['signal'], 'g', label='North')
    plt.plot(time, directions['south']['signal'], 'y', label='South')
    plt.title('North-South Components')
    plt.xlabel('Time')
    plt.ylabel('Amplitude')
    plt.legend()
    
    plt.tight_layout()
    
    # Create figure for frequency domain plots
    plt.figure(figsize=(15, 10))
    
    # Plot frequency domain signals
    plt.subplot(3, 1, 1)
    plt.plot(directions['vertical']['freq'], directions['vertical']['fft'])
    plt.title('Vertical Component - Frequency Domain')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude')
    
    plt.subplot(3, 1, 2)
    plt.plot(directions['east']['freq'], directions['east']['fft'], 'r', label='East')
    plt.plot(directions['west']['freq'], directions['west']['fft'], 'b', label='West')
    plt.title('East-West Components - Frequency Domain')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude')
    plt.legend()
    
    plt.subplot(3, 1, 3)
    plt.plot(directions['north']['freq'], directions['north']['fft'], 'g', label='North')
    plt.plot(directions['south']['freq'], directions['south']['fft'], 'y', label='South')
    plt.title('North-South Components - Frequency Domain')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude')
    plt.legend()
    
    plt.tight_layout()
    plt.show()

def main():
    file_path = "new_data.txt"
    sampling_rate = 1/0.004

    x_orientation = "east-west"
    z_orientation = "north-south"

    try:
        data = load_data(file_path)
    except Exception as e:
        print(f"Error loading data from file: {e}")
        return
    
    directions, time = separate_directions(data, sampling_rate, x_orientation, z_orientation)

    # Visualize results
    plot_directional_analysis(directions, time)
    
    # Optional: Save processed data to CSV
    result_df = pd.DataFrame({
        'Time': time,
        'Vertical': directions['vertical']['signal'],
        'East': directions['east']['signal'],
        'West': directions['west']['signal'],
        'North': directions['north']['signal'],
        'South': directions['south']['signal']
    })
    result_df.to_csv('directional_components.csv', index=False)
    print("Directional components saved to 'directional_components.csv'")

if __name__ == "__main__":
    main()
