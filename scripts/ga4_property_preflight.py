"""Verify that read-only GA4 access belongs to the owned Commerce Lab stream.

No credentials are bundled. Reads Google Analytics Admin account summaries and
web stream metadata to find an exact G-... Measurement ID + stream ID pair.
Never selects a property merely because its display name resembles 'NEXUS'.
The final Data API export stays under scripts.lab_ga4_events and is separate.
"""
from __future__ import annotations

import argparse
import os
import re
from urllib.parse import quote
from google.auth.exceptions import DefaultCredentialsError  # google-auth installed explicitly

from scripts.google_measurement import access_token, fetch_json, GA4_SCOPE

OWNED_MEASUREMENT_ID = "G-F0B2EQVC8M"
OWNED_STREAM_ID = "16145034201"
ADMIN = "https://analyticsadmin.googleapis.com/v1beta"


def candidates(account_summaries: list[dict]) -> list[str]:
    found = set()
    for account in account_summaries:
        for prop in account.get("propertySummaries", []):
            path = prop.get("property", "")
            if isinstance(path, str) and re.fullmatch(r"properties/[0-9]+", path):
                found.add(path)
    return sorted(found)


def match_stream(property_resource: str, streams: list[dict]) -> bool:
    if not re.fullmatch(r"properties/[0-9]+", property_resource):
        raise ValueError("Invalid property resource")
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        name = stream.get("name", "")
        web = stream.get("webStreamData") or {}
        if (name == f"{property_resource}/dataStreams/{OWNED_STREAM_ID}"
                and web.get("measurementId") == OWNED_MEASUREMENT_ID
                and web.get("defaultUri", "").rstrip("/")
                == "https://nexus-commerce-lab.vercel.app"):
            return True
    return False


def _paged(url: str, key: str, token: str) -> list[dict]:
    result, next_page = [], ""
    seen = set()
    for _ in range(50):
        full = url + ("&pageToken=" + quote(next_page, safe="") if next_page else "")
        payload = fetch_json(full, token=token)
        if not isinstance(payload, dict) or not isinstance(payload.get(key, []), list):
            raise ValueError("Invalid GA4 Admin API page")
        result.extend(payload.get(key, []))
        next_page = payload.get("nextPageToken", "")
        if not next_page:
            return result
        if next_page in seen:
            raise ValueError("GA4 Admin pagination cycle detected")
        seen.add(next_page)
    raise ValueError("GA4 Admin result exceeds 50 pages; refusing partial selection")


def discover_property(token: str) -> str:
    if not token:
        raise ValueError("Owner-authorized Analytics read-only token is required")
    accounts = _paged(f"{ADMIN}/accountSummaries?pageSize=200", "accountSummaries", token)
    matches = []
    for resource in candidates(accounts):
        streams = _paged(f"{ADMIN}/{resource}/dataStreams?pageSize=200", "dataStreams", token)
        if match_stream(resource, streams):
            matches.append(resource.split("/")[1])
    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one authorized Commerce Lab GA4 property matching "
            "the exact Measurement ID, Stream ID and URL; found " + str(len(matches))
        )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolve", action="store_true",
                        help="Use existing authorized ADC to identify Commerce Lab property")
    args = parser.parse_args()
    if not args.resolve:
        print("OWNER SITE: https://nexus-commerce-lab.vercel.app/")
        print("EXPECTED Measurement ID: " + OWNED_MEASUREMENT_ID)
        print("EXPECTED Stream ID: " + OWNED_STREAM_ID)
        print("GA4 API credential present: " + str(bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))))
        print("Property ID: not established by Measurement ID alone")
        print("Next: Admin > Property details for numeric ID, plus Analytics read-only ADC.")
        print("Nothing queried or collected. Run --resolve only after authorized ADC setup.")
        return 0
    try:
        token = access_token(GA4_SCOPE)
        prop_id = discover_property(token)
    except DefaultCredentialsError:
        print("BLOCKED: no authorized Google Application Default Credentials for Analytics.")
        return 2
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"BLOCKED: Analytics Admin read-only property identity not confirmed ({type(exc).__name__}).")
        return 2
    print(f"Verified owned Commerce Lab GA4 Property ID: {prop_id}")
    print("Set GA4_LAB_PROPERTY_ID to this numeric value, then run scripts.lab_ga4_events.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
