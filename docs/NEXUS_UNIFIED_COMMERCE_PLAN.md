# NEXUS Commerce Intelligence — One Workspace, Separate Data Sources

## Goal and architecture

E-Commerce is the MASTER GitHub product repository and now hosts one NEXUS Streamlit interface with independent tabs: **Overview**, **Greenweez Finance**, **GA4 Acquisition**, **GSC Search**, **PageSpeed**, **NEXUS Commerce Lab test events** and **Data Contracts**.

- E-Commerce / TheLook historical business analytics: existing dbt and Power BI artifacts within this repository.
- Greenweez: original independent dbt finance/campaign upstream at https://github.com/senanurcetin/greenweez-finance-campaign-analytics. E-Commerce now contains its **read-only DuckDB finance-mart bridge and its own NEXUS visual module**; raw order/customer data is not copied.
- NEXUS Commerce Lab: owned sandbox website, optional opted-in GA4 custom lab events; never a source of historical TheLook orders.
- Olist notebooks: separate sample business domain.

The addition is an **integrated app / data-product view**, not a row-wise merger of companies or proof that they share customers, transactions, currency, advertisers, or a date window. The original Greenweez dbt project remains a distinct upstream dependency at this stage.

### Source statuses and controls

1. **Not imported**: No Greenweez snapshot; never display fabricated revenue.
2. **Synthetic demo**: Its upstream DuckDB seed/demo data is explicitly labelled as synthetic, including chart/KPI screens.
3. **External unverified**: The file may be extracted from a non-demo Greenweez DuckDB; its business provenance has not been reconciled to an authoritative source. A schema pass is NOT evidence of a real financial fact.
4. **Verified real data (future)**: Requires independent authorized BigQuery/source totals, currency, date range, refund definition, and model/Power BI reconciliation. No automatic path in the bridge can grant this status.

Bridge technical gates: strict expected schema and mart grains, SHA-256 of original DuckDB file, generation timestamp, row count equality, sum-of-days against month, advertising margin identity and optional monthly ad-platform spend equality. Unknown columns, negative ad spend, duplicate grains, invalid ratios, missing marts or partial data are rejected. Full upstream DuckDB is opened read-only.

### Run in Windows

From existing E-Commerce checkout:

~~~cmd
cd /d C:\Users\MONSTER\E-commerce
git pull origin main
python -m pip install -r dashboard\requirements.txt
python -m streamlit run dashboard\google_marketing_app.py
~~~

**Connect Greenweez synthetic demo as a clearly labeled test source** (the original Greenweez dbt project must first have built the database):

~~~cmd
cd /d C:\Users\MONSTER\E-commerce
python -m scripts.greenweez_bridge --db "C:\Users\MONSTER\greenweez-finance-campaign-analytics\target\demo.duckdb" --provenance synthetic_demo
~~~

**Connect an independently available real-source candidate** (for example, authorized Greenweez fvt_gsheet BigQuery-export dbt marts), explicitly marked UNVERIFIED until reconciled:

~~~cmd
python -m scripts.greenweez_bridge --db "C:\Users\MONSTER\greenweez-finance-campaign-analytics\target\gsheet_real.duckdb" --provenance external_unverified
~~~

Both commands output only gitignored E-Commerce target/greenweez_bridge/snapshot.json. The Greenweez tab reads that local snapshot and does not query credentials, raw orders or third-party production services.

### Preserved KPI semantics

- Weighted average basket = sum(revenue) / sum(transactions).
- Operational margin includes upstream shipping and logistics components; margin after ads subtracts ad spend.
- Days with ad spend but no orders are preserved.
- **Blended ROAS** is ratio of total Greenweez revenue to total Greenweez ad spend. Per-source ad-platform CPC, CTR and spend share **are not revenue attribution or source-level ROAS**.
- Greenweez historical refunds have uncertain units; don't subtract them or publish net revenue unless the unit is independently confirmed.
- Do not sum monetary values, customers or transactions across Greenweez, TheLook and the controlled NEXUS Commerce Lab. Currency is not verified by this bridge.

## Release plan

| Stage | Deliverable | Status |
| --- | --- | --- |
| 1 | Greenweez original schema audit, distinct source identity | Code complete |
| 2 | E-Commerce-local read-only Greenweez finance mart bridge | Code complete, CI acceptance pending |
| 3 | Greenweez charts + an overview tab in existing NEXUS app | Code complete, CI acceptance pending |
| 4 | E-Commerce dbt, storefront, dashboard and bridge CI green | Pending |
| 5 | Original Greenweez DuckDB on authorized Windows machine; read-only snapshot created and visually inspected | Pending |
| 6 | Upstream real Greenweez financial totals reconciled vs source; currency/refund semantics accepted | Pending |
| 7 | Commerce Lab GA4 read-only Property ID authorization, actual event extraction and dashboard validation | Pending |
| 8 | Original Power BI Desktop report source measures/screens reconciled | Pending |
| 9 | Optional deeper consolidation: copy/rehome upstream Greenweez dbt project as isolated subproject after license/build review | Future, NOT claimed in this phase |
| 10 | Final business/evidence and UI acceptance for presentation | Pending |

Source schema tests use synthetic CI fixtures exclusively, never as real production numbers. The unified app is not presentation-ready until business data, original BI artifacts and source ownership are independently checked.
