#!/usr/bin/env python3
"""Build wheel and sdist, install wheel in a clean venv, and run smoke commands."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import shutil
import os
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)


def main() -> int:
    repo_root = Path(__file__).parent.parent.resolve()
    errors: list[str] = []

    # 1. Build wheel and sdist
    print("==> Building wheel and sdist")
    dist = repo_root / "dist"
    if dist.exists():
        resolved_dist = dist.resolve()
        if resolved_dist != repo_root / "dist":
            errors.append(f"Refusing to remove unexpected dist path: {resolved_dist}")
        else:
            shutil.rmtree(resolved_dist)
    result = run([sys.executable, "-m", "build", "--wheel", "--sdist"], cwd=repo_root, check=False)
    if result.returncode != 0:
        errors.append(f"build failed: {result.stderr}")
        print(result.stdout)
        print(result.stderr)
    else:
        print("Build OK")

    wheels = list(dist.glob("*.whl"))
    sdists = list(dist.glob("*.tar.gz"))
    if not wheels:
        errors.append("No wheel produced in dist/")
    if not sdists:
        errors.append("No sdist produced in dist/")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    wheel = wheels[0]
    sdist = sdists[0]
    print(f"Wheel: {wheel.name}")
    print(f"Sdist: {sdist.name}")

    # 2. Clean venv install smoke
    with tempfile.TemporaryDirectory() as tmp:
        venv_path = Path(tmp) / "venv"
        print(f"==> Creating clean venv at {venv_path}")
        run([sys.executable, "-m", "venv", str(venv_path)])

        pip = venv_path / "Scripts" / "pip.exe" if sys.platform == "win32" else venv_path / "bin" / "pip"
        python = venv_path / "Scripts" / "python.exe" if sys.platform == "win32" else venv_path / "bin" / "python"
        agentheim = venv_path / "Scripts" / "agentheim.exe" if sys.platform == "win32" else venv_path / "bin" / "agentheim"

        print("==> Installing wheel")
        result = run([str(pip), "install", str(wheel)])
        if result.returncode != 0:
            errors.append(f"wheel install failed: {result.stderr}")
            print(result.stdout)
            print(result.stderr)
        else:
            print("Install OK")

        # 3. Smoke commands
        env = {
            **os.environ,
            "AGENTHEIM_CONFIG_DIR": str(Path(tmp) / "config"),
            "AGENTHEIM_DATA_DIR": str(Path(tmp) / "data"),
        }
        for cmd_name, args in (
            ("help", ["--help"]),
            ("status-json", ["status", "--json"]),
        ):
            print(f"==> Smoke: agentheim {' '.join(args)}")
            smoke_cmd = [str(agentheim), *args] if agentheim.exists() else [str(python), "-m", "interfaces.cli.cli", *args]
            result = subprocess.run(smoke_cmd, cwd=tmp, check=False, capture_output=True, text=True, env=env)
            if result.returncode != 0:
                errors.append(f"smoke {cmd_name} failed: {result.stderr}")
                print(result.stdout)
                print(result.stderr)
            else:
                print(f"Smoke {cmd_name} OK")

    if errors:
        print("\nFAILURES:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nAll packaging smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
