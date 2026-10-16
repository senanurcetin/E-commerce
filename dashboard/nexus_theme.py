"""NEXUS visual system shared by all Commerce Intelligence tabs."""
from __future__ import annotations

import streamlit as st

COLORS = {
    "page": "#080F20",
    "surface": "#111E38",
    "surface_high": "#192946",
    "cyan": "#47DFF2",
    "purple": "#A892F4",
    "white": "#EDF5FF",
    "muted": "#AFC0DB",
    "border": "#314565",
    "green": "#7ADDB8",
    "amber": "#EFC98D",
}

CSS = r"""
<style>
:root { color-scheme: dark; }
.stApp {
    color: #EDF5FF;
    background:
        radial-gradient(ellipse 60% 34% at 88% -6%, rgba(96,78,196,.22), transparent 76%),
        radial-gradient(ellipse 44% 32% at 20% 1%, rgba(19,120,172,.13), transparent 76%),
        #080F20;
}
[data-testid="stMainBlockContainer"] {max-width: 1536px;padding-top: 2rem;padding-bottom: 4rem;}
[data-testid="stSidebar"] {background: #0B152A;border-right:1px solid #273957;}
[data-testid="stSidebar"] h2 {font-size: 1rem;}
[data-testid="stHeader"] {background: transparent;}
[data-testid="stMetric"] {
    background: linear-gradient(145deg,rgba(30,46,80,.92),rgba(16,29,54,.96));
    border: 1px solid #344968;border-radius: 16px;
    padding: 1.0rem 1.15rem;min-height: 108px;
    box-shadow: 0 12px 30px rgba(0,0,0,.11);
}
[data-testid="stMetricLabel"] {color:#B7CAE2;font-size:.78rem;font-weight:600;}
[data-testid="stMetricValue"] {color:#EDF5FF;font-weight:750;letter-spacing:-.035em;}
[data-testid="stMetricDelta"] {color:#7ADDB8;}
div[data-testid="stTabs"] {margin-top:.6rem;}
button[data-baseweb="tab"] {
    color:#AFBFD7;white-space:nowrap;font-size:.83rem;font-weight:650;
    border-radius: 9px 9px 0 0;padding: .63rem .86rem;
}
button[data-baseweb="tab"][aria-selected="true"] {color:#47DFF2;background:rgba(71,223,242,.08);}
div[data-testid="stTabs"] [role="tablist"] {gap:.15rem;border-bottom:1px solid #344968;}
div[data-testid="stAlert"] {border-radius:12px;border:1px solid #334763;}
div[data-testid="stExpander"] {border:1px solid #314565;border-radius:12px;background:rgba(17,30,56,.42);}
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {border-radius:12px;overflow:hidden;}
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(h2) {margin-top: .25rem;}
h1,h2,h3 {letter-spacing:-.03em;color:#EDF5FF;}
h1 {font-weight:780;font-size:clamp(1.8rem,3vw,2.8rem);}
h2 {font-size:clamp(1.3rem,2vw,1.65rem);}
[data-testid="stCaptionContainer"] {color:#B0C0D9;}
a {color:#47DFF2;}
.nexus-eyebrow {font-size:.74rem;font-weight:800;text-transform:uppercase;letter-spacing:.19em;color:#47DFF2;}
.nexus-hero {
    background: linear-gradient(107deg,rgba(26,52,87,.94),rgba(23,29,69,.88) 75%,rgba(48,37,84,.82));
    border:1px solid #385270;border-radius:22px;padding:clamp(1.2rem,3vw,2rem);
    box-shadow: 0 18px 50px rgba(0,0,0,.17);
    margin: .2rem 0 1.2rem;
}
.nexus-hero h1 {margin:.4rem 0;font-size:clamp(1.65rem,2.8vw,2.55rem);line-height:1.13;}
.nexus-hero p {color:#C3D1E8;margin:.6rem 0 0;max-width:900px;font-size:.95rem;line-height:1.6;}
.nexus-pill {
    display:inline-block;border:1px solid #3D6A7A;color:#B5F2F7;
    background:rgba(22,113,135,.16);padding:.27rem .7rem;border-radius:999px;
    font-size:.7rem;font-weight:720;letter-spacing:.03em;margin:.8rem .45rem 0 0;
}
.nexus-pill-secondary {color:#DACFF9;border-color:#63578E;background:rgba(125,95,192,.14);}
.nexus-source {background:linear-gradient(150deg,#192A48,#111F3A);border:1px solid #354A69;
    border-radius:14px;padding:1.05rem;min-height:124px;}
.nexus-source-name {color:#B1C5DD;font-size:.68rem;letter-spacing:.09em;font-weight:750;}
.nexus-source-state {color:#64E6ED;font-weight:800;font-size:.94rem;margin-top:.68rem;}
.nexus-source-empty {color:#C0CCE0;}
.nexus-source-detail {color:#9EAFCA;font-size:.72rem;line-height:1.42;margin-top:.43rem;}
.nexus-section-label {font-size:.77rem;color:#A9BCDB;letter-spacing:.1em;text-transform:uppercase;font-weight:720;margin:1rem 0 .5rem;}
@media (max-width:750px) {
    [data-testid="stMainBlockContainer"] {padding:1.2rem .8rem 3rem;}
    .nexus-hero {border-radius:15px;padding:1rem;}
    .nexus-hero h1 {line-height:1.2;}
    .nexus-source {min-height:96px;}
    [data-testid="stMetric"] {min-height:94px;}
}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero() -> None:
    st.markdown(
        '<div class="nexus-hero">'
        '<span class="nexus-eyebrow">NEXUS / DATA PRODUCTS / COMMERCE</span>'
        '<h1>Commerce Intelligence</h1>'
        '<p>Historical E-Commerce performance, Greenweez financial evidence, '
        'and first-party Commerce Lab telemetry in one controlled workspace. '
        'Independent sources remain independent: no synthetic revenue, '
        'cross-merchant sales totals or unverified attribution.</p>'
        '<span class="nexus-pill">SOURCE-FIRST ANALYTICS</span>'
        '<span class="nexus-pill nexus-pill-secondary">AUDITABLE · TESTABLE · LOCAL</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def plot_layout(title: str = "") -> dict:
    return {
        "title": {"text": title, "font": {"size": 16, "color": COLORS["white"]},
                  "x": 0.01, "xanchor": "left"},
        "paper_bgcolor": COLORS["page"],
        "plot_bgcolor": COLORS["surface"],
        "font": {"color": COLORS["muted"], "size": 12},
        "margin": {"l": 18, "r": 18, "t": 62, "b": 38},
        "legend": {"orientation": "h", "y": -0.24, "font": {"size": 11}},
        "xaxis": {"gridcolor": "#283C58", "zerolinecolor": "#283C58",
                  "linecolor": "#405272"},
        "yaxis": {"gridcolor": "#283C58", "zerolinecolor": "#283C58",
                  "linecolor": "#405272"},
        "hoverlabel": {"bgcolor": COLORS["surface_high"],
                       "font": {"color": COLORS["white"]}},
    }


def style_chart(fig, title: str) -> None:
    fig.update_layout(**plot_layout(title))
