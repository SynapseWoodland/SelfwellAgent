---
date: 2026-07-19
fr_refs: [C-14-HARNESS-IMPORT]
root_cause: Windows PowerShell (5.x) 默认 GBK 控制台 + ASCII 默认输出流，处理 UTF-8 中文文件时会把多字节序列拆碎或按 GBK 重新解码，造成中文变 `?` 替换符或乱码字符
confirmed_count: 1
status: active
---

## 触发场景

2026-07-19 C-14 迁移 `harness/` → `harness/` 路径替换阶段。PowerShell `Set-Content` 把 41 份 `harness/` 内部文件的 `harness/` 字符串替换为 `harness/` 后，多份文件中文部分（V2 评估报告 / `templates/acceptance.md` / `templates/pre-mortem.md` / `templates/lesson-record.md`）在终端显示成 `?` / 乱码字符，且 `git diff --cached --stat` 显示大幅删行（`+2999/-4227` 净减 1228 行），用户立即警觉并要求"全部回退"。

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

---

# 附录：2026-07-20 追加踩坑经验

## 新增根因：PowerShell Sequential Operator `&&` 不支持 + `git checkout` 恢复损坏版本

### 触发场景（2026-07-20）

今日继续执行路径迁移（`docs/api/` → `docs/architecture/api/`），用 PowerShell 脚本执行批量替换：
1. `fix_paths.py` 脚本用 Python 读写文件（UTF-8 正确）
2. 用 `git checkout -- .` 恢复所有文件（意图重新开始）
3. 恢复后文件仍然是乱码

### 新增根因分析

**问题 1：`&&` Sequential Operator 在 PS 5.x 不支持**

PowerShell 7.0+ 才引入 `&&`（Sequential Operator），在 PS 5.x（Windows 10 内置）上会报 `InvalidEndOfLine` 错误：

```powershell
# 在 PowerShell 5.x 中会失败
cd "project" && python script.py
# 报错：InvalidEndOfLine
```

**问题 2：`git checkout -- .` 恢复的是工作区损坏版本**

当 `git add` 后立即 `git checkout -- .`：
- `git checkout --` 恢复的是**暂存区（index）**的损坏内容
- 而不是从 git 对象库（`.git/objects/`）读取的原始 blob
- 因为损坏的文件已被 `git add` 写入暂存区

**问题 3：PowerShell `&&` 失败导致命令未执行**

```powershell
cd "project" && python fix.py && git add . && git commit -m "..."
#                           ↑ 这行失败了
# 导致 git add . 和 commit 没有执行
```

### 修复路径

#### 1. 从 git blob 获取正确内容（核心修复）

```python
import subprocess
from pathlib import Path

ROOT = Path('d:/agent-project/SelfwellAgent')

def git_cat_file(blob_hash: str) -> bytes:
    """从 git 对象库获取 blob 原始内容"""
    result = subprocess.run(
        ['git', '-C', str(ROOT), 'cat-file', '-p', blob_hash],
        capture_output=True
    )
    return result.stdout

def get_blob_hash(rel_path: str) -> str | None:
    """获取文件的 blob hash"""
    result = subprocess.run(
        ['git', '-C', str(ROOT), 'ls-tree', '-r', 'HEAD', '--', rel_path],
        capture_output=True
    )
    if result.returncode != 0:
        return None
    # 格式: 100644 blob <hash>\t<path>
    parts = result.stdout.decode().strip().split()
    if len(parts) >= 2 and parts[1] == 'blob':
        return parts[2]
    return None

# 使用示例
blob_hash = get_blob_hash('backend/app/conf/recall_safety_keywords.yaml')
correct_content = git_cat_file(blob_hash).decode('utf-8', errors='replace')
```

#### 2. 用 Python 脚本（而非 PowerShell）执行批量替换

```python
# fix_final.py - 完整脚本
import subprocess
import re
from pathlib import Path

ROOT = Path(r'd:/agent-project/SelfwellAgent')

def git_cat_file(blob_hash: str) -> bytes:
    result = subprocess.run(
        ['git', '-C', str(ROOT), 'cat-file', '-p', blob_hash],
        capture_output=True
    )
    return result.stdout

def get_blob_hash(rel_path: str) -> str | None:
    result = subprocess.run(
        ['git', '-C', str(ROOT), 'ls-tree', '-r', 'HEAD', '--', rel_path],
        capture_output=True
    )
    if result.returncode != 0:
        return None
    parts = result.stdout.decode().strip().split()
    if len(parts) >= 2 and parts[1] == 'blob':
        return parts[2]
    return None

REPLACEMENTS = [
    ('docs/adr/', 'docs/architecture/adr/'),
    ('docs/api/openapi.yaml', 'docs/architecture/api.yaml'),
    # ... 更多替换规则
]

extensions = ['.py', '.ts', '.tsx', '.dart', '.yaml', '.yml', '.md', '.txt', '.mdc', '.sh', '.sql']
exclude_dirs = {'node_modules', '.git', 'venv', 'dist', '.venv', '__pycache__'}

for ext in extensions:
    for file_path in ROOT.rglob(f'*{ext}'):
        if any(e in file_path.parts for e in exclude_dirs):
            continue
        rel_path = str(file_path.relative_to(ROOT)).replace('\\', '/')
        blob_hash = get_blob_hash(rel_path)
        if not blob_hash:
            continue
        original_bytes = git_cat_file(blob_hash)
        content = original_bytes.decode('utf-8', errors='replace')
        # ... 执行替换并用 LF 换行写入
```

#### 3. 避免 PowerShell `&&` 问题

```powershell
# ❌ 错误：PS 5.x 不支持 &&
cd "project" && python script.py && git add .

# ✅ 正确：分步执行
cd "project"
python script.py
git add .
git commit -m "message"
```

或者用 `.ps1` 脚本文件执行（避免命令行解析问题）：

```powershell
# run_fix.ps1 - 调用 Python 脚本
python "C:\path\to\fix_final.py"
```

### 额外发现：CRLF vs LF 问题

PowerShell `Set-Content` 会写入 CRLF（`\r\n`），而 git blob 默认用 LF（`\n`）：

```
磁盘文件: 6205 bytes (含 CRLF)
Git blob: 5998 bytes (纯 LF)
差异: 第一个不同在字节 53 - disk=0x0D (CR), git=0x0A (LF)
```

**修复**：写入时强制用 LF 换行：

```python
new_bytes = content.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
file_path.write_bytes(new_bytes)
```

### 验证清单

```python
# verify.py - 验证文件内容
from pathlib import Path

ROOT = Path('d:/agent-project/SelfwellAgent')
test_files = [
    ROOT / 'backend/app/conf/recall_safety_keywords.yaml',
    ROOT / 'harness/templates/acceptance.md',
]

for f in test_files:
    content = f.read_text(encoding='utf-8')
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in content)
    print(f"{f.name}: has_chinese={has_chinese}")
    if has_chinese:
        # 显示包含中文的行
        for line in content.split('\n')[:5]:
            if any('\u4e00' <= c <= '\u9fff' for c in line):
                print(f"  Sample: {line[:80]}")
                break
```

### 触发条件清单

```bash
# 检测 PowerShell Sequential Operator (PS 7+ only)
grep -rn "&&" *.ps1 backend/scripts/ .github/scripts/

# 检测 CRLF 文件（应全部是 LF）
git -C repo ls-files | xargs -I{} git -C repo cat-file -p HEAD:{} > /tmp/git_content
diff <(git ls-files | xargs -I{} cat {}) <(git ls-files | xargs -I{} git show HEAD:{})

# 揪出含 CRLF 的文件
file $(git ls-files) | grep "CRLF"
```

### 总结：PowerShell 文件操作正确姿势

| 场景 | 正确做法 |
|------|----------|
| 读取中文文件 | `Get-Content -Path 'file' -Raw -Encoding utf8`（PS 7+）或 Python |
| 写入中文文件 | **用 Python**，避免 `Set-Content` |
| 批量替换 | **用 Python 脚本**，通过 `.ps1` 包装调用 |
| `&&` 管道符 | **不用**，改用分步执行或 `.ps1` 脚本 |
| 从 git 恢复 | **从 blob 读取** `git cat-file -p <hash>`，不用 `git checkout --` |
| 换行符 | 统一用 LF（`\n`），Python 写入时显式转换 |
