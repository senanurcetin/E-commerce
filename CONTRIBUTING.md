# Contributing to NEXUS Commerce Intelligence

Contributions to dbt model correctness, documentation, reproducible SQL analyses and test coverage are welcome.

## Offline checks (DuckDB)

```bash
python -m pip install dbt-duckdb
dbt deps --profiles-dir .github/dbt-profiles
dbt parse --profiles-dir .github/dbt-profiles
dbt seed --profiles-dir .github/dbt-profiles
dbt run --profiles-dir .github/dbt-profiles
dbt test --profiles-dir .github/dbt-profiles --exclude "source:*"
```

The DuckDB profile and committed sample seeds are intended for local checks; BigQuery is not required for the checks above.

## Pull requests

- Explain the source grain, transformation logic and downstream marts affected.
- Add/adjust schema or data tests for new models or changed assumptions.
- Document metric definitions, especially attribution and funnel denominators; do not infer advertising spend where none exists.
- Keep real customer records, service-account credentials and downloaded private data out of commits and CI artifacts.

Report security issues privately as described in [SECURITY.md](SECURITY.md).
