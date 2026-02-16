from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_depcheck_fails_on_forbidden_import(tmp_path: Path) -> None:
    domain_dir = tmp_path / "domain"
    domain_dir.mkdir(parents=True, exist_ok=True)

    violating_file = domain_dir / "model.py"
    violating_file.write_text("import sqlalchemy\n", encoding="utf-8")

    script_path = Path(__file__).resolve().parents[2] / "tools" / "depcheck.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--path", str(domain_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    combined_output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode != 0
    assert "sqlalchemy" in combined_output
    assert str(violating_file) in combined_output
