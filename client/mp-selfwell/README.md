# Selfwell 自愈 · 微信小程序

> **模块**：M1-M11（MVP 全量客户端）  
> **后端基线**：[MVP-PRD V1.3](../../docs/PRD/MVP-PRD%20V1.3.md) + [mvp-tech-architecture V1.1.1](../../docs/architecture/mvp-tech-architecture.md)  
> **路径约定**：`miniprogram/` 是小程序代码根目录

## 当前状态（W0 占位）

| 项 | 状态 |
|---|---|
| `project.config.json` | ✅ 占位 AppID 待 W0-D1 注册后替换 |
| `project.private.config.json` | ✅ 本地配置（不入 git） |
| `miniprogram/app.json` | ✅ 4 TabBar + 16 页面注册 |
| `miniprogram/app.ts` | ✅ 入口（含登录态检查） |
| `miniprogram/app.wxss` | ✅ 全局样式（与 design-spec 对齐） |
| `miniprogram/pages/**` | ⏳ W1-D3 起按 SPEC 逐页面实现 |

## 16 个页面（与 Pixso 高保真一一对应）

| # | 页面 | 对应 SPEC |
|---|---|---|
| 01 | splash | — |
| 02 | login | SPEC-M1 §2.1 |
| 03 | home | M3 / M4 |
| 04 | diagnosis-upload | SPEC-M2 §3 |
| 05 | diagnosis-loading | SPEC-M2 §3 |
| 06 | diagnosis-report | SPEC-M2 §4 |
| 07 | butler-home | SPEC-M5 §3 |
| 08 | checkin | SPEC-M4 §3 |
| 09 | diary | SPEC-M7 §3 |
| 09b | butler-compare | SPEC-M8 §3 |
| 10 | plaza | SPEC-M6 §3 |
| 11 | profile | M1 |
| 12 | hug-card-day7 | SPEC-M10 §2.1 |
| 13 | hug-card-day14 | SPEC-M10 §2.1 |
| 14 | hug-card-day21 | SPEC-M10 §2.1 |

## W0-W1 开发顺序

1. W0-D1：注册微信小程序账号（个人主体）→ 替换 `project.config.json` 的 `appid`
2. W0-D1：完成基础设置（名称 / 图标 / 简介）
3. W0-D1：拿到 AppID → 填入
4. W1-D3：实现 splash + login + home 三页（最小可运行闭环）
5. W2-D1：补全 M1 相关页面
6. W3-W6：按 SPEC 逐模块实现

## 注意事项

- 类目选择：**MVP 阶段选"工具-效率"**（W6 升级公司主体后切"工具-健康"）
- 简介避免"医疗/医美/治疗"字眼，写成"AI 智能习惯陪伴 / 21 天轻自律"
- 详见 [ADR-0005 微信小程序类目](../../docs/adr/0005-wechat-mp-category.md)