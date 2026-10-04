"""Regression checks for the supported RewriteCond/RewriteRule routing subset.

These exercise the packaged rules with browser and crawler requests. The real
hosting server's module support and headers still require deployment checks.
"""
import re
import unittest
from pathlib import Path


RULES = Path(__file__).resolve().parents[1] / "frontend/public/.htaccess"


def route(host, path, user_agent):
    values = {"HTTP_HOST": host, "HTTP_USER_AGENT": user_agent}
    conditions = []
    for raw in RULES.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("RewriteCond "):
            _, variable, pattern, *flags = line.split()
            conditions.append((variable, pattern, flags))
        elif line.startswith("RewriteRule "):
            _, pattern, target, flags = line.split()
            match = re.search(pattern, path.lstrip("/"))
            permitted = True
            for variable, condition, modifiers in conditions:
                if variable == "%{REQUEST_FILENAME}":
                    # Tested detail paths are not existing filesystem entries.
                    permitted = permitted and condition in ("!-f", "!-d")
                else:
                    key = variable.removeprefix("%{").removesuffix("}")
                    options = re.I if "[NC]" in modifiers else 0
                    permitted = permitted and bool(re.search(condition, values[key], options))
            conditions = []
            if match and permitted:
                destination = re.sub(r"\$(\d+)", lambda item: match.group(int(item.group(1))), target)
                return destination, flags
    raise AssertionError("No matching rule")


class SeoRoutingTests(unittest.TestCase):
    def test_regular_browsers_stay_on_the_styled_frontend(self):
        for agent in ("Mozilla/5.0 Chrome/131.0 Safari/537.36", "Mozilla/5.0 Firefox/131.0", "", "curl/8.0"):
            for host, path in (("organicarchives.organicemperor.com", "/posts/example-post"),
                               ("organicemperor.com", "/products/example-product")):
                with self.subTest(host=host, agent=agent):
                    self.assertEqual(route(host, path, agent), ("index.html", "[L]"))

    def test_search_and_share_crawlers_get_temporary_fixed_upstream_redirects(self):
        for agent in ("Mozilla/5.0 (compatible; Googlebot/2.1)", "Google-InspectionTool/1.0",
                      "bingbot/2.0", "facebookexternalhit/1.1", "LinkedInBot/1.0", "Twitterbot/1.0"):
            with self.subTest(agent=agent):
                self.assertEqual(route("organicarchives.organicemperor.com", "/posts/example-post", agent),
                                 ("https://api.organicemperor.com/site/archives/posts/example-post", "[R=302,L]"))
                self.assertEqual(route("organicemperor.com", "/products/example-product", agent),
                                 ("https://api.organicemperor.com/site/storefront/products/example-product", "[R=302,L]"))

    def test_crawler_user_agent_never_opens_a_draft_or_redirects_assets(self):
        self.assertEqual(route("organicarchives.organicemperor.com", "/preview/12", "Googlebot/2.1"),
                         ("index.html", "[L]"))
        self.assertEqual(route("organicarchives.organicemperor.com", "/assets/missing.css", "Googlebot/2.1"),
                         ("-", "[L]"))
        self.assertEqual(route("organicarchives.organicemperor.com", "/posts/bad/extra", "Googlebot/2.1"),
                         ("-", "[R=404,L]"))

    def test_trailing_slash_normalizes_on_the_frontend_for_everyone(self):
        for agent in ("Mozilla/5.0", "Googlebot/2.1"):
            self.assertEqual(route("organicarchives.organicemperor.com", "/posts/example-post/", agent),
                             ("https://organicarchives.organicemperor.com/posts/example-post", "[R=301,L]"))

    def test_detail_variants_are_not_shared_by_caches(self):
        content = RULES.read_text(encoding="utf-8")
        self.assertIn('SetEnvIf Request_URI "^/(products|posts)/" seo_detail=1', content)
        self.assertIn('Header always merge Vary "User-Agent" env=seo_detail', content)
        self.assertIn('Header always set Cache-Control "no-cache, no-store, must-revalidate" env=seo_detail', content)


if __name__ == "__main__":
    unittest.main()
