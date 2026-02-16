from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

FORBIDDEN_MODULES = {
    "fastapi",
    "pydantic",
    "sqlalchemy",
    "redis",
    "httpx",
    "requests",
    "opentelemetry",
    "prometheus_client",
    "rop.api",
    "rop.infrastructure",
}

DEFAULT_DOMAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "rop" / "domain"


@dataclass(frozen=True)
class Violation:
    file_path: Path
    line: int
    module: str


def _python_files(root: Path) -> Iterable[Path]:
    if root.is_file() and root.suffix == ".py":
        yield root
        return
    if root.is_dir():
        yield from root.rglob("*.py")


def _matches_forbidden(module: str) -> bool:
    for forbidden in FORBIDDEN_MODULES:
        if module == forbidden or module.startswith(f"{forbidden}."):
            return True
    return False


def _scan_file(file_path: Path) -> list[Violation]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    violations: list[Violation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _matches_forbidden(alias.name):
                    violations.append(
                        Violation(file_path=file_path, line=node.lineno, module=alias.name)
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            if _matches_forbidden(node.module):
                violations.append(
                    Violation(file_path=file_path, line=node.lineno, module=node.module)
                )

    return violations


def find_violations(paths: Sequence[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in paths:
        for file_path in _python_files(path):
            violations.extend(_scan_file(file_path))
    return violations


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dependency policy check for backend/src/rop/domain imports."
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Path to scan (repeatable). Defaults to backend/src/rop/domain.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    scan_paths = [Path(item) for item in args.path] if args.path else [DEFAULT_DOMAIN_PATH]

    violations = find_violations(scan_paths)
    if not violations:
        print("depcheck passed")
        return 0

    print("depcheck failed: forbidden imports detected")
    for violation in violations:
        print(f"{violation.file_path}:{violation.line} -> {violation.module}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
