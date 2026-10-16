"""GA4 read-only property resolution contracts; no API/auth in CI."""
import unittest
from unittest.mock import patch

from scripts.ga4_property_preflight import (
    candidates, match_stream, discover_property, OWNED_MEASUREMENT_ID,
    OWNED_STREAM_ID,
)


class GA4PropertyPreflightTests(unittest.TestCase):
    def test_validated_owned_stream_and_exact_host(self):
        good = {
            "name": "properties/12345678/dataStreams/" + OWNED_STREAM_ID,
            "webStreamData": {
                "measurementId": OWNED_MEASUREMENT_ID,
                "defaultUri": "https://nexus-commerce-lab.vercel.app/",
            },
        }
        self.assertTrue(match_stream("properties/12345678", [good]))
        for wrong in [
            {**good, "name": "properties/12345678/dataStreams/14355683064"},
            {**good, "webStreamData": {**good["webStreamData"],
                                      "measurementId": "G-EL4EZ01CVH"}},
            {**good, "webStreamData": {**good["webStreamData"],
                                      "defaultUri": "https://senanurcetin.github.io/GTM/"}},
        ]:
            self.assertFalse(match_stream("properties/12345678", [wrong]))

    def test_only_numeric_properties_eligible(self):
        items = [{"propertySummaries": [{"property": "properties/12345678"},
                                       {"property": "properties/not-a-number"}]}]
        self.assertEqual(candidates(items), ["properties/12345678"])
        with self.assertRaises(ValueError):
            match_stream("properties/notnumeric", [])

    def test_discover_requires_one_exact_stream_match(self):
        matching = {
            "name": "properties/333/dataStreams/" + OWNED_STREAM_ID,
            "webStreamData": {
                "measurementId": OWNED_MEASUREMENT_ID,
                "defaultUri": "https://nexus-commerce-lab.vercel.app/",
            },
        }
        with patch("scripts.ga4_property_preflight._paged") as page:
            page.side_effect = [
                [{"propertySummaries": [{"property": "properties/333"}]}],
                [matching],
            ]
            self.assertEqual(discover_property("CI_ONLY"), "333")
        with patch("scripts.ga4_property_preflight._paged") as page:
            page.side_effect = [
                [{"propertySummaries": [{"property": "properties/333"}]}],
                [{**matching, "webStreamData": {"measurementId": "G-EL4EZ01CVH",
                                               "defaultUri": "https://senanurcetin.github.io/GTM/"}}],
            ]
            with self.assertRaisesRegex(ValueError, "exactly one"):
                discover_property("CI_ONLY")


if __name__ == "__main__":
    unittest.main()
