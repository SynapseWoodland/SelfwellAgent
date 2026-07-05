/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.6 P11 我的
 * 设计稿: docs/design/figma-pixso-spec/pages/11-profile.html
 * 后端端点:
 *   - openapi.yaml tag=users operationId=getCurrentUser
 *   - openapi.yaml tag=users operationId=updatePushToken
 *
 * 占位：头像 + 昵称 + 完成天数 + 进度环 + 设置列表。
 */
Page({
  data: {
    nickname: '自愈用户',
    streak: 7,
    percent: 33,
    settings: [
      { id: 'profile', label: '用户档案' },
      { id: 'notification', label: '通知设置' },
      { id: 'about', label: '关于自愈' },
      { id: 'privacy', label: '隐私政策' },
      { id: 'support', label: '联系客服' },
    ],
  },

  onLoad() {
    // SF1 接入 getCurrentUser
  },

  onGotoShare() {
    wx.navigateTo({ url: '/miniprogram/pages/share-hug-card/index?day=7' });
  },
});