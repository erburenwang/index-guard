from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from helpers import GitProject, run_cli


class IndexGuardCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = GitProject()

    def tearDown(self) -> None:
        self.project.close()

    def test_audit_staged_reports_ignored_paths_and_rule_without_reading_values(self) -> None:
        (self.project.root / ".gitignore").write_text(
            ".env*\n!.env.example\n", encoding="utf-8"
        )
        (self.project.root / ".env.local").write_text(
            "SHOULD_NEVER_BE_READ=private-value\n", encoding="utf-8"
        )
        (self.project.root / ".env.example").write_text("SAFE=example\n", encoding="utf-8")
        self.project.add(".gitignore", ".env.local", ".env.example")

        result = run_cli(self.project.root, "audit", "--format", "json")

        self.assertIn(".env.local", result.stdout)
        self.assertNotIn("private-value", result.stdout + result.stderr)
        self.assertNotIn(str(self.project.root), result.stdout + result.stderr)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["scope"], "staged")
        self.assertEqual([item["path"] for item in payload["findings"]], [".env.local"])
        self.assertEqual(
            (payload["findings"][0]["source"], payload["findings"][0]["line"], payload["findings"][0]["pattern"]),
            (".gitignore", 1, ".env*"),
        )

    def test_audit_tracked_finds_paths_ignored_after_they_were_added(self) -> None:
        (self.project.root / "cache.pyc").write_text("cached bytecode\n", encoding="utf-8")
        self.project.add("cache.pyc")
        (self.project.root / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
        self.project.add(".gitignore")

        result = run_cli(self.project.root, "audit", "--scope", "tracked", "--format", "json")

        self.assertIn("cache.pyc", result.stdout)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["scope"], "tracked")
        self.assertEqual([item["path"] for item in payload["findings"]], ["cache.pyc"])

    def test_audit_reports_nested_ignore_source_relative_to_repository(self) -> None:
        nested = self.project.root / "services" / "api"
        nested.mkdir(parents=True)
        (nested / ".gitignore").write_text("*.cache\n", encoding="utf-8")
        (nested / "response.cache").write_text("payload\n", encoding="utf-8")
        self.project.add("services/api/.gitignore", "services/api/response.cache")

        result = run_cli(self.project.root, "audit", "--format", "json")

        self.assertIn("services/api/response.cache", result.stdout)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        finding = payload["findings"][0]
        self.assertEqual(finding["source"], "services/api/.gitignore")
        self.assertEqual(finding["line"], 1)
        self.assertEqual(finding["pattern"], "*.cache")

    def test_audit_does_not_report_staged_deletions(self) -> None:
        (self.project.root / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
        (self.project.root / "cache.tmp").write_text("stale\n", encoding="utf-8")
        self.project.add(".gitignore", "cache.tmp")
        self.project.run_git("rm", "--cached", "--", "cache.tmp")

        result = run_cli(self.project.root, "audit", "--format", "json")

        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["findings"], [])

    def test_global_exclude_source_does_not_leak_its_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as global_dir:
            global_file = Path(global_dir) / "global-ignore"
            global_file.write_text("*.local-cache\n", encoding="utf-8")
            self.project.run_git("config", "core.excludesFile", str(global_file))
            (self.project.root / "build.local-cache").write_text("private-value\n", encoding="utf-8")
            self.project.add("build.local-cache")

            result = run_cli(self.project.root, "audit", "--format", "json")

        self.assertEqual(result.returncode, 1)
        self.assertNotIn(str(global_file), result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["findings"][0]["source"], "global excludes")

    def test_explain_rejects_paths_that_escape_the_repository(self) -> None:
        result = run_cli(self.project.root, "explain", "../outside.txt")

        self.assertEqual(result.returncode, 2)
        self.assertIn("repository", result.stderr)
        self.assertNotIn(str(self.project.root), result.stdout + result.stderr)

    def test_explain_reports_the_effective_ignored_rule(self) -> None:
        (self.project.root / ".gitignore").write_text("*.secret\n!safe.secret\n", encoding="utf-8")

        ignored = run_cli(self.project.root, "explain", "private.secret", "--format", "json")
        allowed = run_cli(self.project.root, "explain", "safe.secret", "--format", "json")

        self.assertEqual(ignored.returncode, 0)
        self.assertEqual(allowed.returncode, 0)
        ignored_payload = json.loads(ignored.stdout)
        allowed_payload = json.loads(allowed.stdout)
        self.assertTrue(ignored_payload["ignored"])
        self.assertEqual(ignored_payload["pattern"], "*.secret")
        self.assertFalse(allowed_payload["ignored"])
        self.assertTrue(allowed_payload["pattern"].startswith("!"))

    def test_audit_preserves_spaces_and_unicode(self) -> None:
        (self.project.root / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
        unusual = "r\u00e9sum\u00e9 with space.tmp"
        (self.project.root / unusual).write_text("private-value\n", encoding="utf-8")
        self.project.add(".gitignore", unusual)

        result = run_cli(self.project.root, "audit", "--format", "json")

        self.assertNotIn("private-value", result.stdout)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual([item["path"] for item in payload["findings"]], [unusual])

    @unittest.skipIf(os.name == "nt", "Windows filenames cannot contain control characters")
    def test_audit_preserves_embedded_newlines(self) -> None:
        (self.project.root / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
        unusual = "line one\nline two.tmp"
        (self.project.root / unusual).write_text("private-value\n", encoding="utf-8")
        self.project.add(".gitignore", unusual)

        result = run_cli(self.project.root, "audit", "--format", "json")

        self.assertIn("line one\\nline two.tmp", result.stdout)
        self.assertNotIn("private-value", result.stdout)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual([item["path"] for item in payload["findings"]], [unusual])

    @unittest.skipIf(os.name == "nt", "Windows filenames cannot contain control characters")
    def test_audit_preserves_tabs(self) -> None:
        (self.project.root / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
        unusual = "tab\tname.tmp"
        (self.project.root / unusual).write_text("private-value\n", encoding="utf-8")
        self.project.add(".gitignore", unusual)

        result = run_cli(self.project.root, "audit", "--format", "json")

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual([item["path"] for item in payload["findings"]], [unusual])

    def test_clean_staged_scope_returns_zero_and_empty_findings(self) -> None:
        before = self.project.run_git("status", "--porcelain", "-z").stdout
        result = run_cli(self.project.root, "audit", "--format", "json")
        after = self.project.run_git("status", "--porcelain", "-z").stdout

        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(after, before)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["findings"], [])
        self.assertEqual(payload["checked_paths"], 0)

    def test_explain_reports_a_non_ignored_path_without_absolute_root(self) -> None:
        (self.project.root / ".gitignore").write_text("*.tmp\n", encoding="utf-8")

        result = run_cli(self.project.root, "explain", "src/main.py", "--format", "json")

        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["path"], "src/main.py")
        self.assertFalse(payload["ignored"])
        self.assertNotIn(str(self.project.root), result.stdout)

    def test_not_a_repository_returns_two_without_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            result = run_cli(Path(outside), "audit")

        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(str(self.project.root), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
