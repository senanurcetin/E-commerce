# NEXUS Commerce Intelligence — Power BI Theme and Acceptance

The importable JSON theme at [themes/nexus-commerce.json](themes/nexus-commerce.json) now matches the Streamlit NEXUS **midnight navy / cyan / purple** design system. It does **not** prove the original PBIX file has been opened, recolored or refreshed.

| Token | Hex | Usage |
| --- | --- | --- |
| Primary canvas | `#080F20` | Power BI page background |
| Visual surface | `#111E38` | Cards and charts |
| Primary text | `#EDF5FF` | Title and card values |
| Secondary text | `#B8C8DF` | Labels and grid annotations |
| NEXUS cyan | `#47DFF2` | Key data series / table accent |
| NEXUS purple | `#A892F4` | Secondary data series |
| Approved positive | `#7ADDB8` | Positive semantic value |
| Approved warning | `#EFC98D` | Risk / warning value |

Import the theme into an **actual editable** Power BI Desktop report with **View → Themes → Browse for themes**. Individual custom visual overrides, white backgrounds, date filters, drill behaviors and slicer formatting must still be examined manually.

### QA automation

From the E-Commerce repo root:

~~~cmd
python -m scripts.powerbi_acceptance --output target\powerbi_acceptance.json
~~~

This generates a source/documentation audit of JSON theme tokens, the DAX measure registry, attribution semantics and editability. It intentionally leaves **Desktop render, current warehouse refresh, mobile layout, visual-level acceptance and financial reconciliation as NOT DONE** until independent evidence exists. A PBIX merely being present does not auto-promote the release decision.

When the real source is available, run `python -m scripts.powerbi_acceptance --report C:\path\report.pbix` and then perform the checklists in [Power BI visual QA](../docs/POWER_BI_VISUAL_QA.md). Actual Desktop access remains mandatory for final acceptance.

### Known metric distinctions

- Signup source and session traffic source are different dimensions.
- Financial revenue must be read from its own historical E-Commerce mart, never from Greenweez or NEXUS Commerce Lab sandbox events.
- The PE4 CAC input is a sessions-per-user **proxy**, not money spent on customer acquisition.
- The old three PNG illustrations are **historical screenshots**, not renewed evidence after this theme change.
- Turkish **B** means bin (1,000), not billion.

**Release decision: HOLD.** Original editable report and fresh authorized data/render evidence are not established in this repo.
