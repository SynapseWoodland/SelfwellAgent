# ATDD 目录迁移指南：harness/atdd/v2 → docs/atdd

> **版本**: V1.0
> **日期**: 2026-07-22
> **状态**: Draft
> **用途**: 记录将 `harness/atdd/v2/` 迁移到 `docs/atdd/` 所需的全部引用更新

---

## 一、迁移概述

### 1.1 迁移路径

| 变更前 | 变更后 |
|--------|--------|
| `harness/atdd/v2/` | `docs/atdd/` |

### 1.2 相对路径变更规则

由于目录层级从 `harness/atdd/v2/` 变为 `docs/atdd/`，相对路径需要调整：

| 文件位置 | 旧路径 | 新路径 | 调整 |
|---------|--------|--------|------|
| **v2/ 内互引** | `../ATDD-*.md` | `../ATDD-*.md` | ❌ 无需修改 |
| **ATDD-TDS-MATRIX.md** | `harness/atdd/v2/README.md` | `docs/atdd/README.md` | ✅ |
| **harness/issues/** | `../../atdd/v2/` | `../../../docs/atdd/` | ✅ |
| **ATDD-Shared.md** | `../v2/ATDD-*.md` | `../ATDD-*.md` | ✅ 路径简化 |
| **.cursor/rules/** | `harness/atdd/v2/` | `docs/atdd/` | ✅ 需计算 |
| **check_atdd.sh** | `harness/atdd` | `docs/atdd` | ✅ |

---

## 二、需要修改的文件全清单

### 2.1 ATDD V2 内部文件

| 文件 | 需修改 | 原因 |
|------|--------|------|
| `ATDD-TDS-MATRIX.md` | ✅ 是 | 引用 `harness/atdd/v2/README.md` |
| `ATDD-Shared.md` | ✅ 是 | 引用 `../v2/ATDD-Shared.md` → `../ATDD-Shared.md` |
| 其他 13 个 | ❌ 否 | v2/ 内相对路径深度不变 |

### 2.2 Harness Issues 目录

| 文件 | 需修改 | 引用数 |
|------|--------|--------|
| `harness/issues/M3-P1-PRD-conflict.md` | ✅ 是 | 2 处显式引用 |

### 2.3 GitHub Scripts

| 文件 | 需修改 | 引用内容 |
|------|--------|---------|
| `.github/scripts/check_atdd.sh` | ✅ 是 | `ATDD_DIR="harness/atdd"` → `ATDD_DIR="docs/atdd"` |

### 2.4 Cursor Rules

| 文件 | 需修改 | 引用内容 |
|------|--------|---------|
| `.cursor/rules/chinese-doc-utf8-handling.mdc` | ✅ 是 | Python 代码中的路径字符串 |

### 2.5 无需修改的文件

| 文件夹 | 文件 | 原因 |
|--------|------|------|
| `harness/` | README-V2.md | 仅引用 harness 自身目录 |
| `harness/` | checklist-now.md | 无 ATDD 路径引用 |
| `harness/` | DEMO-5-TASK-TYPES.md | 仅注释提及 |
| `harness/` | THEORY-COMPLETION.md | 仅注释提及 |
| `harness/evidence/` | *.md | 仅文本提及 ATDD |
| `harness/lessons/` | *.md | 仅文本提及 |

---

## 三、具体修改对照表

### 3.1 ATDD-TDS-MATRIX.md

```diff
- ATDD V2 索引：`harness/atdd/v2/README.md`
+ ATDD V2 索引：`docs/atdd/README.md`
```

### 3.2 ATDD-Shared.md

```diff
- 详见 [ATDD-Shared.md §一](../v2/ATDD-Shared.md#一用户状态枚举)
+ 详见 [ATDD-Shared.md §一](../ATDD-Shared.md#一用户状态枚举)

- 详见 [ATDD-Shared.md §三](../v2/ATDD-Shared.md#三合规红线)
+ 详见 [ATDD-Shared.md §三](../ATDD-Shared.md#三合规红线)

- 详见 [ATDD-Shared.md §四](../v2/ATDD-Shared.md#四错误码字典)
+ 详见 [ATDD-Shared.md §四](../ATDD-Shared.md#四错误码字典)
```

### 3.3 harness/issues/M3-P1-PRD-conflict.md

```diff
- `harness/atdd/v2/ATDD-Plan.md` V1.1
+ `docs/atdd/ATDD-Plan.md` V1.1

- 已写入 [ATDD-Plan.md V1.1 §四](../../atdd/v2/ATDD-Plan.md#四方案状态同步与生命周期联动)
+ 已写入 [ATDD-Plan.md V1.1 §四](../../../docs/atdd/ATDD-Plan.md#四方案状态同步与生命周期联动)
```

### 3.4 .github/scripts/check_atdd.sh

```diff
# 4. 检查 ATDD 目录是否存在
- ATDD_DIR="harness/atdd"
+ ATDD_DIR="docs/atdd"
```

### 3.5 .cursor/rules/chinese-doc-utf8-handling.mdc

```diff
files = [
    'docs/architecture/TDS/TDS-M5-persona-chat.md',
-   'harness/atdd/v2/ATDD-Journey.md',
+   'docs/atdd/ATDD-Journey.md',
]
```

---

## 四、迁移执行步骤

### Step 1: 备份

```bash
# 创建备份
cp -r harness/atdd/v2 harness/atdd/v2.backup
```

### Step 2: 移动目录

```bash
# 移动目录
mv harness/atdd/v2 docs/atdd
```

### Step 3: 更新引用

#### 3.1 批量替换字符串

```bash
# 在 docs/atdd/ 目录内
# 替换 ATDD-Shared.md 中的旧路径
sed -i 's|../v2/ATDD-|../ATDD-|g' docs/atdd/ATDD-Shared.md

# 替换 ATDD-TDS-MATRIX.md 中的旧路径
sed -i 's|harness/atdd/v2/|docs/atdd/|g' docs/atdd/ATDD-TDS-MATRIX.md

# 替换 harness/issues/ 中的路径
sed -i 's|../../atdd/v2/|../../../docs/atdd/|g' harness/issues/M3-P1-PRD-conflict.md
sed -i 's|harness/atdd/v2/|docs/atdd/|g' harness/issues/M3-P1-PRD-conflict.md

# 更新 check_atdd.sh
sed -i 's|ATDD_DIR="harness/atdd"|ATDD_DIR="docs/atdd"|g' .github/scripts/check_atdd.sh

# 更新 chinese-doc-utf8-handling.mdc
sed -i "s|'harness/atdd/v2/|'docs/atdd/|g" .cursor/rules/chinese-doc-utf8-handling.mdc
```

### Step 4: 验证

```bash
# 检查是否还有旧路径引用
grep -rn "harness/atdd/v2" .
grep -rn "atdd/v2" .
```

预期：无匹配结果

---

## 五、验证清单

### 5.1 目录结构验证

```bash
# 确认目录已移动
ls -la docs/atdd/

# 确认旧目录已删除
ls -la harness/atdd/
```

### 5.2 引用完整性验证

| 检查项 | 命令 | 预期结果 |
|--------|------|---------|
| 无旧路径 | `grep -rn "harness/atdd/v2" .` | 0 结果 |
| 无旧相对路径 | `grep -rn "atdd/v2" .` | 0 结果 |
| check_atdd.sh 正常 | `bash .github/scripts/check_atdd.sh` | 正常执行 |

---

## 六、迁移后的目录结构

```
docs/
├── atdd/                      # ← 原 harness/atdd/v2/
│   ├── ATDD-TDS-MATRIX.md    # ★ 需求追踪矩阵
│   ├── ATDD-Shared.md         # 跨域共享定义
│   ├── ATDD-Journey.md        # 用户旅程覆盖
│   ├── ATDD-Auth.md           # M1 认证
│   ├── ATDD-Diagnosis.md      # M2 诊断
│   ├── ATDD-Plan.md           # M3 方案
│   ├── ATDD-Checkin.md        # M4 打卡
│   ├── ATDD-Conversation.md   # M5 对话
│   ├── ATDD-Feedback.md       # M7 反馈
│   ├── ATDD-Recall.md         # M8 回忆
│   ├── ATDD-Community.md      # M6 社区
│   ├── ATDD-Share.md          # M10 分享
│   ├── ATDD-Push.md           # M13 推送
│   ├── ATDD-Compliance.md     # M14 合规
│   ├── ATDD-Timezone.md       # M12 时区
│   ├── ATDD-Contract-Fix.md   # PRC 契约修复
│   └── MIGRATION-GUIDE.md    # ★ 本文档
└── architecture/
    └── TDS/                   # 技术设计文档（不变）
        └── *.md

harness/
├── issues/
│   └── M3-P1-PRD-conflict.md # ✅ 引用已更新
└── ...

.github/
└── scripts/
    └── check_atdd.sh          # ✅ 引用已更新
```

---

## 七、修订历史

| 日期 | 版本 | 改动 |
|------|------|------|
| 2026-07-22 | V1.0 | 初次创建迁移指南 |
