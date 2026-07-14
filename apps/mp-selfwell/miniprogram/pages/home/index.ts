/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.2 P02 首页（今日打卡）
 * FIGMA  : docs/design/figma-pixso-spec/pages-v2/15b-today-tab2.html
 * API    :
 *   - openapi.yaml tag=users    operationId=getCurrentUser  GET  /users/me
 *   - openapi.yaml tag=checkins operationId=getCheckinCalendar GET /checkins/today
 *   - openapi.yaml tag=plans    operationId=getTodayPlan    GET  /plans/today
 *
 * PR-V2-C · pages/home 升版为「今天」Tab（V2 15b-today-tab2.html）：
 *  - 进度区 mint 渐变（ring 90px 左 + 问候打卡右）
 *  - plan-overview 卡片（day-strip 5 态 + phase-bar + phase-label）
 *  - task-section（今日小动作）
 *  - hug-section（米色渐变抱抱卡入口）
 *  - time-section（我的时光入口）
 *  - complete-overlay（打卡完成全屏遮罩）
 *  - drawer（drawer-overlay 组件，右侧滑入 80%，peek-tab）
 *
 * 真实接入：并发拉 users/me + checkins/today + plans/today，统一 setData；
 * 支持下拉刷新；token 失效跳回 login（§17.14）。
 *
 * SF1 强化（保留）：
 *  - `_inFlight` 标志位防 onShow + onPullDownRefresh + onLoad 重叠重复 bootstrap
 *  - 三接口任一失败不阻塞其他
 *  - 401 走单独的 fast-path，其余 ApiException 保留提示但不 reset jwt
 *  - streak 数显示前 clamp 到 [0, 9999]
 */
import { get, post, ApiException } from '../../utils/request';
import { STORAGE_KEYS } from '../../utils/config';
import type { UserMe, TodayPlan, CheckinToday, CreateCheckinResp } from '../../types/api';
import { getDrawCards } from './index.smart-body';

/** 抽屉卡片（含 icon 背景色） */
function buildDrawerCardsWithBg(): DrawerCardView[] {
  const iconBgs: Record<string, string> = {
    '智能管家': '#E0F0E5',
    '今日任务': '#F5E6D3',
    '智能分析': '#F5E6D3',
    '心情日记': '#F0D9C4',
    '蜕变广场': '#E0E0F0',
    '我的时光': '#F5E6D3',
    '通知设置': '#F0F2F5',
    '问问过去': '#D4C5E2',
    '用户档案': '#E0F0E5',
    '21 天方案': '#C7D8B9',
  };
  return getDrawCards().map((card) => ({
    ...card,
    iconBg: iconBgs[card.title] ?? '#F0F2F5',
  }));
}

interface TodayTaskView {
  id: string;
  title: string;
  subtitle: string;
  done: boolean;
  /** v2 新增：视频 URL（跳转详情页用） */
  videoUrl?: string;
  /** v2 新增：视频封面 URL */
  coverUrl?: string;
  /** v2 新增：视频时长（秒） */
  duration?: number;
  /** v2 新增：身体部位标签 */
  bodyPartTags?: string[];
}

/** 21 天方案 day-strip 单格状态（PR-V2-C 扩展为 5 态）。 */
interface DayStripCell {
  dayNumber: number;
  state: 'completed' | 'today' | 'missed' | 'future' | 'feedback';
}

interface DrawerCardView {
  id: string;
  title: string;
  subtitle: string;
  iconText: string;
  iconBg: string;
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
  totalMinutes: number;
  /** PR-V2-C · 21-day strip（5 态）。 */
  dayStrip: DayStripCell[];
  currentDayIndex: number;
  currentDay: number;
  phaseIndex: number;
  phaseDayStart: number;
  phaseDayEnd: number;
  /** 打卡完成全屏遮罩可见性。 */
  checkinComplete: boolean;
  /** 抽屉管理页可见性。 */
  drawerOpen: boolean;
  /** 抽屉管理卡片（含 iconBg）。 */
  drawerCards: DrawerCardView[];
  /** 抱抱卡是否禁用（未到领取日）。 */
  hugDisabled: boolean;
  /** 抱抱卡副标题。 */
  hugCardSubtitle: string;
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
    totalMinutes: 0,
    dayStrip: [],
    currentDayIndex: 0,
    currentDay: 1,
    phaseIndex: 1,
    phaseDayStart: 1,
    phaseDayEnd: 7,
    checkinComplete: false,
    drawerOpen: false,
    drawerCards: buildDrawerCardsWithBg(),
    hugDisabled: true,
    hugCardSubtitle: '明天可领',
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
        // v2 新增：透传视频字段（用于跳转 task-detail）
        videoUrl: t.video_url || '',
        coverUrl: t.cover_url || '',
        duration: t.duration_sec,
        bodyPartTags: t.body_part_tags || [],
      }));
      console.log('[home] taskCards loaded:', taskCards.map(t => ({ id: t.id, videoUrl: t.videoUrl })));
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

      // PR-V2-C · 21-day strip（5 态）：completed / today / missed / future / feedback
      const currentDay = Math.min(21, Math.max(1, streak || 1));
      const dayStrip: DayStripCell[] = Array.from({ length: 21 }, (_, i) => {
        const dayNum = i + 1;
        if (dayNum < currentDay) return { dayNumber: dayNum, state: 'completed' };
        if (dayNum === currentDay) return { dayNumber: dayNum, state: 'today' };
        return { dayNumber: dayNum, state: 'future' };
      });

      // 阶段计算（1-7 天→阶段1，8-14 天→阶段2，15-21 天→阶段3）
      const phaseIndex = currentDay <= 7 ? 1 : currentDay <= 14 ? 2 : 3;
      const phaseDayStart = phaseIndex === 1 ? 1 : phaseIndex === 2 ? 8 : 15;
      const phaseDayEnd = phaseIndex === 1 ? 7 : phaseIndex === 2 ? 14 : 21;

      // 抱抱卡（7/14/21 天可领）
      const hugDays = [7, 14, 21];
      const nextHugDay = hugDays.find((d) => d > currentDay) ?? 21;
      const daysUntilHug = nextHugDay - currentDay;
      const hugDisabled = daysUntilHug > 0;
      const hugCardSubtitle =
        daysUntilHug === 0
          ? '今日可领'
          : daysUntilHug === 1
            ? '明天可领'
            : `${daysUntilHug} 天后可领`;

      // task total minutes（plan 接口未提供，暂时默认 18 分钟）
      const totalMinutes = plan?.tasks
        ? plan.tasks.reduce((sum: number, t: { duration?: number }) => sum + (t.duration ?? 0), 0) || 18
        : 18;

      this.setData({
        greeting,
        nickname,
        streak,
        total,
        done,
        percent,
        taskCards,
        dayStrip,
        currentDayIndex: currentDay - 1,
        currentDay,
        phaseIndex,
        phaseDayStart,
        phaseDayEnd,
        totalMinutes,
        hugDisabled,
        hugCardSubtitle,
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

  /**
   * task-card 勾选框点击 → 仅更新本地状态，不调 API
   *
   * 语义：单任务"已完成标记"，不是"打卡"
   * 打卡（POST /checkins）统一由顶部「今日打卡」按钮 onToggleCheckin 触发
   */
  onTaskToggle(e: WechatMiniprogram.CustomEvent<{ id: string; done: boolean }>) {
    const { id, done } = e.detail;
    const list = this.data.taskCards.map((t) => (t.id === id ? { ...t, done } : t));
    const completed = list.filter((t) => t.done).length;
    this.setData({
      taskCards: list,
      done: completed,
      percent: this.data.total ? Math.round((completed / this.data.total) * 100) : 0,
    });
  },

  /**
   * v2 新增：task-card 卡片点击 → 跳转视频详情页
   * 打卡与看视频解耦：勾选框触发 toggle，卡片区域触发 tap
   */
  onTaskTap(e: WechatMiniprogram.CustomEvent<{ id: string; videoUrl?: string }>) {
    console.log('[home] onTaskTap received', e.detail);
    const { id, videoUrl } = e.detail;
    const task = this.data.taskCards.find((t) => t.id === id);
    if (!task) return;

    // 如果有视频 URL，跳转到视频详情页
    if (videoUrl) {
      console.log('[home] navigating to video detail', { taskId: id, videoUrl });
      const params = new URLSearchParams({
        taskId: id,
        title: encodeURIComponent(task.title),
        subtitle: encodeURIComponent(task.subtitle || ''),
        videoUrl: encodeURIComponent(videoUrl),
        coverUrl: encodeURIComponent(task.coverUrl || ''),
        duration: encodeURIComponent(task.duration ? `${Math.floor(task.duration / 60)} 分钟` : ''),
        tags: encodeURIComponent((task.bodyPartTags || []).join(',')),
      });
      wx.navigateTo({
        url: `/pages/task-detail/index?${params.toString()}`,
      });
    } else {
      // 没有视频 URL 时，显示提示
      console.log('[home] no videoUrl, showing toast');
      wx.showToast({ title: '暂无可用视频', icon: 'none' });
    }
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
   * 顶部「今日打卡」按钮 → 调用 POST /checkins 提交当天所有已完成任务
   * 语义：每日整体打卡（vs 勾选框仅本地标记）
   */
  onToggleCheckin() {
    // 如果已完成打卡，则取消（允许撤回）
    if (this.data.checkinComplete) {
      this.setData({ checkinComplete: false });
      return;
    }

    const doneIds = this.data.taskCards.filter((t) => t.done).map((t) => t.id);
    if (doneIds.length === 0) {
      wx.showToast({ title: '请先勾选已完成的动作', icon: 'none' });
      return;
    }

    const today = new Date().toISOString().slice(0, 10);
    post<CreateCheckinResp>('/checkins', { date: today, task_ids: doneIds })
      .then((res) => {
        this.setData({ checkinComplete: true });
        wx.showToast({ title: res.ack_text || '打卡成功', icon: 'success' });
        console.log('[home] checkin success, new streak:', res.new_streak);
      })
      .catch((err) => {
        console.warn('[home] checkin fail', err);
        const msg = err instanceof ApiException ? err.message : '打卡失败';
        wx.showToast({ title: msg, icon: 'none' });
      });
  },

  /**
   * PR-V2-C · day-strip 格点击 → 选中当天
   */
  onDayStripSelect(
    e: WechatMiniprogram.CustomEvent<{ index: number; day: DayStripCell }>,
  ) {
    const { index } = e.detail;
    this.setData({ currentDayIndex: index });
  },

  /**
   * PR-3 commit-1 · 抽屉卡片点击：跳对应子页。
   * 子页不在 tabBar 内，必须用 wx.navigateTo。
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