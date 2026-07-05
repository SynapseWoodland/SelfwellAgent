/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.2 P02 首页（今日打卡）
 * 设计稿: docs/design/figma-pixso-spec/pages/03-home.html
 * 后端端点:
 *   - openapi.yaml tag=users operationId=getCurrentUser
 *   - openapi.yaml tag=checkins operationId=getCheckinCalendar
 *   - openapi.yaml tag=plans operationId=getTodayPlan
 *
 * 本 Sprint 占位：展示 progress-ring + task-card 骨架 + 文案；
 * 真实数据接入在 SF1。
 */
interface TodayState {
  greeting: string;
  streak: number;
  todayDone: number;
  todayTotal: number;
  tasks: Array<{ id: string; title: string; subtitle: string; done: boolean }>;
}

Page({
  data: {
    greeting: '今天，慢慢来',
    streak: 0,
    percent: 0,
    taskCards: [] as Array<{
      id: string;
      title: string;
      subtitle: string;
      done: boolean;
    }>,
  } as TodayState,

  onLoad() {
    this.mockBootstrap();
  },

  onShow() {
    // 每次回到首页都重新拉一次（SF1 接入真实 API）
    this.mockBootstrap();
  },

  mockBootstrap() {
    // SF1 替换为真实 API 调用：
    //   getCurrentUser / getCheckinCalendar / getTodayPlan
    const total = 4;
    const done = 1;
    const greeting =
      new Date().getHours() < 12 ? '早安，慢慢来' : '晚安，今天辛苦了';
    const tasks = [
      { id: 't1', title: '冥想 5 分钟', subtitle: '专注呼吸，回到当下', done: true },
      { id: 't2', title: '拉伸肩颈', subtitle: '跟随视频，8 分钟', done: false },
      { id: 't3', title: '记录一段心情', subtitle: '今天发生了什么', done: false },
      { id: 't4', title: '喝水打卡', subtitle: '今天喝够 8 杯了吗', done: false },
    ];
    this.setData({
      greeting,
      streak: 7,
      percent: Math.round((done / total) * 100),
      taskCards: tasks,
    });
  },

  onTaskToggle(
    e: WechatMiniprogram.CustomEvent<{ id: string; done: boolean }>,
  ) {
    const { id, done } = e.detail;
    const list = (this.data.taskCards as TodayState['tasks']).map((t) =>
      t.id === id ? { ...t, done } : t,
    );
    const total = list.length;
    const completed = list.filter((t) => t.done).length;
    this.setData({
      taskCards: list,
      percent: total ? Math.round((completed / total) * 100) : 0,
    });
  },

  onGotoCheckin() {
    wx.navigateTo({ url: '/miniprogram/pages/checkin/index' });
  },

  onGotoAssistant() {
    wx.switchTab({ url: '/miniprogram/pages/assistant-home/index' });
  },
});