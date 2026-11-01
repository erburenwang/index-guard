from __future__ import annotations

import json
import unittest

from index_guard.models import AuditReport, IgnoreDecision
from index_guard.report import audit_payload, render_audit_text, render_json


class ReportTests(unittest.TestCase):
    def test_json_is_versioned_deterministic_and_round_trips_unicode_paths(self) -> None:
        report = AuditReport(
            scope="tracked",
            checked_paths=2,
            findings=(
                IgnoreDecision(
                    path="résumé with space.tmp",
                    ignored=True,
                    source="nested/.gitignore",
                    line=3,
                    pattern="*.tmp",
                ),
            ),
        )

        first = render_json(audit_payload(report))
        second = render_json(audit_payload(report))

        self.assertEqual(first, second)
        self.assertEqual(json.loads(first)["schema_version"], 1)
        self.assertEqual(json.loads(first)["findings"][0]["path"], "résumé with space.tmp")

    def test_text_quotes_paths_and_never_adds_an_absolute_root(self) -> None:
        report = AuditReport(
            scope="staged",
            checked_paths=1,
            findings=(
                IgnoreDecision(
                    path="line one\nline two.tmp",
                    ignored=True,
                    source=".gitignore",
                    line=1,
                    pattern="*.tmp",
                ),
            ),
        )

        output = render_audit_text(report)

        self.assertIn('"line one\\nline two.tmp"', output)
        self.assertIn(".gitignore:1: *.tmp", output)
        self.assertNotIn("C:\\", output)


if __name__ == "__main__":
    unittest.main()
