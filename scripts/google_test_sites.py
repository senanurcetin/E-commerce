"""Explicit public PageSpeed targets; no analytics property ownership is inferred.

The first-party NEXUS Commerce Lab can be measured via Lighthouse. The two
external demo shops are independent performance benchmarks, never TheLook orders.
"""
TEST_SITES = {
    "NEXUS Commerce Lab (owned test storefront)": "https://nexus-commerce-lab.vercel.app/",
    "Custom public HTTPS URL": "",
    "Tricentis Demo Web Shop (third-party)": "https://demowebshop.tricentis.com/",
    "nopCommerce Demo Store (third-party)": "https://demo.nopcommerce.com/",
}

DEFAULT_TEST_SITE = "NEXUS Commerce Lab (owned test storefront)"


def test_site_url(choice: str) -> str:
    """Resolve a fixed public URL only from an explicit allowlist."""
    if choice not in TEST_SITES:
        raise ValueError("Unknown public test-site preset")
    return TEST_SITES[choice]
