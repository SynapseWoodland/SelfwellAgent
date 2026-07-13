/**
 * V2 STYLE · pages/home 升版为「今天」Tab（PR-3 commit-1）
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-IA-pr-internal.md §PR-3 commit-1
 * 真源：docs/design/figma-pixso-spec/pages/15b-today-tab2.html
 *
 * 职责：
 *  - 抽屉 8 个管理入口（与 PR-5 子页路径对齐；不在 tabBar 内，必须 navigateTo）
 *  - 纯函数 getDrawCards()，便于 vitest 静态契约测试
 *
 * 为什么独立文件（与 pages/assistant-home/index.smart-body.ts 同模式）：
 *  1. home/index.ts 升级后结构复杂，抽屉卡片列表是静态纯数据，独立可测；
 *  2. 抽屉打开/关闭的 UI 副作用留在 index.ts（需要 setData + 调用状态），
 *     这里是纯数据源，不调 wx.showToast / wx.navigateTo 等副作用。
 *
 * 抽屉 8 项（按 15b-today-tab2.html 设计稿；PR-5 子页落地后会接进来）：
 *  - 用户档案  → /pages/profile-edit/index?mode=read（PR-5）
 *  - 我的时光  → /pages/record-album/index（PR-5）
 *  - 通知设置  → /pages/notification-settings/index（PR-5）
 *  - 隐私政策  → /pages/privacy-policy/index（PR-5）
 *  - 联系客服  → /pages/contact/index（PR-5）
 *  - 关于自愈  → /pages/about/index（PR-5）
 *  - 反馈日记  → /pages/feedback-diary/index（已存在）
 *  - 21 天方案  → /pages/plan-delivery/index（v2）
 */
export interface DrawerCard {
  id: string;
  title: string;
  subtitle: string;
  iconText: string;
  pagePath: string;
}

/**
 * 返回抽屉管理页 8 个入口卡片。
 * 纯函数：相同输入总是返回相同输出；无副作用、无 wx.* 调用。
 */
export function getDrawCards(): DrawerCard[] {
  return [
    {
      id: 'profile',
      title: '用户档案',
      subtitle: '查看与编辑',
      iconText: '◐',
      pagePath: '/pages/profile-edit/index?mode=read',
    },
    {
      id: 'time',
      title: '我的时光',
      subtitle: '看看你走过的痕迹',
      iconText: '◷',
      pagePath: '/pages/record-album/index',
    },
    {
      id: 'notification',
      title: '通知设置',
      subtitle: '提醒频次 / 时段',
      iconText: '◔',
      pagePath: '/pages/notification-settings/index',
    },
    {
      id: 'privacy',
      title: '隐私政策',
      subtitle: '数据导出 / 注销',
      iconText: '◑',
      pagePath: '/pages/privacy-policy/index',
    },
    {
      id: 'support',
      title: '联系客服',
      subtitle: '常见问题 / 反馈',
      iconText: '◓',
      pagePath: '/pages/contact/index',
    },
    {
      id: 'about',
      title: '关于自愈',
      subtitle: '版本与说明',
      iconText: '◔',
      pagePath: '/pages/about/index',
    },
    {
      id: 'feedback',
      title: '反馈日记',
      subtitle: '记录当下',
      iconText: '✎',
      pagePath: '/pages/feedback-diary/index',
    },
    {
      id: 'plan',
      title: '21 天方案',
      subtitle: '查看我的日历',
      iconText: '☷',
      pagePath: '/pages/plan-delivery/index',
    },
  ];
}

/**
 * 打开抽屉的副作用（保留纯函数导出，便于未来注入埋点）。
 * 当前实现：返回 true 表示应该打开，UI 副作用由 page.ts 触发。
 */
export function openDrawer(): boolean {
  return true;
}

/**
 * 关闭抽屉的副作用。
 */
export function closeDrawer(): boolean {
  return false;
}