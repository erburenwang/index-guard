from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class GitProject:
    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.run_git("init", "-q", "-b", "main")
        self.run_git("config", "user.name", "Index Guard Tests")
        self.run_git("config", "user.email", "index-guard-tests@example.invalid")

    def close(self) -> None:
        self._temporary.cleanup()

    def run_git(self, *args: str, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode not in (0, 1):
            raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
        return result

    def add(self, *paths: str) -> None:
        self.run_git("add", "-f", "--", *paths)


def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    package_path = str(PROJECT_ROOT / "src")
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = package_path if not current else package_path + os.pathsep + current
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "index_guard", *args, "--root", str(root)],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
