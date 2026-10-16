"""NEXUS Commerce Intelligence | Google Measurement (verified snapshots only).

Run from repo root:
    pip install -r dashboard/requirements.txt
    python scripts/google_measurement_marts.py
    streamlit run dashboard/google_marketing_app.py

The local user may explicitly trigger Google's public PageSpeed Insights API.
No background API calls, synthetic metrics, commerce-data joins or live-streaming claims.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import json
from urllib.error import HTTPError, URLError

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.google_dashboard_data import (
    filter_dates, kpis_ga4, kpis_gsc, latest_pagespeed, load_bundle,
)
from scripts.google_dashboard_refresh import audit_public_site
from scripts.google_test_sites import TEST_SITES, DEFAULT_TEST_SITE, test_site_url
from scripts.local_lighthouse import load_lighthouse_reports, parse_lighthouse_report
from scripts.lab_ga4_events import load_lab_snapshot, EVENT_NAMES as LAB_EVENT_NAMES
from scripts.greenweez_bridge import load_snapshot as load_greenweez_snapshot
from dashboard.greenweez_finance import greenweez_finance_tab
from scripts.ecommerce_marts_bridge import load_snapshot as load_historical_snapshot
from dashboard.ecommerce_historical import historical_ecommerce_tab
from scripts.nexus_workspace import inspect_sources

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
.nexus-source {background:linear-gradient(145deg, #142246, #101B38);
    border:1px solid #2B416B;border-radius:15px;padding:17px 18px;min-height:100px;}
.nexus-source-name {color:#DCEBFC;font-size:0.78rem;letter-spacing:0.09em;font-weight:750;}
.nexus-source-state {font-size:1.05rem;color:#29D6EC;font-weight:800;margin-top:8px;}
.nexus-source-empty {color:#A5B4CA;}
.nexus-source-detail {color:#96A9C8;font-size:0.77rem;margin-top:5px;}

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
    st.title("NEXUS Commerce Intelligence Observatory")
    st.markdown(
        '<p class="nexus-subtitle">Independent E-Commerce analytics · '
        "Greenweez finance and campaigns · owned Commerce Lab GA4 · "
        "Google web measurement. Source-isolated evidence, not a merged "
        'company revenue ledger.</p>',
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
        st.plotly_chart(fig, width="stretch")
    with right:
        sources = (data.groupby("ga4_session_channel_group", as_index=False)["sessions"]
                   .sum().sort_values("sessions", ascending=False).head(12))
        fig = px.bar(sources, x="sessions", y="ga4_session_channel_group",
                     orientation="h", color_discrete_sequence=[PALETTE["cyan"]])
        fig.update_layout(**plot_config("Sessions by GA4 channel"))
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig, width="stretch")
    with st.expander("Verified GA4 source rows"):
        st.dataframe(data.sort_values(["date", "ga4_session_channel_group"]), width="stretch", hide_index=True)
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
        st.plotly_chart(fig, width="stretch")
    with b:
        fig = px.line(daily, x="date", y="ctr_pct", color_discrete_sequence=[PALETTE["purple"]])
        fig.update_layout(**plot_config("Click-through rate · %"))
        st.plotly_chart(fig, width="stretch")
    with st.expander("Verified Search Console source rows"):
        st.dataframe(df, width="stretch", hide_index=True)
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
    # Side-by-side device comparison from the latest *actual* lab audit.
    chart_rows = []
    for r in selected:
        for name, column in (
            ("Performance", "performance_score"),
            ("Accessibility", "accessibility_score"),
            ("Best practices", "best_practices_score"),
            ("SEO", "seo_score"),
        ):
            if r[column] not in ("", None):
                chart_rows.append({
                    "Device": r["strategy"].title(), "Category": name,
                    "Lighthouse score": float(r[column]),
                })
    if chart_rows:
        fig = px.bar(
            pd.DataFrame(chart_rows), x="Category", y="Lighthouse score",
            color="Device", barmode="group", range_y=[0, 100],
            color_discrete_sequence=[PALETTE["cyan"], PALETTE["purple"]],
        )
        fig.update_layout(**plot_config("Latest lab score comparison · 0–100"))
        st.plotly_chart(fig, width="stretch")

    # Preserve audit history; never substitute sampled Core Web Vitals.
    history = pd.DataFrame([r for r in rows if r["url"] == url])
    history["lab_lcp_ms"] = pd.to_numeric(history["lab_lcp_ms"], errors="coerce")
    history = history.dropna(subset=["lab_lcp_ms"])
    if len(history) > 1:
        history = history.sort_values("extracted_at_utc")
        trend = px.line(
            history, x="extracted_at_utc", y="lab_lcp_ms",
            color="strategy", markers=True,
            color_discrete_sequence=[PALETTE["cyan"], PALETTE["purple"]],
        )
        trend.update_layout(**plot_config("Lab LCP across recorded audits · milliseconds"))
        st.plotly_chart(trend, width="stretch")

    display = pd.DataFrame(selected)
    st.dataframe(display, width="stretch", hide_index=True)
    download_frame(display, "Export these Lighthouse audits", "nexus_pagespeed_latest.csv")
    st.info("Field Core Web Vitals (p75 LCP, INP and CLS) require separately connected CrUX API data.")



def commerce_lab_ga4_tab() -> None:
    """Distinct opted-in laboratory event counts; no purchase/revenue KPI."""
    st.subheader("NEXUS Commerce Lab · Consented Test Interactions")
    st.caption(
        "An independent, first-party GA4 property is required. These are "
        "event occurrences, NOT unique users, customer orders or sales revenue."
    )
    path = ROOT / "target" / "google_measurement" / "lab_ga4_events.json"
    try:
        loaded = load_lab_snapshot(path)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        st.error(f"Commerce Lab GA4 source validation failed: {exc}")
        return
    if loaded is None:
        st.info(
            "Commerce Lab GA4 is not connected. Create a dedicated GA4 property "
            "and web data stream, deploy its new G-... Measurement ID, opt in on "
            "the storefront, and run an authorized read-only export."
        )
        st.code(
            "GA4_LAB_PROPERTY_ID=<numeric-property-id> "
            "python -m scripts.lab_ga4_events "
            "--start 2026-10-01 --end 2026-10-16",
            language="bash",
        )
        return
    rows, snapshot = loaded
    st.caption(
        f"Source: {snapshot['source']} · Property: {snapshot['property_id']} · "
        f"Host: {snapshot['site_hostname']} · Extraction: {snapshot['extracted_at_utc']}"
    )
    if not rows:
        st.info("Authenticated lab report returned no matching events in the selected window.")
        return
    selected = use_period(rows, "commerce_lab_ga4")
    if not selected:
        return
    totals = {key: sum(r["event_count"] for r in selected if r["event_name"] == key)
              for key in LAB_EVENT_NAMES}
    labels = [
        ("Lab page-view events", "lab_page_view"),
        ("Lab add-to-cart events", "lab_add_to_cart"),
        ("Lab remove-from-cart events", "lab_remove_from_cart"),
        ("Lab completed test checkouts", "lab_checkout_completed"),
    ]
    for column, (label, event) in zip(st.columns(4), labels):
        column.metric(label, f"{totals[event]:,}")
    frame = pd.DataFrame(selected)
    grouped = frame.groupby(["date", "event_name"], as_index=False)["event_count"].sum()
    fig = px.line(
        grouped, x="date", y="event_count", color="event_name", markers=True,
        color_discrete_sequence=[
            PALETTE["cyan"], PALETTE["purple"], PALETTE["pink"],
        ],
    )
    fig.update_layout(**plot_config("Observed sandbox events · source-qualified daily counts"))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(frame, width="stretch", hide_index=True)
    st.caption(
        "Custom lab_checkout_completed is a test-flow completion, never a GA4 "
        "purchase. Event counts are not deduplicated users or validated orders. "
        "No monetary attribution, CAC or ROAS is produced."
    )


def local_lighthouse_tab() -> None:
    """Source-specific browser Lighthouse JSON. Never presented as PSI/CrUX."""
    st.divider()
    st.subheader("Local Chrome Lighthouse · separate lab source")
    st.caption(
        "Real browser Lighthouse reports from Chrome DevTools / Lighthouse CLI. "
        "This is NOT the PageSpeed Insights API, CrUX, GA4 or a sales dataset."
    )
    st.markdown(
        "**Without npm or API keys:** open the public Commerce Lab in Chrome, "
        "press F12 → Lighthouse, choose Mobile or Desktop, click Analyze page load, "
        "then export the full **JSON** report. You may upload it below or place "
        "the report in target/google_measurement/local_lighthouse/."
    )
    target = ROOT / "target" / "google_measurement" / "local_lighthouse"
    try:
        reports = load_lighthouse_reports(target)
    except ValueError as exc:
        st.warning(f"Invalid local Lighthouse report: {exc}")
        reports = []

    uploaded = st.file_uploader(
        "Import real Lighthouse JSON (processed in memory)",
        type=["json"], accept_multiple_files=True, key="local_lh_json",
    )
    if uploaded:
        for file in uploaded:
            try:
                reports.append(parse_lighthouse_report(json.load(file)))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                st.error(f"{file.name}: rejected invalid Lighthouse report: {exc}")

    if not reports:
        st.info("No valid local Chrome Lighthouse report has been imported yet.")
        return

    site_urls = sorted({r["url"] for r in reports})
    selected_url = st.selectbox("Local Lighthouse page", site_urls, key="lh_local_page")
    chosen = [r for r in reports if r["url"] == selected_url]
    latest_by_device = {}
    for item in chosen:
        prev = latest_by_device.get(item["device"])
        if prev is None or item["measured_at_utc"] > prev["measured_at_utc"]:
            latest_by_device[item["device"]] = item
    rows = []
    for device, record in sorted(latest_by_device.items()):
        for category, score in record["scores"].items():
            rows.append({
                "Device": device.title(),
                "Category": category.replace("-", " ").title(),
                "Score": score,
                "Source": "Local Lighthouse CLI / DevTools",
                "Measured": record["measured_at_utc"],
            })
    if rows:
        frame = pd.DataFrame(rows)
        fig = px.bar(
            frame, x="Category", y="Score", color="Device",
            barmode="group", range_y=[0, 100],
            color_discrete_sequence=[PALETTE["cyan"], PALETTE["purple"]],
        )
        fig.update_layout(**plot_config("Local browser Lighthouse scores · 0–100"))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(frame, width="stretch", hide_index=True)
        st.download_button(
            "Export local Lighthouse score summary",
            data=frame.to_csv(index=False).encode("utf-8"),
            file_name="nexus_local_lighthouse_summary.csv",
            mime="text/csv", key="local_lh_export",
        )
    for device, record in sorted(latest_by_device.items()):
        with st.expander(f"{device.title()} · local lab metrics · {record['measured_at_utc']}"):
            st.json({
                "source_system": record["source_system"],
                "lighthouse_version": record["lighthouse_version"],
                "lab_only": True,
                "requested_url": record["requested_url"],
                "lab_metrics": record["lab_metrics"],
            })
    st.caption(
        "Do not treat locally measured Lighthouse lab scores as Google PSI API "
        "server results or representative 75th-percentile real-user Core Web Vitals."
    )


header()
location = ROOT / "target" / "google_measurement" / "marts"
with st.sidebar:
    st.markdown("### NEXUS / SOURCE CONTROLS")
    st.caption("Private local workspace · source-verified reports")
    folder = st.text_input("Validated export folder", value=str(location))
    historical_folder = st.text_input(
        "Historical E-Commerce snapshot file",
        value=str(ROOT / "target" / "ecommerce_bridge" / "snapshot.json"),
        help="Only source-qualified, aggregated dbt marts. No raw user/order IDs.",
    )
    greenweez_folder = st.text_input(
        "Greenweez snapshot file",
        value=str(ROOT / "target" / "greenweez_bridge" / "snapshot.json"),
        help="Only read-only, source-labelled Greenweez dbt mart imports. Never raw orders.",
    )
    st.caption("Google authentication is needed for GA4/GSC only.")
    st.caption("PageSpeed can run on a public HTTPS page without a GA4 property.")
    st.divider()
    st.caption("One NEXUS workspace; E-Commerce/TheLook, Greenweez, Olist and Commerce Lab remain distinct datasets.")

# An entirely empty installation is a NORMAL onboarding state, not a fatal
# dashboard failure. A corrupt/incomplete manifest is still never accepted.
error_message = None
try:
    tables, manifest = load_bundle(Path(folder))
except (OSError, ValueError, json.JSONDecodeError) as exc:
    error_message = str(exc)
    tables = {"ga4": [], "gsc": [], "pagespeed": []}
    manifest = {"source_summary": {}, "warnings": [], "input_snapshot_count": 0}

greenweez_error = None
try:
    greenweez_snapshot = load_greenweez_snapshot(Path(greenweez_folder))
except (ValueError, OSError) as exc:
    greenweez_snapshot = None
    greenweez_error = str(exc)

historical_error = None
try:
    historical_snapshot = load_historical_snapshot(Path(historical_folder))
except (OSError, ValueError) as exc:
    historical_snapshot = None
    historical_error = str(exc)

source_registry = inspect_sources(
    ROOT,
    overrides={
        "ecommerce": Path(historical_folder),
        "greenweez": Path(greenweez_folder),
        "google_marts": Path(folder),
    },
)
source_registry_by_name = {row["source"]: row for row in source_registry}

st.markdown("### Measurement sources")
source_meta = [
    ("GA4 / ACQUISITION", "ga4", "GA4 property access required"),
    ("GSC / ORGANIC SEARCH", "gsc", "Verified Search Console property required"),
    ("PAGESPEED / LIGHTHOUSE", "pagespeed", "Run a public website audit below"),
    ("E-COMMERCE / HISTORY", "historical", "Separate historical orders and sessions"),
    ("GREENWEEZ / FINANCE", "greenweez", "Independent dbt finance and ad marts"),
]
cols = st.columns(5)
for col, (title, key, explanation) in zip(cols, source_meta):
    if key == "historical":
        count = len(historical_snapshot["tables"]["orders"]) if historical_snapshot else 0
        state = (
            "Synthetic source" if historical_snapshot and historical_snapshot["provenance"] == "synthetic_ci"
            else "External · unverified" if historical_snapshot
            else "Invalid source" if historical_error else "Not imported"
        )
    elif key == "greenweez":
        count = len(greenweez_snapshot["tables"]["daily"]) if greenweez_snapshot else 0
        state = (
            "Synthetic source" if greenweez_snapshot and greenweez_snapshot["provenance"] == "synthetic_demo"
            else "External · unverified" if greenweez_snapshot
            else "Invalid source" if greenweez_error else "Not imported"
        )
    else:
        count = len(tables[key])
        state = f"{count:,} API snapshot rows" if count else "Not imported"
    text_style = "" if count else " nexus-source-empty"
    # HTML content below is fixed/number-derived; no user input is interpolated.
    col.markdown(
        '<div class="nexus-source">'
        f'<div class="nexus-source-name">{title}</div>'
        f'<div class="nexus-source-state{text_style}">{state}</div>'
        f'<div class="nexus-source-detail">{explanation}</div>'
        '</div>', unsafe_allow_html=True,
    )

if greenweez_error:
    st.error("Greenweez source integrity gate: " + greenweez_error)
if historical_error:
    st.error("Historical E-Commerce source integrity gate: " + historical_error)

if error_message:
    st.caption("Source status: No complete validated export found. " + error_message)
else:
    st.caption(
        "Source status: Validated local API snapshots · Not a live feed · "
        "No Google Ads spend or verified campaign ROAS"
    )

with st.expander(
    "GET STARTED · Run your first real PageSpeed audit",
    expanded=False,
):
    st.markdown(
        "**No GA4, GSC or BigQuery account is needed for this step.** "
        "Enter any public HTTPS page and explicitly request one real "
        "Google PageSpeed Insights Lighthouse audit. "
        "Google receives the submitted URL; API quotas or availability may apply."
    )
    st.markdown(
        "**Default: our controlled NEXUS Commerce Lab storefront.** "
        "Tricentis and nopCommerce are independent third-party benchmarks. "
        "PageSpeed reports measure the selected public page only; none of "
        "these websites produces the historical TheLook warehouse orders."
    )
    test_choice = st.selectbox(
        "Measurement target",
        options=list(TEST_SITES),
        index=list(TEST_SITES).index(DEFAULT_TEST_SITE),
        help="Selecting a demo URL never starts an audit or retrieves analytics data.",
    )
    suggested_url = test_site_url(test_choice)
    with st.form("real_pagespeed_audit"):
        audit_url = st.text_input(
            "Website URL",
            value=suggested_url,
            key=f"pagespeed_url_{list(TEST_SITES).index(test_choice)}",
            placeholder="https://your-site.example/",
            help="Use a reachable public HTTPS page, not localhost or a private IP.",
        )
        audit_device = st.radio(
            "Test device", options=("mobile", "desktop"),
            horizontal=True, index=0,
        )
        audit_submit = st.form_submit_button(
            "Run real PageSpeed audit", type="primary",
        )
    if audit_submit:
        with st.spinner("Requesting an actual Lighthouse audit from Google…"):
            try:
                completed = audit_public_site(
                    audit_url, audit_device, marts_dir=Path(folder),
                )
            except HTTPError as exc:
                st.error(
                    f"PageSpeed API returned HTTP {exc.code}. "
                    "Check quota, the target page, or optional API key. "
                    "No performance metrics were invented."
                )
            except URLError:
                st.error("Could not reach Google's PageSpeed API. Check your connection.")
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                st.error(f"Audit not imported: {exc}")
            else:
                st.success(
                    f"Google reported a {completed['device']} Lighthouse audit. "
                    "Loading the verified result…"
                )
                st.rerun()
    st.markdown(
        "**For GA4 and Search Console:** these require verified property access. "
        "Run the authenticated collector for the corresponding source, "
        "then rebuild the marts and refresh this page. "
        "See docs/GOOGLE_MEASUREMENT_INTEGRATION.md."
    )

for source_key, table_key in (
    ("GA4", "ga4"), ("Search Console", "gsc"), ("PageSpeed", "pagespeed"),
):
    st.sidebar.caption(f"{source_key}: {len(tables[table_key])} validated rows")
st.sidebar.caption(
    "Commerce Lab GA4 export: "
    + source_registry_by_name["commerce_lab_ga4"]["status"].replace("_", " ")
)
st.sidebar.caption(
    "Historical E-Commerce and Greenweez snapshots: "
    + source_registry_by_name["ecommerce"]["status"].replace("_", " ")
    + " / "
    + source_registry_by_name["greenweez"]["status"].replace("_", " ")
)
if not error_message:
    with st.sidebar.expander("Extraction metadata"):
        st.json({
            "snapshots": manifest.get("input_snapshot_count"),
            "partial_snapshots": manifest.get("partial_snapshot_count", 0),
            "sources": manifest.get("source_summary", {}),
        })

overview_tab, historical_tab, greenweez_tab, tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Overview · Sources", "E-Commerce · Historical", "Greenweez · Finance", "GA4 · Acquisition",
     "GSC · Organic Search", "PSI · Lighthouse",
     "Commerce Lab · Test Events", "Data Contracts"]
)
with overview_tab:
    st.subheader("NEXUS · Unified Evidence Registry")
    st.caption(
        "One E-Commerce product · independent model and measurement domains. "
        "Snapshot availability never implies live collection, verified revenue, "
        "production readiness or a shared merchant identity."
    )
    ready_count = sum(
        row["status"] in ("api_snapshot", "external_unverified", "synthetic")
        for row in source_registry
    )
    invalid_count = sum(row["status"] == "invalid" for row in source_registry)
    st.caption(
        f"Imported source groups: {ready_count}/{len(source_registry)} · "
        f"Invalid source groups: {invalid_count}. "
        "These are source status counts, not traffic, order or financial KPIs."
    )
    registry_frame = pd.DataFrame([
        {
            "Source": row["label"],
            "Status": row["status"].replace("_", " "),
            "Rows": row["rows"],
            "Provenance": row["provenance"] or "none",
            "Interpretation": row["detail"],
        }
        for row in source_registry
    ])
    st.dataframe(registry_frame, width="stretch", hide_index=True)
    st.caption(
        "This catalog is refreshed from local validated files on each rerun. "
        "Use `python -m scripts.nexus_workspace status` to audit from a terminal."
    )
    st.subheader("Separate business systems")

    st.markdown(
        "**E-Commerce / TheLook:** independent historical orders, web events "
        "and dbt marts; not observed transactions on the new Lab.\n\n"
        "**Greenweez:** separate order-level finance, margin and paid-campaign "
        "dbt marts imported through an explicit read-only contract.\n\n"
        "**NEXUS Commerce Lab:** owned, no-payment test storefront whose opted-in "
        "GA4 `lab_*` events are NOT purchase revenue."
    )
    st.info(
        "No cross-business sum of revenue, margin, orders, customers or ROAS "
        "is produced. Greenweez campaign source CPC/CTR are measured from ad "
        "aggregates; campaign-attributed revenue is unavailable."
    )
    st.info(
        "Financial figures from synthetic CI marts or externally imported but "
        "unaudited data are explicitly labeled in their separate tabs. "
        "The observed GA4 Realtime screenshot confirms the web tag collected "
        "test events; it does NOT populate the local API snapshot automatically."
    )
with historical_tab:
    historical_ecommerce_tab(Path(historical_folder))
with greenweez_tab:
    greenweez_finance_tab(Path(greenweez_folder))
with tab1:
    ga4_tab(tables["ga4"])
with tab2:
    gsc_tab(tables["gsc"])
with tab3:
    pagespeed_tab(tables["pagespeed"])
    local_lighthouse_tab()
with tab4:
    commerce_lab_ga4_tab()
with tab5:
    st.subheader("Measurement Integrity & Next Steps")
    st.markdown(
        "**GA4:** one property at a time. Active users cannot be summed across channel/date rows.\n\n"
        "**GSC:** one property at a time. CTR = clicks / impressions and "
        "position uses an impressions-weighted calculation.\n\n"
        "**PageSpeed:** public on-demand Lighthouse *lab* audits; "
        "CrUX real-user field measurements are not connected.\n\n"
        "**Google Ads:** campaign cost and validated attribution are absent, "
        "so CAC and ROAS are unavailable.\n\n"
        "**Historical commerce:** E-Commerce, Olist and Greenweez are "
        "not part of the Google source identity.\n\n"
        "**Greenweez:** separate finance and campaign marts; externally "
        "sourced snapshots remain unverified until independent reconciliation. "
        "Do not join Greenweez to TheLook/Lab events or claim per-source ROAS."
    )
    if error_message:
        st.info(
            "Start with the PageSpeed form above. For GA4/GSC, grant "
            "read-only access to the appropriate owned property; no "
            "test numbers are offered as live data."
        )
    for warning in manifest.get("warnings", []):
        st.caption("• " + str(warning))
