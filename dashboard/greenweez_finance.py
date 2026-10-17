"""NEXUS single-screen source-isolated Greenweez finance module."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.nexus_theme import style_chart, COLORS

from scripts.greenweez_bridge import load_snapshot

CYAN = COLORS["cyan"]
PURPLE = COLORS["purple"]
PINK = "#EC6DCB"


def greenweez_snapshot(default_path: Path) -> dict | None:
    """Load only complete, validated local bridge files. No remote API."""
    return load_snapshot(default_path)


def greenweez_finance_tab(path: Path) -> None:
    st.subheader("Greenweez · Finance & Marketing")
    st.caption(
        "Separate dbt business domain. Source: Greenweez finance_campaigns_day/month "
        "and marketing_source_month. Never joined to TheLook users, NEXUS Lab "
        "GA4 events, or the personal portfolio."
    )
    try:
        snapshot = greenweez_snapshot(path)
    except (OSError, ValueError) as exc:
        st.error(f"Greenweez source rejected: {exc}")
        return

    if snapshot is None:
        st.info(
            "Greenweez finance is not yet imported. Export an EXISTING read-only "
            "dbt DuckDB mart from integrations/greenweez/, then refresh this tab. "
            "No sample revenue is substituted."
        )
        st.code(
            'python -m scripts.greenweez_bridge --db '
            '"integrations/greenweez/target/demo.duckdb" '
            '--provenance synthetic_demo',
            language="bash",
        )
        st.caption(
            "Models and real-source instructions: integrations/greenweez/README.md "
            "(maintained inside this NEXUS repository)."
        )
        return

    provenance = snapshot["provenance"]
    source_title = (
        "Synthetic dbt demonstration" if provenance == "synthetic_demo"
        else "External Greenweez source · NOT independently verified"
    )
    st.warning(
        f"**{source_title}.** Financial numbers have NOT been audited against "
        "an authoritative upstream business/BigQuery source. Do not present them "
        "as verified real trading results."
    )
    st.caption(
        f"Source system: {snapshot['source_system']} · "
        f"Imported: {snapshot['generated_at_utc']} · "
        f"Upstream database SHA256: {snapshot['source_sha256'][:16]}… · "
        "Currency/unit not independently confirmed"
    )
    rows = snapshot["tables"]["daily"]
    d0 = date.fromisoformat(rows[0]["date"])
    d1 = date.fromisoformat(rows[-1]["date"])
    col1, col2 = st.columns(2)
    start = col1.date_input("Greenweez from", value=d0, min_value=d0, max_value=d1, key="gwz_from")
    end = col2.date_input("Greenweez to", value=d1, min_value=d0, max_value=d1, key="gwz_to")
    if start > end:
        st.warning("Greenweez date range is reversed.")
        return
    selected = [r for r in rows if start <= date.fromisoformat(r["date"]) <= end]
    if not selected:
        st.info("No Greenweez rows in selected date range.")
        return

    revenue = sum(r["revenue"] for r in selected)
    transactions = sum(r["transactions"] for r in selected)
    op_margin = sum(r["operational_margin"] for r in selected)
    ads_spend = sum(r["ads_cost"] for r in selected)
    after_ads = sum(r["ads_margin"] for r in selected)

    columns = st.columns(5)
    for col, (label, value) in zip(columns, (
        ("Greenweez revenue · stored units", f"{revenue:,.2f}"),
        ("Greenweez orders · upstream mart", f"{transactions:,}"),
        ("Greenweez operating margin", f"{op_margin:,.2f}"),
        ("Greenweez ad spend", f"{ads_spend:,.2f}"),
        ("Greenweez margin after ads", f"{after_ads:,.2f}"),
    )):
        col.metric(label, value)

    avg_basket = revenue / transactions if transactions else None
    blended_roas = revenue / ads_spend if ads_spend else None
    st.caption(
        f"Weighted average basket: {avg_basket:,.2f}" if avg_basket is not None
        else "Weighted average basket: N/A (no transactions)"
    )
    st.caption(
        f"**Blended** Greenweez ROAS: {blended_roas:.2f}× · "
        "revenue/ad spend across all paid sources, NOT attributed by campaign."
        if blended_roas is not None
        else "Blended Greenweez ROAS: N/A (no ad spend)."
    )
    frame = pd.DataFrame(selected)
    frame["date"] = pd.to_datetime(frame["date"])
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(frame, x="date", y="revenue", markers=True,
                      color_discrete_sequence=[CYAN],
                      title="Greenweez · Daily reported revenue")
        style_chart(fig, str(fig.layout.title.text or ""))
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig = px.bar(frame, x="date", y="ads_cost",
                     color_discrete_sequence=[PURPLE],
                     title="Greenweez · Daily ad cost")
        style_chart(fig, str(fig.layout.title.text or ""))
        st.plotly_chart(fig, width="stretch")

    by_source = snapshot["tables"]["marketing_source"]
    if by_source:
        st.markdown("#### Campaign efficiency by source · monthly aggregates")
        st.caption(
            "All per-source figures are from native ad platform aggregates. "
            "No per-source revenue attribution or per-source ROAS is computed."
        )
        months = sorted({row["datemonth"] for row in by_source})
        chosen = st.selectbox("Greenweez source month", months, key="gwz_source_month")
        subset = [r for r in by_source if r["datemonth"] == chosen]
        spend_df = pd.DataFrame(subset)
        fig = px.bar(spend_df, x="paid_source", y="ads_cost",
                     color="paid_source", color_discrete_sequence=[CYAN, PURPLE, PINK],
                     title=f"Campaign spend by paid platform · {chosen}")
        style_chart(fig, str(fig.layout.title.text or ""))
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")
        with st.expander("Source-level CPC, CTR and ad spend share"):
            st.dataframe(spend_df, width="stretch", hide_index=True)
    else:
        st.caption("No per-source ad/clicks/impressions mart in this Greenweez export; CPC/CTR hidden.")

    refunds = snapshot["tables"]["refunds"]
    if refunds:
        st.markdown("#### Refund field · separate source interpretation")
        st.warning(
            "The historical Google Sheets 'refund' field has unresolved "
            "semantics/units in the upstream model. It is not subtracted "
            "from revenue, margin or order KPIs here."
        )
        with st.expander("Monthly refund observations (source values)"):
            st.dataframe(pd.DataFrame(refunds), width="stretch", hide_index=True)

    with st.expander("Finance source mart · inspect, source-qualified export"):
        st.dataframe(frame, width="stretch", hide_index=True)
        st.download_button(
            "Download selected Greenweez mart rows (provenance-labelled)",
            data=frame.assign(source_system=snapshot["source_system"], provenance=provenance)
                      .to_csv(index=False).encode("utf-8"),
            file_name=f"nexus_greenweez_{provenance}.csv",
            mime="text/csv", key="gwz_export",
        )
