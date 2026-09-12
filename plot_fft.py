"""
fft_seismic.py  –  compute and save FFT results for V / E‑W / N‑S channels
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import detrend, get_window


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def compute_rfft(x: np.ndarray, dt: float, window: str = "hann"):
    """
    Return (freqs [Hz], complex_spectrum, amplitude) for one‑sided rFFT.
    The amplitude is |FFT| scaled to preserve signal energy, i.e. 2/N.
    """
    n = len(x)
    win = get_window(window, n, fftbins=True)
    spec = np.fft.rfft(x * win) / n  # complex
    amp = 2.0 * np.abs(spec)  # one‑sided amplitude
    freqs = np.fft.rfftfreq(n, d=dt)
    return freqs, spec, amp


def build_dataframe(freqs, v, ew, ns) -> pd.DataFrame:
    """Pack real/imag/mag for three channels into a tidy DataFrame."""
    return pd.DataFrame(
        {
            "Frequency_Hz": freqs,
            "Vertical_Real": v.real,
            "Vertical_Imag": v.imag,
            "Vertical_Magnitude": np.abs(v),
            "EastWest_Real": ew.real,
            "EastWest_Imag": ew.imag,
            "EastWest_Magnitude": np.abs(ew),
            "NorthSouth_Real": ns.real,
            "NorthSouth_Imag": ns.imag,
            "NorthSouth_Magnitude": np.abs(ns),
        }
    )


def save_plot(freqs, v_amp, ew_amp, ns_amp, out_png: Path):
    """Quick three‑panel amplitude plot."""
    fig, axes = plt.subplots(
        3, 1, figsize=(10, 8), sharex=True, constrained_layout=True
    )

    axes[0].plot(freqs, v_amp)
    axes[0].set_title("Vertical")
    axes[1].plot(freqs, ew_amp)
    axes[1].set_title("East – West")
    axes[2].plot(freqs, ns_amp)
    axes[2].set_title("North – South")

    for ax in axes:
        ax.set_ylabel("Amplitude")
    axes[-1].set_xlabel("Frequency (Hz)")

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    plt.close(fig)


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description="Compute FFT of 3‑component signal")
    p.add_argument(
        "csv", type=Path, help="Input CSV with columns Time (s), V, E-W, N-S"
    )
    p.add_argument(
        "-o", "--out-dir", type=Path, default=Path("."), help="Output folder"
    )
    args = p.parse_args(argv)

    # ------------------------------------------------------------------
    # load & basic hygiene
    # ------------------------------------------------------------------
    data = pd.read_csv(args.csv, delimiter="\t")
    try:
        t = data["Time (s)"].to_numpy()
        v = data["V"].to_numpy()
        ew = data["E-W"].to_numpy()
        ns = data["N-S"].to_numpy()
    except KeyError as e:
        p.error(f"missing column {e}")

    dt = np.diff(t).mean()
    if not np.allclose(np.diff(t), dt, rtol=1e-4):
        print(
            f"⚠️  Warning: time steps are not strictly uniform; using mean dt={dt:.6f}s"
        )

    # ------------------------------------------------------------------
    # preprocess → detrend → FFT
    # ------------------------------------------------------------------
    v_hat_f, v_hat, v_amp = compute_rfft(detrend(v, type="linear"), dt)
    _, ew_hat, ew_amp = compute_rfft(detrend(ew, type="linear"), dt)
    _, ns_hat, ns_amp = compute_rfft(detrend(ns, type="linear"), dt)

    # ------------------------------------------------------------------
    # outputs
    # ------------------------------------------------------------------
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    df = build_dataframe(v_hat_f, v_hat, ew_hat, ns_hat)
    csv_path = out_dir / "fft_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"FFT table  ➜  {csv_path}")

    png_path = out_dir / "fft_plot.png"
    save_plot(v_hat_f, v_amp, ew_amp, ns_amp, png_path)
    print(f"Plot image ➜  {png_path}")


if __name__ == "__main__":
    main()
