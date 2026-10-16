"""Independent LOCAL Chrome Lighthouse lab reports, never PageSpeed API/CrUX.

This loader consumes full JSON reports generated with Lighthouse CLI. It does
not issue network requests or infer GA4 sessions/revenue. No synthetic fallback.
"""
from __future__ import annotations
from datetime import datetime
import json
import math
from pathlib import Path
from urllib.parse import urlsplit


CATEGORY_KEYS = ("performance", "accessibility", "best-practices", "seo")
AUDIT_KEYS = {
    "fcp_ms": "first-contentful-paint",
    "lcp_ms": "largest-contentful-paint",
    "tbt_ms": "total-blocking-time",
    "speed_index_ms": "speed-index",
    "cls": "cumulative-layout-shift",
}


def safe_metric(value, label: str, *, upper=None):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{label}: must be numeric")
    if not math.isfinite(value) or value < 0 or (upper is not None and value > upper):
        raise ValueError(f"{label}: invalid or out of range")
    return float(value)


def parse_lighthouse_report(data: dict) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("lighthouseVersion"), str):
        raise ValueError("Not a full Lighthouse CLI result; refusing unverified metrics")
    url = data.get("finalDisplayedUrl") or data.get("finalUrl") or data.get("requestedUrl")
    parsed = urlsplit(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Lighthouse URL must be HTTPS")
    request = data.get("requestedUrl", "")
    if not isinstance(request, str) or urlsplit(request).scheme != "https":
        raise ValueError("Missing HTTPS requested URL")
    try:
        when = datetime.fromisoformat(data["fetchTime"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError) as exc:
        raise ValueError("Missing or invalid Lighthouse fetchTime") from exc
    if when.tzinfo is None:
        raise ValueError("Lighthouse fetchTime must be timezone-aware")
    form = data.get("configSettings", {}).get("formFactor")
    if form not in ("mobile", "desktop"):
        raise ValueError("Missing explicit mobile/desktop form factor")
    categories = data.get("categories", {})
    audits = data.get("audits", {})
    if not isinstance(categories, dict) or not isinstance(audits, dict):
        raise ValueError("Malformed Lighthouse categories/audits")
    scores = {}
    for key in CATEGORY_KEYS:
        section = categories.get(key)
        if not isinstance(section, dict) or section.get("score") is None:
            raise ValueError(f"Missing Lighthouse score: {key}")
        scores[key] = round(safe_metric(section["score"], key, upper=1) * 100, 1)
    result = {
        "source_system": "local_lighthouse_cli",
        "lab_only": True,
        "lighthouse_version": data["lighthouseVersion"],
        "url": url,
        "requested_url": request,
        "device": form,
        "measured_at_utc": when.isoformat(),
        "scores": scores,
        "lab_metrics": {},
    }
    for label, audit_id in AUDIT_KEYS.items():
        audit = audits.get(audit_id)
        number = audit.get("numericValue") if isinstance(audit, dict) else None
        result["lab_metrics"][label] = (
            None if number is None else safe_metric(number, label)
        )
    return result


def load_lighthouse_reports(directory: Path) -> list[dict]:
    """Read genuine CLI JSONs only. Files generated in CI tests remain fixtures."""
    reports = []
    if not directory.is_dir():
        return []
    for path in sorted(directory.glob("*.json")):
        try:
            with path.open(encoding="utf-8") as stream:
                data = json.load(stream)
            reports.append(parse_lighthouse_report(data))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
    return reports
