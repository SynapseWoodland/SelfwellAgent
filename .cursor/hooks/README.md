# SelfwellAgent — Cursor Hooks 工程化约束

> 本目录（`.cursor/hooks/`）用 Cursor Hooks 把 `.cursor/rules/` 下 4 条 alwaysApply 规则中的
> **R-5 工具跳级**（对应 `file-operation-stability.mdc`）从「模型自觉遵守」升级为「钩子硬阻塞」。
> 违背规则的 shell 命令会被 exit 2 直接拦截，不需要依赖 agent 自觉 — 工程约束级别的"无法绕过"。
>
> ⚠️ `file-operation-stability.mdc` **不是**主规则文件——它是 4 条规则中**唯一被 hooks 工程化兜底**的那条。
> 其余 3 条规则（`project-meta` / `project-prohibitions` / `skills`）靠 CI / pre-commit / PR-Gate /
> Eval Runner 兜底，详见 `.cursor/rules/README.md`（待补）或各自文件内"谁兜底"一栏。

---

## 一、为什么需要 Hook

旧问题：2026-07-15 用户反馈"cursor 跑 shell 时没看 rules"。调查发现：
- 规则文件 `alwaysApply: true` 已正确加载（Cursor 每次都注入到 system prompt）
- 真正问题是 **agent 在快速出结果的诱惑下，跳级用 shell 跑 cat/cmd/dir 等违规命令**
- Prompt / 规则只能劝阻，硬阻塞只能靠 hook

解决方案：Cursor Hooks 提供的 `beforeShellExecution` 事件可以在 shell 执行前 deny，
比"靠 agent 自觉"可靠得多。

---

## 二、文件结构

```
.cursor/
├── hooks.json                                # 钩子清单（Cursor 读取此文件）
├── rules/
│   └── file-operation-stability.mdc          # 规则源文件（alwaysApply=true，agent 看的）
├── hooks/                                    # 本目录（hook 脚本实现）
│   ├── guard-shell.cmd                       # Windows 入口垫片：探测 Python 解释器
│   ├── guard-shell.py                        # v4 硬阻塞违规 shell（Python 主逻辑）
│   ├── guard-shell.ps1                       # v3 兜底（无 Python 时降级放行）
│   ├── session-inject.ps1                    # sessionStart：向 agent context 注入 5 条铁则摘要
│   ├── subagent-rules-inject.ps1             # subagentStart：派 Task 前强制 Read 两份 rules
│   ├── audit-violations.ps1                  # stop：每轮结束写一条审计到 .cursor/logs/audit.log
│   ├── tests/
│   │   └── test_guard_shell.py               # v4 单元测试（pytest / unittest）
│   └── README.md                             # 本文件
└── logs/
    └── audit.log                             # 审计日志（gitignored）
```

### 关系总览

`.cursor/rules/` 下有 4 条 alwaysApply=true 规则（**全部注入到 system prompt，agent 每条消息都看到**）：

| 规则文件 | 主题 | 谁兜底 |
|----------|------|--------|
| `project-meta.mdc` | **入口元信息**：V3 架构对齐（技术栈 / 目录 / 4 个核心事实） | 无（信息性，靠 agent 自调用） |
| `project-prohibitions.mdc` | **5 条工程红线**：R-1~R-5（依赖声明 / agents 禁区 / L0-L6 门禁 / Prompt 回归 / 工具跳级） | R-1~R-4 由 CI / pre-commit / PR-Gate / Eval Runner 兜底；**R-5 由本 hooks 兜底** |
| `file-operation-stability.mdc` | **工具铁则**：Read / StrReplace / Write / Glob 优先，shell 只许跑 ls/find/tree | **本 hooks (`guard-shell.py` v4.1)** exit 2 硬阻塞 |
| `skills.mdc` | **Skill 导航**：哪些场景读哪个 skill | 无（导航性，靠 agent 自调用） |

> ⚠️ **没有"主规则文件"**——4 条规则角色不同、互补。
> 4 条全部 alwaysApply=true，agent 每条消息都看到全部 4 条。
>
> **新增违规模式的同步规则**：本 hooks 只兜底 `file-operation-stability.mdc`，对应 R-5；
> R-1~R-4 由 CI / pre-commit / PR-Gate / Eval Runner 兜底——修改任一条规则时务必同步它指向的兜底实现。
> `project-meta.mdc` 第 5.2 / 5.3 节有"唯一真源"指向，**不要在 hook README 里复制真源内容**。

**职责边界**：
- `rules/` 给 agent 看（"为什么不能 cat"）
- `hooks/` 给 Cursor 看（"实际拦截"）
- 新增违规模式必须**两边同步更新**——hook 的违规检测表（"四、违规模式清单"）和 `file-operation-stability.mdc` 的"红线速查"必须保持一致

---

## 三、配置的事件 / Hook 矩阵

| 事件 | command | failClosed | matcher | 作用 |
|------|---------|------------|---------|------|
| `sessionStart` | `.cursor/hooks/session-inject.ps1` | false | — | 会话开始时向 agent context 注入 5 条铁则的浓缩摘要（软提醒） |
| `subagentStart` | `.cursor/hooks/subagent-rules-inject.ps1` | true | — | Task 出去的子 agent 必须先 Read 两份 rules 才允许启动 |
| `beforeShellExecution` | `.cursor/hooks/guard-shell.cmd` (→ guard-shell.py) | true | 违规子集 regex | 核心：违规 shell 直接 exit 2 拒绝执行 |
| `stop` | `.cursor/hooks/audit-violations.ps1` | false | — | 每轮结束追加一条审计日志 |

### `beforeShellExecution` matcher 设计（v4）

`hooks.json` 中：
```json
"matcher": "(?i)(cat\\s|head\\s|tail\\s|more\\s|less\\s|sed\\s|awk\\s|perl\\s|echo\\s[^|]*>|...more)"
```

**只匹配"违规触发子集"**（cat/head/sed/awk/echo>/tee/rm -rf/cmd/powershell 等），
**不**触发普通命令（git/ls/curl/python/npm 等）。

这个限制是**必要的**，否则会出现**hook 自递归死锁**：
- 当 agent 运行 `python -m pytest tests/...` 测试 hook 自身时，
- 测试 Python 进程会调用 shell（比如 `git status`），触发 hook
- hook 又在 shell 调用中，导致测 hook 永远测不完

**matcher 也限制 hook 的拦截视野**：违规命令以外的命令完全绕开 hook（性能 + 可预测性）。

---

## 四、违规模式清单（`guard-shell.py`）

下表是 v4 当前所有违规模式。命令匹配规则：
- **违规触发子集**：命中任一模式 → permission=deny + exit 2
- **白名单快速通道**：命令首 token 在白名单内 → 直接 permission=allow + exit 0
- **白名单内 + 违规模式命中**：仍走违规检查（如 `echo hello > out.txt` 拦截但 `echo hello` 放行）

| 类别 | 模式 | 拦截原因 | 用什么工具替代 |
|------|------|----------|---------------|
| **文件读取** | `cat <path>` / `Get-Content <path>` | shell 读文件 | **Read** |
| | `head <path>` / `tail <path>` / `more <path>` / `less <path>` | shell 读文件 | **Read** |
| | `type <path>` (cmd) | shell 读文件 | **Read** |
| **文件修改** | `sed -i ...` / `sed ...` | shell 修改文件 | **StrReplace / Write** |
| | `awk ...` | shell 处理文件 | **StrReplace / Write** |
| | `perl -pi ...` | shell 修改文件 | **StrReplace / Write** |
| **文件写入** | `echo ... > file` | shell 写文件 | **Write** |
| | `printf ... > file` | shell 写文件 | **Write** |
| | `cat ... > file` | shell 写文件 | **Write** |
| | `tee ...` (任何形式，含 pipe) | shell 写文件 | **Write** |
| **高危** | `rm -rf /` | 删除根目录或关键路径 | 需用户书面授权 |
| **列目录** | `dir /X ...` (跨盘) | cmd 跨盘列目录 | **Glob** |
| | `cmd /c "dir ..."` | cmd 转义调 dir | **Glob** |
| **PS 读字节** | `powershell -Command ...[IO.File]...` | 用 .NET 反射读字节 | **Read** |

**白名单快速通道**（首 token 命中即放行）：

```
git, ls, dir, pwd, cd, echo, whoami, date, hostname, clear, cls,
where, which, Get-ChildItem, Get-Item, Get-Location, Test-Path,
Select-Object, Format-List, Format-Table, Measure-Object, tree, find
```

**注意**：`echo` 在白名单里但带 `>` 重定向仍会被拦截；`tee` 因被列为违规模式（不是白名单）放行检查之外。

### 与 `.cursor/rules/file-operation-stability.mdc` 关系

rules 文件中"红线"用**指令式**表述（"用 Read 不用 cat"），是给 agent 看的劝阻；
本表是 hooks 文件**检测逻辑**，是给 Cursor 看的硬约束。
**两边必须同步更新**——下次加新违规类型时（例如禁用 `curl` 测活页），两边都要改。

---

## 五、安装与验证

### 5.1 安装（一次性）

文件已随仓库提交，无需额外安装。但首次 clone 后建议：

```powershell
# 1. 确认 .cursor/hooks 完整
Get-ChildItem -Path '.cursor\hooks' -Recurse

# 2. 确认 Python 3 在 PATH 上（v4 主逻辑依赖）
python --version   # 或 py --version

# 3. 重启 Cursor，让 hooks.json 重新加载
#    （hooks.json 改动其实热加载，但首次安装建议重启确认）
```

### 5.2 验证 Hook 生效（手动）

按以下顺序各触发一次:

| 测试 | 在 Cursor 里让 agent 跑 | 期望结果 |
|------|------------------------|----------|
| **违规应被阻塞** | `cat .cursorrules` | tool 返回 permission=deny，shell 不执行 |
| **正常放行** | `git status` | tool 返回 permission=allow，正常执行 |
| **sessionStart 注入** | 全新开一个 chat | agent 第一条消息引用 5 条铁则摘要 |
| **subagentStart 注入** | 主 agent 用 Task 派出 explore subagent | 子 agent 第一条消息引用 rules 指针 |

### 5.3 单元测试

```bash
# 跑全部测试
python -m pytest .cursor/hooks/tests/test_guard_shell.py -v

# 或 unittest（不依赖 pytest）
python -m unittest discover .cursor/hooks/tests
```

**当前真实测试覆盖**（截至 v4 commit a13c31e）：

| 测试类 | parametrize 用例数 | test 方法数 | 目的 |
|--------|------------------|-------------|------|
| `TestViolationsShouldDeny` | 28 | 1 (parametrize) | 违规模式必须 deny + exit 2 |
| `TestNormalCommandsShouldAllow` | 24 | 1 (parametrize) | 正常命令必须 allow + exit 0 |
| `TestFailOpenBehaviors` | — | 4 | 空 stdin / 坏 JSON / 空 command / 缺 field → fail-open allow |
| `TestWhitelistFastPath` | — | 2 | 白名单命令快速通道放行 |
| `TestCommandCmdFallback` | — | 3 | v4 必备文件存在性（.cmd / .py / .ps1） |
| **总计** | **52 个命令** | **11 个独立测试** | |

**当前已知测试失败**（截至 v4.1 已全部修复，50/50 全过）：
- ~~`less file.log` — `less` 正则 `\ble\s` 误写为 `le` + 边界~~ → 已改为 `\bless\s`
- ~~`echo hi | tee out.txt` — `tee` 通过 pipe 形式被白名单分支误判放行~~ → 已加 tee 二次检查
- ~~`dir /b C:\Users` — cmd 反斜杠路径在 JSON 字符串中双重转义，正则未覆盖~~ → 已从 WHITELIST 移除 `dir`

---

## 六、降级与故障恢复

### 6.1 降级路径触发场景

| 场景 | 触发条件 | 表现 | 降级结果 |
|------|----------|------|----------|
| **Windows 无 Python** | `where python/py/python3` 都失败 | `.cmd` 抛 fail-open JSON + exit 0 | 所有 shell 放行 |
| **Python 崩溃** | hook 自身抛未捕获异常 | stdout 输出 allow JSON + exit 0 | 当前命令放行 |
| **hooks 协议错** | 输入损坏 / stdin 空 / JSON 解析失败 | stdout 输出 allow JSON + exit 0 | 当前命令放行 |
| **超时** | Python > 4s 软超时 或 hooks.json timeout: 5 | stdout 输出 allow JSON + exit 0 | 当前命令放行 |

**重要：所有失败路径均 fail-open**——hook 自身 bug **绝不阻塞**所有 shell（否则 agent 完全瘫痪）。

### 6.2 调试入口

| 调试方式 | 路径 |
|----------|------|
| Cursor IDE 加载状态 | **Settings → Hooks** |
| 每次触发日志 | **Output → Hooks** channel |
| 本地审计 | `.cursor/logs/audit.log` |

### 6.3 完全禁用 hook（紧急逃生口）

v4 没有"局部绕过"机制（`# cursor-hook-bypass` 注释前缀是 **v5 规划功能**）。
**要临时禁用整个 `beforeShellExecution` hook**，三种方式任选：

**方式 1（推荐）：改 hooks.json matcher**
```json
"matcher": "____永远不匹配的字符串____"
```
不影响其他 hook，无需重启。仅不拦截 shell。

**方式 2：把 command 改成 `true`（Windows Git Bash 兼容）**
```json
"command": "cmd /c exit 0"
```
返回 exit 0 + 空 stdout → Cursor 当 fail-open 处理。

**方式 3：把 command 换成 echo allow**
```json
"command": "cmd /c echo {\"permission\":\"allow\"}"
```
直接吐 allow JSON，跳过 Python。

### 6.4 v3 兜底启用（无 Python 时强制 fail-open）

如临时不想装 Python 且想保留"占位 hook"：
- 直接把 `hooks.json` 的 `beforeShellExecution.command` 改回 `.cursor/hooks/guard-shell.ps1`（v3）
- v3 现在是`单纯放行`版——所有 shell 无脑通过，无任何拦截能力
- 适合**调试环境**，**生产环境必须装 Python**

---

## 七、版本演进

| 版本 | 日期 | 变更 | 状态 | commit |
|------|------|------|------|--------|
| v1 | 2026-07-15 初版 | PowerShell + stdin JSON | 已废弃 | — |
| v2 | 同日 | `[Console]::Out.WriteLine` 写 stdout | 已废弃 | — |
| v3 | 同日 | 临时降级为 fail-open 放行版 | 仅作无 Python 时的兜底 | — |
| **v4** | **2026-07-15** | **Python 重写 + stdin/stdout JSON + matcher 精准触发** | **被 v4.1 取代** | **a13c31e** |
| **v4.1** | **2026-07-15** | **修 3 个漏检 bug：less 正则 / tee 走 pipe / dir /b 跨盘** | **当前使用（50/50 测试全过）** | **<pending>** |
| v5 (待) | — | 加 `cursor-hook-bypass` 注释前缀支持 | 规划中 | — |

---

## 八、参考

- 主规则文件（agent 看）：`.cursor/rules/file-operation-stability.mdc`
- Cursor Hooks 官方文档：<https://cursor.com/docs/hooks>
- Cursor Hooks 协议契约（stdin/stdout JSON 格式）：上面的官方文档 `beforeShellExecution` 段
- 本次故障复盘：<待补 — docs/cursor_experience/file-operation-stability-hooks-fix.md>