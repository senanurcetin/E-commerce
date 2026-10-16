"""Explicit, on-demand PageSpeed audit from a locally running NEXUS dashboard.

This is a user-triggered operation, never an automatic monitoring loop.
Only Google's PageSpeed Insights API is called, no credentials are stored, and
no synthetic fallbacks are created. Reports remain in target/ (gitignored).
"""
from __future__ import annotations

from pathlib import Path

from scripts.google_measurement import collect_pagespeed, save_snapshot
from scripts.google_measurement_marts import export_marts


def audit_public_site(url: str, device: str, *, marts_dir: Path) -> dict:
    """Collect a real lab audit and rebuild independent source marts.

    Raises exceptions for unsupported URL, invalid device, API quota failures
    and malformed result. Callers must surface errors instead of inventing KPIs.
    """
    if device not in ("mobile", "desktop"):
        raise ValueError("Device must be mobile or desktop")
    url = url.strip()
    if not url:
        raise ValueError("Enter a public HTTPS URL")
    if not url.startswith("https://"):
        raise ValueError("Enter a full public URL beginning with https://")
    result = collect_pagespeed(url, device)
    # Reject Lighthouse/API error payloads before persisting an empty report.
    scores = result["lighthouse_scores_0_to_100"]
    if all(score is None for score in scores.values()):
        raise ValueError(
            "PageSpeed returned no Lighthouse scores. Check URL and API quota; "
            "no measurement was saved."
        )
    snapshots_dir = marts_dir.parent
    snapshot_path = save_snapshot(result, snapshots_dir)
    # Exporter rejects partial data and invalid schema across ALL collected
    # snapshots; missing GA4/GSC are fine (they yield header-only CSV files).
    manifest = export_marts(snapshots_dir, marts_dir)
    return {
        "source": "pagespeed_insights_api",
        "device": device,
        "url": url,
        "snapshot_path": str(snapshot_path),
        "total_audits": manifest["source_summary"]["pagespeed_insights_api"]["rows"],
    }
