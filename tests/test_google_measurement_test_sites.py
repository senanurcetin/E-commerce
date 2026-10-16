"""Public example stores are convenience URLs, not linked customer data."""
import unittest

from scripts.google_test_sites import DEFAULT_TEST_SITE, TEST_SITES, test_site_url


class TestSitePresets(unittest.TestCase):
    def test_default_does_not_select_someone_elses_store(self):
        self.assertEqual(TEST_SITES[DEFAULT_TEST_SITE], "")

    def test_public_demo_urls_are_https_and_have_unique_hosts(self):
        urls = [url for url in TEST_SITES.values() if url]
        self.assertEqual(len(urls), 2)
        self.assertEqual(len(set(urls)), len(urls))
        self.assertEqual(
            set(urls),
            {"https://demowebshop.tricentis.com/", "https://demo.nopcommerce.com/"},
        )
        self.assertTrue(all(url.startswith("https://") for url in urls))

    def test_unknown_choice_never_creates_url(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            test_site_url("Unknown or user-supplied code")


if __name__ == "__main__":
    unittest.main()
