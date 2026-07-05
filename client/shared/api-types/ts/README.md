# client/shared/api-types/ts/ — 微信小程序客户端共享类型（SF0 占位）

> 本目录由 `openapi-generator-cli` 从 `docs/api/openapi.yaml` 自动生成。
> **禁止手抄字段、禁止直接编辑**——后端 PR 修改 endpoint 后必须重新跑：
>
> ```bash
> cd client/shared && bash regen.sh
> ```

## 现状（SF0 · 2026-07-06）

- 真实生成产物在 **SF1 接入后端 M1 endpoint 之后**再生成
- 当前为占位：仅一个 README + 1 个手写最小 stub，保证骨架可编译
- 与 Flutter 端（`client/shared/api-types/dart/`）并行；各自 README 指向 SF1 对齐

## SF1 接入 checklist

- [ ] 后端 S1 落地 `auth.wxMpLogin` / `users.getCurrentUser` / `users.updatePushToken`
- [ ] 在 CI 加 step：`openapi-generator-cli generate -i ../../docs/api/openapi.yaml -g typescript -o ./ts --additional-properties=supportsES6=true`
- [ ] 微信小程序 page 通过 `import type { ... } from '../../shared/api-types/ts'` 引入
- [ ] Flutter 端同步生成 Dart 包

## 临时 stub（占位用，SF1 替换）

本目录暂时仅含 `README.md`；不生成 `.d.ts` 文件以避免冲突。