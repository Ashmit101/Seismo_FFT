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
    return detrend, get_window, go, io, make_subplots, mo, np, pd


@app.cell
def _(mo):
    data_file = mo.ui.file(kind="area")
    data_file
    return (data_file,)


@app.cell
def _(data_file):
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
def _(np, pd):
    def remove_mean(data: pd.Series):
        return data - np.mean(data)
    return


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
    return (compute_rfft,)


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
def _(compute_rfft, ew_data, np, ns_data, time_data, v_data):
    dt = np.diff(time_data).mean()
    if not np.allclose(np.diff(time_data), dt, rtol=1e-4):
        print("⚠️  Warning: time steps are not strictly uniform; "
              "using mean dt={:.6f}s".format(dt))

    v_hat_f, v_hat, v_amp   = compute_rfft(v_data, dt)
    _        , ew_hat, ew_amp = compute_rfft(ew_data, dt)
    _        , ns_hat, ns_amp = compute_rfft(ns_data, dt)


    return ew_amp, ns_amp, v_amp, v_hat_f


@app.cell
def _(
    ew_amp,
    ew_column,
    ns_amp,
    ns_column,
    pd,
    v_amp,
    v_hat_f,
    vertical_column,
):
    fourier_df = pd.DataFrame(
        {
            "frequency": v_hat_f,
            vertical_column: v_amp,
            ew_column: ew_amp,
            ns_column: ns_amp
        }
    )

    fourier_df.tail()
    return (fourier_df,)


@app.cell(hide_code=True)
def _(ew_amp, go, make_subplots, ns_amp, v_amp, v_hat_f):
    fourier_fig = make_subplots(rows=3, cols=1, 
                        shared_xaxes=True,
                        vertical_spacing=0.05,
                        subplot_titles=("Vertical Component", 
                                       "East-West Component", 
                                       "North-South Component"))

    # Add traces for each component
    fourier_fig.add_trace(
        go.Scatter(x=v_hat_f, y=v_amp, 
                  name='Vertical', 
                  line=dict(color='blue')),
        row=1, col=1
    )

    fourier_fig.add_trace(
        go.Scatter(x=v_hat_f, y=ew_amp, 
                  name='East-West', 
                  line=dict(color='orange')),
        row=2, col=1
    )

    fourier_fig.add_trace(
        go.Scatter(x=v_hat_f, y=ns_amp, 
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
def _(data, ew_column, fourier_df, np, ns_column, vertical_column):
    hvsr = np.sqrt(np.square(data[ew_column]) + np.square(data[ns_column])) / data[vertical_column]
    fourier_df["hvsr"] = hvsr
    fourier_df.tail()
    return


@app.cell
def _(fourier_df, go):
    # Plot HVSR plot
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(x=fourier_df["frequency"], y=fourier_df["hvsr"], name="HVSR", mode="lines")
    )

    figure.update_layout(
        title="HVSR Plot",  # FIX 4: Add a main plot title
        xaxis_title="Frequency (Hz)", # FIX 5: More descriptive x-axis title
        yaxis_title="HVSR Amplitude", # FIX 6: Add a y-axis title
        hovermode="x unified" # FIX 7: Improve hover experience
    )

    figure
    return


if __name__ == "__main__":
    app.run()
