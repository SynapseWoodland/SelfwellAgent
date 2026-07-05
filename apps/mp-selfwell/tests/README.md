# apps/mp-selfwell/tests/ — 微信小程序测试（Sprint SF0 占位）

> 真正的 miniprogram-automator 接入在 **W5（SF4 之后）** 阶段；本 Sprint 只留 README + 1 个 mock 测试样例。

## 目标

- ✅ SF0：骨架就绪 + 烟雾测试样例 + README
- SF1：补 login / home / checkin 真实冒烟
- SF2：SSE + image-uploader 真实冒烟
- SF4：profile / community / hug-card 真实冒烟
- SF5：推送 4 端 e2e

## miniprogram-automator 接入 checklist（W5 起）

- [ ] CI 镜像内置微信开发者工具 CLI（cli.bat）
- [ ] 项目根 `miniprogram/` 可被 IDE 打开（占位 appid 用 `wx_your_appid`，CI 临时替换为测试 appid）
- [ ] 烟雾脚本：`automator.launch()` → `miniProgram.navigateTo('/miniprogram/pages/home/index')` → 截图

## 像素对比（§17.18）

P0 page（home / diagnosis report / plan / hug-card）必须与
`docs/design/figma-pixso-spec/pages/*.html` 视觉一致（≤ 2% 像素 diff），
SF4 阶段接入像素 diff 工具（pixelmatch / resemblejs）。