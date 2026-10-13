---
description: Read-only acceptance test for Commerce dbt Integrity custom agent
---

# Commerce dbt Integrity — manual acceptance

Agent invocation: use a supported IDE agent selector **or** GitHub Copilot CLI with `--agent=commerce-dbt-integrity`. CLI agent selection is valid; do not mark this test NOT RUN merely because no IDE selector was used. The wrapper must record the requested agent ID and CLI exit status independently. If the actual loaded profile cannot be independently confirmed, report agent identity UNVERIFIED separately from the source-review checks. Do not infer successful runtime tests from a read-only answer.

Inspect repository instructions and these source files:
- models/marts/fct_order_marketing.sql
- models/intermediate/int_orders_enriched.sql
- models/marts/fct_marketing_web_performance.sql
- tests/fct_order_marketing_status_reconciliation.sql
- tests/fct_order_marketing_invalid_sale_price.sql

Without editing any file or executing commands:

1. Explain the order-item grain versus the web-session grain and a possible join fan-out.
2. For a returned item, derive recognized revenue, returned revenue and both status flags. Identify the committed test that detects a stale financial amount.
3. Compare BigQuery and DuckDB unknown-source filtering and deterministic first-touch ordering for source/browser.
4. Explain why user signup acquisition source differs from session traffic source.

Cite source files for every conclusion. Report a PASS/FAIL/UNVERIFIED matrix. Explicitly distinguish code inspection from any unexecuted dbt, BigQuery or dashboard tests. No CI, network, installs, edits or private customer data.