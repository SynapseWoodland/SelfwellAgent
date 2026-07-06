/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.2 P02 首页（今日打卡）
 * FIGMA  : docs/design/figma-pixso-spec/pages/03-home.html
 * API    :
 *   - openapi.yaml tag=users    operationId=getCurrentUser  GET  /users/me
 *   - openapi.yaml tag=checkins operationId=getCheckinCalendar GET /checkins/today
 *   - openapi.yaml tag=plans    operationId=getTodayPlan    GET  /plans/today
 *
 * 真实接入：并发拉 users/me + checkins/today + plans/today，统一 setData；
 * 支持下拉刷新；token 失效跳回 login（§17.14）。
 *
 * SF1 强化：
 *  - `_inFlight` 标志位防 onShow + onPullDownRefresh + onLoad 重叠重复 bootstrap
 *  - 三接口任一失败不阻塞其他（Sprint M1 后端 MOCK 友好）
 *  - 401 走单独的 fast-path，其余 ApiException 保留提示但不 reset jwt
 *  - streak 数显示前 clamp 到 [0, 9999]
 */
import { get, ApiException } from '../../utils/request';
import { STORAGE_KEYS } from '../../utils/config';
import type { UserMe, TodayPlan, CheckinToday } from '../../types/api';

interface TodayTaskView {
  id: string;
  title: string;
  subtitle: string;
  done: boolean;
}

interface HomeData {
  greeting: string;
  nickname: string;
  streak: number;
  percent: number;
  taskCards: TodayTaskView[];
  refreshing: boolean;
  loading: boolean;
  total: number;
  done: number;
}

interface HomeCustomState {
  _inFlight: boolean;
}

Page<HomeData, Record<string, never>, HomeCustomState>({
  data: {
    greeting: '今天，慢慢来',
    nickname: '',
    streak: 0,
    percent: 0,
    taskCards: [],
    refreshing: false,
    loading: true,
    total: 0,
    done: 0,
  },

  _inFlight: false,

  onLoad() {
    void this.bootstrap();
  },

  onShow() {
    // tabBar 切回也要重拉：M4 打卡后回首页反映最新状态
    void this.bootstrap();
  },

  onPullDownRefresh() {
    this.setData({ refreshing: true });
    void this.bootstrap().finally(() => {
      wx.stopPullDownRefresh();
      this.setData({ refreshing: false });
    });
  },

  async bootstrap(): Promise<void> {
    const self = this as unknown as HomeCustomState;
    if (self._inFlight) return;
    self._inFlight = true;

    try {
      let me: UserMe | null = null;
      let today: CheckinToday | null = null;
      let plan: TodayPlan | null = null;

      // 三接口并发，任一失败不阻塞其他
      const results = await Promise.allSettled([
        get<UserMe>('/users/me'),
        get<CheckinToday>('/checkins/today'),
        get<TodayPlan>('/plans/today'),
      ]);

      if (results[0].status === 'fulfilled') {
        me = results[0].value;
      } else if (
        results[0].status === 'rejected' &&
        (results[0].reason as ApiException)?.httpStatus === 401
      ) {
        this.handleTokenExpired();
        return;
      }
      if (results[1].status === 'fulfilled') today = results[1].value;
      if (results[2].status === 'fulfilled') plan = results[2].value;

      const doneIds = new Set(today?.done_task_ids || []);
      const taskCards: TodayTaskView[] = (plan?.tasks || []).map((t) => ({
        id: t.task_id,
        title: t.title,
        subtitle: t.subtitle,
        done: doneIds.has(t.task_id),
      }));
      const total = today?.total ?? taskCards.length;
      const done = today?.done ?? taskCards.filter((t) => t.done).length;
      const percent = total > 0 ? Math.round((done / total) * 100) : 0;
      const hour = new Date().getHours();
      const nickname = me?.nickname || '你';
      const streak = Math.max(0, Math.min(9999, me?.current_streak_days || 0));
      const greeting =
        hour < 6
          ? '夜深了，记得休息'
          : hour < 12
            ? `早安，${nickname}`
            : hour < 18
              ? `午安，${nickname}`
              : hour < 22
                ? `晚上好，${nickname}`
                : `夜深了，${nickname}`;

      this.setData({
        greeting,
        nickname,
        streak,
        total,
        done,
        percent,
        taskCards,
        loading: false,
      });
    } catch (e) {
      this.setData({ loading: false });
      console.warn('[home] bootstrap fail', e);
    } finally {
      (this as unknown as HomeCustomState)._inFlight = false;
    }
  },

  handleTokenExpired() {
    try {
      wx.removeStorageSync(STORAGE_KEYS.jwt);
      wx.removeStorageSync(STORAGE_KEYS.userId);
    } catch {
      /* ignore */
    }
    wx.showToast({ title: '登录已过期，请重新登录', icon: 'none' });
    setTimeout(() => wx.reLaunch({ url: '/miniprogram/pages/login/index' }), 800);
  },

  onTaskToggle(e: WechatMiniprogram.CustomEvent<{ id: string; done: boolean }>) {
    const { id, done } = e.detail;
    const list = this.data.taskCards.map((t) => (t.id === id ? { ...t, done } : t));
    const total = list.length;
    const completed = list.filter((t) => t.done).length;
    this.setData({
      taskCards: list,
      total,
      done: completed,
      percent: total ? Math.round((completed / total) * 100) : 0,
    });
  },

  onGotoCheckin() {
    wx.navigateTo({ url: '/miniprogram/pages/checkin/index' });
  },

  onGotoAssistant() {
    wx.switchTab({ url: '/miniprogram/pages/assistant-home/index' });
  },

  onGotoPlan() {
    wx.navigateTo({ url: '/miniprogram/pages/plan/index' });
  },
});
