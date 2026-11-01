# Index Guard Implementation Plan

> **For agentic workers:** Implement inline in this session. Steps use checkbox syntax for tracking.

**Goal:** Ship a dependency-free CLI that audits staged or tracked paths against Git ignore rules without reading file contents or mutating the repository.

**Architecture:** `git_ops.py` calls Git with argument arrays and NUL-delimited I/O, returning typed findings. `cli.py` validates input and exit codes; `report.py` renders deterministic text or versioned JSON. Integration tests create isolated temporary Git repositories.

**Tech Stack:** Python 3.11+, standard library, `unittest`, Git CLI, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-01-index-guard-design.md`

## File Map

- `src/index_guard/models.py`: immutable finding/report records.
- `src/index_guard/git_ops.py`: repository detection, staged/tracked path enumeration, ignore-rule evaluation, and safe diagnostics.
- `src/index_guard/report.py`: text and JSON formatters.
- `src/index_guard/cli.py`, `__main__.py`: argparse interface and exit codes.
- `tests/helpers.py`: temporary Git repository fixture and byte-safe Git helper.
- `tests/test_cli.py`: CLI behavior and real Git integration coverage.
- `tests/test_report.py`: deterministic/versioned output checks.
- `pyproject.toml`, English/Chinese READMEs, `LICENSE`, `.gitignore`, `.github/workflows/ci.yml`: packaging, user documentation, license, safe excludes, and cross-platform CI.

## Tasks

### 1. Git-backed path audit

- [x] Write integration tests for staged vs tracked scope, ignored tracked files, ignored staged paths, no staged paths, NUL-safe odd filenames, nested `.gitignore`, negation, and source/line/pattern attribution.
- [x] Run `PYTHONPATH=src python -m unittest discover -s tests -p test_cli.py -v`; confirm the new tests fail because the CLI/Git adapter is absent.
- [x] Implement immutable models and `git_ops.py` with `git diff --cached`, `git ls-files -z`, and `git check-ignore --no-index --verbose --non-matching -z --stdin`.
- [x] Rerun the focused integration tests; confirm exact findings and that Git/index files remain unchanged.
- [x] Commit as `feat: audit git index against ignore rules` (`9feb7a7`).

### 2. CLI and reports

- [x] Add tests for `audit` defaulting to staged scope, tracked scope, `explain PATH`, text/JSON output, stable ordering, root discovery, bad arguments, and fixed path-free Git errors.
- [x] Run the new CLI tests and confirm expected failures before adding the CLI.
- [x] Implement `argparse` commands, JSON schema version 1, deterministic report rendering, and exit codes `0` clean / `1` ignored paths / `2` invocation or Git error.
- [x] Run the complete unit suite; verify outputs include no absolute paths or file contents.
- [x] Commit CLI, reports, Git integration, and tests together in `9feb7a7` so the runnable feature remains a single coherent change.

### 3. Package and release checks

- [x] Add Python 3.11+ packaging metadata, zero runtime dependencies, console entry point, MIT license, and `.gitignore` rules that keep local secrets and build artifacts out.
- [x] Write English and Simplified Chinese READMEs with install, commands, exact scope, privacy boundary, exit codes, CI, and pre-commit examples.
- [x] Add least-privilege GitHub Actions for Ubuntu, Windows, and macOS with Python 3.11 and 3.14; run compile, tests, isolated install, `--help`, and JSON smoke checks.
- [x] Run full tests, compileall, `git diff --check`, isolated package install, installed CLI help, and a JSON scan against a temporary test repository.
- [ ] Review staged files for secrets, generated files, and unexpected absolute paths; commit as `chore: package and document Index Guard`.

### 4. Public GitHub release

- [x] Create public repository `erburenwang/index-guard` with description `Audit staged and tracked Git paths against ignore rules without reading file contents.`
- [ ] Upload the committed source and documentation with the exact local tree, update `main` without forcing, and verify public visibility, commit/ref, and tree equality.
- [ ] Wait for the latest commit's six CI jobs; require all six to pass before marking release complete.

## Review Focus

- NUL-delimited paths must survive spaces, Unicode, tabs, and embedded newlines without shell parsing or line splitting.
- A final negation pattern (for example `!.env.example`) must be reported as not ignored, even if an earlier pattern matched.
- Global exclude sources must not leak absolute local paths.
- Staged deletions must not be reported as files being added to the commit.
- Git errors must not echo raw stderr or any file contents.

## Self-review

- Every acceptance item maps to Tasks 1–4; no file-content scan, auto-fix, or dependency is planned.
- Git supplies ignore semantics; `-z` is used on both input and output; results are sorted in application code.
- Tests use temporary repositories, including negative and unusual-path cases.
