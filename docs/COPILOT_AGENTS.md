# GitHub Copilot custom agents — E-commerce

The two version-controlled profiles in `.github/agents/` are **configuration**, not proof that an interactive Copilot session was executed. They can be selected in supported GitHub Copilot interfaces once the profile is visible to the user's entitlement and repository policies.

| Agent file | Task scope | Guardrail |
| --- | --- | --- |
| `commerce-dbt-integrity.agent.md` | dbt staging/intermediate/marts, revenue/return correctness, first-touch attribution, tests | Synthetic/local-first, no BigQuery or CI |
| `commerce-powerbi-evidence.agent.md` | DAX/model lineage, Power BI screenshot provenance and theme QA | No invented PBIX/PBIP, render, refresh or screenshot |

## How to select

On GitHub.com, start a supported Copilot coding-agent task in this repository and choose the custom agent in the agent selector. In a supported IDE, select it from the Copilot agents dropdown. In the Copilot CLI use `/agent` to choose a profile; repository configuration may require restarting the client or refreshing the selector.

**The agents will not run continuously on their own.** Both are manually invocable and have model-triggered invocation disabled. A PR/merge requires an authorized user or an explicitly delegated workflow. Merely merging the files does not run a Copilot agent.

## Manual smoke-test prompts (no CI)

1. Select **Commerce dbt Integrity** and ask: "Read `fct_order_marketing.sql` and `tests/fct_order_marketing_status_reconciliation.sql`. Explain the order-item grain, how a returned item affects revenue, and which test would catch a stale return amount. Do not modify any file or run remote commands." Expected: correct status-based metric logic and explicit test limitations.
2. Use the same agent: "Compare BigQuery and DuckDB branches of `fct_marketing_web_performance.sql`. Confirm how session traffic source and browser first touch are ordered and how `unknown` is skipped. Only inspect sources." Expected: event-ID final tiebreak and accurate session-grain explanation.
3. Select **Commerce Power BI Evidence**: "Can we claim `powerbi/themes/nexus-commerce.json` has been applied to a current editable report? What proof is missing?" Expected: **no**, because the editable PBIX/PBIP and actual Desktop refresh/render evidence are absent.
4. With the evidence agent: "Explain why `dim_user.signup_traffic_source` cannot be used interchangeably with `fct_marketing_web_performance.traffic_source`, and what `B` means on historical Turkish screenshots." Expected: acquisition versus session attribution, and `B=thousand`.

If a client is available locally and the repository is checked out, existing offline checks include:

```bash
python scripts/check_order_fact_refresh.py
python scripts/check_order_fact_invariants.py
python -m unittest discover -s tests -p 'test_session_first_touch_order.py'
```

Do **not** interpret a successful YAML/frontmatter check or these Python checks as evidence that a Copilot session, BigQuery dbt run, or Power BI Desktop review has completed. CI providers are out of scope.

## Review and acceptance record

- [x] Two agent definitions committed under standard repository paths.
- [x] Repository-wide Copilot instructions present.
- [x] Offline QA scenario prompts documented.
- [ ] Actual Copilot agent appears and can be selected in the user's client.
- [ ] Both agents answer the four smoke-test prompts as expected.
- [ ] Full dbt tests and editable Power BI report visual QA — independent release gates.

Record a real client run, selected agent, date, test prompt and observed output here only after it happens.
