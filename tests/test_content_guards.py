"""content_guards: retired careers must not be regenerated."""
from __future__ import annotations

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "scripts")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, REPO)

from content_guards import (  # noqa: E402
    filter_related_jobs,
    is_blocked_position,
    is_blocked_slug,
)
from app.seo_helpers import REMOVED_CAREER_SLUGS  # noqa: E402


class ContentGuardsTests(unittest.TestCase):
    def test_removed_slug_blocked(self):
        self.assertTrue(is_blocked_slug("solutions_architect"))
        self.assertTrue(is_blocked_slug("MLOps_Engineer"))
        self.assertTrue(is_blocked_position("Solutions Architect"))
        self.assertFalse(is_blocked_slug("data_scientist"))
        self.assertFalse(is_blocked_position("Product Manager"))

    def test_removed_set_non_empty(self):
        self.assertGreaterEqual(len(REMOVED_CAREER_SLUGS), 50)

    def test_filter_related_drops_removed(self):
        cleaned = filter_related_jobs(
            ["data_scientist", "solutions_architect", "mlops_engineer", "cto"],
            allow={"data_scientist", "cto", "prompt_engineer"},
        )
        self.assertEqual(cleaned, ["data_scientist", "cto"])


if __name__ == "__main__":
    unittest.main()
