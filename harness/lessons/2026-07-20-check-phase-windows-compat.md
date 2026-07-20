---
date: 2026-07-20
fr_refs: []
root_cause: check_phase.py 在 Windows PowerShell 环境存在跨平台兼容性问题
confirmed_count: 3
status: active
---

# Lesson: check_phase.py Windows 跨平台兼容性问题

## 触发场景

在 Windows PowerShell 环境运行 `python harness/scripts/check_phase.py PRD` 时，`grep` 命令始终返回 FAIL。

## 根因分析

发现 3 个 Windows 兼容性问题：

1. **shlex.split() 引号保留问题**：Windows 上 `posix=False` 时，双引号被保留在参数中，导致模式变成 `'"^signed: true"'`

2. **合并参数未展开**：`-qE` 被当作单个参数，而代码只处理 `-q` 和 `-E` 分开的情况

3. **正则缺少 MULTILINE 标志**：grep 的 `^` 在 bash 中匹配行首，但 Python `re.findall()` 默认不启用 `MULTILINE`

## 修复内容

### 1. Windows shlex 引号处理（check_phase.py run_exit_criterion）

```python
# Windows shlex 在 posix=False 时会保留引号，需要预处理移除
processed_args = []
for arg in args:
    if ((arg.startswith('"') and arg.endswith('"')) or
            (arg.startswith("'") and arg.endswith("'"))):
        processed_args.append(arg[1:-1])
    else:
        processed_args.append(arg)
```

### 2. 合并参数展开（check_phase.py _builtin_grep）

```python
# 预处理：展开合并的参数如 -qE → -q -E
processed_args = []
for arg in args:
    if arg.startswith("-") and len(arg) > 2:
        for ch in arg[1:]:
            processed_args.append("-" + ch)
    else:
        processed_args.append(arg)
```

### 3. MULTILINE 正则标志（check_phase.py _builtin_grep）

```python
if extended_regex:
    regex_flags = re.MULTILINE | (re.IGNORECASE if "-i" in args else 0)
else:
    regex_flags = re.MULTILINE
```

### 4. workflow-v2.yaml exit_criteria 正则修正

原正则 `FR-[0-9]` 只匹配单个数字后跟数字，但实际 FR-ID 格式是 `FR-M1-01-20260719`（含字母 M）。

```yaml
# 修正前
'grep -qE "fr_refs:.*FR-[0-9]" harness/evidence/01-requirement.md'
# 修正后
'grep -qE "fr_refs:.*FR-[A-Z0-9-]+" harness/evidence/01-requirement.md'
```

## 触发条件清单

| 场景 | 正确做法 |
|------|---------|
| Windows PowerShell 运行 check_phase.py | 使用 Python 内置实现（已修复） |
| 添加新的 exit_criteria 正则 | 考虑实际数据格式（可能含字母） |
| 使用 `-qE` 等合并参数 | 展开为 `-q -E` |

## 晋升评估

- [ ] 触发条件可机器检测：✅ ruff check + check_phase.py --all
- [ ] 同类问题在过去 90 天内出现 ≥ 2 次：❌ 首次发现
- [ ] 修复方式可抽象为通用 pattern：✅ 已内联修复

→ **暂不晋升，等待更多实战验证**

## 参考

- 修复文件：`harness/scripts/check_phase.py`
- 修复文件：`harness/workflow-v2.yaml`
