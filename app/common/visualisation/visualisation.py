#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from operator import itemgetter
from urllib.parse import quote

# 3rd party:
from plotly import graph_objects as go
from pandas import Series

# Internal:
from ..data.variables import IsImproving

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'plot_thumbnail',
    'get_colour',
    'svg_to_url'
]


TIMESERIES_LAYOUT = go.Layout(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin={
        'l': 0,
        'r': 0,
        'b': 4,
        't': 0,
    },
    showlegend=False,
    height=350,
    autosize=False,
    xaxis={
        "showgrid": False,
        "zeroline": False,
        "showline": False,
        "ticks": "outside",
        "tickson": "boundaries",
        "type": "date",
        "tickformat": '%b',
        # "tickvals": x[::30],
        # "tickmode": 'array',
        "tickfont": {
            "family": '"GDS Transport", Arial, sans-serif',
            "size": 20,
            "color": "#6B7276"
        }
    }
)

COLOURS = {
    "good": {
        "line": "rgba(0,90,48,1)",
        "fill": "rgba(204,226,216,1)"
    },
    "bad": {
        "line": "rgba(148,37,20,1)",
        "fill": "rgba(246,215,210,1)"
    },
    "neutral": {
        "line": "rgba(56,63,67,1)",
        "fill": "rgba(235,233,231,1)"
    }
}


def get_colour(change, metric_name) -> dict:
    change_value = float(change or 0)
    improving = IsImproving[metric_name](change_value)

    trend_colour = COLOURS["neutral"]

    if isinstance(improving, bool):
        if improving:
            trend_colour = COLOURS["good"]
        else:
            trend_colour = COLOURS["bad"]

    return trend_colour


def svg_to_url(svg):
    return f"data:image/svg+xml;utf8,{quote(svg)}"


async def plot_thumbnail(timeseries, change, metric_name):
    get_date = itemgetter("date")
    get_value = itemgetter("value")

    change_data = await change

    trend_colour = get_colour(get_value(change_data), metric_name)
    data = await timeseries

    x = list(map(get_date, data))
    y = Series(list(map(get_value, data))).rolling(7, center=True).mean()
    fig = go.Figure(
        go.Scatter(
            x=x[13:],
            y=y[13:],
            line={
                "width": 2,
                "color": COLOURS['neutral']['line']
            }
        ),
        layout=TIMESERIES_LAYOUT
    )

    fig.add_trace(
        go.Scatter(
            x=x[:14],
            y=y[:14],
            line={
                "width": 2
            },
            mode='lines',
            fill='tozeroy',
            hoveron='points',
            opacity=.5,
            line_color=trend_colour['line'],
            fillcolor=trend_colour['fill'],
        )
    )

    fig.update_yaxes(showticklabels=False)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)

    return svg_to_url(fig.to_image(format="svg", height='150px').decode())
