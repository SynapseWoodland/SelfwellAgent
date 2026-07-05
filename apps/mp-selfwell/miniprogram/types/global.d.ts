/**
 * Selfwell 自愈 · 微信小程序全局类型补充
 * 微信开发者工具内置 wechat-miniprogram 类型已覆盖大部分；本文件仅放跨文件共享的扩展。
 */

declare global {
  namespace WechatMiniprogram {
    interface SocketTask {
      onOpen(callback: () => void): void;
      onMessage(
        callback: (res: { data: string | ArrayBuffer }) => void,
      ): void;
      onError(callback: (err: { errMsg: string }) => void): void;
      onClose(callback: (res: { code: number; reason: string }) => void): void;
      close(opt?: { code?: number; reason?: string }): void;
    }
  }

  interface AppOption<TData extends Record<string, unknown>> {
    globalData: TData;
  }

  // 小程序没有内置 wx.compressImage；类型补丁
  interface Wx {
    compressImage(opt: {
      src: string;
      quality: number;
      compressedWidth: number;
      compressedHeight: number;
      success: (res: { tempFilePath: string }) => void;
      fail: (err: { errMsg: string }) => void;
    }): void;
  }
}

export {};