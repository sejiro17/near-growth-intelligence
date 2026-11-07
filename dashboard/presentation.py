"""Display formatting and lossless downloads for saved research inputs."""

import csv
import io
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st


RESULTS = Path(__file__).resolve().parents[1] / "results"


def column_label(name):
    if "_" not in name:
        return name
    words = name.replace("_pct", " (%)").replace("_near", " (NEAR)")
    words = words.replace("_utc", " UTC").replace("_id", " ID")
    return (words.replace("_", " ").capitalize().replace("(near)", "(NEAR)")
            .replace(" utc", " UTC").replace(" id", " ID"))


def table(frame, *, near_places=2, **kwargs):
    """Configure display only; retain unrounded numeric values and sorting."""
    display = frame.copy()
    config = {}
    for name in display.columns:
        series = display[name]
        label = column_label(str(name))
        monetary = "near" in str(name).lower()
        if monetary and not pd.api.types.is_numeric_dtype(series):
            values = series.dropna()
            if len(values) and all(isinstance(x, (str, Decimal)) for x in values):
                try:
                    display[name] = series.map(lambda x: None if pd.isna(x) else Decimal(str(x)))
                    series = display[name]
                except (ValueError, ArithmeticError):
                    pass  # Explicit unavailable text remains text, never zero.
        if pd.api.types.is_datetime64_any_dtype(series):
            config[name] = st.column_config.DateColumn(label, format="DD MMM YYYY")
        elif pd.api.types.is_integer_dtype(series):
            config[name] = st.column_config.NumberColumn(label, format="%,d")
        elif pd.api.types.is_float_dtype(series) or any(isinstance(x, Decimal) for x in series.dropna()):
            places = near_places if monetary else 2
            if monetary:
                positive = [abs(Decimal(str(x))) for x in series.dropna() if x != 0]
                if (positive and min(positive) < Decimal("0.01")) or "average" in str(name):
                    places = 8
            config[name] = st.column_config.NumberColumn(label, format=f"%,.{places}f")
        else:
            config[name] = st.column_config.TextColumn(label)
    config.update(kwargs.pop("column_config", {}))
    kwargs.setdefault("alt", "Saved observations: " + ", ".join(column_label(str(x)) for x in display.columns[:2]))
    return st.dataframe(display, column_config=config, **kwargs)


def saved_csv(filename, filters=None):
    """Return original bytes, or filter cells as strings without float parsing."""
    raw = (RESULTS / filename).read_bytes()
    if not filters:
        return raw
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    if not reader.fieldnames or not set(filters) <= set(reader.fieldnames):
        raise ValueError("Download filter is not a saved CSV column")
    rows = [row for row in reader if all(row[key] == value for key, value in filters.items())]
    if not rows:
        raise ValueError("No saved rows match the download selection")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")
