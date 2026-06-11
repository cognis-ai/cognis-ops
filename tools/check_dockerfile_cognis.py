#!/usr/bin/env python3
"""Guard the Cognis telemetry/branding invariants in Dockerfile.cognis.

Gate-1 ops AR-4: a rebase or careless image rebuild could silently re-enable
Sentry/LangSmith/LangChain-tracing egress. This check fails CI if any of the
three telemetry unsets — required by cognis-platform/docs/specs/cost-policy.md
— or the COGNIS_BRANDING default disappears from Dockerfile.cognis:

    SENTRY_DSN=""
    LANGSMITH_API_KEY=""
    LANGCHAIN_TRACING_V2="false"
    COGNIS_BRANDING=on

Stdlib-only so it runs on any CI Python without installing the project.

Usage: check_dockerfile_cognis.py [path-to-Dockerfile.cognis]
(defaults to Dockerfile.cognis next to the repo root)
"""

import re
import sys
from pathlib import Path

# Each entry: (env var, required value regex, expected literal, reason).
# Values may be quoted or bare in Dockerfile ENV syntax — accept both.
REQUIRED_ENV = (
    (
        "SENTRY_DSN",
        r'(""|\'\')',
        'SENTRY_DSN=""',
        "Sentry egress must stay disabled (cost-policy.md)",
    ),
    (
        "LANGSMITH_API_KEY",
        r'(""|\'\')',
        'LANGSMITH_API_KEY=""',
        "LangSmith egress must stay disabled (cost-policy.md)",
    ),
    (
        "LANGCHAIN_TRACING_V2",
        r'("false"|\'false\'|false)',
        'LANGCHAIN_TRACING_V2="false"',
        "LangChain tracing must stay off (cost-policy.md)",
    ),
    (
        "COGNIS_BRANDING",
        r'("on"|\'on\'|on)',
        "COGNIS_BRANDING=on",
        "Cognis image must default to branded output",
    ),
)


def check(dockerfile: Path) -> list[str]:
    """Return a list of violation messages (empty = OK)."""
    if not dockerfile.is_file():
        return [f"{dockerfile}: file is missing"]
    content = dockerfile.read_text(encoding="utf-8")

    violations = []
    for var, value_re, expected, reason in REQUIRED_ENV:
        # Matches `VAR=<value>` inside an ENV instruction (incl. backslash
        # continuation lines, which begin with whitespace).
        pattern = rf"^\s*(ENV\s+)?{re.escape(var)}={value_re}\s*(\\)?\s*$"
        if not re.search(pattern, content, flags=re.MULTILINE):
            violations.append(f"{var}: expected `{expected}` assignment — {reason}")
    return violations


def main(argv: list[str]) -> int:
    default = Path(__file__).resolve().parent.parent / "Dockerfile.cognis"
    dockerfile = Path(argv[1]) if len(argv) > 1 else default

    violations = check(dockerfile)
    if violations:
        print(f"ERROR: {dockerfile} lost required telemetry/branding guards:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print(
            "Restore the ENV unsets per cognis-platform/docs/specs/cost-policy.md "
            "(Gate-1 ops AR-4).",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {dockerfile} retains the telemetry unsets + COGNIS_BRANDING default.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
