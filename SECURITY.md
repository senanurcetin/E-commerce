# Security policy

## Private vulnerability reports

Email [senanur.cetin.work@gmail.com](mailto:senanur.cetin.work@gmail.com) with subject `[NEXUS Commerce Intelligence security]`, the affected version/commit, impact and safe reproduction steps. Do not post credentials, personal data or actionable exploit details in a public issue. This research/portfolio repository has no guaranteed security response or support schedule.

## Warehouse and data boundaries

- Use the synthetic DuckDB demo for public reproduction; do not upload production customer data into issues or public artifacts.
- Keep BigQuery service-account credentials and local profiles out of version control. Grant least-privilege IAM roles.
- Validate SQL/model changes against synthetic seeds before running on a paid warehouse.
- Reporting results from source datasets does not imply personal-data consent or permission to redistribute third-party records.
