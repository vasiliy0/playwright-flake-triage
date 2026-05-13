from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class Rule:
    id: str
    label: str
    severity: str
    patterns: tuple[str, ...]
    why: str
    fixes: tuple[str, ...]
    priority: int = 50
    suppresses: tuple[str, ...] = ()

    def match_count(self, text: str) -> int:
        return sum(1 for p in self.patterns if re.search(p, text, flags=re.I | re.M))


RULES: tuple[Rule, ...] = (
    Rule(
        id="selector-ambiguity",
        label="Ambiguous or brittle selector",
        severity="high",
        patterns=(
            r"strict mode violation",
            r"resolved to \d+ elements",
            r"locator.*matched",
            r"element is not attached",
            r"detached from DOM",
        ),
        why="The locator may target multiple elements or a DOM node that is re-rendered during the action.",
        fixes=(
            "Prefer role/test-id locators and narrow with accessible name or parent scope.",
            "Avoid index-based selectors unless the order is part of the contract.",
            "Re-query after UI transitions instead of storing element handles.",
        ),
        priority=100,
        suppresses=("timeout-wait",),
    ),
    Rule(
        id="auth-session-state",
        label="Auth/session or expected page state mismatch",
        severity="high",
        patterns=(
            r"not signed in|logged out|login page|sign in|authenticated|unauthorized|access denied",
            r"role .*not .*allowed|permission|redirect|session expired|cookie|storage state",
            r"waiting for .*checkbox|waiting for .*Username|waiting for .*password",
        ),
        why="The test may be on the wrong page/state because authentication, role permissions, cookies, or setup data differ from expectations.",
        fixes=(
            "Verify the test starts with the intended storage state, user role, and seeded data.",
            "Assert the current URL/page heading before waiting for app-specific controls.",
            "Separate product auth failures from selector/wait flakes in the CI report.",
        ),
        priority=90,
        suppresses=("timeout-wait",),
    ),
    Rule(
        id="timeout-wait",
        label="Timeout / wait condition instability",
        severity="high",
        patterns=(r"Timeout\s+\d+ms exceeded", r"waiting for", r"toBeVisible|toHaveText|toBeEnabled|toHaveURL", r"exceeded.*timeout"),
        why="The test likely assumes UI/network readiness earlier than the app can guarantee in CI.",
        fixes=(
            "Replace fixed sleeps with web-first assertions on the real readiness signal.",
            "Assert route/API completion or durable UI state before interacting.",
            "Check whether CI CPU/network variance makes the timeout too aggressive.",
        ),
        priority=60,
    ),
    Rule(
        id="network-backend",
        label="Network or backend dependency flake",
        severity="medium",
        patterns=(r"net::ERR", r"ECONNRESET|ECONNREFUSED|ETIMEDOUT|ENOTFOUND", r"5\d\d", r"request failed", r"response status"),
        why="The test depends on live services, slow APIs, or unstable test data setup.",
        fixes=(
            "Mock third-party calls or record deterministic fixtures for non-contract tests.",
            "Add explicit API health/data setup checks before the UI flow.",
            "Separate product failures from environment failures in CI reporting.",
        ),
        priority=70,
    ),
    Rule(
        id="browser-lifecycle",
        label="Browser/context/page lifecycle race",
        severity="medium",
        patterns=(r"Target page, context or browser has been closed", r"Browser has been closed", r"Protocol error", r"Execution context was destroyed"),
        why="The page/context may close while async work is still running, often from teardown or navigation races.",
        fixes=(
            "Await navigations/downloads/popups explicitly with Promise.all patterns.",
            "Check afterEach/fixture teardown for un-awaited async operations.",
            "Avoid sharing mutable page/context state across parallel tests.",
        ),
        priority=70,
    ),
    Rule(
        id="navigation-frame-race",
        label="Navigation/frame detachment race",
        severity="medium",
        patterns=(r"Frame was detached", r"Navigation .*interrupted", r"navigating frame was detached", r"frame.*detached"),
        why="The test may interact with a frame or page while the app is navigating, reloading, or replacing embedded content.",
        fixes=(
            "Wrap the action that triggers navigation in an explicit wait/expect pattern.",
            "Avoid interacting with frame locators captured before navigation or iframe replacement.",
            "Assert a durable post-navigation URL, heading, or app-ready marker before the next action.",
        ),
        priority=75,
        suppresses=("timeout-wait",),
    ),
    Rule(
        id="visual-snapshot",
        label="Visual/snapshot instability",
        severity="medium",
        patterns=(r"toHaveScreenshot|toMatchSnapshot", r"Screenshot comparison failed", r"pixel.*different", r"snapshot.*does not match"),
        why="Rendering may vary by font, animation, viewport, OS, time, or dynamic content.",
        fixes=(
            "Freeze animations, dates, random values, fonts, and viewport.",
            "Mask dynamic regions and use deterministic test data.",
            "Keep visual tests in a controlled browser/OS image.",
        ),
        priority=70,
    ),
    Rule(
        id="parallel-state",
        label="Parallelism / shared state collision",
        severity="medium",
        patterns=(r"already exists", r"duplicate key", r"locked", r"is being used", r"parallel", r"worker \d+"),
        why="Tests may collide on users, records, files, ports, local storage, or worker-shared fixtures.",
        fixes=(
            "Namespace test data by worker/test id and clean it idempotently.",
            "Avoid order dependence; make each test create its own state.",
            "Run suspected specs serially once to confirm a parallel-state smell.",
        ),
        priority=50,
    ),
)


def classify(text: str, rules: Sequence[Rule] | None = None) -> list[tuple[Rule, int]]:
    active_rules = rules or RULES
    hits = [(rule, rule.match_count(text)) for rule in active_rules]
    hits = [h for h in hits if h[1] > 0]
    suppressed = {rid for rule, _ in hits for rid in rule.suppresses}
    hits = [(rule, count) for rule, count in hits if rule.id not in suppressed]
    return sorted(hits, key=lambda x: (-x[0].priority, -x[1], x[0].id))


def load_rules_config(path: str | Path) -> tuple[Rule, ...]:
    """Load custom rules from a JSON config file.

    Expected shape:
    {
      "rules": [
        {
          "id": "my-rule",
          "label": "My custom category",
          "severity": "medium",
          "patterns": ["regex"],
          "why": "Why this happens",
          "fixes": ["Suggested fix"],
          "priority": 80,
          "suppresses": ["timeout-wait"]
        }
      ]
    }
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_rules = data.get("rules") if isinstance(data, dict) else None
    if not isinstance(raw_rules, list):
        raise ValueError("Rules config must be a JSON object with a 'rules' list.")
    return tuple(_rule_from_dict(item, path) for item in raw_rules)


def _rule_from_dict(item: Any, path: str | Path) -> Rule:
    if not isinstance(item, dict):
        raise ValueError(f"Invalid rule in {path}: each rule must be an object.")
    required = ("id", "label", "severity", "patterns", "why", "fixes")
    missing = [key for key in required if key not in item]
    if missing:
        raise ValueError(f"Invalid rule in {path}: missing {', '.join(missing)}.")
    patterns = item["patterns"]
    fixes = item["fixes"]
    if not isinstance(patterns, list) or not patterns or not all(isinstance(p, str) and p for p in patterns):
        raise ValueError(f"Invalid rule {item.get('id')!r} in {path}: patterns must be a non-empty string list.")
    if not isinstance(fixes, list) or not fixes or not all(isinstance(f, str) and f for f in fixes):
        raise ValueError(f"Invalid rule {item.get('id')!r} in {path}: fixes must be a non-empty string list.")
    suppresses = item.get("suppresses", [])
    if not isinstance(suppresses, list) or not all(isinstance(s, str) for s in suppresses):
        raise ValueError(f"Invalid rule {item.get('id')!r} in {path}: suppresses must be a string list.")
    priority = item.get("priority", 50)
    if not isinstance(priority, int):
        raise ValueError(f"Invalid rule {item.get('id')!r} in {path}: priority must be an integer.")
    return Rule(
        id=_required_str(item, "id", path),
        label=_required_str(item, "label", path),
        severity=_required_str(item, "severity", path),
        patterns=tuple(patterns),
        why=_required_str(item, "why", path),
        fixes=tuple(fixes),
        priority=priority,
        suppresses=tuple(suppresses),
    )


def _required_str(item: dict[str, Any], key: str, path: str | Path) -> str:
    value = item[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid rule in {path}: {key} must be a non-empty string.")
    return value.strip()


def all_rule_ids() -> Iterable[str]:
    return (r.id for r in RULES)
