"""Public third-party storefronts for manually initiated PageSpeed comparison.

These hosts are NOT affiliated with our warehouse data. They are not GA4
properties we control and do not supply purchase/session transaction tables.
"""
TEST_SITES = {
    "Custom public HTTPS URL": "",
    "Tricentis Demo Web Shop": "https://demowebshop.tricentis.com/",
    "nopCommerce Demo Store": "https://demo.nopcommerce.com/",
}

DEFAULT_TEST_SITE = "Custom public HTTPS URL"


def test_site_url(choice: str) -> str:
    """Resolve a fixed documented URL, never take an unvalidated arbitrary host."""
    if choice not in TEST_SITES:
        raise ValueError("Unknown public test-site preset")
    return TEST_SITES[choice]
