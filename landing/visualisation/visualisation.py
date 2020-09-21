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
        'b': 0,
        't': 0,
    },
    showlegend=False,
    xaxis={
        "showgrid": False,
        "zeroline": False,
        "showline": False,
        "ticks": "outside",
        "tickson": "boundaries",
        "type": "date",
        "tickformat": '%b',
        "tickfont": {
            "family": '"GDS Transport", Arial, sans-serif',
            "size": 20,
            "color": "#6B7276"
        }
    }
)

COLOURS = {
    "good": {
        "line": "rgba(30,150,0,1)",
        "fill": "rgba(100,200,0,0.1)"
    },
    "bad": {
        "line": "rgba(255,0,0,1)",
        "fill": "rgba(255,0,0,0.1)"
    },
    "neutral": {
        "line": "rgba(107,114,118,1)",
        "fill": "rgba(107,114,118,0.1)"
    }
}


# @lru_cache()
def get_colour(change, is_improving):
    change_value = float(change["value"])

    trend_colour = str()

    if change_value == 0:
        trend_colour = COLOURS["neutral"]
    elif is_improving(change_value):
        trend_colour = COLOURS["good"]
    elif not is_improving(change_value):
        trend_colour = COLOURS["bad"]

    return trend_colour


# @lru_cache()
def svg_to_url(svg):
    return "data:image/svg+xml;utf8," + quote(svg)


def plot_thumbnail(timeseries, change, is_improving):
    get_date = itemgetter("date")
    get_value = itemgetter("value")

    trend_colour = get_colour(change, is_improving)

    x = list(map(get_date, timeseries))
    y = Series(list(map(get_value, timeseries))).rolling(7, center=True).mean()
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
            text="Points only",
            hoverinfo='text+x+y'
        )
    )

    # fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)

    return svg_to_url(fig.to_image(format="svg", height='150px').decode())
