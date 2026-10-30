#!/usr/bin/env python3
"""Run the test command declared in each project manifest.

Projects without a declared test command are skipped and reported, so a
silent project cannot pass unnoticed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402

TIMEOUT_SECONDS = 900


def run(root: Path) -> list[str]:
    findings: list[str] = []
    base = root / "projects"
    manifests = sorted(base.glob("*/*/*/project.json")) if base.exists() else []
    for manifest in manifests:
        pdir = manifest.parent
        rel = pdir.relative_to(root).as_posix()
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            findings.append(f"{rel}: unreadable project.json ({exc})")
            continue
        command = (data.get("commands") or {}).get("test")
        if not command:
            print(f"SKIP {rel}: no test command declared")
            continue
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=pdir,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            findings.append(f"{rel}: test command timed out after {TIMEOUT_SECONDS}s")
            continue
        if proc.returncode == 0:
            print(f"PASS {rel}")
        else:
            findings.append(f"{rel}: test command failed (exit {proc.returncode})")
            output = (proc.stdout + proc.stderr).strip().splitlines()
            for line in output[-15:]:
                print(f"    {line}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    findings = run(Path(args.root).resolve())
    return _common.report(
        f"project test suites: {len(findings)} failure(s)", findings
    )


if __name__ == "__main__":
    sys.exit(main())
