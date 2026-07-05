/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.1 P01 微信登录
 * 设计稿: docs/design/figma-pixso-spec/pages/02-login.html
 * 后端端点: openapi.yaml tag=auth operationId=wxMpLogin
 *
 * 行为：
 *  - 点击"微信登录" → wx.login → SF1 接入后端换 JWT
 *  - 本 Sprint 仅占位：拿到 code 后提示成功，跳转 home
 */
import { post } from '../../utils/request';
import { STORAGE_KEYS } from '../../utils/config';

interface WxLoginResp {
  token: string;
  userId: string;
}

Page({
  data: {
    agreed: false,
    loading: false,
  },

  onLoad() {
    // 校验是否同意隐私协议；未同意则弹窗提示
    this.setData({ agreed: false });
  },

  async onTapLogin() {
    if (!this.data.agreed) {
      wx.showToast({ title: '请先同意隐私政策', icon: 'none' });
      return;
    }
    if (this.data.loading) return;
    this.setData({ loading: true });

    try {
      // 1) 微信 code
      const code = await this.wxLogin();
      // 2) 调后端 wxMpLogin —— SF1 正式接入；当前 mock
      const resp = await post<WxLoginResp>('/auth/wx-login', {
        code,
        client_platform: 'wechat_mp',
      }).catch(() => ({ token: 'MOCK_JWT_' + Date.now(), userId: 'mock_user' }));

      // 3) 持久化 + 跳转
      wx.setStorageSync(STORAGE_KEYS.jwt, resp.token);
      wx.setStorageSync(STORAGE_KEYS.userId, resp.userId);
      const app = getApp();
      if (app?.globalData) {
        app.globalData.token = resp.token;
        app.globalData.userId = resp.userId;
      }

      wx.showToast({ title: '登录成功', icon: 'success' });
      setTimeout(() => wx.reLaunch({ url: '/miniprogram/pages/home/index' }), 600);
    } catch (e) {
      const msg = e instanceof Error ? e.message : '登录失败';
      wx.showToast({ title: msg, icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  wxLogin(): Promise<string> {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (res) => (res.code ? resolve(res.code) : reject(new Error('no code'))),
        fail: (err) => reject(new Error(err.errMsg ?? 'wx.login fail')),
      });
    });
  },

  onToggleAgree(e: WechatMiniprogram.CustomEvent<{ value: boolean }>) {
    this.setData({ agreed: !!(e.detail && e.detail.value) });
  },
});