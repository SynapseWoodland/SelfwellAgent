---
date: 2026-07-19
fr_refs: [C-14-HARNESS-IMPORT]
root_cause: Windows PowerShell (5.x) 默认 GBK 控制台 + ASCII 默认输出流，处理 UTF-8 中文文件时会把多字节序列拆碎或按 GBK 重新解码，造成中文变 `?` 替换符或乱码字符
confirmed_count: 1
status: active
---

## 触发场景

2026-07-19 C-14 迁移 `harness/` → `harness/` 路径替换阶段。PowerShell `Set-Content` 把 41 份 `harness/` 内部文件的 `harness/` 字符串替换为 `harness/` 后，多份文件中文部分（`HARNESS-EVALUATION.md` / `templates/acceptance.md` / `templates/pre-mortem.md` / `templates/lesson-record.md`）在终端显示成 `?` / 乱码字符，且 `git diff --cached --stat` 显示大幅删行（`+2999/-4227` 净减 1228 行），用户立即警觉并要求"全部回退"。

## 根因分析

**核心机制**：Windows PowerShell 5.x 有两套编码链路，与 UTF-8 文件不兼容：

1. **`Set-Content` 默认 ANSI/UTF-16 LE**：在 PowerShell 5.x 上 `Set-Content` 默认按 `[System.Text.Encoding]::Default`（中文 Windows = GBK/CP936）写入；UTF-8 多字节序列（`0xE4 0xBD 0xA0` = `你`）被按 GBK 重新拆解，单字节被独立编码后写入。
2. **`Get-Content` 与终端显示**：PowerShell 终端控制台（`$Host.UI.RawUI` / `$OutputEncoding`）默认 GBK，从管道读取已损坏的字节流时显示为 `?`。
3. **PowerShell `-replace` 操作符**：基于 .NET `String.Replace`，本身不破坏字节，但**写入端**的 `Set-Content -Encoding` 默认值决定了最终字节。

**对比 PowerShell 7+ / Core**：`Set-Content -Encoding utf8` 在 PS Core 上是**不带 BOM 的真 UTF-8**（PSCore 7+ 修复了此问题）；PS 5.x 写 `-Encoding utf8` 是 **UTF-8 BOM**（`0xEF 0xBB 0xBF` 开头），仍可能与某些读取器冲突。

**症状叠加 git diff 误报**：
- `Set-Content` 写错编码后，文件总字节数大幅变化 → `git diff --stat` 显示超大删行
- 但**实际**文件内 byte-level 仍是中文，只是被错误编码（CP936 单字节替代 UTF-8 多字节）→ 文件**逻辑**内容未丢
- 终端显示的 `?` 是**解码**问题，**字节**还在原位

## 修复路径

### 1. 立刻回退（实测已成功）

```powershell
# 回退 commit（保留 reflog，可 cherry-pick 恢复）
git reset --hard HEAD~N    # N = 本次会话创建的 commit 数
# 验证 reflog 还在
git reflog -10

# 用 cherry-pick 重新 apply（commit 对象未丢失，只是被 reset 移除分支引用）
git cherry-pick <hash1> <hash2> ...
```

> **关键**：未 tracked 的工作区文件**不能**用 `git reset` 恢复——因为它们本来就不在 git 里。`harness/*` 因为 `.gitignore` 第 21 行 `docs/` 整体 ignore 从未进 git，所以 mv 后源文件位置**没有备份**。
> 但 commit 1+2 里的文件已被 git 索引，**可以从 reflog 找回 commit 对象并 cherry-pick**。

### 2. 避免再次踩坑：UTF-8 文件操作三原则

| 原则 | 工具 | 备注 |
|------|------|------|
| **A. 优先用 StrReplace / Write / Read 原生工具** | Cursor 原生文件工具 | 这些工具底层用 Node.js / Python，UTF-8 兼容，无 PowerShell 编码 bug |
| **B. 必须用 shell 时，强制 UTF-8 + 不用 Set-Content** | `Get-Content -Raw -Encoding utf8` + Python heredoc + `git show:path > out` | 避免 PowerShell 默认 ANSI |
| **C. 验证段：每次大改动后跑 `git diff --stat` 对比"改动行数 vs 预期"** | `git diff --cached --stat` | 异常大行数（如净减 1228 行）= 编码损坏信号 |

### 3. 正确的 UTF-8 文件读写模式（PowerShell 5.x 必须）

```powershell
# 读 UTF-8 文件 -Encoding utf8 是带 BOM
$content = Get-Content -Path 'foo.md' -Raw -Encoding utf8

# 写 UTF-8 文件 -Encoding utf8 (PS 5.x) 带 BOM
# 推荐改用 .NET 直接写无 BOM UTF-8
[System.IO.File]::WriteAllText(
    'foo.md',
    $content,
    [System.Text.UTF8Encoding]::new($false)  # $false = 不要 BOM
)
```

或者**最佳路径：用 Python**（已有 uv 运行时）：

```python
# Python 永远是真 UTF-8
with open('harness/X.md', 'rb') as f:
    content = f.read()
content = content.replace(b'old/path', b'new/path')
with open('harness/X.md', 'wb') as f:
    f.write(content)
```

### 4. 预防兜底：写入前先备份关键中文文件

```powershell
# 大批量 replace 前
Copy-Item -Path 'harness/X.md' -Destination 'harness/X.md.bak'
# 出问题可还原
```

## 触发条件清单（grep 兜底）

```bash
# 1. 揪出 PowerShell 写文件命令（应只在本地 dev 出现，不应在 CI / scripts 里）
grep -rn "Set-Content\|Out-File" backend/scripts/ .github/ docs/ 2>&1 | grep -v ".md"

# 2. 揪出未指定 -Encoding utf8 的 PowerShell 操作
grep -rEn "Set-Content|Out-File" *.ps1 backend/scripts/ 2>&1 | grep -v "Encoding utf8"

# 3. 揪出 PowerShell 默认 ANSI 输出（CI 环境变量缺失时）
# 在 PowerShell 5.x 上：$OutputEncoding = [System.Text.Encoding]::UTF8 必须显式设置
grep -rEn '\$OutputEncoding' backend/scripts/ .github/ 2>&1
```

**强约束**：本项目应**永远不**在 CI workflow / scripts 里用 `Set-Content` / `Out-File` 写中文文件——改用 `python` / `git show:path > file` / `tee <(git show ...) > file` 等 UTF-8 兼容工具。

## 相关 lesson

- lesson `2026-07-19-c14-pr-gate-is-markdown.md`（待写）：pr-gate.yml 是 markdown 文档不是真 CI workflow，PR-Gate 卡口 6 = 600 行硬卡没有真实 CI 在跑
- lesson `2026-07-19-pr-a-replan-redundant.md`（待写）：REPLAN-A 拆 PR-A 加 asset-import 豁免机制，但发现 pr-gate.yml 不是真 CI 后该方案作废，浪费一轮 checklist 修订
