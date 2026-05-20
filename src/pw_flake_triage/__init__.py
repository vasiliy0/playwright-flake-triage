"""Playwright flaky test triage toolkit."""

from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("playwright-flake-triage")
except PackageNotFoundError:
    # Source-tree fallback for local test runs before the package is installed.
    __version__ = "0.1.5"
