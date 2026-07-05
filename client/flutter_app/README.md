# Selfwell 自愈 · Flutter APP

> **模块**：M1-M11（MVP 全量客户端）  
> **后端基线**：[MVP-PRD V1.3](../../docs/PRD/MVP-PRD%20V1.3.md) + [mvp-tech-architecture V1.1.1](../../docs/architecture/mvp-tech-architecture.md)  
> **MVP 优先级**：iOS 优先（P1 扩 HarmonyOS）

## 当前状态（W0 占位）

| 项 | 状态 |
|---|---|
| `pubspec.yaml` | ✅ 完整依赖（dio / riverpod / go_router / fluwx / share_plus 等） |
| `analysis_options.yaml` | ✅ 与 coding-standards SKILL 对齐（prefer_const / require_trailing_commas） |
| `lib/main.dart` | ✅ 占位启动页（已绑定 design-spec 主色 #A8C5B5） |
| `lib/**` | ⏳ W1-D3 起按 SPEC 逐页面实现 |

## 16 个页面（与 Pixso 高保真一一对应）

| # | 页面 | 对应 SPEC | 优先级 |
|---|---|---|---|
| 01 | splash | — | W1-D3 |
| 02 | login | SPEC-M1 §2.2 | W1-D3 |
| 03 | home | M3 / M4 | W1-D4 |
| 04 | diagnosis-upload | SPEC-M2 §3 | W3 |
| 05 | diagnosis-loading | SPEC-M2 §3 | W3 |
| 06 | diagnosis-report | SPEC-M2 §4 | W3 |
| 07 | butler-home | SPEC-M5 §3 | W4 |
| 08 | checkin | SPEC-M4 §3 | W4 |
| 09 | diary | SPEC-M7 §3 | W4 |
| 09b | butler-compare | SPEC-M8 §3 | W5 |
| 10 | plaza | SPEC-M6 §3 | W5 |
| 11 | profile | M1 | W2 |
| 12-14 | hug-card-day7/14/21 | SPEC-M10 §2.1 | W5 |

## 多端打包（V1.3 MVP）

| 平台 | MVP 状态 | 备注 |
|---|---|---|
| **iOS** | ✅ P0 必出 | Apple Developer 个人账号 W0-D3 注册 |
| Android | ❌ 不出 | 详见 w0-checklist.md W0-D5（6 家市场审核成本不可承受）|
| HarmonyOS | ⏸️ 被动上架 | 华为开发者 W0-D3 注册；P1 用户量起来后再正式投放 |

## W0-W1 启动顺序

1. W0-D3：注册 Apple Developer 个人账号（$99/年）
2. W0-D3：注册华为开发者联盟账号
3. W1-D3：在本目录执行 `flutter create . --platforms=ios` 初始化原生工程
4. W1-D3：实现 splash + login + home 三页（最小可运行闭环）
5. W2-D1：补全 M1 相关页面
6. W3-W6：按 SPEC 逐模块实现

## 注意事项

- **MVP 不上 Android 市场**（1 人精力不可承受 6 家市场审核）
- **HarmonyOS 仅后台创建应用，不主动投**
- 详见 [ADR-0006 不做 Web 平台](../../docs/adr/0006-no-web-platform.md) / [ADR-0010 HarmonyOS 时机](../../docs/adr/0010-harmonyos-timing.md)