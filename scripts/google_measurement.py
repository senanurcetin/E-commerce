"""Read-only Google measurement snapshots. No synthetic data and no credential files.

Usage:
  pip install "google-auth[requests]>=2,<3"
  GA4_PROPERTY_ID=123 python scripts/google_measurement.py ga4 --start 2026-10-01 --end 2026-10-15
  GSC_SITE_URL=sc-domain:example.com python scripts/google_measurement.py gsc --start 2026-10-01 --end 2026-10-15
  python scripts/google_measurement.py pagespeed --url https://example.com/ --strategy mobile

Authenticated commands use Application Default Credentials. Exports go under
target/google_measurement/ (gitignored) and are NEVER added to existing marts.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
from datetime import date, datetime, timezone
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
OUTPUT_DIR = Path("target/google_measurement")


def validate_dates(start: str, end: str) -> None:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValueError("--start must be on or before --end")
    if last > date.today():
        raise ValueError("--end cannot be in the future")


def access_token(scope: str) -> str:
    try:
        import google.auth
        from google.auth.transport.requests import Request as GoogleAuthRequest
    except ImportError as exc:
        raise RuntimeError('Install: pip install "google-auth[requests]>=2,<3"') from exc
    credentials, _ = google.auth.default(scopes=[scope])
    credentials.refresh(GoogleAuthRequest())
    return credentials.token


def lab_access_token(scope: str) -> str:
    """Obtain an Analytics-only token without a JSON private key when opted in.

    The active gcloud user must hold Service Account Token Creator on ONLY
    nexus-commerce-lab@workintech-working. Its temporary user token is sent
    to Google's IAM Credentials API, requesting exactly Analytics read-only
    scope for a short-lived service-account token. No token is printed,
    persisted, logged, or transmitted to any other service.
    """
    method = os.environ.get("NEXUS_GA4_KEYLESS_IMPERSONATION", "")
    if not method:
        return access_token(scope)
    if method != "1" or scope != GA4_SCOPE:
        raise ValueError("Unsupported NEXUS GA4 keyless auth configuration")
    try:
        proc = subprocess.run(
            ["gcloud", "auth", "print-access-token", "--project=workintech-working"],
            check=False, capture_output=True, text=True, timeout=45,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Could not obtain current gcloud user credentials") from exc
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError("Active gcloud user login required for GA4 keyless impersonation")
    user_token = proc.stdout.strip()
    try:
        response = fetch_json(
            "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
            "nexus-commerce-lab@workintech-working.iam.gserviceaccount.com:generateAccessToken",
            body={"scope": [GA4_SCOPE], "lifetime": "1800s"},
            token=user_token,
        )
    except Exception as exc:
        # Suppress provider response bodies, which can include auth diagnostics.
        raise RuntimeError(
            "GA4 service account impersonation denied: verify "
            "roles/iam.serviceAccountTokenCreator on the service account"
        ) from None
    token = response.get("accessToken") if isinstance(response, dict) else None
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("IAMCredentials API did not return an access token")
    return token


def fetch_json(url: str, body: dict | None = None, token: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urlopen(request, timeout=40) as response:
        return json.load(response)


def normalize_ga4(response: dict) -> list[dict]:
    """Keep only non-identifying date/channel metrics from GA4 reporting API."""
    expected_dimensions = ["date", "sessionDefaultChannelGroup"]
    expected_metrics = [
        "sessions", "engagedSessions", "activeUsers",
        "ecommercePurchases", "purchaseRevenue",
    ]
    dims = [c["name"] for c in response.get("dimensionHeaders", [])]
    metrics = [c["name"] for c in response.get("metricHeaders", [])]
    if dims != expected_dimensions or metrics != expected_metrics:
        raise ValueError(f"GA4 schema mismatch: dimensions={dims}, metrics={metrics}")
    records = []
    for row in response.get("rows", []):
        d = [v["value"] for v in row["dimensionValues"]]
        m = [v["value"] for v in row["metricValues"]]
        records.append({
            "date": f"{d[0][:4]}-{d[0][4:6]}-{d[0][6:]}",
            "ga4_session_channel_group": d[1],
            "sessions": int(m[0]),
            "engaged_sessions": int(m[1]),
            "active_users": int(m[2]),
            "ecommerce_purchases": int(m[3]),
            "purchase_revenue_property_currency": float(m[4]),
        })
    return records


def collect_ga4(start: str, end: str) -> dict:
    property_id = os.environ.get("GA4_PROPERTY_ID", "").strip()
    if not property_id.isdigit():
        raise ValueError("GA4_PROPERTY_ID must be the numeric GA4 property ID")
    token = access_token(GA4_SCOPE)
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    rows: list[dict] = []
    offset, limit = 0, 10000
    row_count = None
    for _ in range(20):
        response = fetch_json(url, {
            "dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [
                {"name": "date"}, {"name": "sessionDefaultChannelGroup"}
            ],
            "metrics": [{"name": name} for name in (
                "sessions", "engagedSessions", "activeUsers",
                "ecommercePurchases", "purchaseRevenue"
            )],
            "limit": str(limit), "offset": str(offset),
        }, token)
        rows.extend(normalize_ga4(response))
        row_count = int(response.get("rowCount", len(rows)))
        offset += len(response.get("rows", []))
        if offset >= row_count or not response.get("rows"):
            break
    return {
        "source": "ga4_data_api", "property_id": property_id,
        "date_start": start, "date_end": end, "rows": rows,
        "partial": row_count is not None and offset < row_count,
        "interpretation": "GA4 UI-aligned aggregates; not the repo's historical clickstream",
    }


def normalize_gsc(response: dict) -> list[dict]:
    """Raw search queries and page URLs intentionally omitted from the export."""
    records = []
    for row in response.get("rows", []):
        keys = row["keys"]
        if len(keys) != 2:
            raise ValueError("GSC schema mismatch: expected date, device")
        records.append({
            "date": keys[0], "device": keys[1],
            "clicks": float(row["clicks"]),
            "impressions": float(row["impressions"]),
            "ctr_ratio": float(row["ctr"]),
            "average_position": float(row["position"]),
        })
    return records


def collect_gsc(start: str, end: str) -> dict:
    site = os.environ.get("GSC_SITE_URL", "").strip()
    if not (site.startswith("sc-domain:") or site.startswith(("https://", "http://"))):
        raise ValueError("GSC_SITE_URL must be the exact Search Console property identifier")
    token = access_token(GSC_SCOPE)
    url = "https://www.googleapis.com/webmasters/v3/sites/" + quote(site, safe="") + "/searchAnalytics/query"
    rows: list[dict] = []
    row_limit, reached_limit = 25000, False
    for page in range(20):
        response = fetch_json(url, {
            "startDate": start, "endDate": end, "dimensions": ["date", "device"],
            "type": "web", "rowLimit": row_limit, "startRow": page * row_limit,
            "dataState": "final",
        }, token)
        part = normalize_gsc(response)
        rows.extend(part)
        if len(part) < row_limit:
            break
    else:
        reached_limit = True
    return {
        "source": "gsc_search_analytics_api", "site_property": site,
        "date_start": start, "date_end": end, "rows": rows,
        "partial": reached_limit,
        "interpretation": "Google organic Search clicks/impressions, not GA4 website sessions; API may omit some rows",
    }


def normalize_pagespeed(response: dict) -> dict:
    lighthouse = response.get("lighthouseResult", {})
    categories = lighthouse.get("categories", {})
    audits = lighthouse.get("audits", {})
    scores = {}
    for key in ("performance", "accessibility", "best-practices", "seo"):
        raw = categories.get(key, {}).get("score")
        scores[key] = round(raw * 100) if raw is not None else None
    metric_ids = (
        "first-contentful-paint", "largest-contentful-paint",
        "speed-index", "total-blocking-time", "cumulative-layout-shift",
    )
    return {
        "lighthouse_scores_0_to_100": scores,
        "lab_metrics": {
            metric: audits.get(metric, {}).get("numericValue") for metric in metric_ids
        },
        "field_data": "not_collected_use_crux_api",
        "notes": "Lighthouse lab data; do not describe lab metrics as field Core Web Vitals.",
    }


def collect_pagespeed(url: str, strategy: str) -> dict:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("--url requires a public HTTPS address without embedded credentials")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local") or "." not in host:
        raise ValueError("--url requires a public HTTPS hostname")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("--url requires a public HTTPS address")
    query = {"url": url, "strategy": strategy,
             "category": ["PERFORMANCE", "ACCESSIBILITY", "BEST_PRACTICES", "SEO"]}
    key = os.environ.get("GOOGLE_PAGESPEED_API_KEY")
    if key:
        query["key"] = key
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urlencode(query, doseq=True)
    data = normalize_pagespeed(fetch_json(endpoint))
    return {"source": "pagespeed_insights_api", "url": url, "strategy": strategy, **data}


def save_snapshot(result: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    collected = datetime.now(timezone.utc)
    result["fetched_at_utc"] = collected.isoformat()
    source = result["source"].replace("_api", "")
    identity = str(result.get("property_id") or result.get("site_property") or result.get("url") or "")
    identity_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    stamp = f"{collected:%Y%m%dT%H%M%S%fZ}"
    if "date_start" in result:
        suffix = f"{identity_hash}_{result['date_start']}_{result['date_end']}_{stamp}"
    else:
        suffix = f"{result.get('strategy', 'snapshot')}_{identity_hash}_{stamp}"
    output = output_dir / f"{source}_{suffix}.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    subs = parser.add_subparsers(dest="source", required=True)
    for name in ("ga4", "gsc"):
        sub = subs.add_parser(name)
        sub.add_argument("--start", required=True)
        sub.add_argument("--end", required=True)
    psi = subs.add_parser("pagespeed")
    psi.add_argument("--url", required=True)
    psi.add_argument("--strategy", choices=("mobile", "desktop"), default="mobile")
    args = parser.parse_args()
    if args.source in ("ga4", "gsc"):
        validate_dates(args.start, args.end)
        result = collect_ga4(args.start, args.end) if args.source == "ga4" else collect_gsc(args.start, args.end)
    else:
        result = collect_pagespeed(args.url, args.strategy)
    path = save_snapshot(result, args.output_dir)
    print(f"Read-only snapshot saved to {path}; source={result['source']}; partial={result.get('partial', False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
