# Playwright Flake Triage Report

Scanned files: **14**
Findings: **14**

## Summary by suspected cause
- **Ambiguous or brittle selector**: 4
- **Network or backend dependency flake**: 3
- **Browser/context/page lifecycle race**: 2
- **Auth/session or expected page state mismatch**: 2
- **Visual/snapshot instability**: 1
- **Timeout / wait condition instability**: 1
- **Navigation/frame detachment race**: 1

## Repeated failure groups
- **Ambiguous or brittle selector**: 2 findings
  - Tests: dynamic-ci-retry-1.log, dynamic-ci-retry-2.log

## Findings
### 1. Visual/snapshot instability
- File: `products/playwright-flake-triage/examples/ci.log`
- Test: `ci.log`
- Status: `log`
- Severity: **medium**; confidence: **100%**
- Signal: Error: expect(page).toHaveScreenshot('dashboard.png') failed Screenshot comparison failed: 103 pixels different
- Why this happens: Rendering may vary by font, animation, viewport, OS, time, or dynamic content.
- Suggested fixes:
  - Freeze animations, dates, random values, fonts, and viewport.
  - Mask dynamic regions and use deterministic test data.
  - Keep visual tests in a controlled browser/OS image.

### 2. Ambiguous or brittle selector
- File: `products/playwright-flake-triage/examples/dynamic-ci-retry-1.log`
- Test: `dynamic-ci-retry-1.log`
- Status: `log`
- Severity: **high**; confidence: **85%**
- Signal: Error: strict mode violation: getByRole('button', { name: 'Save' }) resolved to 2 elements at /home/runner/work/app/app/tests/settings.spec.ts:47:13 worker-1 retry-1 pid 12345 run 778899 screenshot: /tmp/playwright-artifacts/48f97d4e965e4c4ab333aa0011223344/error-context.png duration 30124ms at http://localhost:4173/settings
- Why this happens: The locator may target multiple elements or a DOM node that is re-rendered during the action.
- Suggested fixes:
  - Prefer role/test-id locators and narrow with accessible name or parent scope.
  - Avoid index-based selectors unless the order is part of the contract.
  - Re-query after UI transitions instead of storing element handles.

### 3. Ambiguous or brittle selector
- File: `products/playwright-flake-triage/examples/dynamic-ci-retry-2.log`
- Test: `dynamic-ci-retry-2.log`
- Status: `log`
- Severity: **high**; confidence: **85%**
- Signal: Error: strict mode violation: getByRole('button', { name: 'Save' }) resolved to 2 elements at /Users/runner/work/app/app/tests/settings.spec.ts:93:21 worker-4 retry-2 pid 67890 run 112233 screenshot: /var/folders/playwright-artifacts/0123456789abcdef0123456789abcdef/error-context.png duration 29876ms at http://localhost:5173/settings
- Why this happens: The locator may target multiple elements or a DOM node that is re-rendered during the action.
- Suggested fixes:
  - Prefer role/test-id locators and narrow with accessible name or parent scope.
  - Avoid index-based selectors unless the order is part of the contract.
  - Re-query after UI transitions instead of storing element handles.

### 4. Network or backend dependency flake
- File: `products/playwright-flake-triage/examples/dynamic-ci-retry-2.log`
- Test: `dynamic-ci-retry-2.log`
- Status: `log`
- Severity: **medium**; confidence: **70%**
- Signal: Error: strict mode violation: getByRole('button', { name: 'Save' }) resolved to 2 elements at /Users/runner/work/app/app/tests/settings.spec.ts:93:21 worker-4 retry-2 pid 67890 run 112233 screenshot: /var/folders/playwright-artifacts/0123456789abcdef0123456789abcdef/error-context.png duration 29876ms at http://localhost:5173/settings
- Why this happens: The test depends on live services, slow APIs, or unstable test data setup.
- Suggested fixes:
  - Mock third-party calls or record deterministic fixtures for non-contract tests.
  - Add explicit API health/data setup checks before the UI flow.
  - Separate product failures from environment failures in CI reporting.

### 5. Browser/context/page lifecycle race
- File: `products/playwright-flake-triage/examples/junit.xml`
- Test: `auth.spec.ts.login redirects`
- Status: `failure`
- Severity: **medium**; confidence: **100%**
- Signal: Target page, context or browser has been closed Protocol error during navigation
- Why this happens: The page/context may close while async work is still running, often from teardown or navigation races.
- Suggested fixes:
  - Await navigations/downloads/popups explicitly with Promise.all patterns.
  - Check afterEach/fixture teardown for un-awaited async operations.
  - Avoid sharing mutable page/context state across parallel tests.

### 6. Timeout / wait condition instability
- File: `products/playwright-flake-triage/examples/playwright-report.json`
- Test: `checkout.spec.ts > submits order`
- Status: `timedOut`
- Severity: **high**; confidence: **85%**
- Signal: Timeout 30000ms exceeded. locator('[data-testid=submit]').click: waiting for element to be visible
- Why this happens: The test likely assumes UI/network readiness earlier than the app can guarantee in CI.
- Suggested fixes:
  - Replace fixed sleeps with web-first assertions on the real readiness signal.
  - Assert route/API completion or durable UI state before interacting.
  - Check whether CI CPU/network variance makes the timeout too aggressive.

### 7. Ambiguous or brittle selector
- File: `products/playwright-flake-triage/examples/playwright-report.json`
- Test: `checkout.spec.ts > shows product card`
- Status: `failed`
- Severity: **high**; confidence: **85%**
- Signal: strict mode violation: locator('.card') resolved to 2 elements
- Why this happens: The locator may target multiple elements or a DOM node that is re-rendered during the action.
- Suggested fixes:
  - Prefer role/test-id locators and narrow with accessible name or parent scope.
  - Avoid index-based selectors unless the order is part of the contract.
  - Re-query after UI transitions instead of storing element handles.

### 8. Auth/session or expected page state mismatch
- File: `products/playwright-flake-triage/examples/public-issue-symptoms/auth-session-timeout.log`
- Test: `auth-session-timeout.log`
- Status: `log`
- Issue: Synthetic auth/session timeout symptom
- Source: https://github.com/example/repo/issues/123
- Severity: **high**; confidence: **70%**
- Signal: Playwright TimeoutError: Timeout 30000ms exceeded. logs: waiting for get_by_label("Keep me signed in") The browser reached a login page but expected an authenticated application page.
- Why this happens: The test may be on the wrong page/state because authentication, role permissions, cookies, or setup data differ from expectations.
- Suggested fixes:
  - Verify the test starts with the intended storage state, user role, and seeded data.
  - Assert the current URL/page heading before waiting for app-specific controls.
  - Separate product auth failures from selector/wait flakes in the CI report.

### 9. Browser/context/page lifecycle race
- File: `products/playwright-flake-triage/examples/public-issue-symptoms/browser-lifecycle-target-closed.log`
- Test: `browser-lifecycle-target-closed.log`
- Status: `log`
- Issue: Synthetic browser lifecycle target-closed symptom
- Source: https://github.com/example/repo/issues/126
- Severity: **medium**; confidence: **85%**
- Signal: Playwright::TargetClosedError: Target page, context or browser has been closed. The job finished while an async page operation was still running.
- Why this happens: The page/context may close while async work is still running, often from teardown or navigation races.
- Suggested fixes:
  - Await navigations/downloads/popups explicitly with Promise.all patterns.
  - Check afterEach/fixture teardown for un-awaited async operations.
  - Avoid sharing mutable page/context state across parallel tests.

### 10. Navigation/frame detachment race
- File: `products/playwright-flake-triage/examples/public-issue-symptoms/navigation-frame-detached.log`
- Test: `navigation-frame-detached.log`
- Status: `log`
- Issue: Synthetic navigation/frame detachment symptom
- Source: https://github.com/example/repo/issues/456
- Severity: **medium**; confidence: **100%**
- Signal: Error: locator.click: Frame was detached Call log: - waiting for getByRole('link', { name: 'Checkout' }) - attempting click action - navigation interrupted by another navigation
- Why this happens: The test may interact with a frame or page while the app is navigating, reloading, or replacing embedded content.
- Suggested fixes:
  - Wrap the action that triggers navigation in an explicit wait/expect pattern.
  - Avoid interacting with frame locators captured before navigation or iframe replacement.
  - Assert a durable post-navigation URL, heading, or app-ready marker before the next action.

### 11. Network or backend dependency flake
- File: `products/playwright-flake-triage/examples/public-issue-symptoms/network-econnreset.log`
- Test: `network-econnreset.log`
- Status: `log`
- Issue: Synthetic network ECONNRESET symptom
- Source: https://github.com/example/repo/issues/127
- Severity: **medium**; confidence: **85%**
- Signal: Error: request failed while running Playwright in a container. Socket error: ECONNRESET when targeting the browser service.
- Why this happens: The test depends on live services, slow APIs, or unstable test data setup.
- Suggested fixes:
  - Mock third-party calls or record deterministic fixtures for non-contract tests.
  - Add explicit API health/data setup checks before the UI flow.
  - Separate product failures from environment failures in CI reporting.

### 12. Network or backend dependency flake
- File: `products/playwright-flake-triage/examples/public-issue-symptoms/network-neterr-timeout.log`
- Test: `network-neterr-timeout.log`
- Status: `log`
- Issue: Synthetic net::ERR timeout symptom
- Source: https://github.com/example/repo/issues/128
- Severity: **medium**; confidence: **70%**
- Signal: page.goto failed: net::ERR_CONNECTION_TIMED_OUT at https://localhost:7119/ The application server was not reachable before the Playwright test started.
- Why this happens: The test depends on live services, slow APIs, or unstable test data setup.
- Suggested fixes:
  - Mock third-party calls or record deterministic fixtures for non-contract tests.
  - Add explicit API health/data setup checks before the UI flow.
  - Separate product failures from environment failures in CI reporting.

### 13. Auth/session or expected page state mismatch
- File: `products/playwright-flake-triage/examples/public-issue-symptoms/route-permission-hang.log`
- Test: `route-permission-hang.log`
- Status: `log`
- Issue: Synthetic role permission page-state symptom
- Source: https://github.com/example/repo/issues/125
- Severity: **high**; confidence: **85%**
- Signal: Page.goto: Timeout 30000ms exceeded waiting for networkidle. The CEO role is not allowed for this route and the app hangs instead of redirecting to Access Denied.
- Why this happens: The test may be on the wrong page/state because authentication, role permissions, cookies, or setup data differ from expectations.
- Suggested fixes:
  - Verify the test starts with the intended storage state, user role, and seeded data.
  - Assert the current URL/page heading before waiting for app-specific controls.
  - Separate product auth failures from selector/wait flakes in the CI report.

### 14. Ambiguous or brittle selector
- File: `products/playwright-flake-triage/examples/public-issue-symptoms/strict-mode-selector.log`
- Test: `strict-mode-selector.log`
- Status: `log`
- Issue: Synthetic strict mode selector symptom
- Source: https://github.com/example/repo/issues/124
- Severity: **high**; confidence: **85%**
- Signal: Error: strict mode violation: getByRole('heading', { name: /devices/i }).or(getByRole('heading', { name: /sessions/i })) resolved to 2 elements. await expect(locator).toBeVisible({ timeout: 10000 })
- Why this happens: The locator may target multiple elements or a DOM node that is re-rendered during the action.
- Suggested fixes:
  - Prefer role/test-id locators and narrow with accessible name or parent scope.
  - Avoid index-based selectors unless the order is part of the contract.
  - Re-query after UI transitions instead of storing element handles.
