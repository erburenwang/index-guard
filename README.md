# Index Guard

[![CI](https://github.com/erburenwang/index-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/erburenwang/index-guard/actions/workflows/ci.yml)

Find paths that are already in Git's index but still match the effective ignore rules. This catches the common surprise where a file remains tracked after a later `.gitignore` change. Index Guard uses Git itself to evaluate ignore rules and never opens file contents.

## Install

Requires Python 3.11+ and Git.

```console
python -m pip install git+https://github.com/erburenwang/index-guard.git
```

## Use

```console
# Check staged additions and changes before committing
index-guard audit

# Check every path currently in the Git index (useful in CI)
index-guard audit --scope tracked

# See the effective rule for a path, even if it is already tracked
index-guard explain .env.local

# Get machine-readable output
index-guard audit --scope tracked --format json
```

`audit` defaults to the staged scope. It checks staged additions, copies, modifications, renames, and type changes; staged deletions are excluded. `--scope tracked` checks all cached index paths. Both modes ask Git to test those names against the current ignore rules, including nested `.gitignore` files, `.git/info/exclude`, and the configured global excludes file.

Example:

```text
Index Guard: Checked 4 staged path(s); 1 ignored path(s).
- ".env.local"
  rule: .gitignore:1: .env*
```

Text output quotes unusual path characters. JSON is versioned (`schema_version: 1`) and escapes non-ASCII characters when needed; normal JSON parsers recover the original path.

## Exit codes

| Command | Code | Meaning |
|---|---:|---|
| `audit` | `0` | No audited path matches an ignore rule |
| `audit` | `1` | One or more audited paths still match an ignore rule |
| Either | `2` | Invalid input, not a Git repository, or a Git command error |
| `explain` | `0` | Explanation produced, whether the path is ignored or not |

## CI and pre-commit

Run this in CI to catch tracked files that became ignored after they entered the index:

```yaml
- name: Check tracked paths against ignore rules
  run: index-guard audit --scope tracked
```

For a local pre-commit hook, install Index Guard in the environment that runs `pre-commit`, then add:

```yaml
repos:
  - repo: local
    hooks:
      - id: index-guard
        name: Check staged paths against ignore rules
        entry: index-guard audit
        language: system
        pass_filenames: false
```

## Privacy and limits

- Reads Git's index path list and ignore-rule metadata only. It does not open indexed files, inspect file values, or print absolute repository paths.
- Does not call the network, modify the index, delete files, or rewrite `.gitignore`.
- A matching ignore rule is a policy signal, not proof that file contents are secret. Some teams intentionally force-add ignored files; review the reported path and rule.
- It is not a content-based secret scanner and does not report untracked ignored files. Use `git check-ignore -v PATH` when you need to inspect an untracked path directly.

Git's `--no-index` and NUL-delimited `-z` behavior are documented in the [git-check-ignore manual](https://git-scm.com/docs/git-check-ignore).
