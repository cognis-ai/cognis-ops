#!/usr/bin/env python3
"""Brand-residue gate for the Cognis layer (gate2 ops B5).

Fails CI if the upstream brand — ``(?i)opensre|tracer`` — appears in any
*customer-facing string* in the Cognis-owned surfaces:

- ``app/cognis/**/*.py``: every string literal EXCEPT docstrings. Code
  comments and docstrings referencing upstream are deliberately allowed
  (honest fork attribution); rendered output strings are not.
- ``COGNIS-README.md``: every line, EXCEPT lines carrying an explicit
  ``<!-- upstream-ok -->`` marker (deliberate Apache-2.0 attribution /
  upstream pointers).

Stdlib-only so it runs on any CI Python without installing the project.
The runtime twin of this static gate is
``tests/cognis/test_branding_output.py::test_cognis_layer_output_has_no_upstream_residue``.

Usage: check_brand_residue.py [repo-root]   (defaults to the script's repo)
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

RESIDUE = re.compile(r"(?i)(opensre|tracer)")
README_ALLOW_MARKER = "<!-- upstream-ok -->"


def _docstring_constants(tree: ast.AST) -> set[int]:
    """ids of Constant nodes that are docstrings (module/class/function)."""
    allowed: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                allowed.add(id(body[0].value))
    return allowed


def check_python_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings = _docstring_constants(tree)
    violations = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            match = RESIDUE.search(node.value)
            if match:
                violations.append(
                    f"{path}:{node.lineno}: upstream residue {match.group(0)!r} "
                    f"in string literal {node.value!r}"
                )
    return violations


def check_readme(path: Path) -> list[str]:
    violations = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if README_ALLOW_MARKER in line:
            continue
        match = RESIDUE.search(line)
        if match:
            violations.append(
                f"{path}:{lineno}: upstream residue {match.group(0)!r} "
                f"(add {README_ALLOW_MARKER} only for deliberate attribution)"
            )
    return violations


def main(argv: list[str]) -> int:
    repo_root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent

    violations: list[str] = []
    for py_file in sorted((repo_root / "app" / "cognis").rglob("*.py")):
        violations.extend(check_python_file(py_file))

    readme = repo_root / "COGNIS-README.md"
    if readme.is_file():
        violations.extend(check_readme(readme))
    else:
        violations.append(f"{readme}: file is missing")

    if violations:
        print("ERROR: upstream brand residue in customer-facing strings:", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        print(
            "Customer-facing Cognis-layer copy must not carry the upstream brand "
            "(gate2 ops B5). Reword the string, or keep the reference in a code "
            "comment/docstring instead.",
            file=sys.stderr,
        )
        return 1

    print("OK: no upstream brand residue in customer-facing Cognis-layer strings.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
