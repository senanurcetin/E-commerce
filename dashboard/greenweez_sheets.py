"""NEXUS Greenweez actual Google Sheets observations, strictly source-labelled."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.nexus_theme import style_chart, COLORS

from scripts.greenweez_sheets_observed import load_observed


def greenweez_sheets_tab(path: Path) -> None:
    st.subheader("Greenweez · Original Google Sheets Evidence")
    st.caption(
        "Authenticated owner-provided Sheets · historical source observations, "
        "not a live financial feed or dbt-reconciled report. "
        "Only date-level aggregates: no raw order IDs, names or campaign keys."
    )
    try:
        obs = load_observed(path)
    except ValueError as exc:
        st.error(str(exc))
        return
    if obs is None:
        st.info(
            "No authenticated Google Sheets observations imported. "
            "This page never substitutes synthetic or unverifiable finance numbers."
        )
        return
    st.warning(
        "Original Google Sheets observations · **financial semantics and currency "
        "NOT independently verified**. Turnover and advertising cost are shown "
        "in original stored units. These are not certified sales, margin, "
        "ROAS or attribution outcomes."
    )
    st.caption(
        f"Observed at: {obs['observed_at_utc']} · "
        f"Order worksheet rows: {obs['row_counts']['orders']:,} · "
        f"Campaign worksheet rows: {obs['row_counts']['campaigns']:,}. "
        "No user/order/campaign identifiers are stored in the aggregate snapshot."
    )
    quality = obs["origin_coverage"]
    ga_total = quality["ga_rows"]
    non_ga_total = quality["non_ga_rows"]
    ga_missing = quality["ga_missing_turnover"]
    non_ga_missing = quality["non_ga_missing_turnover"]
    all_rows = ga_total + non_ga_total
    missing_total = ga_missing + non_ga_missing
    coverage_fraction = (all_rows - missing_total) / all_rows if all_rows else 0
    st.markdown("#### Turnover coverage · source reconciliation")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Known turnover coverage", f"{coverage_fraction:.1%}")
    q2.metric("GA-marked rows · is_ga=1", f"{ga_total:,}")
    q3.metric("Non-GA rows · is_ga=0", f"{non_ga_total:,}")
    q4.metric("Rows with missing turnover", f"{missing_total:,}")
    st.progress(coverage_fraction, text=f"{all_rows - missing_total:,} of {all_rows:,} order rows contain a turnover value")
    if ga_missing == 0 and non_ga_missing == non_ga_total and ga_total > 0:
        st.warning(
            "Source-level finding: every is_ga=0 row has blank turnover, "
            "while all is_ga=1 rows contain turnover. This is a conditional "
            "coverage pattern, **not evidence of zero revenue** for is_ga=0. "
            "The source owner must confirm whether non-GA orders intentionally "
            "lack a financial value, and whether the two groups are comparable."
        )
    else:
        st.warning(
            f"GA-marked rows with missing turnover: {ga_missing:,}; "
            f"non-GA rows with missing turnover: {non_ga_missing:,}. "
            "Incomplete financial fields never count as zero revenue."
        )
    with st.expander("What these source amounts do and do not mean"):
        st.markdown(
            "**Known:** worksheet turnover is observed only on rows with values; "
            "the count, coverage and original stored numbers have been checked.\n\n"
            "**Unknown:** settlement/payment completion, why non-GA records "
            "lack turnover, reporting currency, tax/refund treatment, and "
            "equivalence with Greenweez's separate finance dbt marts.\n\n"
            "**Decision:** don't extrapolate, zero-fill or show an overall "
            "transaction-level revenue, ROAS or profit KPI until signed off."
        )
    orders = pd.DataFrame(obs["daily_orders"])
    campaign = pd.DataFrame(obs["daily_campaigns"])
    orders["date"] = pd.to_datetime(orders["date"])
    campaign["date"] = pd.to_datetime(campaign["date"])
    first, second, third = st.columns(3)
    first.metric("Source order rows · not reconciled transactions", f"{orders['order_rows'].sum():,}")
    second.metric("Known distinct order IDs · incomplete if IDs missing", f"{orders['distinct_order_ids'].sum():,}")
    third.metric("Nonblank turnover values · stored units", f"{orders['turnover_as_stored'].sum():,.2f}")
    missing_ids = int(orders["missing_order_ids"].sum())
    if missing_ids:
        st.warning(f"{missing_ids:,} source order rows have no order ID; the distinct count is only a lower bound.")
    missing_turnover = int(orders["missing_turnover_rows"].sum())
    if missing_turnover:
        st.warning(f"{missing_turnover:,} order rows have blank turnover; the displayed sum covers only observed values.")
    incomplete_ads = sum(int(campaign[col].sum()) for col in ("missing_cost_rows", "missing_impressions_rows", "missing_clicks_rows"))
    if incomplete_ads:
        st.warning("Campaign worksheets have incomplete cost, impressions or clicks. Charts include observed numeric values only.")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(
            orders, x="date", y="turnover_as_stored", markers=True,
            color_discrete_sequence=[COLORS["cyan"]],
            title="Daily worksheet turnover · as stored",
        )
        style_chart(fig, str(fig.layout.title.text or ""))
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig = px.bar(
            campaign, x="date", y="cost_as_stored", color="paid_source",
            color_discrete_sequence=[COLORS["purple"], COLORS["cyan"], "#EC6DCB", "#78A7FF"],
            title="Campaign worksheet advertising costs · as stored",
        )
        style_chart(fig, str(fig.layout.title.text or ""))
        st.plotly_chart(fig, width="stretch")
    st.caption(
        "These workbook sources may differ from the Greenweez finance dbt input "
        "window and lineage. They are not merged into finance margin/ROAS; "
        "no campaign-level causal revenue attribution has been established."
    )
    with st.expander("Aggregated source worksheets — no personal identifiers"):
        a, b = st.tabs(["Order observations", "Campaign observations"])
        with a:
            st.dataframe(orders, hide_index=True, width="stretch")
        with b:
            st.dataframe(campaign, hide_index=True, width="stretch")
