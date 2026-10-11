"""Group pull requests into work themes from labels, title prefixes and keywords."""

from __future__ import annotations

import re

from impact_review.core.models import PullRequest

THEMES = (
    "feature",
    "fix",
    "refactor",
    "test",
    "docs",
    "ci_infra",
    "performance",
    "security",
    "dependencies",
    "other",
)

_LABEL_THEMES = (
    ("security", ("security", "vulnerability", "cve")),
    ("dependencies", ("dependencies", "deps", "dependabot", "renovate")),
    ("fix", ("bug", "fix", "hotfix", "regression")),
    ("performance", ("performance", "perf")),
    ("docs", ("documentation", "docs")),
    ("test", ("test", "testing", "tests")),
    ("ci_infra", ("ci", "infra", "infrastructure", "build", "devops")),
    ("refactor", ("refactor", "refactoring", "cleanup", "tech-debt", "tech debt")),
    ("feature", ("feature", "enhancement", "feat")),
)

_PREFIX_THEMES = {
    "feat": "feature",
    "feature": "feature",
    "fix": "fix",
    "hotfix": "fix",
    "bugfix": "fix",
    "refactor": "refactor",
    "test": "test",
    "tests": "test",
    "docs": "docs",
    "doc": "docs",
    "ci": "ci_infra",
    "build": "ci_infra",
    "infra": "ci_infra",
    "perf": "performance",
    "security": "security",
    "deps": "dependencies",
    "dependencies": "dependencies",
}

_KEYWORD_THEMES = (
    ("security", r"\b(security|vuln\w*|cve-\d+|hardening)\b"),
    ("dependencies", r"\b(bump|dependenc\w*|upgrade\w*|dependabot|renovate)\b"),
    ("fix", r"\b(fix\w*|bug\w*|hotfix|regression|broken|crash\w*)\b"),
    ("performance", r"\b(perf\w*|faster|speed\w*|latency|optimi\w*|cache|caching)\b"),
    ("test", r"\b(test\w*|coverage|e2e|spec)\b"),
    ("docs", r"\b(doc\w*|readme|changelog|guide)\b"),
    (
        "ci_infra",
        r"\b(ci|cd|pipeline|workflow\w*|docker\w*|terraform|helm|k8s|kubernetes|deploy\w*|infra\w*)\b",
    ),
    ("refactor", r"\b(refactor\w*|clean\s?up|rename\w*|simplif\w*|extract\w*|restructur\w*)\b"),
    ("feature", r"\b(add\w*|implement\w*|support\w*|introduc\w*|enable\w*|new|create\w*)\b"),
)
_KEYWORD_PATTERNS = [
    (theme, re.compile(pattern, re.IGNORECASE)) for theme, pattern in _KEYWORD_THEMES
]
_PREFIX = re.compile(
    r"^\s*(?:\[(?P<bracket>[a-z]+)\]|(?P<word>[a-z]+)(?:\([^)]*\))?!?:)", re.IGNORECASE
)


def classify(pull_request: PullRequest) -> str:
    """Return the theme name: labels first, then a title prefix, then title keywords."""
    labels = [label.lower() for label in pull_request.labels]
    for theme, words in _LABEL_THEMES:
        if any(any(word in label for word in words) for label in labels):
            return theme
    title = pull_request.title
    if match := _PREFIX.match(title):
        prefix = (match.group("bracket") or match.group("word")).lower()
        if prefix in _PREFIX_THEMES:
            return _PREFIX_THEMES[prefix]
        if prefix == "chore" and re.search(r"dep", title, re.IGNORECASE):
            return "dependencies"
    for theme, pattern in _KEYWORD_PATTERNS:
        if pattern.search(title):
            return theme
    return "other"
