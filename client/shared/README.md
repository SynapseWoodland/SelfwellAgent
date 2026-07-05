# Client · Shared

`client/shared/` 是 Flutter APP + 微信小程序**双端共享**的真源目录，
由 SF0 阶段 Flutter worker 占位（README 注明待 Sprint SF1 双端对齐）。

## 子目录

| 路径 | 用途 | Sprint |
|------|------|--------|
| `api-types/dart/`  | `openapi-generator-cli` 自动生成的 Dart 类型（占位） | SF1 |
| `api-types/ts/`    | 同上，TypeScript 输出（待微信小程序 worker 启用） | SF1 |
| `design-tokens.json` | 跨端 Design Tokens（与 `docs/design/figma-pixso-spec/dist/tokens-flat.json` 同步） | SF0 ✅ |
| `i18n/`             | zh-CN / en 文案池（待建） | SF1 |
| `lint-rules/`       | 跨端 OPA 规则 / 禁色 / 禁词 regex | SF0 ✅ |

## 强制契约

1. **真源锁定**：`docs/design/figma-pixso-spec/dist/tokens-flat.json` 为
   唯一真源；CI 比对 `design-tokens.json::$sha256.selfFileSha256` 与
   `design-tokens.json::$sha256.upstreamSourceSha256` 防止漂移。
2. **禁色表**：`lint-rules/no-forbidden-colors.json` 列出 `#FF4D4F` /
   `#D32F2F` / `#007BFF` 三色，CI 用
   `client/flutter_app/scripts/check_forbidden_colors.{sh,ps1}` 扫描所有
   端（Flutter + 小程序 + 后端 PIL 合成输出）。
3. **生成器基线**：SF1 接入 openapi-generator，详见
   `docs/plan/mvp-implementation-plan.md` §16.2。