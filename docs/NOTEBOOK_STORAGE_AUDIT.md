# Olist analysis notebook — lossless storage review (12 October 2026)

This audit inspected the actual `notebooks/olist-ecommerce-analysis.ipynb` blob
(`d0a8b5918ad329acf5eb1dcdfc416e53aa78042a`) and counted the JSON cell
outputs. It did not execute the notebook, download proprietary datasets, or
change reported results.

## Measured breakdown

| Measure | Observed |
| --- | ---: |
| Notebook Git blob | 18,562,754 bytes |
| Total cells | 91 |
| Code / Markdown cells | 38 / 53 |
| Stored outputs | 46 |
| Stored PNG outputs | 0 |
| Serialized stored output payload | Approximately 18.47 MB |
| Dominant output MIME type | `text/html` with Plotly chart data |

**Root cause:** Several Plotly scatter, distribution and box-plot outputs
contain large embedded HTML and point data. The three largest chart outputs
alone occupy approximately **3.83 MB**, **3.72 MB** and **3.43 MB**.
Other large Plotly outputs occupy approximately **1.98 MB**, **1.89 MB**
and **1.27 MB** each. These are real stored analytical visuals,
not decorative GitHub cover images.

## Preservation decision

**Do not strip all cell outputs to make a smaller repository.**
That would delete the charts the reviewer expects to inspect. The code and
Markdown would remain, but the notebook would no longer display the reported
visual analyses without rerunning cells against the original data.

The helper `python scripts/notebook_output_audit.py` reports output sizes without
changing files. Its `--clean` mode now refuses to remove Plotly output without
`--acknowledge-output-loss`. That override creates only a separate copy;
neither the helper nor this audit overwrites the original notebook.

## Proposed genuinely smaller deliverable

1. Export **representative figures** to authentic static PNG/SVG files, or
   generate a notebook containing Plotly figure specs instead of duplicated
   standalone HTML with large embedded row-level data.
2. Verify the plots against the original notebook and source records,
   especially outlier trimming, scatter density and regression trends.
3. Retain an immutable original or clearly traceable source version and
   document any sampling/aggregation. Do not claim sampled plots show every row.
4. Compare notebook sizes and manually review GitHub rendering and offline
   reproducibility before replacing the original.
5. Update README screenshots **after** the revised visual evidence is approved;
   only then should GitHub Social Preview artwork be regenerated.

**Current state:** No chart output, data point, notebook cell, or embedded
visual evidence was deleted by this work. The safety guard and these
measured findings are the completed changes.
