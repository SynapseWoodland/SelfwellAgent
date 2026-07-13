/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.2 P02 首页（今日打卡）
 * FIGMA  : docs/design/figma-pixso-spec/pages/15b-today-tab2.html
 * API    :
 *   - openapi.yaml tag=users    operationId=getCurrentUser  GET  /users/me
 *   - openapi.yaml tag=checkins operationId=getCheckinCalendar GET /checkins/today
 *   - openapi.yaml tag=plans    operationId=getTodayPlan    GET  /plans/today
 *
 * PR-3 commit-1 · pages/home 升版为「今天」Tab（V2 15b-today-tab2.html）：
 *  - 进度环 90px（PR-6 token --progress-ring-size）
 *  - 21-day strip（21 天方案 day-strip）
 *  - hug-section（抱抱卡入口）
 *  - time-section（我的时光入口）
 *  - drawer（管理页抽屉，drawer-card 8 个）
 *
 * 真实接入：并发拉 users/me + checkins/today + plans/today，统一 setData；
 * 支持下拉刷新；token 失效跳回 login（§17.14）。
 *
 * SF1 强化（保留）：
 *  - `_inFlight` 标志位防 onShow + onPullDownRefresh + onLoad 重叠重复 bootstrap
 *  - 三接口任一失败不阻塞其他
 *  - 401 走单独的 fast-path，其余 ApiException 保留提示但不 reset jwt
 *  - streak 数显示前 clamp 到 [0, 9999]
 *
 * PR-3 commit-1 新增：
 *  - getDrawCards() / openDrawer() / closeDrawer() 抽到 index.smart-body.ts
 *  - 抽屉管理页（drawer）8 个管理入口（与 PR-5 子页对齐）
 */
import { get, post, ApiException } from '../../utils/request';
import { STORAGE_KEYS } from '../../utils/config';
import type { UserMe, TodayPlan, CheckinToday, CreateCheckinResp } from '../../types/api';
import { getDrawCards } from './index.smart-body';

interface TodayTaskView {
  id: string;
  title: string;
  subtitle: string;
  done: boolean;
}

/** 21 天方案 day-strip 单格状态。PR-3 commit-1 新增。 */
interface DayStripCell {
  index: number;
  state: 'done' | 'today' | 'future';
}

interface DrawerCard {
  id: string;
  title: string;
  subtitle: string;
  iconText: string;
  pagePath: string;
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
  /** PR-3 commit-1 · 21-day strip（21 天方案 day-strip）。 */
  dayStrip: DayStripCell[];
  /** PR-3 commit-1 · 抽屉管理页可见性。 */
  drawerOpen: boolean;
  /** PR-3 commit-1 · 抽屉 8 个管理卡片。 */
  drawerCards: DrawerCard[];
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
    dayStrip: Array.from({ length: 21 }, (_, i) => ({
      index: i + 1,
      state: i < 1 ? 'today' : 'future',
    })),
    drawerOpen: false,
    drawerCards: getDrawCards(),
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

      // PR-3 commit-1 · 21-day strip：当前第几天走 done / today / future 三态。
      // 接口未直接给 day_index，按 streak 长度推断（streak=已坚持天数 = 当前第 N 天）。
      const currentDay = Math.min(21, Math.max(1, streak || 1));
      const dayStrip: DayStripCell[] = Array.from({ length: 21 }, (_, i) => {
        const idx = i + 1;
        if (idx < currentDay) return { index: idx, state: 'done' };
        if (idx === currentDay) return { index: idx, state: 'today' };
        return { index: idx, state: 'future' };
      });

      this.setData({
        greeting,
        nickname,
        streak,
        total,
        done,
        percent,
        taskCards,
        dayStrip,
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
    setTimeout(() => wx.reLaunch({ url: '/pages/login/index' }), 800);
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
    const today = new Date().toISOString().slice(0, 10);
    const doneIds = list.filter((t) => t.done).map((t) => t.id);
    post<CreateCheckinResp>('/checkins', { date: today, task_ids: doneIds }).catch((err) => {
      console.warn('[home] checkin sync fail', err);
      const rollback = this.data.taskCards.map((t) =>
        t.id === id ? { ...t, done: !done } : t,
      );
      const rollTotal = rollback.length;
      const rollDone = rollback.filter((t) => t.done).length;
      this.setData({
        taskCards: rollback,
        total: rollTotal,
        done: rollDone,
        percent: rollTotal ? Math.round((rollDone / rollTotal) * 100) : 0,
      });
      const msg = err instanceof ApiException ? err.message : '打卡失败';
      wx.showToast({ title: msg, icon: 'none' });
    });
  },

  onGotoCheckin() {
    wx.navigateTo({ url: '/pages/checkin/index' });
  },

  onGotoAssistant() {
    wx.switchTab({ url: '/pages/assistant-home/index' });
  },

  onGotoPlan() {
    wx.navigateTo({ url: '/pages/plan-delivery/index' });
  },

  // TODO: PR-A4-后续
  // 当前 home 页没有"查看全部 21 天"按钮（仅 "去打卡" / "找管家聊聊"）；
  // plan-delivery/index 设计作为 21 天方案查看入口，等视觉确认后补 bindtap；
  // 现保留 onGotoPlanTabs 作为后续 PR 的过渡接口。
  onGotoPlanTabs() {
    wx.navigateTo({ url: '/pages/plan-delivery/index' });
  },

  /** PR-3 commit-1 · 抱抱卡入口。 */
  onGotoShare() {
    wx.navigateTo({ url: '/pages/share-hug-card/index' });
  },

  /** PR-3 commit-1 · 我的时光入口（PR-5 record-album 子页落地后承接）。 */
  onGotoTimeAlbum() {
    wx.navigateTo({ url: '/pages/record-album/index' });
  },

  /** PR-3 commit-1 · 打开管理抽屉（drawer-card 8 项）。 */
  onOpenDrawer() {
    this.setData({ drawerOpen: true });
  },

  /** PR-3 commit-1 · 关闭管理抽屉。 */
  onCloseDrawer() {
    this.setData({ drawerOpen: false });
  },

  /**
   * PR-3 commit-1 · 抽屉卡片点击：跳对应子页。
   * 子页不在 tabBar 内，必须用 wx.navigateTo。
   * 抽屉背景点击也走 close 逻辑（外层 catchtap）。
   */
  onTapDrawerCard(e: WechatMiniprogram.BaseEvent) {
    const id = (e.currentTarget.dataset as { id?: string }).id;
    if (!id) return;
    const card = this.data.drawerCards.find((c) => c.id === id);
    if (!card) return;
    this.setData({ drawerOpen: false });
    wx.navigateTo({ url: card.pagePath });
  },
});