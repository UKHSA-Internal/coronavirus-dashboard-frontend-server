#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from datetime import datetime
from os.path import abspath, split as split_path, join as join_path

# 3rd party:

# Internal:
from ..common.visualisation import plot_thumbnail

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

metrics = [
    'newAdmissions',
    'newCasesByPublishDate',
    'newDeaths28DaysByPublishDate',
    'newVirusTests'
]


curr_dir, _ = split_path(abspath(__file__))
queries_dir = join_path(curr_dir, "queries")


with open(join_path(queries_dir, "time_series_data.sql")) as fp:
    time_series_data_query = fp.read()


with open(join_path(queries_dir, "latest_change_data.sql")) as fp:
    latest_change_data_query = fp.read()


async def get_timeseries(conn, timestamp):
    ts = datetime.fromisoformat(timestamp.replace("5Z", ""))
    partition = f"{ts:%Y_%-m_%-d}_other"
    partition_id = f"{ts:%Y_%-m_%-d}|other"
    values_query = time_series_data_query.format(partition=partition)
    change_query = latest_change_data_query.format(partition=partition)

    for metric in metrics:
        values = conn.fetch(values_query, partition_id, ts, metric)
        change = conn.fetchrow(change_query, partition_id, ts, metric + "Change")
        yield metric, plot_thumbnail(values, metric_name=metric, change=change)
