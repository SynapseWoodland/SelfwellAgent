# Selfwell Flutter APP (Sprint SF0 scaffold)

> **范围**：本目录是 `docs/plan/mvp-implementation-plan.md` §15.2 的 Flutter
> 客户端骨架（V1.3 iOS P0）。SF0 只立骨架 + 5 个 page 占位 + 7 个核心组件 +
> ThemeData。所有 endpoint 联调在 SF1+ 启动。

---

## 目录速查

```
flutter_app/
├── pubspec.yaml                    # 依赖（Riverpod / go_router / Dio / Firebase 等）
├── analysis_options.yaml           # flutter_lints + strict-casts/inference/raw
├── scripts/
│   ├── check_forbidden_colors.sh   # §17 #11 颜色禁用 CI 卡点（bash）
│   └── check_forbidden_colors.ps1  # PowerShell 镜像（Windows / CI）
├── lib/
│   ├── main.dart                   # ProviderScope + token bootstrap + router
│   ├── core/
│   │   ├── api/{dio_client, exceptions}.dart      # Dio + 3 interceptors + 4 级 ErrorSeverity
│   │   ├── notification/fcm_service.dart          # FCM + APNs, payload 含 traceparent + client_platform + user_id_pseudo
│   │   ├── router/app_router.dart                 # 14 routes go_router
│   │   ├── storage/secure_storage.dart            # JWT + user_id + device_id
│   │   └── theme/{color_tokens, text_styles, spacing, app_theme}.dart
│   ├── widgets/                    # 7 个核心组件
│   │   ├── progress_ring.dart      # CustomPainter; 48/80/120 三档
│   │   ├── task_card.dart          # 今日小动作卡片
│   │   ├── persona_bubble.dart     # M5 4 态 FSM 映射 (warm/neutral/slight_hug/medical_guarded)
│   │   ├── ack_bubble.dart         # 30 字 ACK 渲染 + tooltip 截断（§17 #15）
│   │   ├── sse_progress.dart       # SSE 8 阶段进度条（§17 #16）
│   │   ├── image_uploader.dart     # 选图 + 压缩到 ≤ 1024px
│   │   └── error_toast.dart        # 4 级 ErrorSeverity → snackbar / banner / modal
│   └── pages/                      # 5 个 SF0 占位 page（带 IA-REF 注释）
│       ├── splash/
│       ├── login/
│       ├── home/
│       ├── diagnosis/upload/
│       └── profile/
├── test/widgets/                   # 7 widget tests + 1 golden test
└── integration_test/               # e2e（SF1+ 接入）
```

---

## 与真源对齐

| 真源 | 落地 |
|------|------|
| `docs/design/figma-pixso-spec/dist/tokens-flat.json` | `lib/core/theme/color_tokens.dart` + `spacing.dart` + `text_styles.dart` |
| `docs/design/ia-and-wireframe.md` §4 | 每个 page 顶部 `/// IA-REF:` 注释 |
| `docs/design/figma-pixso-spec/pages/*.html` | 每个 page 顶部 `/// 设计稿:` 注释 |
| `docs/api/openapi.yaml` (38 endpoints) | 每个 page 顶部 `/// 后端端点:` 注释引用 `tag=[..] operationId=..` |
| `docs/api/error-codes.md` | `_FallbackCodes` + `ErrorSeverity` 映射 |

---

## 强约束（来自 `docs/plan/mvp-implementation-plan.md` §17）

1. **Pixel-级禁用色**：`#FF4D4F` / `#D32F2F` / `#007BFF` 严禁出现在 `lib/`。
   CI 通过 `scripts/check_forbidden_colors.sh` / `.ps1` 卡点。
2. **页面 IA 锚点 1:1**：每个 page 顶部 `IA-REF` + `设计稿` + `后端端点`
   三件套注释必须齐备。
3. **双端对同一接口**：待 Sprint SF1 接入 `client/shared/api-types/dart/`
   自动生成类型，本 Sprint 不手抄 endpoint。
4. **设计稿契约**：见 page 顶部注释，UI 调整必须先改设计稿 PR。
5. **30 字 ACK 渲染**：`AckBubble` 默认 30 字上限 + tooltip 显示完整原文。
6. **SSE 断线重连**：上层 `SseService`（SF1+）按 1s→2s→4s 上限 30s 退避，
   5 次失败后展示"网络异常"。`sse_progress.dart` 只负责渲染。
7. **推送 4 端 payload**：`PushPayload.toMap()` 严格包含
   `traceparent` + `client_platform` + `user_id_pseudo`。
8. **golden 像素对比**：`progress_ring_golden_test.dart` 基线截图，与
   `pages/03-home.html` 视觉差异 ≤ 2%。

---

## 必跑命令（commit 前）

```bash
cd client/flutter_app

# 0. flutter --version (SF0 启动前确认 3.24+)
flutter --version

# 1. 装包
flutter pub get

# 2. 静态检查
flutter analyze

# 3. 单元 + widget 测试（带覆盖率）
flutter test --coverage

# 4. 更新 golden baseline（CI 第一次需要）
flutter test --update-goldens test/widgets/progress_ring_golden_test.dart

# 5. 禁用色卡点
./scripts/check_forbidden_colors.sh         # bash / Linux/macOS CI
# 或者在 PowerShell 下
pwsh -File scripts/check_forbidden_colors.ps1
```

---

## SF0 状态

- ✅ 骨架 + 7 widget + 5 page 占位 + ThemeData 翻译完成
- ✅ 7 widget test + 1 golden test 落地
- ⏳ `flutter pub get` + `flutter analyze` + `flutter test` **必须**在带
  Flutter SDK 的机器上跑通（本次 worker 在无 SDK 的 Windows PowerShell
  环境下完成代码撰写，未实跑命令 — 见 SF0 自审报告）。
- ⏳ SF1：替换 5 个 page 占位为真实实现 + `wx.login` + `/auth/wx-login` 联调
- ⏳ SF2：SSE 客户端 + 8 阶段进度（页面 `diagnosis/loading` 实装）
- ⏳ SF5：推送 4 端对接 + 跨端兼容冒烟