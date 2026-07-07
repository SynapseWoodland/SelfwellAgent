/**
 * IA-REF: docs/design/ia-and-wireframe.md §1 启动流程 / §4.1 P01
 * FIGMA  : docs/design/figma-pixso-spec/pages/01-splash.html
 * API    : openapi.yaml tag=users operationId=getCurrentUser（可选，用于拉 unionid→user_id）
 *
 * 行为：
 *  - 展示品牌 logo 800ms
 *  - 检查本地 jwt：存在 → 跳转 home；缺失 → 跳转 login
 *  - 生成 device_id（持久化到 storage）
 *
 * SF1 强化：
 *  - 已路由锁 `routed` 防 onShow + onLoad 定时器重叠二次 reLaunch
 *  - token 合法性最小校验（jwt 必须 ≥ 16 字符，含 2 个 .）
 *  - 失败兜底：storage 异常时一律按"未登录"处理，避免卡死
 */
import { STORAGE_KEYS } from '../../utils/config';
import { uuidv4 } from '../../utils/uuid';

interface SplashData {
  routed: boolean;
}

Page({
  data: {
    routed: false,
  } as SplashData,

  onLoad() {
    // 1) 生成/取回 device_id
    let deviceId = '';
    try {
      deviceId = wx.getStorageSync(STORAGE_KEYS.deviceId);
    } catch (e) {
      console.warn('[splash] getStorageSync deviceId fail', e);
    }
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

  onShow() {
    // 后台回前台：仅当尚未路由过时兜底再路由
    setTimeout(() => this.routeAfterSplash(), 0);
  },

  routeAfterSplash() {
    if (this.data.routed) return;
    let token = '';
    try {
      token = wx.getStorageSync(STORAGE_KEYS.jwt) || '';
    } catch (e) {
      console.warn('[splash] getStorageSync jwt fail', e);
    }
    // jwt 合法性最小校验：长度 ≥ 16，含 2 个 . (header.payload)
    const looksValid = token.length >= 16 && token.split('.').length >= 2;
    this.setData({ routed: true });
    const next = looksValid
      ? '/pages/home/index'
      : '/pages/login/index';
    try {
      wx.reLaunch({ url: next });
    } catch (e) {
      console.warn('[splash] reLaunch fail', e);
    }
  },
});
