"""
Smart Healthcare Analytics — Streamlit frontend.

Start the API first:
    uvicorn app:app --reload

Then run:
    streamlit run dashboard.py

Deployment:
    Set HEALTH_API_URL to the public FastAPI origin. The sidebar exposes
    service status only; end users never configure the API URL.
"""

from __future__ import annotations

import math
import os
from datetime import date, timedelta
from html import escape
from typing import Any

import altair as alt
import pandas as pd
import requests
import streamlit as st

ALL_DEPARTMENTS = "All departments"
PAGES = [
    "Hospital Overview",
    "Demand & Staffing Planner",
    "Appointment Risk Check",
    "Patient Segment Explorer",
]

st.set_page_config(
    page_title="Smart Healthcare Analytics",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="auto",
)


def resolve_api_url() -> str:
    """Read the prediction-service URL from the deployment environment.

    Render exposes service hostnames without a scheme, so a bare host is
    upgraded to HTTPS. Streamlit secrets are supported for Streamlit
    Community Cloud deployments.
    """
    value = os.getenv("HEALTH_API_URL", "").strip()
    if not value:
        try:
            value = str(st.secrets.get("HEALTH_API_URL", "")).strip()
        except Exception:
            value = ""
    value = value or "http://127.0.0.1:8000"
    if "://" not in value:
        value = f"https://{value}"
    return value.rstrip("/")


api_url = resolve_api_url()

# ---------------------------------------------------------------------------
# Design system
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
        :root {
            color-scheme: dark;
            --ink: #e8f0fb;
            --ink-soft: #c3d2e4;
            --muted: #93a6bc;
            --muted-light: #7f93a9;
            --line: #233146;
            --line-soft: #1b2737;
            --surface: #111a28;
            --surface-2: #162233;
            --surface-3: #0e1725;
            --canvas: #0a111c;
            --line-strong: #2b3b52;
            --brand: #8ec7ff;
            --blue: #4da3e8;
            --teal: #38c7b2;
            --green: #45c98b;
            --amber: #f0a54a;
            --red: #f0736a;
            --purple: #b39ddb;
            --shadow: 0 6px 22px rgba(0, 0, 0, 0.30);
        }

        html, body, [class*="css"] {
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }
        .stApp {
            background:
                radial-gradient(1100px 520px at 88% -12%, rgba(56, 199, 178, 0.08), transparent 62%),
                radial-gradient(900px 460px at 8% 0%, rgba(77, 163, 232, 0.09), transparent 58%),
                var(--canvas);
        }
        [data-testid="stHeader"] {
            background: rgba(10, 17, 28, 0.88);
            backdrop-filter: blur(8px);
        }
        [data-testid="stDecoration"] {display: none;}
        .block-container {
            max-width: 1260px;
            padding: 1.45rem 1.7rem 3.5rem 1.7rem;
        }

        h1, h2, h3, h4, h5 {
            color: var(--ink);
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            letter-spacing: -0.02em;
        }
        p, li, label, [data-testid="stMarkdownContainer"] {color: var(--ink-soft);}
        [data-testid="stWidgetLabel"] p {
            font-size: 0.8rem;
            font-weight: 600;
            color: #c3d2e4;
        }

        /* Hero ------------------------------------------------------------ */
        .hero {
            position: relative;
            overflow: hidden;
            border-radius: 20px;
            padding: 2rem 2.2rem;
            margin: 0 0 1.4rem 0;
            color: #fff;
            background: linear-gradient(125deg, #07111f 0%, #0c2942 48%, #0f4a46 100%);
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.40);
        }
        .hero::before {
            content: "";
            position: absolute;
            width: 330px;
            height: 330px;
            right: -100px;
            top: -190px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.08);
        }
        .hero::after {
            content: "";
            position: absolute;
            width: 190px;
            height: 190px;
            right: 130px;
            bottom: -130px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.05);
        }
        .hero-inner {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 2rem;
        }
        .hero-copy {max-width: 560px;}
        .hero-eyebrow {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.7rem;
            color: #9ee6d8;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }
        .hero-pulse {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #63e0b8;
            box-shadow: 0 0 0 4px rgba(99, 224, 184, 0.16);
        }
        .hero h1 {
            margin: 0;
            color: #fff;
            font-size: 2.15rem;
            line-height: 1.12;
            letter-spacing: -0.03em;
        }
        .hero p {
            max-width: 760px;
            margin: 0.65rem 0 0 0;
            color: rgba(255, 255, 255, 0.82);
            font-size: 0.96rem;
            line-height: 1.6;
        }
        .hero-tags {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 0.45rem;
            max-width: 420px;
        }
        .hero-tags {flex: 0 0 auto;}
        .hero-tag {
            padding: 0.38rem 0.72rem;
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            color: #eaf5ff;
            font-size: 0.7rem;
            font-weight: 600;
            white-space: nowrap;
        }

        /* Section headings ------------------------------------------------ */
        .section-head {margin: 1.65rem 0 0.55rem 0;}
        .section-kicker {
            margin-bottom: 0.2rem;
            color: #6cb6f0;
            font-size: 0.67rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }
        .section-head h2 {
            margin: 0;
            padding: 0 !important;
            color: var(--ink);
            font-size: 1.35rem;
            line-height: 1.25;
        }
        .section-head p {
            margin: 0.28rem 0 0 0;
            color: var(--muted);
            font-size: 0.87rem;
            line-height: 1.5;
        }

        /* KPI cards ------------------------------------------------------- */
        .kpi-grid {
            display: grid;
            gap: 0.85rem;
            margin: 0 0 0.3rem 0;
        }
        .kpi-grid.cols-2 {grid-template-columns: repeat(2, minmax(0, 1fr));}
        .kpi-grid.cols-3 {grid-template-columns: repeat(3, minmax(0, 1fr));}
        .kpi-grid.cols-4 {grid-template-columns: repeat(4, minmax(0, 1fr));}
        .kpi-grid.cols-5 {grid-template-columns: repeat(5, minmax(0, 1fr));}
        .kpi-card {
            display: flex;
            flex-direction: column;
            min-height: 112px;
            padding: 1rem 1.1rem;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: var(--surface);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.26);
        }
        .kpi-label {
            color: var(--muted);
            font-size: 0.67rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            line-height: 1.35;
            text-transform: uppercase;
        }
        .kpi-value {
            margin-top: 0.38rem;
            color: #e8f0fb;
            font-size: 1.6rem;
            font-weight: 750;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }
        .kpi-note {
            margin-top: 0.22rem;
            color: #93a6bc;
            font-size: 0.76rem;
            line-height: 1.35;
        }
        .kpi-card.compact {
            min-height: 86px;
            padding: 0.8rem 0.95rem;
        }
        .kpi-card.compact .kpi-value {font-size: 1.24rem; margin-top: 0.22rem;}
        .kpi-card.compact .kpi-note {font-size: 0.72rem;}
        .kpi-card.tone-warn .kpi-value {color: #f3b45f;}
        .kpi-card.tone-danger .kpi-value {color: var(--red);}
        .kpi-card.tone-teal .kpi-value {color: #5ad9c4;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>

        /* Native Streamlit surfaces -------------------------------------- */
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            background: transparent;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 12px;
            overflow: hidden;
        }
        [data-testid="stDataFrame"] [role="columnheader"] {
            background: var(--surface-2);
            color: var(--muted);
        }
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p {
            color: var(--muted);
        }
        [data-testid="stWidgetLabel"] p {
            color: var(--ink-soft);
        }
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p {
            color: var(--ink-soft);
        }
        .stButton > button,
        .stDownloadButton > button {
            background: var(--surface-2);
            color: var(--ink-soft);
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover {
            background: #1a2a3e;
        }
        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTextInput"] input {
            background-color: var(--surface-2) !important;
            border-color: var(--line-strong) !important;
            color: var(--ink) !important;
        }
        [data-baseweb="popover"] [role="listbox"],
        [data-baseweb="menu"] {
            background: var(--surface-2);
            color: var(--ink);
        }
        [data-testid="stAlert"] {
            border-radius: 12px;
        }
        [data-testid="stDateInput"] input::-webkit-calendar-picker-indicator {
            filter: invert(0.85);
            opacity: 0.8;
            cursor: pointer;
        }
        #vg-tooltip-element {
            background: #162233 !important;
            border: 1px solid #2b3b52 !important;
            border-radius: 10px !important;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.45) !important;
            color: #e8f0fb !important;
        }
        #vg-tooltip-element h2 {
            color: #e8f0fb !important;
        }
        #vg-tooltip-element table tr td.key {
            color: #93a6bc !important;
        }
        #vg-tooltip-element table tr td.value {
            color: #e8f0fb !important;
        }

        /* Panels and chart headers ---------------------------------------- */
        div[data-testid="stVerticalBlock"][class*="st-key-panel-"] {
            padding: 1.15rem 1.25rem !important;
            border: 1px solid var(--line) !important;
            border-radius: 16px !important;
            background: var(--surface) !important;
            box-shadow: var(--shadow) !important;
        }
        .panel-head h3,
        .panel-head h3 span,
        .mini-head h4,
        .mini-head h4 span,
        .empty-state h4,
        .empty-state h4 span,
        .step-card h4,
        .step-card h4 span,
        .playbook-card h4,
        .playbook-card h4 span {padding: 0 !important;}
        .panel-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            margin: 0 0 0.75rem 0;
        }
        .panel-head h3 {
            margin: 0;
            color: var(--ink);
            font-size: 1.02rem;
            font-weight: 700;
            letter-spacing: -0.01em;
        }
        .panel-head p {
            margin: 0.22rem 0 0 0;
            color: #93a6bc;
            font-size: 0.81rem;
            line-height: 1.45;
        }
        .panel-head-right {
            flex: 0 0 auto;
            padding-top: 0.1rem;
        }
        .mini-head {margin: 0 0 0.45rem 0;}
        .mini-head h4 {
            margin: 0;
            color: #dbe7f5;
            font-size: 0.82rem;
            font-weight: 700;
        }
        .mini-head p {
            margin: 0.15rem 0 0 0;
            color: #7f93a9;
            font-size: 0.72rem;
            line-height: 1.35;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.28rem 0.6rem;
            border: 1px solid #2a405a;
            border-radius: 999px;
            background: #17263a;
            color: #8ec7ff;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            white-space: nowrap;
        }
        .chip.teal {
            border-color: #245049;
            background: #102a28;
            color: #5ad9c4;
        }
        .chart-legend {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.85rem;
            padding-top: 0.15rem;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 0.35rem;
            color: #93a6bc;
            font-size: 0.67rem;
            font-weight: 600;
            white-space: nowrap;
        }
        .legend-swatch {
            width: 9px;
            height: 9px;
            border-radius: 3px;
        }

        /* Two-column workflow alignment ---------------------------------- */
        div[data-testid="stHorizontalBlock"]:has(.st-key-panel-no-show-form) > div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"]:has(.st-key-panel-segment-form) > div[data-testid="stColumn"] {
            display: flex;
            flex-direction: column;
            align-self: stretch;
        }
        div[data-testid="stHorizontalBlock"]:has(.st-key-panel-no-show-form) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"],
        div[data-testid="stHorizontalBlock"]:has(.st-key-panel-segment-form) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"],
        div[data-testid="stHorizontalBlock"]:has(.st-key-panel-no-show-form) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stLayoutWrapper"],
        div[data-testid="stHorizontalBlock"]:has(.st-key-panel-segment-form) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stLayoutWrapper"] {
            height: 100%;
        }
        .st-key-panel-no-show-form,
        .st-key-panel-segment-form {height: 100%;}
        .st-key-panel-no-show-form > div[data-testid="stElementContainer"]:last-child,
        .st-key-panel-segment-form > div[data-testid="stElementContainer"]:last-child {
            margin-top: auto;
        }

        /* Forms ----------------------------------------------------------- */
        [data-testid="stForm"] {
            padding: 0 !important;
            border: none !important;
            background: transparent !important;
        }
        .form-section {
            margin: 0.55rem 0 0.05rem 0;
            padding-bottom: 0.35rem;
            border-bottom: 1px solid #1f2b3c;
            color: #6cb6f0;
            font-size: 0.67rem;
            font-weight: 750;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }
        .field-label {
            margin: 0.15rem 0 0.1rem 0;
            color: #c3d2e4;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .stButton > button,
        .stDownloadButton > button,
        .stFormSubmitButton > button {
            min-height: 2.45rem;
            border-radius: 10px;
            font-weight: 650;
        }
        .stButton > button,
        .stDownloadButton > button {
            border-color: #33455d;
            color: #dce8f6;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover {
            border-color: var(--blue);
            color: var(--blue);
        }
        button[kind="primary"],
        .stFormSubmitButton > button {
            border-color: var(--blue) !important;
            background: var(--blue) !important;
            color: #fff !important;
        }
        button[kind="primary"] *,
        .stFormSubmitButton > button * {
            color: #fff !important;
        }
        button[kind="primary"]:hover,
        .stFormSubmitButton > button:hover {
            border-color: #2f8dcc !important;
            background: #2f8dcc !important;
        }
        button p,
        button [data-testid="stMarkdownContainer"],
        button [data-testid="stMarkdownContainer"] p {
            color: inherit !important;
        }

        /* Callouts, empty states and notes -------------------------------- */
        .callout {
            display: flex;
            gap: 0.75rem;
            margin-top: 0.65rem;
            padding: 0.85rem 0.95rem;
            border: 1px solid #2a405a;
            border-radius: 12px;
            background: #111f30;
        }
        .callout-icon {
            flex: 0 0 auto;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            border-radius: 9px;
            background: #18324a;
            color: var(--blue);
        }
        .callout-title {
            margin-bottom: 0.15rem;
            color: #9fd0f5;
            font-size: 0.76rem;
            font-weight: 750;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .callout-text {
            color: #a9bbcf;
            font-size: 0.8rem;
            line-height: 1.5;
        }
        .callout.warning {
            border-color: #4a3820;
            background: #241c10;
        }
        .callout.warning .callout-icon {background: #3a2a14; color: #f3b45f;}
        .callout.warning .callout-title {color: #f3b45f;}
        .callout.success {
            border-color: #254a3b;
            background: #10211a;
        }
        .callout.success .callout-icon {background: #18382c; color: #5ad9a3;}
        .callout.success .callout-title {color: #5ad9a3;}

        .empty-state {
            padding: 1.2rem 1rem;
            border: 1px dashed #2a3a50;
            border-radius: 13px;
            background: #101927;
        }
        .empty-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 42px;
            height: 42px;
            margin-bottom: 0.65rem;
            border-radius: 12px;
            background: #172a3e;
            color: var(--blue);
        }
        .empty-state h4 {
            margin: 0 0 0.25rem 0;
            color: #dce8f6;
            font-size: 0.92rem;
        }
        .empty-state p {
            margin: 0;
            color: #93a6bc;
            font-size: 0.8rem;
            line-height: 1.55;
        }
        .subhead {
            margin: 1rem 0 0.45rem 0;
            color: #7f93a9;
            font-size: 0.65rem;
            font-weight: 750;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }
        .note-list {display: flex; flex-direction: column; gap: 0.55rem;}
        .note-row {
            display: flex;
            align-items: flex-start;
            gap: 0.6rem;
        }
        .note-index {
            flex: 0 0 auto;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 23px;
            height: 23px;
            border-radius: 7px;
            background: #172a3e;
            color: var(--blue);
            font-size: 0.68rem;
            font-weight: 800;
        }
        .note-row strong {
            display: block;
            color: #dbe7f5;
            font-size: 0.77rem;
        }
        .note-row p {
            margin: 0.1rem 0 0 0;
            color: #93a6bc;
            font-size: 0.75rem;
            line-height: 1.45;
        }
        .fine-print {
            margin-top: 0.7rem;
            color: #7f93a9;
            font-size: 0.71rem;
            line-height: 1.5;
        }

        /* Result presentation --------------------------------------------- */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.28rem 0.65rem;
            border-radius: 999px;
            font-size: 0.68rem;
            font-weight: 750;
            letter-spacing: 0.02em;
        }
        .badge::before {
            content: "";
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: currentColor;
        }
        .badge-low {background: #123326; color: #5ad9a3;}
        .badge-medium {background: #2e2612; color: #f5c451;}
        .badge-high {background: #351b1b; color: #ff8b82;}
        .badge-neutral {background: #17263a; color: #8ec7ff;}

        .result-card {
            --accent: var(--blue);
            margin-bottom: 0.2rem;
            padding: 1.1rem 1.15rem;
            border: 1px solid var(--line);
            border-top: 4px solid var(--accent);
            border-radius: 15px;
            background: var(--surface);
        }
        .result-card.high {
            --accent: #f0736a;
            background: linear-gradient(180deg, #1d1416 0%, var(--surface) 70%);
        }
        .result-card.medium {
            --accent: #f0a54a;
            background: linear-gradient(180deg, #1e1a11 0%, var(--surface) 70%);
        }
        .result-card.low {
            --accent: #45c98b;
            background: linear-gradient(180deg, #0f1c18 0%, var(--surface) 70%);
        }
        .result-card.segment {background: #101a29;}
        .result-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            margin-bottom: 0.55rem;
        }
        .result-kicker {
            color: #7f93a9;
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .result-title {
            color: var(--ink);
            font-size: 1.45rem;
            font-weight: 750;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }
        .result-score {
            margin-top: 0.3rem;
            color: #e8f0fb;
            font-size: 2.05rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.1;
        }
        .result-score span {
            margin-left: 0.45rem;
            color: #93a6bc;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0;
        }
        .result-description {
            margin: 0.45rem 0 0 0;
            color: #a9bbcf;
            font-size: 0.81rem;
            line-height: 1.55;
        }
        .cluster-tag {
            display: inline-flex;
            align-items: center;
            padding: 0.27rem 0.6rem;
            border-radius: 999px;
            background: var(--segment-tint, #17263a);
            color: var(--segment-color, var(--blue));
            font-size: 0.66rem;
            font-weight: 750;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .risk-meter {position: relative; margin: 0.9rem 0 0.45rem 0;}
        .risk-track {
            display: flex;
            height: 8px;
            overflow: hidden;
            border-radius: 999px;
            background: #223047;
        }
        .risk-seg.low {background: #45c98b;}
        .risk-seg.medium {background: #f0c24a;}
        .risk-seg.high {background: #f0736a;}
        .risk-pointer {
            position: absolute;
            top: -4px;
            width: 3px;
            height: 16px;
            border-radius: 2px;
            background: #e8f0fb;
            box-shadow: 0 0 0 2px #0a111c;
            transform: translateX(-50%);
        }
        .risk-labels {
            display: flex;
            justify-content: space-between;
            gap: 0.45rem;
            color: #7f93a9;
            font-size: 0.64rem;
            line-height: 1.35;
        }
        .band-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.5rem;
            margin-top: 0.35rem;
        }
        .band-item {
            padding: 0.6rem 0.65rem;
            border: 1px solid #243146;
            border-radius: 10px;
            background: #101a29;
        }
        .band-item strong {
            display: block;
            color: #dbe7f5;
            font-size: 0.73rem;
        }
        .band-item span {
            color: #7f93a9;
            font-size: 0.68rem;
        }
        .band-dot {
            display: inline-block;
            width: 7px;
            height: 7px;
            margin-right: 0.3rem;
            border-radius: 50%;
        }
        .band-dot.low {background: #45c98b;}
        .band-dot.medium {background: #f0c24a;}
        .band-dot.high {background: #f0736a;}

        /* Resource and segment lists -------------------------------------- */
        .resource-list {
            border: 1px solid #243146;
            border-radius: 12px;
            background: #101a29;
            overflow: hidden;
        }
        .resource-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            padding: 0.62rem 0.8rem;
            font-size: 0.8rem;
        }
        .resource-row + .resource-row {border-top: 1px dashed #1b2737;}
        .resource-row span {color: #93a6bc;}
        .resource-row strong {
            color: #e8f0fb;
            font-size: 0.96rem;
            font-weight: 750;
        }
        .segment-list {display: flex; flex-direction: column; gap: 0.35rem; margin-top: 0.35rem;}
        .segment-row {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            padding: 0.45rem 0.55rem;
            border: 1px solid #1f2b3c;
            border-radius: 9px;
            background: #101a29;
            font-size: 0.76rem;
        }
        .segment-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: var(--segment-color, var(--blue));
        }
        .segment-row .segment-name {
            flex: 1;
            color: #c3d2e4;
            font-weight: 600;
        }
        .segment-row .segment-value {color: #7f93a9; font-weight: 600;}
        .focus-card {
            padding: 1rem 1.05rem;
            border: 1px solid #2a405a;
            border-radius: 13px;
            background: linear-gradient(135deg, #122233 0%, #101a29 100%);
        }
        .focus-card .focus-label {
            color: #6cb6f0;
            font-size: 0.65rem;
            font-weight: 750;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }
        .focus-card .focus-title {
            margin-top: 0.4rem;
            color: #dce8f6;
            font-size: 1.1rem;
            font-weight: 750;
        }
        .focus-card .focus-value {
            margin-top: 0.2rem;
            color: #e8f0fb;
            font-size: 1.8rem;
            font-weight: 800;
            letter-spacing: -0.03em;
        }
        .focus-card p {
            margin: 0.55rem 0 0 0;
            color: #93a6bc;
            font-size: 0.78rem;
            line-height: 1.5;
        }

        /* Workflow and playbook ------------------------------------------- */
        .steps-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
        }
        .step-card {
            position: relative;
            overflow: hidden;
            min-height: 170px;
            padding: 1rem;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: var(--surface);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.24);
        }
        .step-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, var(--blue), var(--teal));
            opacity: 0.8;
        }
        .step-num {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 30px;
            height: 30px;
            margin-bottom: 0.7rem;
            border-radius: 9px;
            background: #172a3e;
            color: var(--blue);
            font-size: 0.72rem;
            font-weight: 800;
        }
        .step-card h4 {
            margin: 0 0 0.3rem 0;
            color: var(--ink);
            font-size: 0.93rem;
        }
        .step-card p {
            margin: 0;
            color: #93a6bc;
            font-size: 0.76rem;
            line-height: 1.5;
        }
        .playbook-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.85rem;
            margin-top: 0.25rem;
        }
        .playbook-card {
            padding: 0.9rem 1rem;
            border: 1px solid #243146;
            border-top: 3px solid var(--segment-color, var(--blue));
            border-radius: 12px;
            background: #101a29;
        }
        .playbook-card h4 {
            margin: 0 0 0.15rem 0;
            color: #dce8f6;
            font-size: 0.86rem;
        }
        .playbook-card .playbook-meta {
            margin-bottom: 0.45rem;
            color: #7f93a9;
            font-size: 0.68rem;
            font-weight: 600;
        }
        .playbook-card p {
            margin: 0;
            color: #93a6bc;
            font-size: 0.76rem;
            line-height: 1.5;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
        /* Sidebar --------------------------------------------------------- */
        [data-testid="stSidebar"] {
            border-right: 1px solid #1f2b3c;
            background: #0d1522;
        }
        [data-testid="stSidebar"] .block-container {
            max-width: 100%;
            padding: 1.15rem 1.1rem 2rem 1.1rem;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.25rem 0 0.15rem 0;
        }
        .brand-mark {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 44px;
            height: 44px;
            border-radius: 13px;
            background: linear-gradient(135deg, #8ec7ff 0%, #38c7b2 100%);
            color: #fff;
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.35);
        }
        .brand-title {
            color: var(--ink);
            font-size: 0.97rem;
            font-weight: 750;
            line-height: 1.2;
        }
        .brand-sub {
            margin-top: 0.1rem;
            color: #7f93a9;
            font-size: 0.7rem;
        }
        .side-label {
            margin: 1.15rem 0 0.45rem 0;
            color: #7f93a9;
            font-size: 0.64rem;
            font-weight: 750;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }
        .side-rule {
            height: 1px;
            margin: 1rem 0;
            background: #1f2b3c;
        }
        .status-pill {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.48rem 0.65rem;
            border-radius: 9px;
            font-size: 0.75rem;
            font-weight: 650;
        }
        .status-pill.ok {
            border: 1px solid #24503d;
            background: #0f2a20;
            color: #5ad9a3;
        }
        .status-pill.bad {
            border: 1px solid #5a2b2a;
            background: #2a1616;
            color: #ff8b82;
        }
        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: currentColor;
        }
        .status-pill.ok .status-dot {
            box-shadow: 0 0 0 3px rgba(90, 217, 163, 0.18);
        }
        .status-pill.bad .status-dot {
            box-shadow: 0 0 0 3px rgba(255, 139, 130, 0.18);
        }
        [data-testid="stSidebar"] [role="radiogroup"] {gap: 0.2rem;}
        [data-testid="stSidebar"] [role="radiogroup"] label {
            padding: 0.58rem 0.7rem 0.58rem 0.85rem;
            border: 1px solid transparent;
            border-radius: 10px;
            transition: background 0.15s ease, border-color 0.15s ease;
            cursor: pointer;
        }
        [data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {
            display: none;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label p {
            color: #a9bbcf;
            font-size: 0.85rem;
            font-weight: 600;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: #131f2e;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            border-color: #2a4d6e;
            background: #172a3e;
            box-shadow: inset 3px 0 0 var(--blue);
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {
            color: var(--brand);
            font-weight: 700;
        }
        .coverage-card {
            padding: 0.65rem 0.75rem;
            border: 1px solid #243146;
            border-radius: 12px;
            background: #101a29;
        }
        .coverage-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.6rem;
            padding: 0.32rem 0;
            font-size: 0.76rem;
        }
        .coverage-row + .coverage-row {border-top: 1px dashed #1b2737;}
        .coverage-row span {color: #93a6bc;}
        .coverage-row strong {color: #dce8f6; font-weight: 700;}
        .side-foot {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            font-size: 0.74rem;
            color: #7f93a9;
        }
        .side-foot a {
            color: var(--blue);
            font-weight: 650;
            text-decoration: none;
        }
        .side-foot a:hover {text-decoration: underline;}
        .side-note {
            margin-top: 0.55rem;
            color: #7f93a9;
            font-size: 0.68rem;
            line-height: 1.5;
        }

        /* Expanders and tables ------------------------------------------- */
        [data-testid="stExpander"] details {
            border: 1px solid var(--line);
            border-radius: 14px;
            background: var(--surface);
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        [data-testid="stExpander"] summary {
            padding: 0.8rem 1rem;
            font-weight: 650;
        }
        [data-testid="stExpander"] summary:hover {background: #162335;}
        [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
            padding: 0.25rem 1rem 1rem 1rem;
        }
        .expander-note {
            margin: 0 0 0.8rem 0;
            color: #93a6bc;
            font-size: 0.8rem;
            line-height: 1.5;
        }

        /* Performance table ---------------------------------------------- */
        .perf-table-wrap {
            margin-top: 0.35rem;
            overflow-x: auto;
            border: 1px solid var(--line);
            border-radius: 12px;
            background: var(--surface);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.24);
        }
        .perf-table {
            width: 100%;
            min-width: 620px;
            border-collapse: collapse;
            font-size: 0.8rem;
        }
        .perf-table th {
            padding: 0.7rem 0.9rem;
            background: #162335;
            border-bottom: 1px solid var(--line);
            color: #93a6bc;
            font-size: 0.66rem;
            font-weight: 750;
            letter-spacing: 0.05em;
            text-align: left;
            text-transform: uppercase;
        }
        .perf-table td {
            padding: 0.68rem 0.9rem;
            border-top: 1px solid #223047;
            color: #c3d2e4;
            vertical-align: top;
        }
        .perf-table tbody tr:first-child td {border-top: 0;}
        .perf-table td:first-child {
            color: var(--ink);
            font-weight: 650;
        }

        /* Footer ---------------------------------------------------------- */
        .page-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-top: 2.4rem;
            padding-top: 1rem;
            border-top: 1px solid #1f2b3c;
            color: #7f93a9;
            font-size: 0.71rem;
        }
        .page-footer strong {color: #a9bbcf; font-weight: 650;}

        /* Responsive ------------------------------------------------------ */
        @media (max-width: 1180px) {
            div[data-testid="stHorizontalBlock"]:has(.st-key-panel-no-show-form),
            div[data-testid="stHorizontalBlock"]:has(.st-key-panel-segment-form) {
                flex-direction: column;
                align-items: stretch;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-panel-no-show-form) > div[data-testid="stColumn"],
            div[data-testid="stHorizontalBlock"]:has(.st-key-panel-segment-form) > div[data-testid="stColumn"] {
                width: 100% !important;
                flex: 1 1 auto !important;
                min-width: 0 !important;
            }
            .st-key-panel-no-show-form,
            .st-key-panel-segment-form {height: auto;}
            div[data-testid="stHorizontalBlock"]:has(.st-key-panel-no-show-form) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stLayoutWrapper"],
            div[data-testid="stHorizontalBlock"]:has(.st-key-panel-segment-form) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stLayoutWrapper"] {
                height: auto;
            }
        }
        @media (max-width: 1050px) {
            div[data-testid="stHorizontalBlock"]:has(.mini-head) {
                flex-direction: column;
            }
            div[data-testid="stHorizontalBlock"]:has(.mini-head) > div[data-testid="stColumn"] {
                width: 100% !important;
                flex: 1 1 auto !important;
            }
            .st-key-panel-demand-planner div[data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]) {
                flex-direction: column;
                gap: 0.3rem !important;
            }
            .st-key-panel-demand-planner div[data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]) > div[data-testid="stColumn"] {
                width: 100% !important;
                flex: 1 1 auto !important;
            }
        }
        @media (max-width: 950px) {
            .st-key-panel-demand-settings div[data-testid="stHorizontalBlock"] {
                flex-direction: column;
                gap: 0.3rem !important;
            }
            .st-key-panel-demand-settings div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                width: 100% !important;
                flex: 1 1 auto !important;
                margin-top: 0 !important;
            }
        }
        @media (max-width: 1100px) {
            .kpi-grid.cols-4 {grid-template-columns: repeat(2, minmax(0, 1fr));}
            .kpi-grid.cols-5 {grid-template-columns: repeat(3, minmax(0, 1fr));}
            .hero-inner {flex-direction: column; align-items: flex-start;}
            .hero-tags {justify-content: flex-start; max-width: none;}
            .steps-grid {grid-template-columns: repeat(2, minmax(0, 1fr));}
        }
        @media (max-width: 850px) {
            div[data-testid="stHorizontalBlock"]:has(.st-key-panel-no-show-form) [data-testid="stHorizontalBlock"],
            div[data-testid="stHorizontalBlock"]:has(.st-key-panel-segment-form) [data-testid="stHorizontalBlock"] {
                flex-direction: column;
                gap: 0.2rem !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-panel-no-show-form) [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
            div[data-testid="stHorizontalBlock"]:has(.st-key-panel-segment-form) [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                width: 100% !important;
                flex: 1 1 auto !important;
            }
        }
        @media (max-width: 960px) {
            .perf-table-wrap {overflow: visible; border-radius: 14px;}
            .perf-table {display: block; min-width: 0;}
            .perf-table thead {display: none;}
            .perf-table tbody {display: block;}
            .perf-table tr {
                display: block;
                padding: 0.8rem 0.9rem;
                border-top: 1px solid #223047;
            }
            .perf-table tbody tr:first-child {border-top: 0;}
            .perf-table td {
                display: grid;
                grid-template-columns: 128px minmax(0, 1fr);
                gap: 0.6rem;
                padding: 0.18rem 0;
                border: 0;
            }
            .perf-table td::before {
                content: attr(data-label);
                color: #7f93a9;
                font-size: 0.64rem;
                font-weight: 750;
                letter-spacing: 0.05em;
                line-height: 1.5;
                text-transform: uppercase;
                white-space: nowrap;
            }
            .perf-table td:first-child {
                display: block;
                padding: 0 0 0.35rem 0;
                font-size: 0.9rem;
            }
            .perf-table td:first-child::before {display: none;}
        }
        @media (max-width: 760px) {
            .block-container {padding: 1rem 0.9rem 2.5rem 0.9rem;}
            .hero {padding: 1.35rem 1.2rem; border-radius: 16px;}
            .hero h1 {font-size: 1.65rem;}
            .hero p {font-size: 0.9rem;}
            .kpi-grid.cols-2,
            .kpi-grid.cols-3,
            .kpi-grid.cols-4,
            .kpi-grid.cols-5 {grid-template-columns: repeat(2, minmax(0, 1fr));}
            .section-head h2 {font-size: 1.18rem;}
            .steps-grid,
            .playbook-grid,
            .band-grid {grid-template-columns: 1fr;}
            .page-footer {flex-direction: column; align-items: flex-start;}
            .result-score {font-size: 1.75rem;}
            .panel-head,
            .result-top {flex-wrap: wrap;}
            .risk-labels {flex-wrap: wrap;}
        }
        @media (max-width: 480px) {
            .kpi-grid.cols-2,
            .kpi-grid.cols-3,
            .kpi-grid.cols-4,
            .kpi-grid.cols-5 {grid-template-columns: 1fr;}
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def api_get(api_url: str, path: str, params: dict[str, Any] | None = None) -> dict:
    response = requests.get(f"{api_url}{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def api_post(api_url: str, path: str, payload: dict[str, Any]) -> dict:
    response = requests.post(f"{api_url}{path}", json=payload, timeout=30)
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(f"API error {response.status_code}: {detail}")
    return response.json()


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------
ICONS = {
    "chart": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "calendar": (
        '<rect x="3" y="5" width="18" height="16" rx="3"/>'
        '<path d="M8 3v4M16 3v4M3 10h18"/>'
    ),
    "users": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>'
    ),
    "info": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M12 11v5M12 8h.01"/>'
    ),
    "alert": (
        '<path d="M10.3 4.1 2.8 17a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L13.7 4.1a2 2 0 0 0-3.4 0Z"/>'
        '<path d="M12 9v4M12 17h.01"/>'
    ),
    "check": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="m8.5 12.5 2.4 2.4 4.8-5.2"/>'
    ),
    "activity": '<path d="M3 12h4l2.5-7 5 14 2.5-7h4"/>',
    "hospital": (
        '<rect x="3" y="4" width="18" height="17" rx="2"/>'
        '<path d="M9 4V2h6v2M12 8v6M9 11h6M7 21v-3h10v3"/>'
    ),
}


def icon_svg(name: str, size: int = 19) -> str:
    path = ICONS.get(name, ICONS["info"])
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{path}</svg>'
    )


def hero(title: str, subtitle: str, eyebrow: str, tags: list[str]) -> None:
    tag_html = "".join(f'<span class="hero-tag">{escape(tag)}</span>' for tag in tags)
    st.markdown(
        f"""
        <section class="hero">
            <div class="hero-inner">
                <div class="hero-copy">
                    <div class="hero-eyebrow">
                        <span class="hero-pulse"></span>{escape(eyebrow)}
                    </div>
                    <h1>{escape(title)}</h1>
                    <p>{escape(subtitle)}</p>
                </div>
                <div class="hero-tags">{tag_html}</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, note: str = "", kicker: str = "") -> None:
    kicker_html = (
        f'<div class="section-kicker">{escape(kicker)}</div>' if kicker else ""
    )
    note_html = f"<p>{escape(note)}</p>" if note else ""
    st.markdown(
        f'<div class="section-head">{kicker_html}<h2>{escape(title)}</h2>{note_html}</div>',
        unsafe_allow_html=True,
    )


def panel_heading(title: str, note: str = "", right: str = "") -> None:
    note_html = f"<p>{escape(note)}</p>" if note else ""
    right_html = f'<div class="panel-head-right">{right}</div>' if right else ""
    st.markdown(
        f'<div class="panel-head"><div><h3>{escape(title)}</h3>{note_html}</div>{right_html}</div>',
        unsafe_allow_html=True,
    )


def mini_title(title: str, note: str = "") -> None:
    note_html = f"<p>{escape(note)}</p>" if note else ""
    st.markdown(
        f'<div class="mini-head"><h4>{escape(title)}</h4>{note_html}</div>',
        unsafe_allow_html=True,
    )


def metric_grid(
    items: list[tuple[Any, ...]], columns: int = 4, compact: bool = False
) -> None:
    cards = []
    for item in items:
        label, value, note = item[0], item[1], item[2] if len(item) > 2 else ""
        tone = item[3] if len(item) > 3 else ""
        classes = "kpi-card"
        if compact:
            classes += " compact"
        if tone:
            classes += f" tone-{tone}"
        note_html = f'<div class="kpi-note">{escape(str(note))}</div>' if note else ""
        cards.append(
            f'<div class="{classes}"><div class="kpi-label">{escape(str(label))}</div>'
            f'<div class="kpi-value">{escape(str(value))}</div>{note_html}</div>'
        )
    st.markdown(
        f'<div class="kpi-grid cols-{columns}">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def form_section(label: str) -> None:
    st.markdown(f'<div class="form-section">{escape(label)}</div>', unsafe_allow_html=True)


def chip(text: str, tone: str = "") -> str:
    classes = "chip" + (f" {tone}" if tone else "")
    return f'<span class="{classes}">{escape(text)}</span>'


def status_pill(text: str, tone: str = "ok") -> str:
    return (
        f'<div class="status-pill {tone}"><span class="status-dot"></span>'
        f"<span>{escape(text)}</span></div>"
    )


def chart_legend(items: list[tuple[str, str]]) -> str:
    entries = "".join(
        f'<span class="legend-item"><span class="legend-swatch" '
        f'style="background:{color}"></span>{escape(label)}</span>'
        for label, color in items
    )
    return f'<div class="chart-legend">{entries}</div>'


def callout(title: str, text: str, tone: str = "info") -> str:
    icon = {"warning": "alert", "success": "check"}.get(tone, "info")
    return (
        f'<div class="callout {tone}"><div class="callout-icon">{icon_svg(icon)}</div>'
        f'<div><div class="callout-title">{escape(title)}</div>'
        f'<div class="callout-text">{escape(text)}</div></div></div>'
    )


def empty_state(title: str, text: str, icon: str = "calendar") -> str:
    return (
        f'<div class="empty-state"><div class="empty-icon">{icon_svg(icon, 21)}</div>'
        f"<h4>{escape(title)}</h4><p>{escape(text)}</p></div>"
    )


def subhead(text: str) -> None:
    st.markdown(f'<div class="subhead">{escape(text)}</div>', unsafe_allow_html=True)


def note_list(items: list[tuple[str, str]]) -> str:
    rows = "".join(
        f'<div class="note-row"><span class="note-index">{index}</span>'
        f"<div><strong>{escape(title)}</strong><p>{escape(text)}</p></div></div>"
        for index, (title, text) in enumerate(items, start=1)
    )
    return f'<div class="note-list">{rows}</div>'


def resource_list(items: list[tuple[str, Any]]) -> str:
    rows = "".join(
        f'<div class="resource-row"><span>{escape(label)}</span>'
        f"<strong>{escape(str(value))}</strong></div>"
        for label, value in items
    )
    return f'<div class="resource-list">{rows}</div>'


def band_legend(low_max: float, high_min: float) -> str:
    return (
        f'<div class="band-grid">'
        f'<div class="band-item"><strong><span class="band-dot low"></span>Low</strong>'
        f"<span>&lt; {low_max:.1%} probability</span></div>"
        f'<div class="band-item"><strong><span class="band-dot medium"></span>Medium</strong>'
        f"<span>{low_max:.1%} – {high_min:.1%}</span></div>"
        f'<div class="band-item"><strong><span class="band-dot high"></span>High</strong>'
        f"<span>≥ {high_min:.1%} probability</span></div></div>"
    )


def risk_result_card(result: dict) -> str:
    probability = max(0.0, min(float(result["no_show_probability"]), 1.0))
    level = str(result["risk_level"])
    tone = level.lower()
    bands = result["risk_bands"]
    low_max = float(bands["low_max"])
    high_min = float(bands["high_min"])
    pointer = probability * 100
    return f"""
    <div class="result-card {escape(tone)}">
        <div class="result-top">
            <span class="badge badge-{escape(tone)}">{escape(level)} risk</span>
            <span class="result-kicker">Calibrated logistic regression</span>
        </div>
        <div class="result-title">{escape(str(result["prediction"]))}</div>
        <div class="result-score">{probability:.1%}<span>estimated no-show probability</span></div>
        <div class="risk-meter">
            <div class="risk-track">
                <div class="risk-seg low" style="width:{low_max * 100:.2f}%"></div>
                <div class="risk-seg medium" style="width:{(high_min - low_max) * 100:.2f}%"></div>
                <div class="risk-seg high" style="width:{(1 - high_min) * 100:.2f}%"></div>
            </div>
            <div class="risk-pointer" style="left:{pointer:.2f}%"></div>
        </div>
        <div class="risk-labels">
            <span>0%</span>
            <span>Low &lt; {low_max:.1%}</span>
            <span>High ≥ {high_min:.1%}</span>
            <span>100%</span>
        </div>
    </div>
    """


def segment_result_card(
    result: dict, color_map: dict[str, str]
) -> str:
    label = str(result["segment"])
    color = color_map.get(label, "#4da3e8")
    return f"""
    <div class="result-card segment" style="--segment-color:{color}; border-top-color:{color};">
        <div class="result-top">
            <span class="cluster-tag" style="--segment-color:{color}; --segment-tint:{color}18;">
                Cluster {escape(str(result["cluster"]))}
            </span>
            <span class="result-kicker">K-Means match</span>
        </div>
        <div class="result-title">{escape(label)}</div>
        <p class="result-description">{escape(str(result["description"]))}</p>
    </div>
    """


def segment_list_html(
    segments: pd.DataFrame, color_map: dict[str, str]
) -> str:
    rows = "".join(
        f'<div class="segment-row"><span class="segment-dot" '
        f'style="--segment-color:{color_map.get(str(row["label"]), "#4da3e8")}"></span>'
        f'<span class="segment-name">{escape(str(row["label"]))}</span>'
        f'<span class="segment-value">{float(row["share"]):.1%}</span></div>'
        for _, row in segments.iterrows()
    )
    return f'<div class="segment-list">{rows}</div>'


def steps_grid(steps: list[tuple[str, str, str]]) -> None:
    cards = "".join(
        f'<div class="step-card"><div class="step-num">{escape(number)}</div>'
        f"<h4>{escape(title)}</h4><p>{escape(text)}</p></div>"
        for number, title, text in steps
    )
    st.markdown(f'<div class="steps-grid">{cards}</div>', unsafe_allow_html=True)


def performance_table(rows: list[dict[str, str]]) -> None:
    head = "".join(f"<th>{escape(key)}</th>" for key in rows[0])
    body = "".join(
        "<tr>"
        + "".join(
            f'<td data-label="{escape(key)}">{escape(str(value))}</td>'
            for key, value in row.items()
        )
        + "</tr>"
        for row in rows
    )
    st.markdown(
        f'<div class="perf-table-wrap"><table class="perf-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def playbook_grid(
    segments: list[dict], color_map: dict[str, str]
) -> None:
    cards = "".join(
        f'<div class="playbook-card" style="--segment-color:'
        f'{color_map.get(str(segment["label"]), "#4da3e8")}">'
        f'<h4>{escape(str(segment["label"]))}</h4>'
        f'<div class="playbook-meta">{int(segment["patients"]):,} patients · '
        f'{float(segment["share"]):.1%} of cohort</div>'
        f'<p>{escape(str(segment["description"]))}</p></div>'
        for segment in segments
    )
    st.markdown(f'<div class="playbook-grid">{cards}</div>', unsafe_allow_html=True)


def segment_colors(labels: list[str]) -> dict[str, str]:
    preferred = {
        "Older chronic patients": "#5aa9f0",
        "Long-lead bookers": "#f0a54a",
        "Young low-contact patients": "#45c98b",
        "Frequent attenders": "#b39ddb",
    }
    palette = ["#5aa9f0", "#45c98b", "#f0a54a", "#b39ddb", "#e58aa5", "#38c7b2"]
    mapping: dict[str, str] = {}
    for index, label in enumerate(labels):
        mapping[label] = preferred.get(label, palette[index % len(palette)])
    return mapping


def month_year(value: str) -> str:
    return pd.to_datetime(value).strftime("%b %Y")


def page_footer() -> None:
    st.markdown(
        """
        <div class="page-footer">
            <span><strong>Smart Healthcare Analytics</strong> · operational decision support</span>
            <span>Planning estimates only · not clinical advice</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------
def polish_chart(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure(background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(
            domain=False,
            ticks=False,
            labelColor="#8fa3ba",
            labelFontSize=11,
            titleColor="#8fa3ba",
            titleFontSize=11,
            titleFontWeight="normal",
            gridColor="#1b2737",
            gridWidth=1,
            labelPadding=6,
            titlePadding=8,
        )
        .configure_legend(disable=True)
        .configure_title(color="#e8f0fb", fontSize=12, fontWeight=600, anchor="start")
    )


def history_chart(history: list[dict]) -> alt.Chart:
    frame = pd.DataFrame(history)
    frame["date"] = pd.to_datetime(frame["date"])
    frame["rolling_7d"] = frame["patients"].rolling(7, min_periods=1).mean()
    base = (
        alt.Chart(frame)
        .mark_area(color="#2a5d88", opacity=0.55, line=False, interpolate="monotone")
        .encode(
            x=alt.X(
                "date:T",
                title=None,
                axis=alt.Axis(format="%b %Y", labelAngle=0, tickCount=8, grid=False),
            ),
            y=alt.Y(
                "patients:Q",
                title="Patients / day",
                scale=alt.Scale(zero=True, padding=10),
                axis=alt.Axis(grid=True, tickCount=5),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Date", format="%d %b %Y"),
                alt.Tooltip("patients:Q", title="Patients"),
            ],
        )
    )
    trend = (
        alt.Chart(frame)
        .mark_line(color="#8ec7ff", strokeWidth=2.3, interpolate="monotone")
        .encode(
            x="date:T",
            y="rolling_7d:Q",
            tooltip=[
                alt.Tooltip("date:T", title="Date", format="%d %b %Y"),
                alt.Tooltip("rolling_7d:Q", title="7-day average", format=".1f"),
            ],
        )
    )
    return polish_chart((base + trend).properties(height=305))


def eda_bar_chart(
    labels: list[str],
    values: list[float],
    *,
    color: str,
    height: int = 205,
) -> alt.Chart:
    frame = pd.DataFrame({"label": labels, "rate": values})
    max_rate = max(values) if values else 0.0
    y_max = max(max_rate * 1.28, 0.05)
    bars = (
        alt.Chart(frame)
        .mark_bar(
            color=color,
            cornerRadiusTopLeft=3,
            cornerRadiusTopRight=3,
            size=46,
        )
        .encode(
            x=alt.X(
                "label:N",
                title=None,
                sort=labels,
                axis=alt.Axis(labelAngle=0, labelFontSize=10, grid=False),
            ),
            y=alt.Y(
                "rate:Q",
                title=None,
                scale=alt.Scale(domain=[0, y_max]),
                axis=alt.Axis(format="%", grid=True, tickCount=4),
            ),
            tooltip=[
                alt.Tooltip("label:N", title="Group"),
                alt.Tooltip("rate:Q", title="No-show rate", format=".1%"),
            ],
        )
    )
    labels_layer = (
        alt.Chart(frame)
        .mark_text(dy=-8, color="#a9bbcf", fontSize=10, fontWeight=600)
        .encode(
            x=alt.X("label:N", title=None, sort=labels),
            y="rate:Q",
            text=alt.Text("rate:Q", format=".1%"),
        )
    )
    return polish_chart((bars + labels_layer).properties(height=height))


def forecast_chart(frame: pd.DataFrame) -> alt.Chart:
    band = (
        alt.Chart(frame)
        .mark_area(color="#2a5d88", opacity=0.38, line=False, interpolate="monotone")
        .encode(
            x=alt.X(
                "date:T",
                title=None,
                axis=alt.Axis(
                    format="%a %d %b",
                    labelAngle=0,
                    tickCount=min(8, len(frame)),
                    grid=False,
                ),
            ),
            y=alt.Y(
                "lower:Q",
                title="Patients / day",
                scale=alt.Scale(zero=False, padding=12),
                axis=alt.Axis(grid=True, tickCount=5),
            ),
            y2=alt.Y2("upper:Q"),
        )
    )
    line = (
        alt.Chart(frame)
        .mark_line(
            color="#8ec7ff",
            strokeWidth=2.4,
            interpolate="monotone",
            point=alt.OverlayMarkDef(size=42, color="#8ec7ff"),
        )
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("predicted_patients:Q", title="Patients / day"),
            tooltip=[
                alt.Tooltip("date:T", title="Date", format="%a %d %b %Y"),
                alt.Tooltip("weekday:N", title="Weekday"),
                alt.Tooltip("predicted_patients:Q", title="Predicted", format=".1f"),
                alt.Tooltip("lower:Q", title="Lower 95%", format=".1f"),
                alt.Tooltip("upper:Q", title="Upper 95%", format=".1f"),
            ],
        )
    )
    return polish_chart((band + line).properties(height=320))


def department_mix_chart(breakdown: pd.DataFrame) -> alt.Chart:
    max_value = float(breakdown["expected_patients"].max()) if len(breakdown) else 1.0
    bars = (
        alt.Chart(breakdown)
        .mark_bar(
            color="#5aa9f0",
            cornerRadiusTopRight=4,
            cornerRadiusBottomRight=4,
            size=22,
        )
        .encode(
            y=alt.Y(
                "department:N",
                title=None,
                sort="-x",
                axis=alt.Axis(labelLimit=175, labelFontSize=10.5, grid=False),
            ),
            x=alt.X(
                "expected_patients:Q",
                title=None,
                scale=alt.Scale(domain=[0, max_value * 1.18]),
                axis=alt.Axis(grid=True, tickCount=4),
            ),
            tooltip=[
                alt.Tooltip("department:N", title="Department"),
                alt.Tooltip("expected_patients:Q", title="Patients", format=".2f"),
                alt.Tooltip("share:Q", title="Share", format=".1%"),
            ],
        )
    )
    labels = (
        alt.Chart(breakdown)
        .mark_text(
            align="left",
            dx=5,
            color="#a9bbcf",
            fontSize=10,
            fontWeight=600,
        )
        .encode(
            y=alt.Y("department:N", sort="-x"),
            x="expected_patients:Q",
            text=alt.Text("expected_patients:Q", format=".1f"),
        )
    )
    return polish_chart((bars + labels).properties(height=285))


def segment_chart(
    frame: pd.DataFrame,
    field: str,
    color_map: dict[str, str],
    *,
    label_field: str,
    label_format: str,
    axis_format: str,
    field_title: str,
    height: int = 245,
) -> alt.Chart:
    max_value = float(frame[field].max()) if len(frame) else 1.0
    tooltip = [
        alt.Tooltip("label:N", title="Segment"),
        alt.Tooltip(f"{field}:Q", title=field_title, format=axis_format),
        alt.Tooltip("share:Q", title="Share of cohort", format=".1%"),
    ]
    bars = (
        alt.Chart(frame)
        .mark_bar(
            cornerRadiusTopRight=4,
            cornerRadiusBottomRight=4,
            size=24,
        )
        .encode(
            y=alt.Y(
                "label:N",
                title=None,
                sort="-x",
                axis=alt.Axis(labelLimit=160, labelFontSize=10.5, grid=False),
            ),
            x=alt.X(
                f"{field}:Q",
                title=None,
                scale=alt.Scale(domain=[0, max_value * 1.18]),
                axis=alt.Axis(format=axis_format, grid=True, tickCount=4),
            ),
            color=alt.Color(
                "label:N",
                scale=alt.Scale(
                    domain=list(color_map.keys()),
                    range=list(color_map.values()),
                ),
                legend=None,
            ),
            tooltip=tooltip,
        )
    )
    labels = (
        alt.Chart(frame)
        .mark_text(
            align="left",
            dx=5,
            color="#a9bbcf",
            fontSize=10,
            fontWeight=600,
        )
        .encode(
            y=alt.Y("label:N", sort="-x"),
            x=f"{field}:Q",
            text=alt.Text(f"{label_field}:Q", format=label_format),
        )
    )
    return polish_chart((bars + labels).properties(height=height))


# ---------------------------------------------------------------------------
# Sidebar and shared service metadata
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"""
        <div class="brand">
            <div class="brand-mark">{icon_svg("hospital", 23)}</div>
            <div>
                <div class="brand-title">Smart Healthcare</div>
                <div class="brand-sub">Analytics workspace</div>
            </div>
        </div>
        <div class="side-label">Service status</div>
        """,
        unsafe_allow_html=True,
    )

    try:
        health = requests.get(f"{api_url}/health", timeout=5)
        health.raise_for_status()
        health_data = health.json()
        models_online = sum(
            1 for loaded in health_data.get("models_loaded", {}).values() if loaded
        )
        service_online = True
        st.markdown(
            status_pill(f"{models_online} models online", "ok"),
            unsafe_allow_html=True,
        )
    except Exception:
        service_online = False
        st.markdown(
            status_pill("Service unavailable", "bad"),
            unsafe_allow_html=True,
        )

if not service_online:
    hero(
        "Prediction service unavailable",
        "The analytics service is temporarily offline. Your data has not been changed. "
        "Retry the connection in a moment.",
        "Connection status",
        ["Demand", "No-show", "Segments"],
    )
    st.markdown(
        callout(
            "Temporary outage",
            "This usually clears on its own while the prediction service restarts. "
            "If the issue continues, contact the workspace administrator.",
            tone="warning",
        ),
        unsafe_allow_html=True,
    )
    if st.button("Retry connection", type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

try:
    options = api_get(api_url, "/options")
    metadata = api_get(api_url, "/metadata")
except Exception as error:
    print(f"[dashboard] Could not load API metadata: {error}")
    hero(
        "Prediction service unavailable",
        "The analytics service could not load its model metadata. "
        "Retry the connection in a moment.",
        "Connection status",
        ["Demand", "No-show", "Segments"],
    )
    st.markdown(
        callout(
            "Metadata not available",
            "The service is running but its model metadata is not ready yet. "
            "Please retry shortly.",
            tone="warning",
        ),
        unsafe_allow_html=True,
    )
    if st.button("Retry connection", type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

demand_meta = metadata["demand"]
no_show_meta = metadata["no_show"]
segments_meta = metadata["segments"]
demand_metrics = demand_meta["metrics"]["department_day"]
logistic_metrics = no_show_meta["metrics"]["logistic"]
tree_metrics = no_show_meta["metrics"]["tree"]

with st.sidebar:
    st.markdown('<div class="side-label">Workspace</div>', unsafe_allow_html=True)
    page = st.radio("Workspace", PAGES, label_visibility="collapsed")
    st.markdown('<div class="side-rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="side-label">Data coverage</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="coverage-card">
            <div class="coverage-row"><span>Demand history</span><strong>{demand_meta["n_days"]:,} days</strong></div>
            <div class="coverage-row"><span>Appointments</span><strong>{no_show_meta["n_records"]:,}</strong></div>
            <div class="coverage-row"><span>Patient profiles</span><strong>{segments_meta["n_patients"]:,}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-rule"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="side-note">Demand {month_year(demand_meta["data_start"])} – '
        f'{month_year(demand_meta["data_end"])}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="side-note">Model build '
        f'{pd.to_datetime(demand_meta["trained_at"]).strftime("%d %b %Y")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="side-note">Planning estimates only · not clinical advice.</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Hospital Overview
# ---------------------------------------------------------------------------
if page == "Hospital Overview":
    hero(
        "Smart Healthcare Analytics",
        "Forecast patient demand, flag appointment no-show risk, and segment patients "
        "for operational planning — one prediction service, three model families.",
        "Operations intelligence",
        ["Demand forecasting", "No-show risk", "Patient segmentation"],
    )

    metric_grid(
        [
            (
                "Average daily demand",
                f"{demand_meta['mean_daily_demand']:.1f}",
                "patients per day",
            ),
            (
                "Department demand R²",
                f"{demand_metrics['R²']:.3f}",
                "Linear Regression · test set",
            ),
            (
                "Historical no-show rate",
                f"{no_show_meta['positive_rate']:.1%}",
                f"{no_show_meta['n_records']:,} appointments",
            ),
            (
                "Patients segmented",
                f"{segments_meta['n_patients']:,}",
                f"K-Means · {segments_meta['k']} segments",
            ),
        ]
    )

    with st.container(border=True, key="panel-overview-history"):
        panel_heading(
            "Patient demand history",
            f"Daily arrivals from {month_year(demand_meta['data_start'])} to "
            f"{month_year(demand_meta['data_end'])}; the light-blue line is the 7-day rolling average.",
            right=chart_legend(
                [("Daily volume", "#2a5d88"), ("7-day average", "#8ec7ff")]
            ),
        )
        st.altair_chart(history_chart(demand_meta["history"]), width="stretch")

    with st.container(border=True, key="panel-overview-noshow"):
        panel_heading(
            "No-show patterns",
            "Historical rates from the appointment dataset. Both views use the same denominator.",
            right=chip("Appointment cohort", "teal"),
        )
        sms_eda = no_show_meta["eda"]["no_show_rate_by_sms"]
        lead_eda = no_show_meta["eda"]["no_show_rate_by_lead_bin"]
        lead_labels = [
            "Same day",
            "1-3 days",
            "4-7 days",
            "8-14 days",
            "15-30 days",
            "31+ days",
        ]
        chart_cols = st.columns(2, gap="large")
        with chart_cols[0]:
            mini_title("Reminder channel", "No-show rate with and without an SMS reminder.")
            st.altair_chart(
                eda_bar_chart(
                    ["No SMS", "SMS sent"],
                    [float(sms_eda["0"]), float(sms_eda["1"])],
                    color="#38c7b2",
                ),
                width="stretch",
            )
        with chart_cols[1]:
            mini_title("Booking lead time", "No-show rate by days between booking and visit.")
            st.altair_chart(
                eda_bar_chart(
                    lead_labels,
                    [float(lead_eda[label]) for label in lead_labels],
                    color="#f0a54a",
                ),
                width="stretch",
            )

    section_header(
        "Model performance",
        "Held-out test metrics stored alongside each model artifact.",
        "Model evaluation",
    )
    performance_table(
        [
            {
                "Model": "Linear Regression",
                "Operational task": "Department demand",
                "Headline score": f"R² {demand_metrics['R²']:.3f}",
                "Error / threshold": f"MAE {demand_metrics['MAE']:.2f} / dept-day",
            },
            {
                "Model": "Logistic Regression",
                "Operational task": "No-show probability",
                "Headline score": f"ROC-AUC {logistic_metrics['roc_auc']:.3f}",
                "Error / threshold": (
                    f"Recall {logistic_metrics['recall']:.1%} @ "
                    f"{logistic_metrics['threshold']:.1%} threshold"
                ),
            },
            {
                "Model": "Decision Tree",
                "Operational task": "Appointment classification",
                "Headline score": f"ROC-AUC {tree_metrics['roc_auc']:.3f}",
                "Error / threshold": (
                    f"F1 {tree_metrics['f1']:.3f} @ "
                    f"{tree_metrics['threshold']:.1%} threshold"
                ),
            },
            {
                "Model": "K-Means",
                "Operational task": "Patient segmentation",
                "Headline score": f"Silhouette {segments_meta['silhouette']:.3f}",
                "Error / threshold": f"k={segments_meta['k']} · {segments_meta['n_patients']:,} patients",
            },
        ]
    )

    section_header(
        "How the pieces fit",
        "From raw records to an operational decision in four steps.",
        "Workflow",
    )
    steps_grid(
        [
            (
                "01",
                "Data",
                "Patient-flow records power demand forecasts; appointment records power "
                "no-show models and patient segmentation.",
            ),
            (
                "02",
                "Notebooks",
                "Three training notebooks cover feature engineering, evaluation, "
                "calibration and model selection.",
            ),
            (
                "03",
                "FastAPI",
                "A typed prediction service loads the joblib artifacts and exposes "
                "demand, no-show and segmentation endpoints.",
            ),
            (
                "04",
                "Streamlit",
                "This workspace turns the API into what-if planning, risk scoring and "
                "segment lookup for operational teams.",
            ),
        ]
    )

    with st.expander("Technical details", icon=":material/code:"):
        st.markdown(
            """
            **Demand** — department-day Linear Regression with calendar features.
            The API aggregates department forecasts into a hospital total and derives
            a 95% interval from training residuals.

            **No-show** — sigmoid-calibrated Logistic Regression and a depth-6 Decision
            Tree, both class-balanced and using validation-selected F1 thresholds.

            **Segmentation** — 5-feature K-Means on patient-level appointment history.
            No-show rate is used only for post-hoc profiling, never as a clustering feature.
            """
        )
        st.markdown(
            "**Service** — the dashboard reads predictions and metadata from the "
            "FastAPI service at runtime. Model artifacts and thresholds are versioned "
            "with the deployment."
        )

# ---------------------------------------------------------------------------
# Demand & Staffing Planner
# ---------------------------------------------------------------------------
elif page == "Demand & Staffing Planner":
    hero(
        "Demand & Staffing Planner",
        "Department-aware patient-volume estimates with a 95% planning interval "
        "and a transparent staffing plan.",
        "Capacity planning",
        ["14-day horizon", "95% planning interval", "Staffing ratios"],
    )

    default_start = pd.to_datetime(demand_meta["data_end"]).date() + timedelta(days=1)
    with st.container(border=True, key="panel-demand-settings"):
        panel_heading(
            "Forecast settings",
            "Choose the planning window and scope. Results update automatically.",
        )
        controls = st.columns([1, 1, 1.25], vertical_alignment="bottom", gap="medium")
        with controls[0]:
            start_date = st.date_input(
                "Start date", value=default_start, format="DD/MM/YYYY"
            )
        with controls[1]:
            horizon = st.slider(
                "Horizon (days)",
                min_value=7,
                max_value=30,
                value=14,
            )
        with controls[2]:
            department = st.selectbox(
                "Department",
                options["departments"],
                index=0,
                help=(
                    "Choose All departments for a hospital-wide plan, or one department "
                    "for a focused plan."
                ),
            )

    try:
        forecast_data = api_get(
            api_url,
            "/forecast/demand",
            params={
                "start_date": start_date.isoformat(),
                "days": horizon,
                "department": department,
            },
        )
    except Exception as error:
        print(f"[dashboard] Could not load the forecast: {error}")
        st.error(
            "The forecast could not be loaded right now. Adjust the settings or "
            "retry in a moment."
        )
        st.stop()

    rows = []
    for item in forecast_data["forecast"]:
        rows.append(
            {
                "date": item["forecast_date"],
                "weekday": item["weekday"],
                "predicted_patients": item["predicted_patients"],
                "lower": item["prediction_interval"][0],
                "upper": item["prediction_interval"][1],
                "expected_admissions": item["expected_admissions"],
                "exam_rooms": item["resource_plan"]["exam_rooms"],
                "beds": item["resource_plan"]["beds"],
                "doctors": item["resource_plan"]["doctors"],
                "nurses": item["resource_plan"]["nurses"],
                "support_staff": item["resource_plan"]["support_staff"],
            }
        )
    forecast_frame = pd.DataFrame(rows)
    forecast_frame["date"] = pd.to_datetime(forecast_frame["date"])
    summary = forecast_data["summary"]
    first_interval = forecast_data["forecast"][0]["prediction_interval"]
    first_day = forecast_frame["date"].min().strftime("%d %b")
    last_day = forecast_frame["date"].max().strftime("%d %b %Y")

    metric_grid(
        [
            (
                "Expected volume",
                f"{summary['total_predicted_patients']:.1f}",
                f"patients over {horizon} days",
            ),
            (
                "Average daily demand",
                f"{summary['average_daily_patients']:.1f}",
                "patients per day",
            ),
            (
                "Peak day",
                f"{summary['peak_patients']:.1f}",
                pd.to_datetime(summary["peak_date"]).strftime("%a, %d %b"),
            ),
            (
                "95% planning range",
                f"{first_interval[0]:.0f}–{first_interval[1]:.0f}",
                f"patients on {first_day}",
            ),
        ]
    )

    with st.container(border=True, key="panel-demand-chart"):
        panel_heading(
            "Forecast trajectory",
            f"{department} · {first_day} to {last_day}",
            right=chart_legend(
                [("Predicted patients", "#8ec7ff"), ("95% interval", "#2a5d88")]
            ),
        )
        st.altair_chart(forecast_chart(forecast_frame), width="stretch")

    with st.container(border=True, key="panel-demand-planner"):
        planner_head, planner_control = st.columns(
            [2.2, 1], vertical_alignment="top", gap="large"
        )
        with planner_head:
            panel_heading(
                "Day planner",
                "Inspect one forecast day, its department mix and the resulting staffing plan.",
            )
        with planner_control:
            inspect_date = st.selectbox(
                "Forecast day",
                options=forecast_frame["date"].dt.date.tolist(),
                format_func=lambda value: pd.Timestamp(value).strftime(
                    "%a, %d %b %Y"
                ),
            )
        selected_row = next(
            item
            for item in forecast_data["forecast"]
            if item["forecast_date"] == inspect_date.isoformat()
        )
        selected_low, selected_high = selected_row["prediction_interval"]
        metric_grid(
            [
                (
                    "Predicted patients",
                    f"{selected_row['predicted_patients']:.1f}",
                    pd.Timestamp(inspect_date).strftime("%A"),
                ),
                (
                    "95% planning interval",
                    f"{selected_low:.0f}–{selected_high:.0f}",
                    "patients on this day",
                ),
                (
                    "Expected admissions",
                    f"{selected_row['expected_admissions']:.1f}",
                    "from the predicted volume",
                ),
            ],
            columns=3,
            compact=True,
        )

        detail_left, detail_right = st.columns([1.2, 1], gap="large")
        breakdown = pd.DataFrame(selected_row["department_breakdown"])
        with detail_left:
            mini_title(
                "Department mix",
                "Expected patients by department for the selected day.",
            )
            if department == ALL_DEPARTMENTS:
                st.altair_chart(
                    department_mix_chart(breakdown), width="stretch"
                )
            else:
                focus = breakdown.iloc[0]
                st.markdown(
                    f"""
                    <div class="focus-card">
                        <div class="focus-label">Department focus</div>
                        <div class="focus-title">{escape(str(focus["department"]))}</div>
                        <div class="focus-value">{float(focus["expected_patients"]):.1f}</div>
                        <p>expected patients on this day. Select <strong>All departments</strong>
                        in the forecast settings to see the hospital-wide mix.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        with detail_right:
            mini_title(
                "Resource plan",
                "Minimum one unit per category; staffing scales with volume.",
            )
            plan = selected_row["resource_plan"]
            st.markdown(
                resource_list(
                    [
                        ("Exam rooms", plan["exam_rooms"]),
                        ("Beds", plan["beds"]),
                        ("Doctors", plan["doctors"]),
                        ("Nurses", plan["nurses"]),
                        ("Support staff", plan["support_staff"]),
                    ]
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                '<p class="fine-print">Beds cover expected admissions with a buffer; '
                "the other ratios are applied directly to predicted patient volume.</p>",
                unsafe_allow_html=True,
            )

    section_header(
        "Forecast table",
        "Daily predictions, planning intervals and resource requirements for export.",
        "Planning export",
    )
    display_frame = forecast_frame.copy()
    display_frame["date"] = display_frame["date"].dt.strftime("%Y-%m-%d")
    display_frame = display_frame.rename(
        columns={
            "date": "Date",
            "weekday": "Weekday",
            "predicted_patients": "Predicted patients",
            "lower": "Lower 95%",
            "upper": "Upper 95%",
            "expected_admissions": "Expected admissions",
            "exam_rooms": "Exam rooms",
            "beds": "Beds",
            "doctors": "Doctors",
            "nurses": "Nurses",
            "support_staff": "Support staff",
        }
    )
    st.dataframe(
        display_frame,
        width="stretch",
        hide_index=True,
        height=min(560, 42 + 35 * len(display_frame)),
        column_config={
            "Predicted patients": st.column_config.NumberColumn(format="%.1f"),
            "Lower 95%": st.column_config.NumberColumn(format="%.1f"),
            "Upper 95%": st.column_config.NumberColumn(format="%.1f"),
            "Expected admissions": st.column_config.NumberColumn(format="%.1f"),
            "Exam rooms": st.column_config.NumberColumn(format="%d"),
            "Beds": st.column_config.NumberColumn(format="%d"),
            "Doctors": st.column_config.NumberColumn(format="%d"),
            "Nurses": st.column_config.NumberColumn(format="%d"),
            "Support staff": st.column_config.NumberColumn(format="%d"),
        },
    )
    table_footer = st.columns([2.4, 1], vertical_alignment="center", gap="large")
    with table_footer[0]:
        st.caption(
            "Every row includes the prediction interval and the staffing plan for that day."
        )
    with table_footer[1]:
        st.download_button(
            "Download CSV",
            display_frame.to_csv(index=False).encode("utf-8"),
            file_name="demand_forecast.csv",
            mime="text/csv",
            width="stretch",
        )

    assumptions = forecast_data["assumptions"]
    resource_assumptions = assumptions["resources"]
    st.markdown(
        callout(
            "Planning assumptions",
            f"Admission rate {assumptions['admission_rate']:.1%}; "
            f"1 doctor per {resource_assumptions['patients_per_doctor']} patients; "
            f"1 nurse per {resource_assumptions['patients_per_nurse']} patients; "
            f"{resource_assumptions['bed_buffer']:.2f}× bed buffer. "
            "The 95% interval is estimated from training residuals.",
        ),
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Appointment Risk Check
# ---------------------------------------------------------------------------
elif page == "Appointment Risk Check":
    hero(
        "Appointment Risk Check",
        "Score a single appointment with a calibrated Logistic Regression and compare "
        "the result with a Decision Tree classifier.",
        "Appointment operations",
        ["Calibrated probability", "Tree comparison", "Outreach guidance"],
    )

    form_col, result_col = st.columns([1.02, 1], gap="large")

    with form_col:
        with st.container(border=True, key="panel-no-show-form"):
            panel_heading(
                "Appointment profile",
                "All inputs feed both classification models.",
            )
            with st.form("no_show_form", border=False):
                patient_row = st.columns([1.25, 1], gap="medium")
                with patient_row[0]:
                    age = st.slider(
                        "Patient age", min_value=0, max_value=100, value=45
                    )
                with patient_row[1]:
                    gender = st.segmented_control(
                        "Gender",
                        options["genders"],
                        default="F",
                        selection_mode="single",
                        width="stretch",
                    )

                form_section("Appointment details")
                appointment_row = st.columns([1.4, 1], gap="medium")
                with appointment_row[0]:
                    neighbourhood = st.selectbox(
                        "Neighbourhood",
                        options["neighbourhoods"],
                        index=options["neighbourhoods"].index("JARDIM DA PENHA"),
                    )
                with appointment_row[1]:
                    weekday = st.selectbox(
                        "Weekday",
                        options["weekdays"],
                        index=0,
                    )
                lead_time = st.slider(
                    "Days between booking and appointment",
                    min_value=0,
                    max_value=90,
                    value=7,
                    help="Same-day appointments use a lead time of 0.",
                )

                form_section("Clinical profile")
                handicap = st.select_slider(
                    "Handicap level",
                    options=[0, 1, 2, 3, 4],
                    value=0,
                )
                st.markdown(
                    '<div class="field-label">Chronic conditions</div>',
                    unsafe_allow_html=True,
                )
                condition_cols = st.columns(3, gap="small")
                with condition_cols[0]:
                    hipertension = st.checkbox("Hypertension", value=False)
                with condition_cols[1]:
                    diabetes = st.checkbox("Diabetes", value=False)
                with condition_cols[2]:
                    alcoholism = st.checkbox("Alcoholism", value=False)

                form_section("Contact and support")
                support_cols = st.columns(2, gap="medium")
                with support_cols[0]:
                    sms_received = st.toggle("SMS reminder received", value=True)
                with support_cols[1]:
                    scholarship = st.toggle("Scholarship recipient", value=False)

                submitted = st.form_submit_button(
                    "Score appointment", type="primary", width="stretch"
                )
            st.markdown(
                '<p class="fine-print">Longer booking lead times and missing SMS '
                "reminders typically increase predicted risk. Both models use the "
                "same inputs and are calibrated on held-out data.</p>",
                unsafe_allow_html=True,
            )

    with result_col:
        with st.container(border=True, key="panel-no-show-result"):
            panel_heading(
                "Risk assessment",
                "Calibrated probability, tree comparison and an outreach recommendation.",
            )
            if submitted:
                payload = {
                    "age": int(age),
                    "gender": gender,
                    "scholarship": int(scholarship),
                    "hipertension": int(hipertension),
                    "diabetes": int(diabetes),
                    "alcoholism": int(alcoholism),
                    "handicap": int(handicap),
                    "sms_received": int(sms_received),
                    "lead_time_days": int(lead_time),
                    "weekday": weekday,
                    "neighbourhood": neighbourhood,
                }
                try:
                    st.session_state["no_show_result"] = api_post(
                        api_url, "/predict/no-show", payload
                    )
                except Exception as error:
                    print(f"[dashboard] Could not score the appointment: {error}")
                    st.error(
                        "This appointment could not be scored right now. "
                        "Please retry in a moment."
                    )

            result = st.session_state.get("no_show_result")
            if result is None:
                st.markdown(
                    empty_state(
                        "No appointment scored yet",
                        "Complete the profile and press Score appointment. The result "
                        "will include a calibrated probability, a risk band and a "
                        "recommended outreach action.",
                        icon="calendar",
                    ),
                    unsafe_allow_html=True,
                )
                subhead("Model snapshot")
                metric_grid(
                    [
                        (
                            "ROC-AUC",
                            f"{logistic_metrics['roc_auc']:.3f}",
                            "held-out test set",
                        ),
                        (
                            "Recall",
                            f"{logistic_metrics['recall']:.1%}",
                            "at the tuned threshold",
                        ),
                        (
                            "Threshold",
                            f"{logistic_metrics['threshold']:.1%}",
                            "validation-selected",
                        ),
                    ],
                    columns=3,
                    compact=True,
                )
                subhead("Risk bands")
                st.markdown(
                    band_legend(
                        float(no_show_meta["risk_bands"]["low_max"]),
                        float(no_show_meta["risk_bands"]["high_min"]),
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<p class="fine-print">The binary call uses the recall-tuned '
                    "threshold; the risk band describes the calibrated probability "
                    "on its own.</p>",
                    unsafe_allow_html=True,
                )
            else:
                probability = float(result["no_show_probability"])
                st.markdown(risk_result_card(result), unsafe_allow_html=True)
                metric_grid(
                    [
                        (
                            "Decision tree",
                            f"{result['decision_tree_probability']:.1%}",
                            result["decision_tree_prediction"],
                        ),
                        (
                            "Model agreement",
                            "Agree" if result["models_agree"] else "Split",
                            "binary classification",
                            "teal" if result["models_agree"] else "warn",
                        ),
                    ],
                    columns=2,
                    compact=True,
                )
                st.markdown(
                    callout(
                        "Recommended action",
                        result["recommended_action"],
                        tone="success" if result["risk_level"] == "Low" else "info",
                    ),
                    unsafe_allow_html=True,
                )
                if not result["models_agree"]:
                    st.markdown(
                        callout(
                            "Manual review",
                            "The logistic model and decision tree disagree on the binary "
                            "classification. Treat this appointment as a manual-review case.",
                            tone="warning",
                        ),
                        unsafe_allow_html=True,
                    )
                risk_bands = result["risk_bands"]
                st.markdown(
                    f'<p class="fine-print">Risk bands: Low &lt; '
                    f'{risk_bands["low_max"]:.1%} · Medium '
                    f'{risk_bands["low_max"]:.1%}–{risk_bands["high_min"]:.1%} · '
                    f'High ≥ {risk_bands["high_min"]:.1%}. Logistic ROC-AUC '
                    f'{logistic_metrics["roc_auc"]:.3f}, recall '
                    f'{logistic_metrics["recall"]:.1%}, F1 '
                    f'{logistic_metrics["f1"]:.3f}. Probabilities are '
                    "sigmoid-calibrated.</p>",
                    unsafe_allow_html=True,
                )

        with st.container(border=True, key="panel-no-show-notes"):
            panel_heading(
                "How to read this",
                "Two models, one operational decision.",
            )
            st.markdown(
                note_list(
                    [
                        (
                            "Probability",
                            "Calibrated likelihood that this appointment will not be attended.",
                        ),
                        (
                            "Risk band",
                            "Low, medium or high, based on fixed probability boundaries.",
                        ),
                        (
                            "Binary call",
                            "Uses the validation-selected threshold, tuned for recall.",
                        ),
                    ]
                ),
                unsafe_allow_html=True,
            )

    with st.expander("Explore no-show drivers", icon=":material/insights:"):
        eda = no_show_meta["eda"]
        st.markdown(
            '<p class="expander-note">Historical associations from the appointment '
            "dataset. These are descriptive patterns, not causal effects.</p>",
            unsafe_allow_html=True,
        )
        eda_top = st.columns(2, gap="large")
        with eda_top[0]:
            mini_title("Reminder channel")
            sms_rates = eda["no_show_rate_by_sms"]
            st.altair_chart(
                eda_bar_chart(
                    ["No SMS", "SMS sent"],
                    [float(sms_rates["0"]), float(sms_rates["1"])],
                    color="#38c7b2",
                    height=195,
                ),
                width="stretch",
            )
        with eda_top[1]:
            mini_title("Appointment weekday")
            weekday_rates = eda["no_show_rate_by_weekday"]
            weekday_labels = [
                day
                for day in options["weekdays"]
                if weekday_rates.get(day) is not None
                and math.isfinite(float(weekday_rates[day]))
            ]
            st.altair_chart(
                eda_bar_chart(
                    weekday_labels,
                    [float(weekday_rates[day]) for day in weekday_labels],
                    color="#5aa9f0",
                    height=195,
                ),
                width="stretch",
            )
        eda_bottom = st.columns(2, gap="large")
        with eda_bottom[0]:
            mini_title("Age group")
            age_rates = eda["no_show_rate_by_age_group"]
            age_labels = [group for group in options["age_groups"] if group in age_rates]
            st.altair_chart(
                eda_bar_chart(
                    age_labels,
                    [float(age_rates[group]) for group in age_labels],
                    color="#b39ddb",
                    height=195,
                ),
                width="stretch",
            )
        with eda_bottom[1]:
            mini_title("Booking lead time")
            lead_rates = eda["no_show_rate_by_lead_bin"]
            lead_labels = [
                "Same day",
                "1-3 days",
                "4-7 days",
                "8-14 days",
                "15-30 days",
                "31+ days",
            ]
            st.altair_chart(
                eda_bar_chart(
                    lead_labels,
                    [float(lead_rates[label]) for label in lead_labels],
                    color="#f0a54a",
                    height=195,
                ),
                width="stretch",
            )

# ---------------------------------------------------------------------------
# Patient Segment Explorer
# ---------------------------------------------------------------------------
elif page == "Patient Segment Explorer":
    hero(
        "Patient Segment Explorer",
        "K-Means groups patients by age, appointment frequency, booking lead time, "
        "chronic conditions and SMS contact — then profiles each group's no-show rate.",
        "Patient analytics",
        ["K-Means clustering", "4 operational groups", "Outreach design"],
    )

    try:
        segments_summary = api_get(api_url, "/segments/summary")
    except Exception as error:
        print(f"[dashboard] Could not load segment profiles: {error}")
        st.error(
            "Segment profiles could not be loaded right now. Please retry in a moment."
        )
        st.stop()

    segment_frame = pd.DataFrame(segments_summary["segments"])
    color_map = segment_colors(segment_frame["label"].tolist())

    metric_grid(
        [
            (
                "Patients segmented",
                f"{segments_summary['n_patients']:,}",
                "patient-level appointment history",
            ),
            (
                "Segments",
                str(segments_summary["k"]),
                "K-Means clusters",
            ),
            (
                "Silhouette score",
                f"{segments_summary['silhouette']:.3f}",
                "higher is better",
            ),
            (
                "Overall no-show rate",
                f"{segments_summary['overall_no_show_rate']:.1%}",
                "profiling metric",
            ),
        ]
    )

    form_col, result_col = st.columns([1, 1], gap="large")

    with form_col:
        with st.container(border=True, key="panel-segment-form"):
            panel_heading(
                "Patient profile",
                "Five inputs are used to find the closest segment centroid.",
            )
            with st.form("segment_form", border=False):
                profile_top = st.columns(2, gap="medium")
                with profile_top[0]:
                    age = st.slider("Age", min_value=0, max_value=100, value=40)
                with profile_top[1]:
                    total_appointments = st.number_input(
                        "Total appointments",
                        min_value=1,
                        max_value=50,
                        value=2,
                        help="Number of appointments recorded for this patient.",
                    )
                profile_mid = st.columns(2, gap="medium")
                with profile_mid[0]:
                    avg_lead_time = st.slider(
                        "Average lead time (days)",
                        min_value=0,
                        max_value=90,
                        value=7,
                    )
                with profile_mid[1]:
                    chronic_conditions = st.slider(
                        "Chronic conditions",
                        min_value=0,
                        max_value=4,
                        value=0,
                        help="Hypertension, diabetes, alcoholism and handicap are counted.",
                    )
                sms_rate = st.slider(
                    "SMS contact rate",
                    min_value=0,
                    max_value=100,
                    value=50,
                    format="%d%%",
                    help="Share of this patient's appointments that received an SMS reminder.",
                )
                submitted = st.form_submit_button(
                    "Find segment", type="primary", width="stretch"
                )
            st.markdown(
                '<p class="fine-print">The same profile always maps to the closest '
                "centroid. Compare the full cohort in the segment overview below "
                "before designing an outreach campaign.</p>",
                unsafe_allow_html=True,
            )

    with result_col:
        with st.container(border=True, key="panel-segment-result"):
            panel_heading(
                "Segment match",
                "Closest K-Means centroid and the group's operational profile.",
            )
            if submitted:
                payload = {
                    "age": float(age),
                    "total_appointments": int(total_appointments),
                    "avg_lead_time_days": float(avg_lead_time),
                    "chronic_conditions": float(chronic_conditions),
                    "sms_rate": float(sms_rate) / 100.0,
                }
                try:
                    st.session_state["segment_result"] = api_post(
                        api_url, "/predict/segment", payload
                    )
                except Exception as error:
                    print(f"[dashboard] Could not assign a segment: {error}")
                    st.error(
                        "This patient profile could not be assigned right now. "
                        "Please retry in a moment."
                    )

            result = st.session_state.get("segment_result")
            if result is None:
                st.markdown(
                    empty_state(
                        "No patient profile submitted",
                        "Enter a profile and press Find segment to see the closest "
                        "operational group, its no-show rate and its outreach guidance.",
                        icon="users",
                    ),
                    unsafe_allow_html=True,
                )
                subhead("Segment library")
                st.markdown(
                    segment_list_html(segment_frame, color_map),
                    unsafe_allow_html=True,
                )
            else:
                profile = result["profile"]
                st.markdown(
                    segment_result_card(result, color_map), unsafe_allow_html=True
                )
                metric_grid(
                    [
                        (
                            "Segment no-show rate",
                            f"{profile['no_show_rate']:.1%}",
                            f"{profile['patients']:,} patients",
                            "warn",
                        ),
                        (
                            "Distance to centroid",
                            f"{result['distance_to_centroid']:.2f}",
                            "lower is a closer match",
                        ),
                        (
                            "Average age",
                            f"{profile['age']:.1f}",
                            "years",
                        ),
                        (
                            "Average appointments",
                            f"{profile['appointments']:.2f}",
                            "per patient",
                        ),
                        (
                            "Average lead time",
                            f"{profile['avg_lead_time']:.1f}",
                            "days",
                        ),
                        (
                            "SMS contact rate",
                            f"{profile['sms_rate']:.1%}",
                            "of appointments",
                        ),
                    ],
                    columns=3,
                    compact=True,
                )
                st.markdown(
                    '<p class="fine-print">No-show rate is a post-hoc profiling '
                    "metric, not a clustering feature. Use segment membership to design "
                    "outreach, not to make individual clinical decisions.</p>",
                    unsafe_allow_html=True,
                )

    section_header(
        "Segment overview",
        f"K = {segments_summary['k']} · silhouette {segments_summary['silhouette']:.3f} · "
        f"{segments_summary['n_patients']:,} patients. No-show rate is profiling only.",
        "Cohort composition",
    )
    with st.container(border=True, key="panel-segment-overview"):
        panel_heading(
            "Segment sizes and risk",
            "Compare how patients are distributed and how no-show rates differ by group.",
            right=chip("K-Means · k = 4", "teal"),
        )
        chart_cols = st.columns(2, gap="large")
        with chart_cols[0]:
            mini_title("Patients per segment", "Share of the cohort shown at bar end.")
            st.altair_chart(
                segment_chart(
                    segment_frame,
                    "patients",
                    color_map,
                    label_field="share",
                    label_format=".1%",
                    axis_format=",.0f",
                    field_title="Patients",
                ),
                width="stretch",
            )
        with chart_cols[1]:
            mini_title("No-show rate by segment", "Post-hoc profile of each cluster.")
            st.altair_chart(
                segment_chart(
                    segment_frame,
                    "no_show_rate",
                    color_map,
                    label_field="no_show_rate",
                    label_format=".1%",
                    axis_format="%",
                    field_title="No-show rate",
                ),
                width="stretch",
            )

    section_header(
        "Segment profiles",
        "Average characteristics for each operational group.",
        "Profile table",
    )
    segment_table = segment_frame[
        [
            "label",
            "patients",
            "share",
            "age",
            "appointments",
            "avg_lead_time",
            "sms_rate",
            "no_show_rate",
        ]
    ].rename(
        columns={
            "label": "Segment",
            "patients": "Patients",
            "share": "Share",
            "age": "Avg age",
            "appointments": "Avg appointments",
            "avg_lead_time": "Avg lead time (days)",
            "sms_rate": "SMS rate",
            "no_show_rate": "No-show rate",
        }
    )
    for percentage_column in ["Share", "SMS rate", "No-show rate"]:
        segment_table[percentage_column] = (
            segment_table[percentage_column] * 100
        ).round(1)
    st.dataframe(
        segment_table,
        width="stretch",
        hide_index=True,
        height=190,
        column_config={
            "Segment": st.column_config.TextColumn(width="medium"),
            "Patients": st.column_config.NumberColumn(format="localized"),
            "Share": st.column_config.NumberColumn(format="%.1f%%"),
            "Avg age": st.column_config.NumberColumn(format="%.1f"),
            "Avg appointments": st.column_config.NumberColumn(format="%.2f"),
            "Avg lead time (days)": st.column_config.NumberColumn(format="%.1f"),
            "SMS rate": st.column_config.NumberColumn(format="%.1f%%"),
            "No-show rate": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    st.caption(
        "Segments are descriptive, not causal. They support outreach design and capacity "
        "discussions and are not a substitute for clinical judgment."
    )

    with st.expander("Segment playbook", icon=":material/strategy:"):
        st.markdown(
            '<p class="expander-note">Suggested operational focus for each group. '
            "Use these as starting points for outreach design and review them with "
            "clinical and scheduling teams.</p>",
            unsafe_allow_html=True,
        )
        playbook_grid(segments_summary["segments"], color_map)


page_footer()

