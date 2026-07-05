# SelfwellAgent Commit 规范 + Git Hooks 配置指南

> **V1.3（2026-07-05）** · 统一 commit message 格式 + 自动化质量门禁

---

## 📋 Commit Message 规范（Conventional Commits）

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型（11 种，必须小写）

| Type | 说明 | 触发 semver |
|---|---|---|
| `feat` | 新功能 | MINOR bump |
| `fix` | 修复 bug | PATCH bump |
| `docs` | 文档变更 | — |
| `style` | 代码格式（不影响功能） | — |
| `refactor` | 重构 | — |
| `perf` | 性能优化 | PATCH bump |
| `test` | 测试 | — |
| `build` | 构建系统 / 依赖 | — |
| `ci` | CI 配置 | — |
| `chore` | 杂项 | — |
| `revert` | 回滚 | PATCH bump |

**破坏性变更**：在 type 后加 `!`，或在 footer 写 `BREAKING CHANGE:`

### Scope 范围（可选但推荐）

`backend` / `client` / `ci` / `deps` / `docs` / `config` / `schema` / `eval` / `golden`
`m1`-`m11`（业务模块 M1-M11）

### Subject 标题

- 4-72 字符
- 不以 `.` 结尾
- 中文 / 英文均可（推荐英文 + 中文补充）

### 完整示例

```bash
# ✅ 正确
git commit -m "feat(backend): 添加用户登录接口

- 实现 JWT token 签发
- 密码 bcrypt 加盐
- 登录失败限流（5 次/分钟）

Closes #42"

# ✅ 带破坏性变更
git commit -m "feat(api)!: 重构 /v1/user 返回结构

BREAKING CHANGE: 返回字段从 user_id 改为 id，所有调用方需同步更新"

# ❌ 错误（无 type）
git commit -m "添加了用户登录"

# ❌ 错误（type 不在白名单）
git commit -m "feature(backend): 添加接口"

# ❌ 错误（subject 太短）
git commit -m "feat(backend): ok"
```

---

## 🔧 Git Hooks 自动校验

### 工具链

| Hook | 工具 | 触发 | 失败处理 |
|---|---|---|---|
| **commit-msg** | commitlint | `git commit` | ❌ **阻止 commit** |
| **pre-commit** | ruff + 标准检查 | `git commit` | ❌ **阻止 commit**（除非 `--no-verify`） |
| **pre-push** | mypy + pytest | `git push` | ⚠️ **警告式，不阻止 push**（CI 兜底） |

---

## 🚀 一键安装（首次 clone 后）

### 1. 安装 Python 依赖（含 commitlint / pre-commit / commitizen）

```bash
uv sync --all-extras
```

### 2. 安装 git hooks（pre-commit 框架）

```bash
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

**装完后验证**：

```bash
ls .git/hooks/
# 应看到：commit-msg / pre-commit / pre-push（指向 pre-commit 框架）
```

### 3. 配置 git hooksPath（可选，用于覆盖）

如果想让 .githooks/pre-push.py 生效：

```bash
git config core.hooksPath .githooks
```

---

## 💻 日常使用

### 普通提交（推荐方式：交互式）

```bash
uv run cz commit
# 进入交互式 TUI 引导，逐步填写 type/scope/subject/body/breaking/footer
```

### 普通提交（命令行）

```bash
git commit -m "feat(backend): 添加用户登录接口"
```

### 紧急跳过 hooks（不推荐）

```bash
git commit --no-verify -m "fix: 紧急修复"
git push --no-verify
```

### 手动跑全部 hooks

```bash
uv run pre-commit run --all-files
```

### 自动 bump 版本 + 生成 CHANGELOG

```bash
uv run cz bump
# 自动：
# 1. 读所有 commit，按 type 分组生成 CHANGELOG.md
# 2. bump pyproject.toml:project.version
# 3. git commit -m "chore(release): 0.2.0"
# 4. git tag v0.2.0
```

---

## 🔍 CI 集成（GitHub Actions）

`.github/workflows/backend-ci.yml` 已包含 L0-L4 质量门禁。

**额外建议**：在 CI 中加 commitlint 校验所有历史 commit：

```yaml
- name: Validate all commits (Conventional Commits)
  run: |
    npx -y commitlint --from=HEAD~10 --to=HEAD --verbose
  # 或 Python 版：uv run cz check --rev-range HEAD~10..HEAD
```

---

## 📚 参考

- [Conventional Commits 1.0.0 规范](https://www.conventionalcommits.org/zh-hans/v1.0.0/)
- [commitlint 文档](https://commitlint.js.org/)
- [pre-commit 框架](https://pre-commit.com/)
- [Commitizen 交互式工具](https://commitizen-tools.github.io/commitizen/)
- [standard-version / cz bump](https://commitizen-tools.github.io/commitizen/)

---

## ⚠️ 故障排查

| 问题 | 排查 |
|---|---|
| `git commit` 报错 "commitlint not found" | 跑 `uv run pre-commit install --hook-type commit-msg` |
| `uv run cz commit` 命令不存在 | 跑 `uv sync --all-extras` 重新装 dev 依赖 |
| hooks 不生效 | 检查 `ls .git/hooks/`，确认有 `commit-msg` / `pre-commit` 软链 |
| Windows 下 `pre-push.py` 中文乱码 | 用 PowerShell 7+ 或改 hooks 为 .sh（git bash） |