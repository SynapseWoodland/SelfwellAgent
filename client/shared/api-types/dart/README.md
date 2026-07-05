# client/shared/api-types/dart

> **Sprint SF0 占位** · 详见 `docs/plan/mvp-implementation-plan.md` §16.2

## 当前状态

本目录在 **SF0** 仅放占位 README，**不**实际跑 `openapi-generator-cli`。
真正的类型生成计划在 **Sprint SF1 启动后** 接入，由以下命令驱动：

```bash
$ openapi-generator-cli generate \
    -i ../../docs/api/openapi.yaml \
    -g dart \
    -o . \
    --additional-properties=libraryName=package:selfwell_api_types
```

生成后：

- `client/flutter_app/` 通过 `package:selfwell_api_types/...` 引入（先在
  `pubspec.yaml` 加 `path: ../shared/api-types/dart`）。
- 禁止手抄 endpoint / 字段 / 枚举（`docs/plan/mvp-implementation-plan.md` §17 #13）。

## 与小程序的对应

- 微信小程序 worker 在 `client/shared/api-types/ts/` 同步生成 TS 类型。
- 两条流水线共用 `docs/api/openapi.yaml` v1.1.0 作为唯一真源。
- 任一端 PR 触碰 `openapi.yaml` → 双端必须同时合入（§16.4 提交同步锁）。

## 与字段对齐的字段集合（待 SF1 接入）

| 模块 | operationId | Path |
|------|-------------|------|
| M1 | `wxMpLogin` | `POST /auth/wx-login` |
| M1 | `getCurrentUser` | `GET /users/me` |
| M2 | `createDiagnosis` | `POST /diagnosis` |
| M2 | `streamDiagnosis` | `GET /diagnosis/{id}/stream` |
| M3 | `getActivePlan` | `GET /plans/active` |
| M4 | `createCheckin` | `POST /checkins` |
| M5 | `assistantChat` | `POST /assistant/sessions/{id}/messages` |
| M9 | `subscribeNotifications` | `POST /notifications/subscribe` |

完整清单：`docs/api/openapi.yaml` 38 个 endpoints / 12 个 tag。