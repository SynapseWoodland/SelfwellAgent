# packages/api-types/dart/ — Flutter 端共享类型（SF0 占位）

> 本目录由 `openapi-generator-cli` 从 `docs/architecture/api.yaml` 自动生成。
> 与微信小程序端（`packages/api-types/ts/`）保持 1:1 同步。

## 现状（SF0 · 2026-07-06）

- 仅占位 README；真实生成产物在 SF1 接入后端 M1 endpoint 之后
- Flutter worker 独立维护，本 README 仅为双端对齐标记

## SF1 接入 checklist

- [ ] 后端 S1 落地
- [ ] `cd packages && bash regen.sh` 同步 dart/ ts/
- [ ] Flutter: `pubspec.yaml` 引入 `path: ../packages/api-types/dart`