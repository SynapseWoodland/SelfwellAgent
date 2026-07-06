path = r'd:\agent-project\SelfwellAgent\docs\design\ia-and-wireframe.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Use `|` (single pipe) since that's what the file has
old_92_93 = '''### 9.2 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| V1.0 | 2026-07-05 | 初始版本，基于 design-spec.md（V1.0）+ MVP-PRD（V1.2）+ forbidden-words（V1.0）创建 |
| V2.0 | 2026-07-05 | 智能管家对话主页 P03a + 智能分析报告 P03c + 三步卡 §6.7 + 心情日记卡 §6.8 + 对比回顾卡 §6.9；Tab Bar「诊断」→「智能管家」口径对齐；与 design-spec.md V1.1 保持一致 |

---

**文档结束**'''

new_full = '''### 9.2 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| V1.0 | 2026-07-05 | 初始版本，基于 design-spec.md（V1.0）+ MVP-PRD（V1.2）+ forbidden-words（V1.0）创建 |
| V2.0 | 2026-07-05 | 智能管家对话主页 P03a + 智能分析报告 P03c + 三步卡 §6.7 + 心情日记卡 §6.8 + 对比回顾卡 §6.9；Tab Bar「诊断」→「智能管家」口径对齐；与 design-spec.md V1.1 保持一致 |
| **V2.1** | **2026-07-06** | **本版本**：对齐 `docs/design/figma-pixso-spec/{pages,dist}` 实际交付物。详见下方 §9.3 变更摘要。 |

---

### 9.3 文件交付物对照表（IA P 编号 ↔ HTML 文件）

> **目的**：解决 IA 文档 P 编号体系（P01/P02/P03a/P03c...）与 HTML 文件编号体系（01-splash/02-login/03-home...）不一致问题。
>
> **维护原则**：HTML 文件编号是「按文件创建顺序」的稳定 ID，**不随 IA 改动**；P 编号是「按产品页面」的语义 ID，可演进。两者通过本表解耦。

#### 9.3.1 一一对应表

| P 编号 | 页面语义 | HTML 文件 | dist/ 收录 | 状态 |
|--------|--------|---------|-----------|------|
| P01 | 启动页 | `pages/01-splash.html` | ✅ | ✅ MVP |
| P01b | 登录页（手机号） | `pages/02-login.html` | ✅ | ✅ MVP |
| P02 | 首页（今日打卡） | `pages/03-home.html` | ✅ | ✅ MVP |
| **P02b** | **今日完成页** | **`pages/08-checkin.html`** | ✅ | **✅ 新增对齐（V2.1）** |
| P03a | 智能管家对话主页 | `pages/07-butler-home.html` | ✅ | ✅ MVP |
| P03a-s1 | 三步卡 Step1 · 上传 | `pages/04-butler-analyze-upload.html` | ✅ | ✅ MVP |
| P03a-s2 | 三步卡 Step2 · 分析中 | `pages/05-butler-analyze-loading.html` | ✅ | ✅ MVP |
| P03c | 智能分析报告（对话气泡内推送） | （无独立页，仅 §4.8 描述） | ❌ | ✅ 仅对话流内 |
| P03c-stand | 智能分析报告（独立兜底页） | `pages/06-butler-analyze-report.html` | ✅ | ✅ MVP 兜底用 |
| P04 | 方案页（21 天） | `pages/07-plan.html` | ✅ | ✅ MVP |
| P05 | 广场页（蜕变广场） | `pages/09-plaza.html` | ✅ | ✅ MVP |
| **P05b** | **广场发布子页** | **（无独立 HTML）** | ❌ | **⚠️ MVP 由 P05 全屏编辑器承载，未单独输出** |
| P06 | 我的（个人中心） | `pages/11-profile.html` | ✅ | ✅ MVP |
| P08 | 心情日记列表 | `pages/08-butler-diary.html` | ✅ | ✅ MVP |
| P09 | 对比回顾页（问过去的自己） | `pages/09-butler-compare.html` | ✅ | ✅ MVP |
| **P10** | **时光相册页** | **（无 HTML）** | ❌ | **⚠️ MVP 未交付，§4.11 占位规范** |
| P07-A | 抱抱卡 · 第 7 天 | `pages/12-hug-card-day7.html` | ✅ | ✅ MVP |
| P07-B | 抱抱卡 · 第 14 天 | `pages/13-hug-card-day14.html` | ✅ | ✅ MVP |
| P07-C | 抱抱卡 · 第 21 天 | `pages/14-hug-card-day21.html` | ✅ | ✅ MVP |
| P07-D | 分享卡（朋友圈外链） 750×562 | （无 HTML） | ❌ | ⚠️ MVP 未交付，§6.4 占位规范 |

#### 9.3.2 V2.1 变更摘要（vs pages/ + dist/ 实际交付物）

> 背景：用户反馈 `docs/design/figma-pixso-spec/pages` 和 `docs/design/figma-pixso-spec/dist` 交付物与本 IA 文档存在多处不对齐。

| # | 差异类型 | 文档位置 | V2.1 处理方式 |
|---|---------|---------|--------------|
| 1 | **P02b 今日完成页缺失** | 原 §1.2 页面树未列；`08-checkin.html` 已存在 | **新增 §4.7** 完整规格，对齐 `08-checkin.html` |
| 2 | **P03c 双形态混淆** | 原 IA 仅描述「对话气泡内卡片」；`06-butler-analyze-report.html` 实际为独立兜底页 | §4.8 增加说明：P03c 双向呈现（气泡内 + 独立页） |
| 3 | **P08 心情日记缺独立 IA 章节** | 原仅 §4.3.4 描述入口卡；`08-butler-diary.html` 有完整列表页 | **新增 §4.9** 完整规格 |
| 4 | **P09 命名错位** | 原 §1.2 把 P09 标为「时光相册页」；`09-butler-compare.html` 实际是「对比回顾」 | **新增 §4.10 P09=对比回顾** + **§4.11 P10=时光相册**（新增编号） |
| 5 | **P10 时光相册页缺失** | 原 IA 把 P09 当相册；`pages/` 无相册 HTML | **新增 §4.11 P10 章节**，标注 MVP 未交付 |
| 6 | **P05b 广场发布子页缺失** | 原 §4.5.3 有子页布局；`pages/` 无发布页 HTML | §4.5.3 增加「MVP 由 P05 全屏编辑器承载」说明 |
| 7 | **P01 vs P01b 拆分不清** | 原 §1.2 把启动+登录合在 P01；HTML 拆为 01/02 两个独立页 | §1.2 明确拆为 P01 + P01b |
| 8 | **P07 海报分类混乱** | 原 IA 把抱抱卡标 P08 与 P09 相册混用 | §1.2 重新编号：P07-A/B/C 抱抱卡、P07-D 分享卡 |
| 9 | **跳转矩阵空缺行** | 原 §1.3 有 4 行空白跳转目标 | §1.3 补全所有跳转路径（含 P02b/P01b/P05b/P10/P08/P09） |
| 10 | **首页线框与 HTML 不一致** | 原 §4.2 无问候区；HTML 实际有「早安，小满」+「今天也是慢慢变好的一天」 | §4.2.2/4.2.3/4.2.4/4.2.5 全量对齐 `03-home.html` |
| 11 | **页面树与 §4 章节不对齐** | 原 §1.2 列 P01-P09 但 §4 缺 P02b/P05b/P08/P09/P10 章节 | §1.2 + §4 双向闭环，§4 章节补齐 P02b/P08/P09/P10 |
| 12 | **海报类型 B 标为「已交付」** | 原 §6.4 未标交付状态；`pages/` 无分享卡 HTML | §6.4 类型 B 增加「MVP 未交付 HTML」标注 |

#### 9.3.3 已知遗留问题（下一版本处理）

| # | 问题 | 影响 | 建议处理 |
|---|------|------|---------|
| 1 | P10 时光相册页无 HTML | 设计师无法复刻 | V2.2 补 `15-album.html`（避开 01-14 现有编号） |
| 2 | P05b 广场发布子页无 HTML | 设计师无法复刻 | V2.2 补 `16-publish.html` |
| 3 | P07-D 分享卡 750×562 无 HTML | 设计师无法复刻 | V2.2 补 `17-share-card.html` |
| 4 | `dist/index.html` 复刻工作台未收录 P02b/P08/P09 | 复刻时需手动打开 HTML | V2.2 同步更新 `dist/pixso-handoff.csv` 与 `dist/index.html` nav |
| 5 | HTML 文件名 `08` 同时给 P02b 和 P08 用 | 易混淆 | 下一轮重命名：建议 `02b-checkin.html` 替 `08-checkin.html` |

---

**文档结束**'''

if old_92_93 in content:
    content = content.replace(old_92_93, new_full)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK; new length:', len(content))
else:
    print('NOT FOUND')
    # try locating what's at the end
    idx = content.find('V2.0 | 2026-07-05')
    print('V2.0 idx:', idx)
    print('around:', repr(content[idx-5:idx+250]))
