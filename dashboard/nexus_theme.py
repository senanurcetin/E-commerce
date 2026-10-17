"""NEXUS visual system shared by all Commerce Intelligence tabs."""
from __future__ import annotations

from pathlib import Path

from PIL import Image
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_LOGO = ROOT / "branding" / "nexus_official_transparent.png"

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
.nexus-brand-mark {width:min(290px,66vw);height:auto;object-fit:contain;display:block;
    margin:0 0 .95rem;filter:drop-shadow(0 4px 18px rgba(71,223,242,.08));}
.nexus-hero-kicker{display:flex;align-items:center;gap:.65rem;letter-spacing:.11em;font-size:.69rem;
    font-weight:800;color:#D6E5F7;padding-bottom:1.1rem;margin-bottom:1.3rem;border-bottom:1px solid #45618255;}
.nexus-live-point{width:7px;height:7px;background:#47DFF2;border-radius:100%;
    box-shadow:0 0 0 4px #47DFF220,0 0 20px #47DFF290;}
.nexus-kicker-sep{color:#6387A4;}
.nexus-hero-edition{margin-left:auto;font-variant-numeric:tabular-nums;color:#9FAFCE;}
.nexus-gradient-title{color:#47DFF2;
    background:linear-gradient(102deg,#54EDF3,#9AA1FF 80%,#C1A5FA);background-clip:text;
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.nexus-hero-tags{display:flex;flex-wrap:wrap;gap:.2rem;margin-top:.35rem;}
[data-testid="stSidebar"] [data-testid="stImage"]{padding:.8rem 0 1rem;margin-bottom:.6rem;
    border-bottom:1px solid #324A68;}
.nexus-hero:before{content:"";position:absolute;right:-4.5rem;top:-3rem;width:320px;height:320px;
    border-radius:50%;border:1px solid #8298E935;box-shadow:0 0 0 50px #7F8CF014,0 0 0 100px #47DFF209;
    pointer-events:none;}
.nexus-hero{position:relative;overflow:hidden;}

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
    .nexus-hero:before{display:none;}
    .nexus-hero-kicker{gap:.35rem;flex-wrap:wrap;font-size:.6rem;}
    .nexus-hero h1 {line-height:1.2;}
    .nexus-source {min-height:96px;}
    [data-testid="stMetric"] {min-height:94px;}
}
</style>
"""


def brand_icon() -> Image.Image:
    """Crop the genuine gradient X of the owner's official logo into a square icon."""
    if not OFFICIAL_LOGO.is_file():
        raise FileNotFoundError("Original NEXUS brand asset is missing")
    with Image.open(OFFICIAL_LOGO) as original:
        source = original.convert("RGBA")
    if source.size != (1200, 360):
        raise ValueError("Unexpected NEXUS official logo dimensions")
    mark = source.crop((440, 68, 684, 293))
    mark.thumbnail((212, 210), Image.Resampling.LANCZOS)
    square = Image.new("RGBA", (256, 256), "#0A1428")
    square.alpha_composite(mark, ((256 - mark.width) // 2, (256 - mark.height) // 2))
    return square


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.sidebar.image(str(OFFICIAL_LOGO), width=215)


def hero() -> None:
    """Use native image widgets to ensure the official logo is rendered."""
    st.image(str(OFFICIAL_LOGO), width=340)
    st.markdown(
        '<section class="nexus-hero">'
        '<div class="nexus-hero-kicker"><span class="nexus-live-point"></span>'
        '<span>NEXUS PLATFORM</span><span class="nexus-kicker-sep">/</span>'
        '<span>COMMERCE INTELLIGENCE</span><span class="nexus-hero-edition">2026.10</span></div>'
        '<span class="nexus-eyebrow">ANALYTICS / SOURCE INTEGRITY / BUSINESS INTELLIGENCE</span>'
        '<h1>Every source. <span class="nexus-gradient-title">One workspace.</span></h1>'
        '<p>Historical E-Commerce, Greenweez source observations, and independently '
        'verified Commerce Lab telemetry — organized in one decision workspace. '
        'Unavailable or unverified financial data are clearly identified; '
        'sources are never falsely merged into a single merchant revenue total.</p>'
        '<div class="nexus-hero-tags">'
        '<span class="nexus-pill">SOURCE-FIRST ANALYTICS</span>'
        '<span class="nexus-pill nexus-pill-secondary">AUDITABLE / LOCAL / TESTED</span>'
        '</div></section>',
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
