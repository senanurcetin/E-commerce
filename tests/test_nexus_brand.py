"""Regression gates for the actual NEXUS brand in both apps and deployment bundles."""
from pathlib import Path
import unittest
from PIL import Image

from dashboard.nexus_theme import ROOT, OFFICIAL_LOGO, brand_icon

class NexusOfficialBrandTests(unittest.TestCase):
    def test_favicon_is_cropped_from_owner_logo(self):
        with Image.open(OFFICIAL_LOGO) as im:
            self.assertEqual(im.size, (1200, 360))
        icon = brand_icon()
        self.assertEqual(icon.size, (256, 256))
        self.assertEqual(icon.mode, "RGBA")
        colored = sum(1 for px in icon.getdata() if px != (10, 20, 40, 255))
        self.assertGreater(colored, 8000, "Official NEXUS X must remain visible")
        self.assertEqual(icon.getpixel((0, 0))[:3], (10, 20, 40))

    def test_streamlit_uses_native_brand_assets(self):
        src = (ROOT / "dashboard/google_marketing_app.py").read_text(encoding="utf-8")
        self.assertIn("page_icon=brand_icon()", src)
        theme = (ROOT / "dashboard/nexus_theme.py").read_text(encoding="utf-8")
        self.assertIn("st.image(str(OFFICIAL_LOGO), width=340)", theme)
        self.assertIn("st.sidebar.image(str(OFFICIAL_LOGO)", theme)
        self.assertNotIn("data:image/png;base64,", theme)

    def test_storefront_header_preview_and_browser_tab(self):
        html = (ROOT / "storefront/index.html").read_text(encoding="utf-8")
        self.assertIn('rel="icon" type="image/svg+xml"', html)
        self.assertIn('property="og:image"', html)
        self.assertIn('nexus-logo.png', html)
        self.assertGreaterEqual(html.count('src="./nexus-logo.png"'), 3)
        svg = (ROOT / "storefront/favicon.svg").read_text(encoding="utf-8")
        self.assertIn('viewBox="0 0 256 256"', svg)
        self.assertIn('NEXUS', svg)
        build = (ROOT / "storefront/scripts/build.mjs").read_text(encoding="utf-8")
        self.assertIn('resolve(dist, "nexus-logo.png")', build)
        self.assertIn('"favicon.svg"', build)

if __name__ == "__main__":
    unittest.main()
