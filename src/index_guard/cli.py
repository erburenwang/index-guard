from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .git_ops import GitError, audit_repository, explain_path
from .report import (
    audit_payload,
    explain_payload,
    render_audit_text,
    render_explain_text,
    render_json,
)


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository path (default: current directory)")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="output format")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="index-guard",
        description="Find Git index paths that match the effective ignore rules without reading file contents.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    audit = commands.add_parser("audit", help="audit staged or tracked index paths")
    audit.add_argument("--scope", choices=("staged", "tracked"), default="staged")
    _add_common_options(audit)

    explain = commands.add_parser("explain", help="show the effective ignore rule for one path")
    explain.add_argument("path", help="repository-relative path")
    _add_common_options(explain)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "audit":
            report = audit_repository(args.root, args.scope)
            output = (
                render_json(audit_payload(report))
                if args.format == "json"
                else render_audit_text(report)
            )
            sys.stdout.write(output)
            return 1 if report.findings else 0

        decision = explain_path(args.root, args.path)
        output = (
            render_json(explain_payload(decision))
            if args.format == "json"
            else render_explain_text(decision)
        )
        sys.stdout.write(output)
        return 0
    except GitError as exc:
        sys.stderr.write(f"index-guard: {exc}\n")
        return 2
    except ValueError as exc:
        sys.stderr.write(f"index-guard: {exc}\n")
        return 2
