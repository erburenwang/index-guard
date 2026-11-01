from __future__ import annotations

import json

from .models import AuditReport, IgnoreDecision


def _decision_payload(item: IgnoreDecision) -> dict[str, object]:
    return {
        "ignored": item.ignored,
        "line": item.line,
        "path": item.path,
        "pattern": item.pattern,
        "source": item.source,
    }


def audit_payload(report: AuditReport) -> dict[str, object]:
    return {
        "checked_paths": report.checked_paths,
        "command": "audit",
        "findings": [_decision_payload(item) for item in report.findings],
        "schema_version": 1,
        "scope": report.scope,
    }


def explain_payload(item: IgnoreDecision) -> dict[str, object]:
    return {"command": "explain", "schema_version": 1, **_decision_payload(item)}


def render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def render_audit_text(report: AuditReport) -> str:
    summary = (
        f"Checked {report.checked_paths} {report.scope} path(s); "
        f"{len(report.findings)} ignored path(s)."
    )
    lines = [f"Index Guard: {summary}"]
    if not report.findings:
        lines.append("No paths match Git ignore rules.")
    for item in report.findings:
        lines.append(f"- {_quote(item.path)}")
        if item.source is not None and item.line is not None and item.pattern is not None:
            lines.append(f"  rule: {item.source}:{item.line}: {item.pattern}")
    return "\n".join(lines) + "\n"


def render_explain_text(item: IgnoreDecision) -> str:
    status = "is ignored" if item.ignored else "is not ignored"
    lines = [f"{_quote(item.path)} {status}."]
    if item.source is not None and item.line is not None and item.pattern is not None:
        lines.append(f"Last matching rule: {item.source}:{item.line}: {item.pattern}")
    else:
        lines.append("No ignore rule matched.")
    return "\n".join(lines) + "\n"
