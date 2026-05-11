from pathlib import Path
import sys
import tomllib
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pw_flake_triage
from pw_flake_triage.analyzer import analyze_paths
from pw_flake_triage.cli import render_markdown


TIMEOUT = "Timeout / wait condition instability"
SELECTOR = "Ambiguous or brittle selector"
AUTH_STATE = "Auth/session or expected page state mismatch"
LIFECYCLE = "Browser/context/page lifecycle race"
VISUAL = "Visual/snapshot instability"


class TestCli(unittest.TestCase):
    def fixture(self, *parts: str) -> str:
        return str(Path(__file__).resolve().parents[1].joinpath(*parts))

    def categories_for(self, *parts: str) -> list[str]:
        result = analyze_paths([self.fixture(*parts)])
        return [f.category for f in result.findings]

    def test_package_version_matches_project_metadata(self):
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        project = tomllib.loads(pyproject.read_text())["project"]
        self.assertEqual(pw_flake_triage.__version__, project["version"])

    def test_analyzes_example_json(self):
        categories = set(self.categories_for("examples", "playwright-report.json"))
        self.assertIn(TIMEOUT, categories)
        self.assertIn(SELECTOR, categories)

    def test_renders_markdown_summary(self):
        result = analyze_paths([self.fixture("examples")])
        report = render_markdown(result)
        self.assertIn("Playwright Flake Triage Report", report)
        self.assertIn(VISUAL, report)
        self.assertIn(LIFECYCLE, report)

    def test_issue_derived_strict_mode_selector_regression(self):
        categories = self.categories_for("examples", "public-issue-symptoms", "strict-mode-selector.log")
        self.assertEqual(categories, [SELECTOR])
        self.assertNotIn(TIMEOUT, categories)

    def test_issue_derived_auth_session_timeout_regression(self):
        result = analyze_paths([self.fixture("examples", "public-issue-symptoms", "auth-session-timeout.log")])
        categories = [f.category for f in result.findings]
        self.assertEqual(categories, [AUTH_STATE])
        self.assertNotIn(TIMEOUT, categories)
        report = render_markdown(result)
        self.assertIn("Synthetic auth/session timeout symptom", report)
        self.assertIn("https://github.com/example/repo/issues/123", report)

    def test_issue_derived_role_permission_hang_regression(self):
        categories = self.categories_for("examples", "public-issue-symptoms", "route-permission-hang.log")
        self.assertEqual(categories, [AUTH_STATE])
        self.assertNotIn(TIMEOUT, categories)

    def test_all_issue_derived_fixtures_are_part_of_regression_suite(self):
        result = analyze_paths([self.fixture("examples", "public-issue-symptoms")])
        by_test = {finding.test: finding.category for finding in result.findings}
        self.assertEqual(by_test["strict-mode-selector.log"], SELECTOR)
        self.assertEqual(by_test["auth-session-timeout.log"], AUTH_STATE)
        self.assertEqual(by_test["route-permission-hang.log"], AUTH_STATE)
        self.assertEqual(len(result.findings), 3)


if __name__ == "__main__":
    unittest.main()
