# client/shared — 跨端共享资产

> Flutter APP 与 微信小程序共用的"非代码真源"。
> **严禁两端在 page 内手抄字段、endpoint、文案**——必须从本目录统一引入。

## 目录

| 目录 | 用途 | Sprint 节点 |
|------|------|-------------|
| `api-types/dart/` | 自动生成的 Dart 类型（Flutter 端） | SF1 |
| `api-types/ts/`   | 自动生成的 TS 类型（微信小程序端） | SF1 |
| `design-tokens.json` | Design Tokens 单源（CI 卡 hash） | SF1 |
| `forbidden-words.json` | 与 `docs/design/forbidden-words.md` 同步 | SF0 末 / SF1 |
| `i18n/zh-CN.json` | 中文文案池（推送模板等共用） | SF5 |

## 与后端 openapi.yaml 同步

```bash
cd client/shared
bash regen.sh   # 触发 openapi-generator-cli 双端生成
```

CI 卡点：
- `design-tokens.json` 的 hash 必须等于 `docs/design/figma-pixso-spec/dist/tokens-flat.json` 派生的 hash
- `forbidden-words.json` 必须在 ack-pool.yaml / recall-forbidden-words.yaml 基础上对齐

## SF0 占位

- 仅 `api-types/dart/README.md` 与 `api-types/ts/README.md`，无产物生成
- SF1 后由 CI 接管自动生成