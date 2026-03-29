from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

import pandas as pd


def format_player_name(name: object) -> object:
    if not isinstance(name, str):
        return name
    clean_name = _reorder_comma_name(" ".join(name.split()))
    if not clean_name:
        return None

    pieces = []
    for token in clean_name.split(" "):
        if re.fullmatch(r"(?:[a-z]\.){1,4}", token.lower()):
            pieces.append(token.upper())
        else:
            pieces.append(token.title())
    return " ".join(pieces)


def normalize_player_key(name: object) -> str | None:
    formatted = format_player_name(name)
    if not isinstance(formatted, str):
        return None
    ascii_name = unicodedata.normalize("NFKD", formatted)
    ascii_name = "".join(char for char in ascii_name if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", ascii_name.lower())


def format_display_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    for column in display.columns:
        lowered = column.lower()
        if "player" in lowered or lowered.endswith("_name") or lowered == "name":
            display[column] = display[column].map(format_player_name)
            continue
        display[column] = display[column].map(_format_value)
    return display


def render_centered_table(frame: pd.DataFrame) -> str:
    formatted = format_display_dataframe(frame)
    html = formatted.to_html(index=False, escape=False, classes="phillies-table", border=0)
    return (
        "<style>"
        ".phillies-table-wrap{overflow-x:auto;}"
        ".phillies-table{width:100%;border-collapse:collapse;font-size:0.95rem;}"
        ".phillies-table th,.phillies-table td{padding:0.55rem 0.7rem;border:1px solid rgba(49,51,63,0.2);text-align:center;vertical-align:middle;}"
        ".phillies-table th{background:#f3f4f6;font-weight:600;}"
        "</style>"
        f"<div class='phillies-table-wrap'>{html}</div>"
    )


def format_metric_value(value: object) -> str:
    formatted = _format_value(value)
    return "No data" if formatted is None else str(formatted)


def _format_value(value: object) -> object:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%m-%d-%Y")
    if isinstance(value, (datetime, date)):
        return value.strftime("%m-%d-%Y")
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else f"{value:.2f}"
    return value


def _reorder_comma_name(name: str) -> str:
    if "," not in name:
        return name
    last_name, first_name = [piece.strip() for piece in name.split(",", 1)]
    if not first_name:
        return last_name
    return f"{first_name} {last_name}"
