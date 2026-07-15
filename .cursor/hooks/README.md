# SelfwellAgent — Cursor Hooks 工程化约束

> 本目录（`.cursor/hooks/`）用 Cursor Hooks 把 `.cursor/rules/file-operation-stability.mdc`
> 从「模型自觉遵守」升级为「钩子硬阻塞」。违背规则的 shell 命令会被 exit 2 直接拦截，
> 不需要依赖 agent 自觉 — 工程约束级别的"无法绕过"。

---

## 一、为什么需要 Hook

旧问题：2026-07-15 用户反馈"cursor 跑 shell 时没看 rules"。调查发现：
- 规则文件 `alwaysApply: true` 已正确加载（Cursors 每次都注入到 system prompt）
- 真正问题是 **agent 在快速出结果的诱惑下，跳级用 shell 跑 cat/cmd/dir 等违规命令**

解决方案：Cursor Hooks 提供的 `beforeShellExecution` 事件可以拦截 shell 调用，
直接在执行前 deny，比"靠 agent 自觉"可靠得多。

---

## 二、文件结构

```
.cursor/
├── hooks.json                                # 钩子清单（Cursor 读取此文件）
├── rules/
│   └── file-operation-stability.mdc          # 规则源文件 (alwaysApply=true)
├── hooks/                                    # 本目录
│   ├── guard-shell.ps1                       # ⭐ 硬阻塞违规 shell (exit 2)
│   ├── session-inject.ps1                    # 软提醒: sessionStart 注入规则摘要
│   ├── subagent-rules-inject.ps1             # 强制: subagentStart 注入规则指针
│   ├── audit-violations.ps1                  # 审计: stop 阶段追加日志
│   └── README.md                             # 本文件
└── logs/
    └── audit.log                             # 审计日志 (gitignored)
```

---

## 三、配置的事件 / Hook 矩阵

| 事件 | 脚本 | 阻塞策略 | 作用 |
|------|------|----------|------|
| `sessionStart` | `session-inject.ps1` | failClosed=false | 会话开始时向 agent context 注入 5 条铁则的浓缩摘要，作为软提醒 |
| `subagentStart` | `subagent-rules-inject.ps1` | failClosed=true | **Task 出去的子 agent 必须 Read 两份 rules 才允许启动** |
| `beforeShellExecution` | `guard-shell.ps1` | failClosed=true | **核心**：违规 shell 直接 exit 2 拒绝执行 |
| `stop` | `audit-violations.ps1` | failClosed=false | 兜底: 每轮结束追加一条审计日志 |

---

## 四、违规模式清单 (`guard-shell.ps1`)

被拦截的命令模式（与 rules 红线一一对应）：

| 模式 | 原因 | 用什么工具替代 |
|------|------|---------------|
| `cat file.{md,txt,py,...}` | shell 读文件 | **Read** |
| `head ...` / `tail ...` / `more ...` / `less ...` | shell 读文件 | **Read** |
| `sed -i ...` / `sed ...` | shell 修改文件 | **StrReplace / Write** |
| `awk ...` | shell 处理文件 | **StrReplace / Write** |
| `perl -pi ...` | shell 修改文件 | **StrReplace / Write** |
| `echo ... > file` / `printf ... > file` | shell 写文件 | **Write** |
| `cat ... > file` / `tee ...` | shell 写文件 | **Write** |
| `rm -rf /` | 高危 | 需用户书面授权 |
| `cmd /c "dir ..."` | 跨盘列目录 | **Glob** |
| `powershell -Command ...[IO.File]...` | 用 PS 读字节 | **Read** |

---

## 五、安装与验证

### 5.1 安装（一次性）

文件已随仓库提交，无需额外安装。但首次 clone 后建议：

```powershell
# 1. 确认 .cursor/hooks 完整
Get-ChildItem -Path '.cursor\hooks' -Recurse

# 2. 确认 PowerShell 执行策略允许 .ps1
# Cursor 在 Windows 默认使用 powershell.exe。如果策略限制，
# 需在 User 范围允许:
# Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# 3. 重启 Cursor，让 hooks.json 重新加载
```

### 5.2 验证 Hook 生效

按以下顺序各触发一次:

| 测试 | 操作 | 期望结果 |
|------|------|----------|
| **违规应被阻塞** | 在 Cursor 里让 agent 跑 `cat .cursorrules` | tool 返回 permission=deny，shell 不执行 |
| **正常放行** | 在 Cursor 里让 agent 跑 `git status` | tool 返回 permission=allow，正常执行 |
| **sessionStart 注入** | 全新开一个 chat | agent 第一条消息引用 5 条铁则摘要 |
| **subagentStart 注入** | 让主 agent 用 Task 派出 explore subagent | 子 agent 第一条消息引用 rules 指针 |

### 5.3 调试入口

- Cursor IDE → **Settings** → **Hooks** 查看加载状态
- Cursor IDE → **Output** → 选 "Hooks" channel 看每次触发日志
- 仓库内日志：`.cursor/logs/audit.log`

---

## 六、白名单 / 例外场景

如果某个**必须**的 shell 命令命中拦截模式，可以:

1. **优先用 Cursor 工具替代**（首选）: 比如用 `Read` 而不是 cat
2. **如果非 shell 不可**，临时绕过:
   ```powershell
   # 用 # cursor-hook-bypass 注释前缀（待 v2 支持）
   # cursor-hook-bypass: cat .cursorrules
   cat .cursorrules
   ```
   v1 默认无 bypass，每条违规都必须改用工具。

---

## 七、参考

- 主规则文件: `.cursor/rules/file-operation-stability.mdc`
- Cursor Hooks 文档: <https://cursor.com/docs/hooks>
- 本次故障复盘: <待补 — docs/cursor_experience/file-operation-stability-hooks-fix.md>
