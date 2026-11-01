from __future__ import annotations

import os
import subprocess
from pathlib import Path, PureWindowsPath
from typing import Iterable, Literal

from .models import AuditReport, AuditScope, IgnoreDecision


class GitError(RuntimeError):
    """A fixed, path-free Git operation error."""


def _run_git(
    root: Path | None,
    args: tuple[str, ...],
    *,
    input_bytes: bytes | None = None,
    accepted_codes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    command = ["git"]
    if root is not None:
        command.extend(("-C", str(root)))
    command.extend(args)
    try:
        result = subprocess.run(
            command,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise GitError("Git could not be started") from exc
    if result.returncode not in accepted_codes:
        raise GitError("Git command failed")
    return result


def _without_line_ending(value: bytes) -> bytes:
    if value.endswith(b"\n"):
        value = value[:-1]
    if value.endswith(b"\r"):
        value = value[:-1]
    return value


def find_repo_root(start: Path | None = None) -> Path:
    candidate = start if start is not None else Path.cwd()
    result = _run_git(candidate, ("rev-parse", "--show-toplevel"), accepted_codes=(0, 1, 128))
    if result.returncode != 0:
        raise GitError("not inside a Git repository")
    root_bytes = _without_line_ending(result.stdout)
    if not root_bytes:
        raise GitError("Git did not return a repository root")
    root = Path(os.fsdecode(root_bytes))
    if not root.is_absolute():
        root = (candidate / root).absolute()
    return root


def _path_from_git(raw: bytes) -> str:
    value = os.fsdecode(raw)
    if os.name == "nt":
        value = value.replace("\\", "/")
    return value


def _source_from_git(raw: bytes, root: Path) -> str | None:
    if not raw:
        return None
    value = os.fsdecode(raw)
    source = Path(value)
    if source.is_absolute():
        try:
            relative = source.relative_to(root)
        except ValueError:
            return "global excludes"
        value = relative.as_posix()
    elif os.name == "nt":
        value = value.replace("\\", "/")
    return value


def _parse_ignore_output(data: bytes, root: Path) -> list[IgnoreDecision]:
    fields = data.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    if len(fields) % 4:
        raise GitError("Git returned unexpected ignore output")

    decisions: list[IgnoreDecision] = []
    for offset in range(0, len(fields), 4):
        source_bytes, line_bytes, pattern_bytes, path_bytes = fields[offset : offset + 4]
        path = _path_from_git(path_bytes)
        pattern = os.fsdecode(pattern_bytes) if pattern_bytes else None
        try:
            line = int(line_bytes) if line_bytes else None
        except ValueError as exc:
            raise GitError("Git returned unexpected ignore output") from exc
        decisions.append(
            IgnoreDecision(
                path=path,
                ignored=bool(pattern) and not pattern.startswith("!"),
                source=_source_from_git(source_bytes, root),
                line=line,
                pattern=pattern,
            )
        )
    return decisions


def _check_paths(root: Path, paths: Iterable[bytes]) -> list[IgnoreDecision]:
    ordered_paths = sorted(set(path for path in paths if path))
    if not ordered_paths:
        return []
    input_bytes = b"\0".join(ordered_paths) + b"\0"
    result = _run_git(
        root,
        (
            "check-ignore",
            "--no-index",
            "--verbose",
            "--non-matching",
            "-z",
            "--stdin",
        ),
        input_bytes=input_bytes,
        accepted_codes=(0, 1),
    )
    decisions = _parse_ignore_output(result.stdout, root)
    if len(decisions) != len(ordered_paths):
        raise GitError("Git returned unexpected ignore output")
    return decisions


def audit_repository(start: Path | None = None, scope: AuditScope = "staged") -> AuditReport:
    root = find_repo_root(start)
    if scope == "staged":
        result = _run_git(
            root,
            ("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMRT"),
            accepted_codes=(0,),
        )
    elif scope == "tracked":
        result = _run_git(root, ("ls-files", "--cached", "--full-name", "-z"))
    else:
        raise ValueError("scope must be 'staged' or 'tracked'")

    decisions = _check_paths(root, result.stdout.split(b"\0"))
    findings = tuple(sorted((item for item in decisions if item.ignored), key=lambda item: item.path))
    return AuditReport(scope=scope, checked_paths=len(decisions), findings=findings)


def normalize_requested_path(value: str) -> str:
    if not value or "\0" in value:
        raise ValueError("path must be a non-empty repository-relative path")
    candidate = value.replace("\\", "/") if os.name == "nt" else value
    if candidate.startswith("/") or PureWindowsPath(value).is_absolute() or PureWindowsPath(value).drive:
        raise ValueError("path must be repository-relative")
    parts = [part for part in candidate.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        raise ValueError("path must not escape the repository")
    return "/".join(parts)


def explain_path(start: Path | None, value: str) -> IgnoreDecision:
    root = find_repo_root(start)
    path = normalize_requested_path(value)
    result = _run_git(
        root,
        (
            "check-ignore",
            "--no-index",
            "--verbose",
            "--non-matching",
            "-z",
            "--stdin",
        ),
        input_bytes=os.fsencode(path) + b"\0",
        accepted_codes=(0, 1),
    )
    decisions = _parse_ignore_output(result.stdout, root)
    if len(decisions) != 1:
        raise GitError("Git returned unexpected ignore output")
    return decisions[0]
