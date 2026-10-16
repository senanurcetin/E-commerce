"""NEXUS Commerce Intelligence | Google Measurement (verified snapshots only).

Run from repo root:
    pip install -r dashboard/requirements.txt
    python scripts/google_measurement_marts.py
    streamlit run dashboard/google_marketing_app.py

This viewer does not create traffic/purchase tags, send requests to Google,
intermix E-Commerce/Greenweez historical facts, or claim real-time telemetry.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import json

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.google_dashboard_data import (
    filter_dates, kpis_ga4, kpis_gsc, latest_pagespeed, load_bundle,
)

PALETTE = {
    "background": "#080F25",
    "navy": "#101D3D",
    "cyan": "#29D6EC",
    "purple": "#9569F7",
    "ice": "#E7F2FF",
    "muted": "#95A7C5",
    "pink": "#EC6DCB",
}


st.set_page_config(
    page_title="NEXUS | Commerce Intelligence",
    page_icon="📊", layout="wide",
)

st.markdown("""
<style>
.stApp {background: radial-gradient(circle at 75% -10%, #1C235A 0, #080F25 43%, #080F25 100%);
        color: #E7F2FF;}
[data-testid="stSidebar"] {background: #0D1730;}
h1, h2, h3, p {letter-spacing: -0.015em;}
h1 {font-weight: 800; color: #E7F2FF;}
[data-testid="stMetric"] {background: #121F3F; padding: 18px;
    border: 1px solid #263A60; border-radius: 15px;}
[data-testid="stMetricValue"] {color: #29D6EC;}
[data-testid="stMetricLabel"] {color: #A2B1CA;}
[data-testid="stTabs"] [role="tab"] {font-weight: 650;}
div[data-testid="stAlert"] {border-radius: 12px;}
.nexus-kicker {color:#29D6EC; text-transform:uppercase; letter-spacing:0.18em;
    font-size:0.78rem; font-weight:800;}
.nexus-subtitle {font-size:1rem;color:#A9BBD5;max-width:880px;margin-bottom:16px;}
.nexus-note {color:#A5B4CA;font-size:0.83rem;}
</style>
""", unsafe_allow_html=True)


def plot_config(title: str) -> dict:
    return {
        "title": title,
        "paper_bgcolor": PALETTE["background"],
        "plot_bgcolor": PALETTE["navy"],
        "font": {"color": PALETTE["ice"], "size": 12},
        "margin": {"l": 15, "r": 15, "t": 52, "b": 15},
        "legend": {"orientation": "h", "y": -0.20},
        "xaxis": {"gridcolor": "#243454"},
        "yaxis": {"gridcolor": "#243454"},
    }


def header() -> None:
    st.markdown('<p class="nexus-kicker">NEXUS / COMMERCE INTELLIGENCE</p>', unsafe_allow_html=True)
    st.title("Google Measurement Observatory")
    st.markdown(
        '<p class="nexus-subtitle">GA4 acquisition · Search Console organic reach · '
        "Lighthouse site experience. Each source is separately verified; "
        'not a combined transaction or advertising ledger.</p>',
        unsafe_allow_html=True,
    )


def use_period(records: list[dict], scope: str) -> list[dict]:
    available = sorted(date.fromisoformat(r["date"]) for r in records)
    low, high = available[0], available[-1]
    a, b = st.columns(2)
    with a:
        start = st.date_input("From", value=low, min_value=low, max_value=high, key=scope + "_start")
    with b:
        end = st.date_input("To", value=high, min_value=low, max_value=high, key=scope + "_end")
    if start > end:
        st.warning("The end date must not precede the start date.")
        return []
    return filter_dates(records, start, end)


def download_frame(frame: pd.DataFrame, label: str, filename: str) -> None:
    st.download_button(
        label, data=frame.to_csv(index=False).encode("utf-8"),
        file_name=filename, mime="text/csv", key=filename,
    )


def ga4_tab(rows: list[dict]) -> None:
    st.subheader("Acquisition & Engagement")
    if not rows:
        st.info("GA4 not connected or no verified rows for this source. Complete authorized export first.")
        return
    identities = sorted({r["property_id"] for r in rows})
    chosen = st.selectbox("GA4 property", identities, key="ga4_property")
    scoped = [r for r in rows if r["property_id"] == chosen]
    scoped = use_period(scoped, "ga4")
    if not scoped:
        st.warning("No GA4 records in the selected period.")
        return
    try:
        totals = kpis_ga4(scoped)
    except ValueError as exc:
        st.error(f"GA4 KPI contract failed: {exc}")
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sessions", f"{totals['sessions']:,}")
    c2.metric("Engagement rate", "N/A" if totals["engagement_rate"] is None else f"{totals['engagement_rate']:.1%}")
    c3.metric("E-commerce purchases", f"{totals['ecommerce_purchases']:,}")
    c4.metric("Purchase revenue · property currency", f"{totals['purchase_revenue_in_property_currency']:,.2f}")
    st.caption(
        "GA4 property currency and reporting identity apply. Active users are not shown as a "
        "summed figure: GA4 distinct users cannot be added across channels and dates."
    )
    data = pd.DataFrame(scoped)
    for key in ("sessions", "engaged_sessions", "ecommerce_purchases"):
        data[key] = pd.to_numeric(data[key])
    daily = data.groupby("date", as_index=False)[["sessions", "engaged_sessions", "ecommerce_purchases"]].sum()
    left, right = st.columns([1.7, 1])
    with left:
        fig = px.line(daily, x="date", y=["sessions", "engaged_sessions"],
                      color_discrete_sequence=[PALETTE["cyan"], PALETTE["purple"]])
        fig.update_layout(**plot_config("Daily sessions & engaged sessions"))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        sources = (data.groupby("ga4_session_channel_group", as_index=False)["sessions"]
                   .sum().sort_values("sessions", ascending=False).head(12))
        fig = px.bar(sources, x="sessions", y="ga4_session_channel_group",
                     orientation="h", color_discrete_sequence=[PALETTE["cyan"]])
        fig.update_layout(**plot_config("Sessions by GA4 channel"))
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)
    with st.expander("Verified GA4 source rows"):
        st.dataframe(data.sort_values(["date", "ga4_session_channel_group"]), use_container_width=True, hide_index=True)
        download_frame(data, "Export selected GA4 source rows", "nexus_ga4_filtered.csv")


def gsc_tab(rows: list[dict]) -> None:
    st.subheader("Organic Search Visibility")
    if not rows:
        st.info("Search Console not connected or no verified rows for this source.")
        return
    chosen = st.selectbox("GSC property", sorted({r["site_property"] for r in rows}), key="gsc_property")
    property_rows = [r for r in rows if r["site_property"] == chosen]
    devices = sorted({r["device"] for r in property_rows})
    selected_devices = st.multiselect("Devices", devices, default=devices, key="gsc_devices")
    scoped = [r for r in property_rows if r["device"] in selected_devices]
    if not scoped:
        st.warning("No GSC rows match the selected devices.")
        return
    scoped = use_period(scoped, "gsc")
    if not scoped:
        st.warning("No GSC rows match the selected period.")
        return
    try:
        totals = kpis_gsc(scoped)
    except ValueError as exc:
        st.error(f"Search Console KPI contract failed: {exc}")
        return
    a, b, c, d = st.columns(4)
    a.metric("Search clicks", f"{totals['clicks']:,}")
    b.metric("Impressions", f"{totals['impressions']:,}")
    c.metric("Organic CTR", "N/A" if totals["ctr"] is None else f"{totals['ctr']:.2%}")
    d.metric("Weighted avg. position", "N/A" if totals["impression_weighted_position"] is None else f"{totals['impression_weighted_position']:.2f}")
    st.caption("Search Console organic clicks ≠ GA4 sessions. Average position is weighted by impressions; daily CTR is recomputed from clicks and impressions.")
    df = pd.DataFrame(scoped)
    for key in ("clicks", "impressions", "average_position"):
        df[key] = pd.to_numeric(df[key])
    daily = df.groupby("date", as_index=False)[["clicks", "impressions"]].sum().sort_values("date")
    daily["ctr_pct"] = (100.0 * daily["clicks"] / daily["impressions"].replace({0: float("nan")}))
    a, b = st.columns(2)
    with a:
        fig = px.bar(daily, x="date", y="clicks", color_discrete_sequence=[PALETTE["cyan"]])
        fig.update_layout(**plot_config("Organic search clicks"))
        st.plotly_chart(fig, use_container_width=True)
    with b:
        fig = px.line(daily, x="date", y="ctr_pct", color_discrete_sequence=[PALETTE["purple"]])
        fig.update_layout(**plot_config("Click-through rate · %"))
        st.plotly_chart(fig, use_container_width=True)
    with st.expander("Verified Search Console source rows"):
        st.dataframe(df, use_container_width=True, hide_index=True)
        download_frame(df, "Export selected GSC source rows", "nexus_gsc_filtered.csv")


def pagespeed_tab(rows: list[dict]) -> None:
    st.subheader("Site Experience · Lighthouse Lab")
    if not rows:
        st.info("PageSpeed Insights not connected or no real audit snapshots available.")
        return
    try:
        selected = latest_pagespeed(rows)
    except ValueError as exc:
        st.error(f"PageSpeed audit contract failed: {exc}")
        return
    target_urls = sorted({r["url"] for r in selected})
    url = st.selectbox("Page URL", target_urls, key="psi_url")
    selected = [r for r in selected if r["url"] == url]
    if not selected:
        st.warning("No audits for this URL.")
        return
    st.caption("These scores are point-in-time Lighthouse lab tests, not CrUX real-user Core Web Vitals.")
    for r in sorted(selected, key=lambda r: r["strategy"]):
        st.markdown(f"#### {r['strategy'].title()} · {r['extracted_at_utc']}")
        cols = st.columns(4)
        for i, (name, col) in enumerate((
            ("Performance", "performance_score"),
            ("Accessibility", "accessibility_score"),
            ("Best Practices", "best_practices_score"),
            ("SEO", "seo_score"),
        )):
            cols[i].metric(name, "N/A" if r[col] in ("", None) else f"{float(r[col]):.0f}/100")
    display = pd.DataFrame(selected)
    st.dataframe(display, use_container_width=True, hide_index=True)
    download_frame(display, "Export these Lighthouse audits", "nexus_pagespeed_latest.csv")
    st.info("Field Core Web Vitals (p75 LCP, INP and CLS) require separately connected CrUX API data.")


header()
location = Path(__file__).resolve().parents[1] / "target" / "google_measurement" / "marts"
with st.sidebar:
    st.markdown("### SOURCE CONTROLS")
    st.caption("Read-only local exports. No automatic cloud credentials or production monitoring.")
    folder = st.text_input("Validated export folder", value=str(location))
    st.markdown("**Data provenance**")
    st.caption("GA4 · GSC · PageSpeed Insights")
    st.caption("Legacy E-Commerce, Olist and Greenweez data are independent domains.")

try:
    tables, manifest = load_bundle(Path(folder))
except (OSError, ValueError, json.JSONDecodeError) as exc:
    st.warning("No complete verified Google measurement export is available.")
    st.code(str(exc), language="text")
    st.info(
        "1. Authenticate to an authorized GA4/GSC property or request a public PageSpeed audit.\n"
        "2. Run the collector to target/google_measurement/.\n"
        "3. Run python scripts/google_measurement_marts.py.\n"
        "4. Reload this dashboard. The dashboard never substitutes demo or simulated traffic."
    )
    st.stop()

st.caption("Validated API snapshots only · Not real-time · No advertising cost/ROAS attribution")
status = manifest.get("source_summary", {})
for source_key, table_key in (("ga4_data_api", "ga4"), ("gsc_search_analytics_api", "gsc"), ("pagespeed_insights_api", "pagespeed")):
    st.sidebar.caption(f"{source_key}: {len(tables[table_key])} rows")
with st.sidebar.expander("Extraction metadata"):
    st.json({"snapshots": manifest.get("input_snapshot_count"),
             "partial_snapshots": manifest.get("partial_snapshot_count"),
             "source_summary": status})
tab1, tab2, tab3, tab4 = st.tabs(
    ["GA4 · Acquisition", "GSC · Search", "PSI · Lighthouse", "Measurement Contracts"]
)
with tab1:
    ga4_tab(tables["ga4"])
with tab2:
    gsc_tab(tables["gsc"])
with tab3:
    pagespeed_tab(tables["pagespeed"])
with tab4:
    st.subheader("Data Quality & Interpretation")
    st.markdown(
        "**GA4:** property-specific acquisition and purchase aggregates; non-additive users excluded from rollups.\n\n"
        "**GSC:** organic Search click/impression aggregates; CTR and position use denominator-aware aggregation.\n\n"
        "**PSI:** Lighthouse lab audits; field data need CrUX and separately verified access.\n\n"
        "**Google Ads:** ad spend and campaign conversion attribution not connected, so CAC and ROAS are unavailable.\n\n"
        "**Greenweez / Olist:** no cross-domain join or shared revenue is implied."
    )
    for warning in manifest.get("warnings", []):
        st.caption("• " + str(warning))
