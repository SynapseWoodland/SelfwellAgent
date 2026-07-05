// app.ts — Selfwell 小程序入口
App<{globalData: {userInfo: WechatMiniprogram.UserInfo | null}}>({
  globalData: {
    userInfo: null,
  },
  onLaunch() {
    // 展示本地存储能力
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    // 登录态过期检查
    const token = wx.getStorageSync('jwt')
    if (!token) {
      wx.reLaunch({url: '/miniprogram/pages/login/index'})
    }
  },
  onShow() {
    // 小程序从后台进入前台
  },
  onHide() {
    // 小程序从前台进入后台
  },
})