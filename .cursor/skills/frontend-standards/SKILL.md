---
name: frontend-standards
description: >
  前端编码规范 skill。当编写、审查或重构 Flutter / 微信小程序代码时触发。
  覆盖：状态管理、命名规范、性能优化、审核标准、国际化。
disable-model-invocation: false
---

# 前端编码规范

## Flutter 规范

### 状态管理

Flutter 官方（2026 App Architecture Guide）推荐 `ChangeNotifier` + `Provider` / MVVM 模式。

`BLoC`（bloclibrary.dev）是**社区主流方案**，适合需要严格审计的事件驱动场景。

详见 [docs.flutter.dev/data-and-backend/state-mgmt/options](https://docs.flutter.dev/data-and-backend/state-mgmt/options)

### 禁止的命名

- **神秘命名**：变量/函数名无意义或过度缩写（如 `x1`、`tmp2`）
- **单字母变量**：除循环计数器 `i/j/k` 外，禁止单字母命名
- **匈牙利命名**：禁止 `strName`、`intCount` 前缀

### WXSS / CSS 类名命名规范（2026-07-08 补）

> **wxss class 标识符禁中文**（与 web CSS 共用一套规则）。CSS 标识符规则（CSS Syntax Level 3）：ident 只能由 `[A-Za-z0-9_-]` + Unicode 转义序列组成，**不允许字面中文**。

#### ❌ 错误写法（编译即报错）

```css
/* WXSS 文件编译错误：unexpected `` at pos N */
.direction-level-level-轻度,
.direction-level-中度,
.direction-level-重度 { ... }
```

```html
<view class="direction-level direction-level-{{dir.level}}">  <!-- dir.level='轻度' 拼接后是中文 class -->
```

**报错示例**：

```
[ WXSS 文件编译错误]
./pages/assistant-home/index.wxss(568:24): unexpected `` at pos 11006
```

#### ✅ 推荐写法 1：属性选择器（最适合"动态值"）

业务字段值（如 `intensity=轻柔` / `level=轻度` / `status=active`）是中文/枚举，**用 `[data-xxx='value']` 属性选择器**：

```css
.direction-level[data-level='轻度'] {
  background-color: rgba(168, 197, 181, 0.35);
}
.direction-level[data-level='中度'] {
  background-color: rgba(240, 217, 196, 0.7);
}
.direction-level[data-level='重度'] {
  background-color: rgba(229, 62, 62, 0.15);
}
```

```html
<view class="direction-level" data-level="{{dir.level}}">{{dir.level}}</view>
```

#### ✅ 推荐写法 2：kebab-case 英文别名（静态样式）

明确知道值集合时，class 用英文别名：

```css
.intensity-light, .intensity-soft { ... }
.intensity-normal { ... }
.intensity-strong { ... }
```

```html
<view class="intensity intensity-{{intensityEn}}">  <!-- intensityEn = light | normal | strong -->
```

#### ✅ 推荐写法 3：data 属性 + JS 计算

复杂样式用 inline style：

```html
<view style="background-color: {{bgColor}}; color: {{textColor}};">{{level}}</view>
```

#### 自检清单

- [ ] 任何 `class="xxx-{{y.zz}}"` 模板拼接，`xxx-yzz` 拼接后**整体必须是合法 ASCII 标识符**
- [ ] 中文字段值（如 backend enum）**绝不出现在 class 名里**，只能用 `[data-xxx='中文']` 属性选择器或 inline style
- [ ] PR diff 涉及 wxss / wxml 时，必须跑一遍"开发者工具 → 真机编译"再合并

**踩坑案例**：2026-07-08 Worker B 修复 Bug #3 时写了 `.direction-level-轻度` 三档配色，编译报错 `unexpected '`' at pos 11006`；改用 `[data-level='轻度/中度/重度']` 属性选择器后通过。

---

## 微信小程序审核标准（提交前必查）

> 来源：https://developers.weixin.qq.com/miniprogram/dev/framework/audits/best-practice.html

| # | 标准 | 阈值 |
|---|------|------|
| 1 | 避免 JS 异常 | 0 个未捕获异常 |
| 2 | 避免网络请求失败 | 100% 成功率 |
| 3 | 不使用已废弃 API | 0 个废弃 API 调用 |
| 4 | 使用 HTTPS | 所有请求加密 |
| 5 | 避免 setData 冗余 | 只传渲染相关数据 |
| 6 | 设置最低基础库版本 | 确保 API 可用 |
| 7 | 删除不可达页面 | 不打包未访问页面 |
| 8 | setData 调用频率 | <20 次/秒 |
| 9 | WXML 节点数 | <1000 个/页面 |
| **10** | **WXSS 编译通过（无中文 class 标识符）** | **0 编译错误** |

---

## 输出格式（提交前自检）

```
## Frontend 规范自检结果

### Flutter
| 检查项 | 结果 |
| --- | --- |
| 状态管理（Provider / ChangeNotifier / BLoC） | ✅ / ⚠️ |
| 命名规范（无神秘命名 / 单字母 / 匈牙利） | ✅ / ⚠️ |
| 禁止 `print()` 调试 | ✅ / ⚠️ |

### 微信小程序
| # | 标准 | 结果 |
|---|------| --- |
| 1 | JS 异常为 0 | ✅ / 🔴 |
| 2 | HTTPS 全量 | ✅ / 🔴 |
| 3 | 无废弃 API | ✅ / ⚠️ |
| 4 | setData 频率 <20 次/秒 | ✅ / ⚠️ |
| 5 | WXML 节点 <1000 | ✅ / ⚠️ |

**结论**：✅ 可以提交 / ⚠️ 请修复后再提交 / 🔴 必须修复
```

---

## 触发示例

- 用户：「帮我写一个 Flutter 用户列表页」
- 用户：「改一下这个微信小程序的性能问题」
- 用户：「审查这个组件的命名是否规范」
- AI 主动触发：编辑 `.dart` / `.wxml` / `.wxss` / `.js` 文件后

---

## 与其他 Skill 的边界

| Skill | 职责 | 本 skill 不做什么 |
|-------|------|------------------|
| `coding-standards/SKILL.md` | 后端 Python L0-L6 门禁 | 不查 ruff/mypy/radon |
| `pr-gate/SKILL.md` | PR 守门（FR/验收/ADR/CI） | 不查 FR 编号 |
| `golden-set/SKILL.md` | Prompt 回归 + Eval 跑分 | 不跑 Golden Set |
| `sdd-tdd/SKILL.md` | SDD→TDD 开发流 | 不驱动 TDD 循环 |
