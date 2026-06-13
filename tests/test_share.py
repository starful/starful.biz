import json
import os
import unittest

from fastapi.testclient import TestClient

from app import BASE_URL, app

DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app",
    "static",
    "json",
    "job_data.json",
)


class ShareBarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        with open(DATA_FILE, encoding="utf-8") as handle:
            cls.career_id = json.load(handle)["jobs"][0]["id"]

    def test_career_detail_has_share_bar(self):
        response = self.client.get(f"/career/{self.career_id}")
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn("share-bar", html)
        self.assertIn("share-btn-x", html)
        self.assertIn(f"/card/career/{self.career_id}", html)
        self.assertIn(f"/social/{self.career_id}.jpg", html)

    def test_social_card_page(self):
        response = self.client.get(f"/card/career/{self.career_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            f'property="og:url" content="{BASE_URL}/card/career/{self.career_id}?sc=1"',
            response.text,
        )

    def test_social_image_head(self):
        response = self.client.head(f"/social/{self.career_id}.jpg")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("image/jpeg"))
        self.assertEqual(response.content, b"")


if __name__ == "__main__":
    unittest.main()
