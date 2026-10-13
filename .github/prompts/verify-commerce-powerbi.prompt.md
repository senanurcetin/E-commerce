---
description: Read-only acceptance test for Commerce Power BI Evidence custom agent
---

# Commerce Power BI Evidence — manual acceptance

Agent invocation: use a supported IDE agent selector **or** GitHub Copilot CLI with `--agent=commerce-powerbi-evidence`. CLI agent selection is valid; do not mark this test NOT RUN merely because no IDE selector was used. The wrapper must record the requested agent ID and CLI exit status independently. If the actual loaded profile cannot be independently confirmed, report agent identity UNVERIFIED separately from the source-review checks. Do not infer successful runtime tests from a read-only answer.

Inspect:
- docs/POWER_BI_VISUAL_QA.md
- docs/dax-measures.md
- powerbi/README.md
- README.md (Power BI section)

Answer using tracked source evidence:

1. Is an editable PBIX or PBIP included? May the theme JSON or old screenshots be called a newly refreshed report?
2. What does the Turkish abbreviation B stand for?
3. Are signup traffic source and session traffic source interchangeable, and which distinct denominators/grains matter?
4. Is PE4/CAC proxy based on observed marketing spend? What evidence is missing before current financial/conversion claims could be published?

Mark Power BI Desktop validation and fresh BigQuery numbers UNVERIFIED unless you have genuine, cited runtime evidence. Never invent report renders, data refreshes or improvements. Return PASS/FAIL/UNVERIFIED with file citations. Do not modify files, call paid services, run CI or publish reports.