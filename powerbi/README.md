# NEXUS Commerce — Power BI theme source

The version-controlled [NEXUS Commerce JSON theme](themes/nexus-commerce.json) now uses the same **navy-and-blue presentation direction** as the NEXUS portfolio. It is an **importable design proposal**, not an applied Power BI Desktop report or an updated screenshot.

## Current design tokens

| UI role | Color | Usage |
| --- | --- | --- |
| Header / shell | `#061524` | Navigation and report framing |
| Text | `#091625`, `#122942` | Titles, KPI text, chart labels |
| Canvas | `#F7F8FA`, `#FFFFFF` | Page and visual backgrounds |
| Primary data blue | `#0572A8` | Primary comparison and table accent |
| Secondary lavender | `#8F9BFF` | Secondary categorical series |
| Positive emphasis | `#487FD8` | Positive semantic signal (not green) |
| Warning / risk | `#B47725`, `#C24363` | Thresholds or risk conditions |
| Border | `#D9E1E9` | Card and visual boundaries |

**Eight categorical colors** are defined in `dataColors`; not all pairs have equivalent luminance, so verify legibility on the real charts, particularly small bars, legends and data labels. Color must never be the only way to communicate a KPI change or risk status.

The editorial cover in `docs/assets/ecommerce-analytics-cover.svg` still uses its earlier violet/indigo artwork. It is **not** a screenshot or evidence that this newer theme was deployed. Its potential redesign requires a separate image review.

## Import and review in Power BI Desktop

1. Open the **original report file** from its authorized local source. This repository does not contain a `.pbix` or `.pbip`, so the report cannot be edited or rendered by a GitHub-only change.
2. In **View → Themes → Browse for themes**, choose [`themes/nexus-commerce.json`](themes/nexus-commerce.json).
3. Inspect every report page: slicer/filter states, KPI titles, relative contrast, axis/legend legibility, tooltips, data labels, drill interactions and any per-visual formatting that overrides the theme.
4. Independently reconcile conversion, user acquisition, revenue and basket metrics against the governed mart outputs and the [DAX measures documentation](../docs/dax-measures.md). Preserve the distinction between **signup acquisition source** and **session traffic source**.
5. Once the current report has passed, take fresh *actual Power BI Desktop* screenshots, record the report/version/date and replace the historical assets only after visually comparing them at 100% and checking that no personal/client data appears.
6. Confirm appearance in both desktop and mobile/published views. Applying a JSON theme does not automatically update every custom visual, report container, or preformatted element.

## Historical screenshot inventory

| Existing asset | Report view |
| --- | --- |
| [Channel performance](../docs/assets/powerbi-channel-performance.png) | Channel Acquisition Efficiency & Executive Scorecard |
| [Traffic trend](../docs/assets/powerbi-traffic-trend.png) | Signup, traffic attribution and basket analysis |
| [Demographics](../docs/assets/powerbi-demographics.png) | Age, gender, country and customer type |

These are **historical captures** associated with the [README's three-page gallery](../README.md#power-bi-dashboard). They have **not** been recaptured using the revised navy-blue theme and are **not** evidence of a fresh Desktop refresh. See the [visual acceptance gate](../docs/POWER_BI_VISUAL_QA.md).

**Release status (12 October 2026): HOLD for Desktop/theme import and numerical reconciliation.** This edit changes an importable JSON theme and documentation only; it does not modify or publish a Power BI report or regenerate screenshots.
