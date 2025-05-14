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
    return go, io, make_subplots, mo, np, pd


@app.cell
def _(mo):
    data_file = mo.ui.file(kind="area")
    data_file
    return (data_file,)


@app.cell
def _(data_file, io, pd):
    df = pd.read_csv(io.BytesIO(data_file.contents()), delimiter="\t")
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


@app.cell(hide_code=True)
def _(
    e_w_column_selector,
    go,
    make_subplots,
    n_s_column_selector,
    np,
    pd,
    time_column_selector,
    vertical_column_selector,
):
    def plot_signal_interactive(data: pd.DataFrame):

        time_data = data[time_column_selector.value] if time_column_selector.value else None
        # Remove mean from each signal (baseline correction)
        vertical_data = data[vertical_column_selector.value] if vertical_column_selector.value else np.zeros(1)
        e_w_data = data[e_w_column_selector.value] if e_w_column_selector.value else np.zeros(1)
        n_s_data = data[n_s_column_selector.value] if n_s_column_selector.value else np.zeros(1)

        vertical_data = vertical_data - np.mean(vertical_data)
        e_w_data = e_w_data - np.mean(e_w_data)
        n_s_data = n_s_data - np.mean(n_s_data)
    
        # Create subplots with shared x-axis
        fig = make_subplots(rows=3, cols=1, 
                            shared_xaxes=True,
                            vertical_spacing=0.05,
                            subplot_titles=("Vertical Component", 
                                           "East-West Component", 
                                           "North-South Component"))
    
        # Add traces for each component
        fig.add_trace(
            go.Scatter(x=time_data, y=vertical_data, 
                      name='Vertical', 
                      line=dict(color='blue')),
            row=1, col=1
        )
    
        fig.add_trace(
            go.Scatter(x=time_data, y=e_w_data, 
                      name='East-West', 
                      line=dict(color='orange')),
            row=2, col=1
        )
    
        fig.add_trace(
            go.Scatter(x=time_data, y=n_s_data, 
                      name='North-South', 
                      line=dict(color='green')),
            row=3, col=1
        )
    
        # Update layout
        fig.update_layout(
            height=600,
            width=900,
            title_text="Seismic Signal Components",
            showlegend=True,
            hovermode="x unified"
        )

        xaxis_title = "Time (s)" if time_data is not None else "Index"
    
        # Update axis titles
        fig.update_yaxes(title_text="Amplitude", row=1, col=1)
        fig.update_yaxes(title_text="Amplitude", row=2, col=1)
        fig.update_yaxes(title_text="Amplitude", row=3, col=1)
        fig.update_xaxes(title_text=xaxis_title, row=3, col=1)
    
        return fig
    return (plot_signal_interactive,)


@app.cell
def _(data, plot_signal_interactive):
    fig = plot_signal_interactive(data=data)
    fig
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
