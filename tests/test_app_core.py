import json
import os
import unittest

from fastapi.testclient import TestClient

from app import app
from app.md_parser import parse_starful_md, parse_starful_md_raw
from app.services.jobs_cache import JOB_DATA, load_jobs_on_startup
from app.services.search import expand_query_terms, search_jobs

DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app",
    "static",
    "json",
    "job_data.json",
)


class AppCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_jobs_on_startup()
        cls.client = TestClient(app, base_url="https://starful.biz")

    def test_home_lists_jobs(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn("card-thumb", html)
        total = JOB_DATA.get("total_count", 0)
        self.assertGreater(total, 0)
        self.assertIn(f'id="count-all">{total}<', html)

    def test_search_finds_backend(self):
        response = self.client.get("/search?q=backend")
        self.assertEqual(response.status_code, 200)
        self.assertIn("search", response.text.lower())

    def test_career_slug_alias_redirects(self):
        response = self.client.get("/career/ux_designer", follow_redirects=False)
        self.assertEqual(response.status_code, 301)
        self.assertIn("/career/ui_ux_designer", response.headers.get("location", ""))

    def test_legacy_entry_redirects_home(self):
        response = self.client.get("/entry/old-post", follow_redirects=False)
        self.assertEqual(response.status_code, 301)
        loc = response.headers.get("location", "").rstrip("/")
        self.assertEqual(loc, "https://starful.biz")

    def test_sitemap_includes_careers(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        count = response.text.count("<url>")
        self.assertGreater(count, 100)

    def test_robots_has_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Sitemap: https://starful.biz/sitemap.xml", response.text)


class MdParserTests(unittest.TestCase):
    def test_json_frontmatter(self):
        raw = '---json\n{"title": "Test", "meta_description": "Desc"}\n---\n# Body'
        parsed = parse_starful_md_raw(raw)
        self.assertIsNotNone(parsed)
        meta, body = parsed
        self.assertEqual(meta["title"], "Test")
        self.assertIn("# Body", body)

    def test_yaml_frontmatter(self):
        raw = "---\ntitle: YAML Title\ndescription: YAML desc\n---\n# Content"
        parsed = parse_starful_md_raw(raw)
        self.assertIsNotNone(parsed)
        meta, body = parsed
        self.assertEqual(meta["title"], "YAML Title")
        self.assertEqual(meta["meta_description"], "YAML desc")
        self.assertNotIn("title:", body)

    def test_data_scientist_file(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app",
            "contents",
            "data_scientist.md",
        )
        meta, body = parse_starful_md(path)
        self.assertTrue(meta.get("title"))
        self.assertNotIn("seo_title:", body[:200])


class SearchServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DATA_FILE, encoding="utf-8") as f:
            cls.jobs = json.load(f)["jobs"]

    def test_expand_query_synonyms(self):
        terms = expand_query_terms("backend")
        self.assertIn("backend", terms)
        self.assertTrue(any("バックエンド" in t or t == "backend" for t in terms))

    def test_search_jobs_returns_results(self):
        results = search_jobs(self.jobs, "data")
        self.assertGreater(len(results), 0)


class JobsCacheTests(unittest.TestCase):
    def test_load_populates_shared_dict(self):
        from app.routes import pages as pages_mod

        load_jobs_on_startup()
        self.assertGreater(len(JOB_DATA.get("jobs", [])), 0)
        self.assertIs(pages_mod.JOB_DATA, JOB_DATA)


if __name__ == "__main__":
    unittest.main()
