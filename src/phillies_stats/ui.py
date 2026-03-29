from __future__ import annotations

from datetime import date, datetime
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from phillies_stats.display import format_metric_value

APP_CSS = """
<style>
:root {
    --ph-bg: #08111c;
    --ph-bg-alt: #101a28;
    --ph-panel: rgba(15, 24, 38, 0.92);
    --ph-panel-soft: rgba(20, 31, 47, 0.82);
    --ph-border: rgba(255, 255, 255, 0.08);
    --ph-border-strong: rgba(199, 60, 80, 0.28);
    --ph-text: #f4f7fb;
    --ph-muted: #95a3b9;
    --ph-accent: #c73c50;
    --ph-accent-soft: rgba(199, 60, 80, 0.14);
    --ph-shadow: 0 18px 45px rgba(0, 0, 0, 0.28);
}

.stApp {
    background:
        radial-gradient(circle at top right, rgba(199, 60, 80, 0.11), transparent 30%),
        radial-gradient(circle at top left, rgba(71, 115, 183, 0.10), transparent 26%),
        linear-gradient(180deg, #08111c 0%, #0a1522 100%);
    color: var(--ph-text);
}

[data-testid="stAppViewContainer"] > .main,
[data-testid="stAppViewContainer"] > .main > div {
    background: transparent;
}

header[data-testid="stHeader"] {
    background: transparent;
}

div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
footer {
    display: none;
}

.block-container {
    padding-top: 1.65rem;
    padding-bottom: 3rem;
    max-width: 1440px;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(8, 17, 28, 0.98) 0%, rgba(13, 22, 35, 0.98) 100%);
    border-right: 1px solid var(--ph-border);
}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
    padding-top: 1rem;
}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
    border-radius: 14px;
    margin-bottom: 0.25rem;
    color: #dce4f2;
}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
    background: rgba(255, 255, 255, 0.04);
}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(199, 60, 80, 0.16);
    border: 1px solid var(--ph-border-strong);
    color: var(--ph-text);
}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > div > p {
    color: var(--ph-muted);
    font-size: 0.76rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 1.2rem;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, rgba(16, 26, 40, 0.94) 0%, rgba(13, 22, 35, 0.94) 100%);
    border: 1px solid var(--ph-border) !important;
    border-radius: 24px;
    box-shadow: var(--ph-shadow);
}

div[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 0.35rem 0.4rem;
}

div[data-testid="stMetric"] {
    background: linear-gradient(180deg, rgba(16, 26, 40, 0.95) 0%, rgba(12, 20, 32, 0.95) 100%);
    border: 1px solid var(--ph-border);
    border-radius: 20px;
    padding: 0.55rem 0.85rem;
    box-shadow: var(--ph-shadow);
}

div[data-testid="stMetricLabel"] p {
    color: var(--ph-muted);
}

div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--ph-text);
}

label[data-testid="stWidgetLabel"] p {
    color: var(--ph-muted);
    font-size: 0.82rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

div[data-baseweb="select"] > div,
div[data-baseweb="base-input"] > div {
    background: rgba(16, 26, 40, 0.88);
    border: 1px solid var(--ph-border);
    border-radius: 16px;
    min-height: 3rem;
}

div[data-baseweb="select"] svg {
    color: var(--ph-muted);
}

div.stButton > button {
    min-height: 3rem;
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(199, 60, 80, 0.92) 0%, rgba(164, 42, 59, 0.94) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: white;
    font-weight: 600;
    box-shadow: var(--ph-shadow);
}

div.stButton > button:hover {
    border-color: rgba(255, 255, 255, 0.12);
    filter: brightness(1.04);
}

.page-hero {
    background:
        linear-gradient(135deg, rgba(199, 60, 80, 0.18) 0%, rgba(199, 60, 80, 0.06) 36%, rgba(16, 26, 40, 0.96) 100%),
        linear-gradient(180deg, rgba(16, 26, 40, 0.95) 0%, rgba(11, 19, 31, 0.95) 100%);
    border: 1px solid var(--ph-border);
    border-radius: 28px;
    padding: 1.6rem 1.7rem;
    margin-bottom: 1.25rem;
    box-shadow: var(--ph-shadow);
}

.page-eyebrow {
    color: var(--ph-muted);
    font-size: 0.76rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin-bottom: 0.55rem;
}

.page-title {
    color: var(--ph-text);
    font-family: "Aptos Display", "Trebuchet MS", "Segoe UI", sans-serif;
    font-size: clamp(2rem, 3vw, 3.1rem);
    font-weight: 700;
    line-height: 1.05;
    margin: 0;
}

.page-subtitle {
    color: var(--ph-muted);
    font-size: 1rem;
    line-height: 1.7;
    margin-top: 0.7rem;
    max-width: 58rem;
}

.page-meta {
    color: #d7deea;
    margin-top: 1rem;
    display: inline-flex;
    gap: 0.4rem;
    align-items: center;
    font-size: 0.92rem;
    padding: 0.45rem 0.8rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--ph-border);
    border-radius: 999px;
}

.section-heading {
    margin-bottom: 0.9rem;
}

.section-heading h2 {
    color: var(--ph-text);
    font-size: 1.08rem;
    font-weight: 650;
    margin: 0;
}

.section-heading p {
    color: var(--ph-muted);
    font-size: 0.92rem;
    line-height: 1.6;
    margin: 0.3rem 0 0;
}

.filter-caption {
    color: var(--ph-muted);
    font-size: 0.82rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}

.stat-card {
    background: linear-gradient(180deg, rgba(16, 26, 40, 0.98) 0%, rgba(11, 19, 31, 0.98) 100%);
    border: 1px solid var(--ph-border);
    border-radius: 22px;
    padding: 1rem 1.05rem;
    min-height: 8.4rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: var(--ph-shadow);
}

.stat-card--accent {
    border-color: var(--ph-border-strong);
    background:
        linear-gradient(180deg, rgba(199, 60, 80, 0.16) 0%, rgba(16, 26, 40, 0.98) 58%),
        linear-gradient(180deg, rgba(16, 26, 40, 0.98) 0%, rgba(11, 19, 31, 0.98) 100%);
}

.stat-label {
    color: var(--ph-muted);
    font-size: 0.82rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.stat-value {
    color: var(--ph-text);
    font-family: "Aptos Display", "Trebuchet MS", "Segoe UI", sans-serif;
    font-size: clamp(1.6rem, 2.1vw, 2.45rem);
    font-weight: 700;
    line-height: 1.08;
    margin-top: 0.6rem;
}

.stat-helper {
    color: #d7deea;
    font-size: 0.92rem;
    margin-top: 0.85rem;
}

.profile-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: end;
}

.profile-title {
    color: var(--ph-text);
    font-family: "Aptos Display", "Trebuchet MS", "Segoe UI", sans-serif;
    font-size: 2rem;
    font-weight: 700;
    margin: 0;
}

.profile-subtitle {
    color: var(--ph-muted);
    margin-top: 0.35rem;
    line-height: 1.6;
}

.profile-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.45rem 0.8rem;
    border-radius: 999px;
    border: 1px solid var(--ph-border-strong);
    background: var(--ph-accent-soft);
    color: #f8e8eb;
    font-size: 0.84rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 0.45rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--ph-border);
    border-radius: 999px;
    padding: 0.3rem;
    margin-bottom: 1rem;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 999px;
    color: var(--ph-muted);
    min-height: 2.6rem;
}

.stTabs [aria-selected="true"] {
    background: rgba(199, 60, 80, 0.18) !important;
    color: var(--ph-text) !important;
}

.stAlert {
    border-radius: 18px;
    border: 1px solid var(--ph-border);
    background: rgba(16, 26, 40, 0.92);
}

.phillies-table-wrap {
    overflow-x: auto;
}

table.phillies-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
}

table.phillies-table thead th {
    color: var(--ph-muted);
    font-size: 0.75rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.03);
    padding: 0.85rem 1rem;
    border-bottom: 1px solid var(--ph-border);
}

table.phillies-table tbody td {
    color: var(--ph-text);
    font-size: 0.95rem;
    padding: 0.95rem 1rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

table.phillies-table tbody tr:last-child td {
    border-bottom: none;
}

table.phillies-table tbody tr:hover td {
    background: rgba(255, 255, 255, 0.02);
}

table.phillies-table .cell-emphasis {
    color: #ffffff;
    font-weight: 700;
}

table.phillies-table .cell-secondary {
    color: var(--ph-muted);
}

table.phillies-table .cell-rank {
    color: #fcecef;
    font-weight: 700;
}
</style>
"""


def apply_app_theme() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str, *, eyebrow: str | None = None, meta: str | None = None) -> None:
    eyebrow_html = f"<div class='page-eyebrow'>{escape(eyebrow)}</div>" if eyebrow else ""
    meta_html = f"<div class='page-meta'>{escape(meta)}</div>" if meta else ""
    st.markdown(
        f"""
        <section class="page-hero">
            {eyebrow_html}
            <h1 class="page-title">{escape(title)}</h1>
            <p class="page-subtitle">{escape(subtitle)}</p>
            {meta_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="section-heading">
            <h2>{escape(title)}</h2>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_filter_caption(text: str) -> None:
    st.markdown(f"<div class='filter-caption'>{escape(text)}</div>", unsafe_allow_html=True)


def render_profile_header(name: str, subtitle: str, chip: str | None = None) -> None:
    chip_html = f"<div class='profile-chip'>{escape(chip)}</div>" if chip else ""
    st.markdown(
        f"""
        <div class="profile-header">
            <div>
                <h2 class="profile-title">{escape(name)}</h2>
                <div class="profile-subtitle">{escape(subtitle)}</div>
            </div>
            {chip_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stat_cards(cards: list[dict[str, str | None]], *, columns: int | None = None) -> None:
    if not cards:
        return
    row_size = columns or len(cards)
    for start in range(0, len(cards), row_size):
        row_cards = cards[start : start + row_size]
        card_columns = st.columns(len(row_cards))
        for column, card in zip(card_columns, row_cards):
            tone = card.get("tone") or "default"
            helper = card.get("helper")
            helper_html = f"<div class='stat-helper'>{escape(str(helper))}</div>" if helper else ""
            with column:
                st.markdown(
                    f"""
                    <div class="stat-card stat-card--{escape(str(tone))}">
                        <div>
                            <div class="stat-label">{escape(str(card.get("label", "")))}</div>
                            <div class="stat-value">{escape(str(card.get("value", "")))}</div>
                        </div>
                        {helper_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def style_chart(chart: alt.Chart, *, height: int = 320) -> alt.Chart:
    return (
        chart.properties(height=height, background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor="#d7deea",
            titleColor="#d7deea",
            domainColor="rgba(255,255,255,0.14)",
            gridColor="rgba(255,255,255,0.08)",
            tickColor="rgba(255,255,255,0.12)",
        )
        .configure_title(color="#f4f7fb", fontSize=16)
        .configure_legend(
            titleColor="#d7deea",
            labelColor="#d7deea",
            orient="bottom",
            padding=12,
            fillColor="transparent",
            strokeColor="transparent",
        )
        .configure_header(labelColor="#d7deea", titleColor="#f4f7fb")
    )


def format_card(value: object, suffix: str = "") -> str:
    formatted = format_metric_value(value)
    if formatted == "No data":
        return formatted
    return f"{formatted}{suffix}"


def format_timestamp(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y %I:%M %p")
    if isinstance(value, date):
        return value.strftime("%b %d, %Y")
    return str(value)
