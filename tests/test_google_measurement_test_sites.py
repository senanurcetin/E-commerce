"""Public example stores are convenience URLs, not linked customer data."""
import unittest

from scripts.google_test_sites import DEFAULT_TEST_SITE, TEST_SITES, test_site_url


class TestSitePresets(unittest.TestCase):
    def test_default_is_our_controlled_lab(self):
        self.assertEqual(TEST_SITES[DEFAULT_TEST_SITE], "https://nexus-commerce-lab.vercel.app/")
        self.assertNotEqual(TEST_SITES[DEFAULT_TEST_SITE], "https://demo.nopcommerce.com/")

    def test_public_demo_urls_are_https_and_have_unique_hosts(self):
        urls = [url for url in TEST_SITES.values() if url]
        self.assertEqual(len(urls), 3)
        self.assertEqual(len(set(urls)), len(urls))
        self.assertEqual(
            set(urls),
            {"https://demowebshop.tricentis.com/", "https://demo.nopcommerce.com/", "https://nexus-commerce-lab.vercel.app/"},
        )
        self.assertTrue(all(url.startswith("https://") for url in urls))

    def test_unknown_choice_never_creates_url(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            test_site_url("Unknown or user-supplied code")


if __name__ == "__main__":
    unittest.main()
