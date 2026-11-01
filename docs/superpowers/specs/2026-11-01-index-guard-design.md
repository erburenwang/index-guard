# Index Guard Design

## Intent

Index Guard is a small local CLI for finding Git index entries that still match the repository's effective ignore rules. This catches the surprising case where a file remains tracked after a later `.gitignore` change. It also explains the exact rule Git matched for a path.

## Goals

- Audit staged paths before a commit or all paths in the Git index in CI.
- Report only paths that Git says are ignored, with the rule source, line, and pattern.
- Explain a single repository-relative path, including when a negated rule means it is not ignored.
- Offer stable text and versioned JSON output with relative paths only.
- Use no runtime dependencies, network, file-content reads, or index/worktree writes.

## Non-goals

- Scanning file contents for credentials or secret values.
- Adding, removing, or untracking files automatically.
- Reimplementing `.gitignore` pattern matching.
- Reporting every untracked ignored file; this tool focuses on paths in the index and explicit `explain` requests.

## Interface

- `index-guard audit [--scope staged|tracked] [--root PATH] [--format text|json]`
  - `staged` is the default and considers staged additions, copies, modifications, renames, and type changes; staged deletions are excluded.
  - `tracked` checks all cached index paths.
- `index-guard explain PATH [--root PATH] [--format text|json]` shows whether one repository-relative path is ignored and the decisive rule when available.
- Exit `0` when an audit finds no ignored paths, `1` when it finds one or more, and `2` for invalid input or Git errors.

## Approach

Python 3.11+ and the standard library provide the CLI, JSON, and subprocess handling. Git remains the authority for path inventory and ignore semantics: use NUL-delimited `git diff --cached` or `git ls-files`, then `git check-ignore --no-index --verbose --non-matching -z --stdin`. Parse its NUL-separated source, line, pattern, and path fields; a decisive `!` pattern means the path is not ignored.

The program passes argument arrays to subprocesses, never invokes a shell, and never prints raw Git stderr. Paths are normalized to repository-relative POSIX form. External/global exclude-file locations are labeled without exposing absolute paths. Git errors become fixed, value-free diagnostics.

## Acceptance

- Correctly handles nested ignore files, `.git/info/exclude`, negations, spaces, Unicode, tabs, and newline-containing paths.
- Ignores staged deletions and returns deterministic sorted results.
- Integration tests use temporary Git repositories and never modify the user's index.
- CI covers Windows, macOS, and Ubuntu with Python 3.11 and 3.13; package install and CLI JSON smoke checks pass.
- English and Simplified Chinese READMEs explain scope, privacy, exit codes, and CI/pre-commit use.

## References

- Git documents `--no-index` as the way to test tracked paths against ignore rules and `-z` as the machine-readable, NUL-delimited mode: https://git-scm.com/docs/git-check-ignore
- Git documents `git ls-files -z` for verbatim NUL-delimited index paths: https://git-scm.com/docs/git-ls-files
