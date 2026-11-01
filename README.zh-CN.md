# Index Guard

[![CI](https://github.com/erburenwang/index-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/erburenwang/index-guard/actions/workflows/ci.yml)

检查已经进入 Git 索引、但仍匹配当前忽略规则的路径。它能发现 `.gitignore` 后来新增了规则、文件却依然被跟踪的情况。Index Guard 让 Git 自己判断忽略规则，并且不会打开文件内容。

## 安装

需要 Python 3.11+ 和 Git。

```console
python -m pip install git+https://github.com/erburenwang/index-guard.git
```

## 使用

```console
# 提交前检查暂存的新文件和改动
index-guard audit

# 检查 Git 索引中的全部路径（适合放进 CI）
index-guard audit --scope tracked

# 查看某个路径实际命中的规则，即使它已经被跟踪
index-guard explain .env.local

# 输出 JSON，方便脚本处理
index-guard audit --scope tracked --format json
```

`audit` 默认检查暂存范围：新增、复制、修改、重命名和类型变化；暂存删除不会报告。`--scope tracked` 检查索引中的所有路径。两种模式都会让 Git 按当前有效规则判断，包括嵌套 `.gitignore`、`.git/info/exclude` 和配置的全局忽略文件。

示例：

```text
Index Guard: Checked 4 staged path(s); 1 ignored path(s).
- ".env.local"
  rule: .gitignore:1: .env*
```

文本输出会转义特殊路径字符。JSON 使用 `schema_version: 1`；必要时会转义非 ASCII 字符，标准 JSON 解析器可还原原始路径。

## 退出码

| 命令 | 代码 | 含义 |
|---|---:|---|
| `audit` | `0` | 被检查的路径均未匹配忽略规则 |
| `audit` | `1` | 至少一个被检查路径仍匹配忽略规则 |
| 任一命令 | `2` | 参数错误、当前目录不属于 Git 仓库，或 Git 命令失败 |
| `explain` | `0` | 已生成解释；路径是否被忽略不影响退出码 |

## CI 和 pre-commit

可以在 CI 中检查索引里那些在规则更新后仍被跟踪的文件：

```yaml
- name: Check tracked paths against ignore rules
  run: index-guard audit --scope tracked
```

本地 pre-commit 例子（先在运行 `pre-commit` 的环境里安装 Index Guard）：

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

## 隐私与边界

- 只读取 Git 索引中的路径名和忽略规则元数据，不打开索引文件、不读取文件值，也不输出仓库绝对路径。
- 不联网、不修改索引、不删除文件，也不改写 `.gitignore`。
- 命中忽略规则表示需要检查的策略信号，并不证明文件内容是秘密。有些团队会有意强制添加被忽略的文件，请结合路径和规则判断。
- 它不是内容型密钥扫描器，也不会列出未跟踪且被忽略的文件。需要检查这类路径时，可直接运行 `git check-ignore -v PATH`。

Git 的 `--no-index` 和 NUL 分隔 `-z` 行为见 [git-check-ignore 手册](https://git-scm.com/docs/git-check-ignore)。
