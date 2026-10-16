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
