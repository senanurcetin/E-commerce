# E-commerce analytics milestone — candidate release notes

**Status:** Not a published release. No tag or GitHub Release is created by this file. Review a stable snapshot and choose a version only after independent verification.

## Included capabilities

- Three-layer dbt architecture (staging, intermediate, marts) for e-commerce orders and clickstream analytics.
- BigQuery-oriented transformations with a reproducible local DuckDB adapter/seed path.
- Three genuine Power BI dashboard pages covering channel efficiency, acquisition/basket trends, and demographics.
- A separate Olist Python notebook, explicitly **not** the same dataset as the main clickstream/order models.
- Documented source-vs-signup traffic fields and conversion/attribution caveats.

## Evidence and limitations

- Reproduction is based on synthetic DuckDB seed data; published warehouse-scale counts should not be misread as the seed's volume.
- Traffic-channel revenue efficiency is **not acquisition cost** when advertising spend is missing.
- The Turkish Power BI abbreviation `B` means *bin* (thousands), not billions.
- A large embedded-output notebook is intentionally retained until reviewers decide which plots must remain. See [the audit helper](../scripts/notebook_output_audit.py).

## Checklist before tagging

- [ ] Identify and review an immutable candidate commit.
- [ ] Run `dbt deps`, `dbt seed`, `dbt run` and `dbt test` with `--profiles-dir .github/dbt-profiles` using the documented local environment.
- [ ] Inspect three Power BI screenshots and check their numerical/unit captions.
- [ ] Confirm external dataset rights and preserve the Olist analysis independently.
- [ ] Include reproducibility details, limits and actual validation evidence in the GitHub Release.

Related: [primary README](../README.md), [data models](../models/) and [Power BI report assets](assets/).
