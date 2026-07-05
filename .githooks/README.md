#!/usr/bin/env bash
# =============================================================================
# SelfwellAgent core.hooksPath 配置（V1.3）
#
# 把 git hooks 指向 .githooks/ 目录（入仓，可分享）
# 这样团队成员 clone 后只需跑一次：git config core.hooksPath .githooks
#
# 注：pre-commit 框架（.pre-commit-config.yaml）会通过 uv run pre-commit install 自动安装
# 本文件仅用于非 pre-commit 框架覆盖的钩子（如 pre-push）
# =============================================================================

# 使用方式：
#   cd selfwell-agent
#   git config core.hooksPath .githooks
#   git config --local core.hooksPath .githooks   # 仅当前仓库
#
# 验证：
#   git config core.hooksPath
#   # 应输出：.githooks

# =============================================================================
# 可选：手写 git hooks（如不用 pre-commit 框架）
# =============================================================================
# 以下是手写版本示例，正常情况下由 .pre-commit-config.yaml + pre-commit install 自动生成
# 仅作为参考，**不要**直接复制到 .githooks/（会与 pre-commit 框架冲突）

# ─────────────────────────────────────────────────────────────────────────────
# commit-msg（手写版本 - 参考）
# ─────────────────────────────────────────────────────────────────────────────
# #!/usr/bin/env bash
# commit_msg_file=$1
# commit_msg=$(cat "$commit_msg_file")
# if ! echo "$commit_msg" | grep -qE "^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?: .{4,72}$"; then
#     echo "❌ Commit message 不符合 Conventional Commits 规范"
#     echo ""
#     echo "格式：<type>(<scope>): <subject>"
#     echo "示例：feat(backend): 添加用户登录接口"
#     echo ""
#     echo "可选 type: feat/fix/docs/style/refactor/perf/test/build/ci/chore/revert"
#     exit 1
# fi

# ─────────────────────────────────────────────────────────────────────────────
# pre-commit（手写版本 - 参考）
# ─────────────────────────────────────────────────────────────────────────────
# #!/usr/bin/env bash
# # 仅对 staged Python 文件跑 ruff
# staged_py_files=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')
# if [ -n "$staged_py_files" ]; then
#     uv run ruff check --fix $staged_py_files
#     uv run ruff format $staged_py_files
# fi

# ─────────────────────────────────────────────────────────────────────────────
# pre-push（手写版本 - 参考，本项目使用 .githooks/pre-push.py）
# ─────────────────────────────────────────────────────────────────────────────
# #!/usr/bin/env bash
# python .githooks/pre-push.py