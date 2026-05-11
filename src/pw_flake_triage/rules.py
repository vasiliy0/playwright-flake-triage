from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


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


def classify(text: str) -> list[tuple[Rule, int]]:
    hits = [(rule, rule.match_count(text)) for rule in RULES]
    hits = [h for h in hits if h[1] > 0]
    suppressed = {rid for rule, _ in hits for rid in rule.suppresses}
    hits = [(rule, count) for rule, count in hits if rule.id not in suppressed]
    return sorted(hits, key=lambda x: (-x[0].priority, -x[1], x[0].id))


def all_rule_ids() -> Iterable[str]:
    return (r.id for r in RULES)
