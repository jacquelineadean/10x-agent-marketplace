#!/usr/bin/env bash
# Builds a Python service repo with its own PR template and CONTRIBUTING rules, plus a fix branch.
set -eu
mkdir -p repo && cd repo
git init -q -b main
git config user.email dev@example.com && git config user.name "Dev"
mkdir -p .github billing tests
cat > .github/pull_request_template.md <<'T'
## What

## Why

## QA notes

## Deploy notes

## Checklist
- [ ] Tests pass (`make test`)
- [ ] Migration reviewed by #db-owners if any
- [ ] Runbook updated
T
cat > CONTRIBUTING.md <<'T'
# Contributing
PR titles: `<type>(<scope>): <subject>`. Allowed scopes: `billing`, `auth`, `api`, `infra`.
Keep PRs under 300 lines. Every PR fills every section of the template; write "n/a" with a reason.
T
cat > billing/invoice.py <<'P'
def total_cents(lines):
    return sum(round(l["qty"] * l["unit_price"] * 100) for l in lines)
P
cat > Makefile <<'P'
test:
	pytest -q
P
git add -A && git commit -qm "chore: initial billing service"
git switch -qc fix/318-invoice-rounding
cat > billing/invoice.py <<'P'
from decimal import Decimal, ROUND_HALF_EVEN


def total_cents(lines):
    """Sum invoice lines in integer cents, rounding once at the end (banker's rounding).

    Rounding per line made a 3-line invoice of 3 x 0.335 total 102 cents instead of 100.
    """
    total = sum(Decimal(str(l["qty"])) * Decimal(str(l["unit_price"])) for l in lines)
    return int((total * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
P
cat > tests/test_invoice.py <<'P'
from billing.invoice import total_cents

def test_rounds_once_at_the_end():
    assert total_cents([{"qty": 1, "unit_price": 0.335}] * 3) == 100

def test_whole_cents_unchanged():
    assert total_cents([{"qty": 2, "unit_price": 4.5}]) == 900
P
git add -A && git commit -qm "fix(billing): round invoice totals once, not per line"
