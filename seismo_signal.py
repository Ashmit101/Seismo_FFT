import marimo

__generated_with = "0.13.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import pandas as pd
    import io

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from scipy.signal import detrend, get_window
    from scipy.fft import fft, fftfreq
    return detrend, fft, fftfreq, get_window, go, io, make_subplots, mo, np, pd


@app.cell
def _(mo):
    data_file = mo.ui.file(kind="area")
    data_file
    return (data_file,)


@app.cell
def _(data_file):
    if data_file.name():
        extension = data_file.name().split(".")[1]
        if extension == "txt":
            delimiter = "\t"
        elif extension == "csv":
            delimiter = ","
    return (delimiter,)


@app.cell
def _(data_file, delimiter, io, pd):
    df = pd.read_csv(io.BytesIO(data_file.contents()), delimiter=delimiter)
    df.head()
    return (df,)


@app.cell
def _(df, mo):
    data = df.copy()
    data.columns

    time_column_selector = mo.ui.dropdown(data.columns)
    vertical_column_selector = mo.ui.dropdown(data.columns)
    e_w_column_selector = mo.ui.dropdown(data.columns)
    n_s_column_selector = mo.ui.dropdown(data.columns)
    return (
        data,
        e_w_column_selector,
        n_s_column_selector,
        time_column_selector,
        vertical_column_selector,
    )


@app.cell
def _(mo, time_column_selector):
    mo.md(text=f"Time Column: {time_column_selector}")
    return


@app.cell
def _(mo, vertical_column_selector):
    mo.md(text=f"Vertical Column: {vertical_column_selector}")
    return


@app.cell
def _(e_w_column_selector, mo):
    mo.md(text=f"East-West Column: {e_w_column_selector}")
    return


@app.cell
def _(mo, n_s_column_selector):
    mo.md(text=f"North-South Column: {n_s_column_selector}")
    return


@app.cell
def _(
    e_w_column_selector,
    n_s_column_selector,
    time_column_selector,
    vertical_column_selector,
):
    if vertical_column_selector.value:
        vertical_column = vertical_column_selector.value

    if e_w_column_selector.value:
        ew_column = e_w_column_selector.value

    if n_s_column_selector.value:
        ns_column = n_s_column_selector.value

    if time_column_selector.value:
        time_column = time_column_selector.value
    return ew_column, ns_column, time_column, vertical_column


@app.cell
def _(data, detrend, ew_column, ns_column, time_column, vertical_column):
    time_data = data[time_column]
    v_data = data[vertical_column]
    ew_data = data[ew_column]
    ns_data = data[ns_column]

    v_data = detrend(v_data)
    ew_data = detrend(ew_data)
    ns_data = detrend(ns_data)
    return ew_data, ns_data, time_data, v_data


@app.cell(hide_code=True)
def _(ew_data, go, make_subplots, ns_data, time_data, v_data):
    signal_fig = make_subplots(rows=3,
                              cols=1,
                              shared_xaxes=True,
                              vertical_spacing=0.05,
                              subplot_titles=("Vertical Component",
                                             "East-West Component",
                                             "North-South Component"))
    signal_fig.add_trace(
        go.Scatter(x=time_data,y=v_data, name="Vertical", line=dict(color='blue'))
    )

    signal_fig.add_trace(
        go.Scatter(x=time_data, y=ew_data, 
                  name='East-West', 
                  line=dict(color='orange')),
        row=2, col=1
        )

    signal_fig.add_trace(
        go.Scatter(x=time_data, y=ns_data, 
                  name='North-South', 
                  line=dict(color='green')),
        row=3, col=1
        )

    signal_fig.update_layout(
            height=600,
            width=900,
            title_text="Seismic Signal Components",
            showlegend=True,
            hovermode="x unified"
        )

    xaxis_title = "Time (s)" if time_data is not None else "Index"

        # Update axis titles
    signal_fig.update_yaxes(title_text="Amplitude", row=1, col=1)
    signal_fig.update_yaxes(title_text="Amplitude", row=2, col=1)
    signal_fig.update_yaxes(title_text="Amplitude", row=3, col=1)
    signal_fig.update_xaxes(title_text=xaxis_title, row=3, col=1)

    signal_fig
    return


@app.cell
def _(get_window, np):
    def compute_rfft(x: np.ndarray, dt: float, window: str = "hann"):
        """
        Return (freqs [Hz], complex_spectrum, amplitude) for one‑sided rFFT.
        The amplitude is |FFT| scaled to preserve signal energy, i.e. 2/N.
        """
        n = len(x)
        win = get_window(window, n, fftbins=True)
        spec = np.fft.rfft(x * win) / n           # complex
        amp = 2.0 * np.abs(spec)                  # one‑sided amplitude
        freqs = np.fft.rfftfreq(n, d=dt)
        return freqs, spec, amp
    return


@app.cell(hide_code=True)
def _(np, pd):
    def build_dataframe(freqs, v, ew, ns) -> pd.DataFrame:
        """Pack real/imag/mag for three channels into a tidy DataFrame."""
        return pd.DataFrame({
            "Frequency_Hz"      : freqs,
            "Vertical_Real"     : v.real,
            "Vertical_Imag"     : v.imag,
            "Vertical_Magnitude": np.abs(v),
            "EastWest_Real"     : ew.real,
            "EastWest_Imag"     : ew.imag,
            "EastWest_Magnitude": np.abs(ew),
            "NorthSouth_Real"   : ns.real,
            "NorthSouth_Imag"   : ns.imag,
            "NorthSouth_Magnitude": np.abs(ns),
        })
    return


@app.cell
def _(ew_data, fft, fftfreq, np, ns_data, time_data, v_data):
    dt = np.diff(time_data).mean()
    if not np.allclose(np.diff(time_data), dt, rtol=1e-4):
        print("⚠️  Warning: time steps are not strictly uniform; "
              "using mean dt={:.6f}s".format(dt))
    N = len(time_data)
    frequency_data = fftfreq(N, dt)[:N//2]
    v_f = fft(v_data)
    ew_f = fft(ew_data)
    ns_f = fft(ns_data)

    v_amp = 2.0/N * np.abs(v_f[:N//2])
    ew_amp = 2.0/N * np.abs(ew_f[:N//2])
    ns_amp = 2.0/N * np.abs(ns_f[:N//2])
    return ew_amp, frequency_data, ns_amp, v_amp


@app.cell
def _(ew_amp, frequency_data, ns_amp, time_data, v_amp):
    print(f"Time data: {len(time_data)}")
    print(f"Frequency data: {len(frequency_data)}")
    print(f"Vertical data: {len(v_amp)}")
    print(f"East-West data: {len(ew_amp)}")
    print(f"North-South data: {len(ns_amp)}")
    return


@app.cell
def _(
    ew_amp,
    ew_column,
    frequency_data,
    ns_amp,
    ns_column,
    pd,
    v_amp,
    vertical_column,
):
    fourier_df = pd.DataFrame(
        {
            "frequency": frequency_data,
            vertical_column: v_amp,
            ew_column: ew_amp,
            ns_column: ns_amp
        }
    )

    fourier_df.tail()
    return (fourier_df,)


@app.cell(hide_code=True)
def _(ew_amp, frequency_data, go, make_subplots, ns_amp, v_amp):
    fourier_fig = make_subplots(rows=3, cols=1, 
                        shared_xaxes=True,
                        vertical_spacing=0.05,
                        subplot_titles=("Vertical Component", 
                                       "East-West Component", 
                                       "North-South Component"))

    # Add traces for each component
    fourier_fig.add_trace(
        go.Scatter(x=frequency_data, y=v_amp, 
                  name='Vertical', 
                  line=dict(color='blue')),
        row=1, col=1
    )

    fourier_fig.add_trace(
        go.Scatter(x=frequency_data, y=ew_amp, 
                  name='East-West', 
                  line=dict(color='orange')),
        row=2, col=1
    )

    fourier_fig.add_trace(
        go.Scatter(x=frequency_data, y=ns_amp, 
                  name='North-South', 
                  line=dict(color='green')),
        row=3, col=1
    )

    # Update layout
    fourier_fig.update_layout(
        height=600,
        width=900,
        title_text="Fourier Transformation of Seismic Signal Components",
        showlegend=True,
        hovermode="x unified"
    )

    fourier_fig_xaxis_title = "Frequency (Hz)"

    # Update axis titles
    fourier_fig.update_yaxes(title_text="Amplitude", row=1, col=1)
    fourier_fig.update_yaxes(title_text="Amplitude", row=2, col=1)
    fourier_fig.update_yaxes(title_text="Amplitude", row=3, col=1)
    fourier_fig.update_xaxes(title_text=fourier_fig_xaxis_title, row=3, col=1)

    fourier_fig
    return


@app.cell
def _(ew_amp, fourier_df, np, ns_amp, v_amp):
    epsilon = 1e-10
    hvsr = np.sqrt(ew_amp**2 + ns_amp**2) / (2 * (v_amp + epsilon))
    fourier_df["hvsr"] = hvsr
    fourier_df.tail()
    return (hvsr,)


@app.cell
def _(frequency_data, go, hvsr):
    # Plot HVSR plot
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(x=frequency_data, y=hvsr, name="HVSR", mode="lines")
    )

    figure.update_layout(
        title="HVSR Plot",  # FIX 4: Add a main plot title
        xaxis_title="Frequency (Hz)", # FIX 5: More descriptive x-axis title
        yaxis_title="HVSR Amplitude", # FIX 6: Add a y-axis title
        hovermode="x unified" # FIX 7: Improve hover experience
    )

    figure
    return


@app.cell
def _(fourier_df, io, mo):
    fourier_csv_bytes = io.BytesIO()
    fourier_df.to_csv(fourier_csv_bytes, index=False)
    fourier_csv_bytes.seek(0)

    download_button = mo.download(
        label="Download CSV File",
        filename="seismic_data.csv",
        data=fourier_csv_bytes.getvalue(),
    )
    download_button
    return


if __name__ == "__main__":
    app.run()
