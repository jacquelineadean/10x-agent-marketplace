"""Print a `claude plugin eval` result document as a Markdown score table.

CI appends the output to the job summary, so a reviewer sees each case's score next to
the threshold without downloading the HTML report.

Usage: python3 eval_summary.py results.json THRESHOLD
"""

import json
import sys
from pathlib import Path
from typing import Any


def _score(value: object) -> str:
    return f"{value:.2f}" if isinstance(value, (int, float)) else "n/a"


def _delta(value: object) -> str:
    return f"{value:+.2f}" if isinstance(value, (int, float)) else "n/a"


def _row(case: dict[str, Any], threshold: float) -> str:
    totals = case.get("aggregates", {})
    score = totals.get("score")
    passed = isinstance(score, (int, float)) and score >= threshold
    runs = case.get("arms", {}).get("with", [])
    errors = sorted({run["error"] for run in runs if run.get("error")})
    note = "; ".join(errors)[:120]
    return (
        f"| {case['name']} | {_score(score)} | {_delta(totals.get('delta'))} "
        f"| {len(runs)} | {'pass' if passed else 'FAIL'} | {note} |"
    )


def render(result: dict[str, Any], threshold: float) -> str:
    totals = result.get("aggregates", {})
    lines = [
        "## chronicle evals",
        "",
        f"Suite score {_score(totals.get('overallScore'))}, "
        f"{totals.get('casesPassed', 0)} of {totals.get('casesTotal', 0)} cases at or above "
        f"{threshold:.2f}, mean delta {_delta(totals.get('meanDelta'))}, "
        f"cost ${result.get('costUsd', 0):.2f}, Claude Code {result.get('claudeVersion', '?')}.",
    ]
    if result.get("partial"):
        lines.append(f"Partial run: {result.get('partialReason', 'unknown reason')}.")
    lines += [
        "",
        "| Case | Score | Delta | Runs | Result | Run errors |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines += [_row(case, threshold) for case in result.get("cases", [])]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.stderr.write("usage: eval_summary.py results.json THRESHOLD\n")
        return 2
    result = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    sys.stdout.write(render(result, float(argv[2])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
