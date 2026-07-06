/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.1 P01 微信登录
 * FIGMA  : docs/design/figma-pixso-spec/pages/02-login.html
 * API    : openapi.yaml tag=auth operationId=wxMpLogin POST /auth/wx-login
 *
 * 真实接入：wx.login → /auth/wx-login → 持久化 jwt + user_id_pseudo → 拉 /users/me → 跳转 home
 * §17 强约束：
 *  - 推送 payload 字段登记在请求头：X-Client-Platform + X-Device-Id
 *  - 后端返回 user_id_pseudo（§17.10）而非真实 openid
 *  - error_capture 上报 traceparent，便于 LLM fallback 反查
 *
 * SF1 增量：
 *  - 错误码 → 中文 toast 映射（`error-code.ts`）
 *  - 401 由 utils/request.ts 拦截器统一跳转 splash/login（这里不再处理）
 *  - 隐私协议持久化 key 抽到 STORAGE_KEYS
 */
import { post } from '../../utils/request';
import { CLIENT_PLATFORM, STORAGE_KEYS } from '../../utils/config';
import { ERR_LABEL } from '../../utils/error-code';
import type { WxLoginReq, WxLoginResp, UserMe } from '../../types/api';

Page({
  data: {
    agreed: false,
    loading: false,
  },

  onLoad() {
    // 检查是否同意隐私协议；SF1 占位：默认 false 必须勾选
    try {
      const agreed = wx.getStorageSync(STORAGE_KEYS.privacyAgreed);
      if (agreed) this.setData({ agreed: true });
    } catch {
      /* ignore */
    }
  },

  onToggleAgree(e: WechatMiniprogram.CustomEvent<{ value: boolean }>) {
    const agreed = !!(e.detail && e.detail.value);
    this.setData({ agreed });
    try {
      wx.setStorageSync(STORAGE_KEYS.privacyAgreed, agreed);
    } catch {
      /* ignore */
    }
  },

  async onTapLogin() {
    if (!this.data.agreed) {
      wx.showToast({ title: '请先同意《隐私政策》《用户协议》', icon: 'none' });
      return;
    }
    if (this.data.loading) return;
    this.setData({ loading: true });

    try {
      const code = await this.wxLogin();
      const deviceId = wx.getStorageSync(STORAGE_KEYS.deviceId) || '';
      const req: WxLoginReq = {
        code,
        client_platform: CLIENT_PLATFORM,
        device_id: deviceId,
      };
      const resp = await post<WxLoginResp>('/auth/wx-login', req);

      // §17.10：前端只持久化 user_id_pseudo 与 token
      wx.setStorageSync(STORAGE_KEYS.jwt, resp.token);
      wx.setStorageSync(STORAGE_KEYS.userId, resp.user_id_pseudo);
      try {
        wx.setStorageSync(STORAGE_KEYS.openidE, resp.openid_e);
      } catch {
        /* ignore */
      }
      const app = getApp();
      if (app?.globalData) {
        app.globalData.token = resp.token;
        app.globalData.userId = resp.user_id_pseudo;
      }

      // 可选：拉一次 /users/me 用于后续页面渲染
      try {
        const me = await post<UserMe>('/users/me', {});
        wx.setStorageSync('me_cached', JSON.stringify(me));
      } catch {
        /* 后端不可用时不算致命 */
      }

      wx.showToast({ title: '登录成功', icon: 'success' });
      setTimeout(() => {
        wx.reLaunch({ url: '/miniprogram/pages/home/index' });
      }, 600);
    } catch (e) {
      const code =
        e && typeof e === 'object' && 'code' in e ? String((e as { code: unknown }).code) : '';
      const msg =
        e instanceof Error
          ? ERR_LABEL[code] ?? e.message ?? '登录失败，请稍后再试'
          : '登录失败，请稍后再试';
      wx.showToast({ title: msg.slice(0, 24), icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  wxLogin(): Promise<string> {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (res) =>
          res.code ? resolve(res.code) : reject(new Error('wechat login no code')),
        fail: (err) => reject(new Error(err.errMsg ?? 'wx.login fail')),
      });
    });
  },
});
