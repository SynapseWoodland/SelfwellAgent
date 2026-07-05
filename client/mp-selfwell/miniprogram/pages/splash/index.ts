/**
 * IA-REF: docs/design/ia-and-wireframe.md §1 启动流程 / §4.1 P01
 * 设计稿: docs/design/figma-pixso-spec/pages/01-splash.html
 * 后端端点: openapi.yaml tag=users operationId=getCurrentUser（可选，用于拉 unionid→user_id）
 *
 * 行为：
 *  - 展示品牌 logo 800ms
 *  - 检查本地 jwt：存在 → 跳转 home；缺失 → 跳转 login
 *  - 生成 device_id（持久化到 storage）
 */
import { STORAGE_KEYS } from '../../utils/config';
import { uuidv4 } from '../../utils/uuid';

Page({
  data: {},

  onLoad() {
    // 1) 生成/取回 device_id
    let deviceId = wx.getStorageSync(STORAGE_KEYS.deviceId);
    if (!deviceId) {
      deviceId = uuidv4();
      try {
        wx.setStorageSync(STORAGE_KEYS.deviceId, deviceId);
      } catch (e) {
        console.warn('[splash] setStorageSync deviceId fail', e);
      }
    }
    // 2) 同步到 globalData（供后续请求携带）
    const app = getApp();
    if (app?.globalData) app.globalData.deviceId = deviceId;

    // 3) 800ms 后决定去向
    setTimeout(() => this.routeAfterSplash(), 800);
  },

  routeAfterSplash() {
    const token = wx.getStorageSync(STORAGE_KEYS.jwt);
    if (token) {
      wx.reLaunch({ url: '/miniprogram/pages/home/index' });
    } else {
      wx.reLaunch({ url: '/miniprogram/pages/login/index' });
    }
  },
});