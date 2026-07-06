/**
 * utils/request.js — plan §15.3 文档口径的 wx.request 封装入口
 * ────────────────────────────────────────────────────────────
 * 该文件是 .js 入口别名；真正的实现（含类型 / ApiException 类 / 拦截器栈）
 * 由 utils/request.ts 承载（编译期 / IDE 解析）。本文件仅作为：
 *   1) plan §15.3 树中点名入口（"utils/request.js"）的兼容锚点
 *   2) 第三方小工具如 npm 包可直接 require/import 的稳定入口
 *
 * 行为与 SF0 utils/request.ts 完全等价：
 *   - 拦截器 1: Auth        (Authorization: Bearer <jwt>)
 *   - 拦截器 2: Traceparent (W3C traceparent)
 *   - 拦截器 3: Log         (dev/staging 输出，prod 静默)
 *
 * SF1 落地：4 个 page（splash/login/home/checkin）联调认证链路
 * 复用 utils/request.ts 即可；本文件不重写实现。
 */

const tsImpl = require('./request');
module.exports = {
  request: tsImpl.request,
  get: tsImpl.get,
  post: tsImpl.post,
  put: tsImpl.put,
  del: tsImpl.del,
  ApiException: tsImpl.ApiException,
};
