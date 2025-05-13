import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def  main():
    parser = argparse.ArgumentParser(
        prog='Signal Plotter',
        description='Plot signal data from a CSV file.'
    )

    parser.add_argument('filename')
    args = parser.parse_args()
    
    # Read CSV file
    data = pd.read_csv(args.filename, delimiter="\t")

    data['V'] = data['V'] -  np.mean(data['V'])
    data['E-W'] = data['E-W'] -  np.mean(data['E-W'])
    data['N-S'] = data['N-S'] -  np.mean(data['N-S'])

    fig, axes = plt.subplots(3, 1, figsize=(10, 6), sharex=True)

    axes[0].plot(data['Time (s)'], data['V'], label='Vertical')
    axes[0].set_ylabel('Amplitude')
    
    axes[1].plot(data['Time (s)'], data['E-W'], label='East-West', color='orange')
    axes[1].set_ylabel('Amplitude')

    axes[2].plot(data['Time (s)'], data['N-S'], label='North-South', color='green')
    axes[2].set_ylabel('Amplitude')
    axes[2].set_xlabel('Time (s)')

    plt.savefig("output_plot.png")

if __name__ == "__main__":
    main()

