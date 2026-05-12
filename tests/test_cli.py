from pathlib import Path
import json
import os
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pw_flake_triage
from pw_flake_triage.analyzer import analyze_paths
from pw_flake_triage.cli import main, render_markdown


TIMEOUT = "Timeout / wait condition instability"
SELECTOR = "Ambiguous or brittle selector"
AUTH_STATE = "Auth/session or expected page state mismatch"
LIFECYCLE = "Browser/context/page lifecycle race"
VISUAL = "Visual/snapshot instability"
NETWORK = "Network or backend dependency flake"


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

    def test_writes_github_step_summary_markdown_while_returning_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "step-summary.md"
            output = Path(tmpdir) / "report.json"
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}):
                exit_code = main([
                    self.fixture("examples", "public-issue-symptoms"),
                    "--format",
                    "json",
                    "--output",
                    str(output),
                    "--github-step-summary",
                ])
            self.assertEqual(exit_code, 0)
            self.assertIn('"finding_count": 6', output.read_text())
            summary_text = summary.read_text()
            self.assertIn("# Playwright Flake Triage Report", summary_text)
            self.assertIn("Network or backend dependency flake", summary_text)

    def test_github_step_summary_requires_environment_variable(self):
        with patch.dict(os.environ, {}, clear=True):
            exit_code = main([self.fixture("examples"), "--github-step-summary"])
        self.assertEqual(exit_code, 2)

    def test_loads_custom_rules_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            log = tmp / "custom.log"
            log.write_text("ACME hydration deadlock after client boot", encoding="utf-8")
            rules_config = tmp / "rules.json"
            rules_config.write_text(json.dumps({
                "rules": [{
                    "id": "app-hydration",
                    "label": "Application hydration race",
                    "severity": "medium",
                    "patterns": ["ACME hydration deadlock"],
                    "why": "The app may not have finished client-side hydration before the test interacted with it.",
                    "fixes": ["Wait for the durable hydrated UI marker before interacting."],
                    "priority": 95,
                }]
            }), encoding="utf-8")
            output = tmp / "report.json"
            exit_code = main([str(log), "--rules-config", str(rules_config), "--format", "json", "-o", str(output)])
            self.assertEqual(exit_code, 0)
            report = json.loads(output.read_text())
            self.assertEqual(report["finding_count"], 1)
            self.assertEqual(report["findings"][0]["category"], "Application hydration race")

    def test_groups_duplicate_failure_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            message = "Error: strict mode violation: getByRole('button', { name: 'Save' }) resolved to 2 elements"
            (tmp / "retry-1.log").write_text(message, encoding="utf-8")
            (tmp / "retry-2.log").write_text(message, encoding="utf-8")
            result = analyze_paths([str(tmp)])
            groups = result.to_dict()["duplicate_groups"]
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0]["category"], SELECTOR)
            self.assertEqual(groups[0]["count"], 2)
            report = render_markdown(result)
            self.assertIn("Repeated failure groups", report)
            self.assertIn("2 findings", report)

    def test_invalid_custom_rules_config_returns_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_config = Path(tmpdir) / "rules.json"
            rules_config.write_text(json.dumps({"rules": [{"id": "missing-fields"}]}), encoding="utf-8")
            exit_code = main([self.fixture("examples"), "--rules-config", str(rules_config)])
            self.assertEqual(exit_code, 2)

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

    def test_issue_derived_browser_lifecycle_regression(self):
        categories = self.categories_for("examples", "public-issue-symptoms", "browser-lifecycle-target-closed.log")
        self.assertEqual(categories, [LIFECYCLE])

    def test_issue_derived_network_econnreset_regression(self):
        categories = self.categories_for("examples", "public-issue-symptoms", "network-econnreset.log")
        self.assertEqual(categories, [NETWORK])

    def test_issue_derived_neterr_timeout_regression(self):
        categories = self.categories_for("examples", "public-issue-symptoms", "network-neterr-timeout.log")
        self.assertIn(NETWORK, categories)

    def test_all_issue_derived_fixtures_are_part_of_regression_suite(self):
        result = analyze_paths([self.fixture("examples", "public-issue-symptoms")])
        by_test = {finding.test: finding.category for finding in result.findings}
        self.assertEqual(by_test["strict-mode-selector.log"], SELECTOR)
        self.assertEqual(by_test["auth-session-timeout.log"], AUTH_STATE)
        self.assertEqual(by_test["route-permission-hang.log"], AUTH_STATE)
        self.assertEqual(by_test["browser-lifecycle-target-closed.log"], LIFECYCLE)
        self.assertEqual(by_test["network-econnreset.log"], NETWORK)
        self.assertEqual(by_test["network-neterr-timeout.log"], NETWORK)
        self.assertEqual(len(result.findings), 6)


if __name__ == "__main__":
    unittest.main()
