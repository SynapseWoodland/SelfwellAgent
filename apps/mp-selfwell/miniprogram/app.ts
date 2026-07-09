/// <reference path="./types/global.d.ts" />
/**
 * app.ts — Selfwell 自愈 · 微信小程序入口
 * ────────────────────────────────────────
 * 启动流程（SF0 占位）：
 *  1. 生成/读取 device_id（持久化到 storage）
 *  2. 静默 wx.login 拿 code（暂不上送，SF1 接入后端 /auth/wx-login）
 *  3. 检查更新（wx.getUpdateManager）+ storage hydrate
 *  4. 800ms 后由 splash 路由判断进入 home / login
 *
 * globalData：
 *  - token        JWT（SF1 接入）
 *  - userId       后端 user_id（unionid 映射后）
 *  - deviceId     客户端本地生成
 *  - clientPlatform 'wechat_mp'（§17.17 推送 payload 必填）
 */
import { STORAGE_KEYS } from './utils/config';
import { uuidv4 } from './utils/uuid';

interface GlobalData {
  token: string;
  userId: string;
  deviceId: string;
  clientPlatform: 'wechat_mp';
}

App<{ globalData: GlobalData }>({
  globalData: {
    token: '',
    userId: '',
    deviceId: '',
    clientPlatform: 'wechat_mp',
  },

  onLaunch() {
    // 1) device_id
    let deviceId = '';
    try {
      deviceId = wx.getStorageSync(STORAGE_KEYS.deviceId);
    } catch (e) {
      console.warn('[app] getStorageSync deviceId fail', e);
    }
    if (!deviceId) {
      deviceId = uuidv4();
      try {
        wx.setStorageSync(STORAGE_KEYS.deviceId, deviceId);
      } catch (e) {
        console.warn('[app] setStorageSync deviceId fail', e);
      }
    }
    this.globalData.deviceId = deviceId;

    // 2) 静默 wx.login（SF1 接入后端）
    wx.login({
      success: (res) => {
        if (res.code) {
          console.log('[app] wx.login code acquired (length=' + res.code.length + ')');
          // SF1: post('/auth/wx-login', { code, client_platform: 'wechat_mp' })
        }
      },
      fail: (err) => {
        console.warn('[app] wx.login fail', err);
      },
    });

    // 3) 检查更新（仅在 release 环境有意义；SF0 mock 友好）
    try {
      const updateManager = wx.getUpdateManager?.();
      if (updateManager) {
        updateManager.onCheckForUpdate(() => {
          /* ignore */
        });
        updateManager.onUpdateReady(() => {
          wx.showModal({
            title: '更新提示',
            content: '新版本已就绪，是否立即重启？',
            success: (m) => {
              if (m.confirm) updateManager.applyUpdate();
            },
          });
        });
        updateManager.onUpdateFailed(() => {
          /* ignore */
        });
      }
    } catch (e) {
      console.warn('[app] getUpdateManager fail', e);
    }

    // 4) storage hydrate
    try {
      const token = wx.getStorageSync(STORAGE_KEYS.jwt);
      const userId = wx.getStorageSync(STORAGE_KEYS.userId);
      if (token) this.globalData.token = token;
      if (userId) this.globalData.userId = userId;
    } catch (e) {
      console.warn('[app] hydrate fail', e);
    }

    // 5) 写一条日志（占位）
    try {
      const logs = wx.getStorageSync(STORAGE_KEYS.logs) || [];
      logs.unshift(Date.now());
      wx.setStorageSync(STORAGE_KEYS.logs, logs);
    } catch (e) {
      /* ignore */
    }
  },

  onShow() {
    // 从后台进入前台（SF5 推送回调接入）
  },

  onHide() {
    // 从前台进入后台
  },

  onError(err: string) {
    console.error('[app] onError', err);
  },
});