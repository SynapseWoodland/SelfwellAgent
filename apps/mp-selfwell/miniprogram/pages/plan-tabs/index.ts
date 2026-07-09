/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.4 P04 21 天方案 Tab
 * 设计稿: docs/design/figma-pixso-spec/pages/07d-plan-tabs.html
 * 后端端点（PR-A3 落地后启用）：
 *   - GET /plans/current?view=today  （首页 + 详情）
 *   - GET /plans/current?view=all    （3 周周卡 + 21 天日格）
 *   - GET /plans/today?day={N}       （特定 N 天的 task 详情）
 *
 * 行为：
 *  1) onLoad 拉 view=today 数据，渲染当前阶段 + 今日详情
 *  2) 用户切到「全部 21 天」→ 拉 view=all（仅拉一次，缓存到 data._all）
 *  3) 全部视图点 day-cell → 切回 today 并加载该天详情
 */
import { get } from '../../utils/request';
import { PLAN_TABS_COPY } from '../../utils/copy';
import type {
  PlanAllViewData,
  PlanDayCell,
  PlanDayState,
  PlanWeek,
  TodayPlan,
} from '../../types/api';

interface TodayTaskView {
  id: string;
  title: string;
  subtitle: string;
  done: boolean;
}

interface PageData {
  /** 当前 tab：today / all */
  activeTab: 'today' | 'all';
  segToday: string;
  segAll: string;
  /** 当前阶段标题（如「第一阶段 · 习惯启动」） */
  stageTitle: string;
  weekProgressText: string;
  /** 「全部视图」3 周 21 天 */
  weeks: PlanWeek[];
  /** 「今日视图」今日任务详情 */
  todayTasks: TodayTaskView[];
  /** 当前选中的 day（仅 all 视图点击切换时使用） */
  selectedDay: number;
  loading: boolean;
  noPlan: boolean;
}

Page<PageData>({
  data: {
    activeTab: 'today',
    segToday: PLAN_TABS_COPY.segToday,
    segAll: PLAN_TABS_COPY.segAll,
    stageTitle: PLAN_TABS_COPY.week1,
    weekProgressText: PLAN_TABS_COPY.weekProgress(1),
    weeks: [],
    todayTasks: [],
    selectedDay: 1,
    loading: true,
    noPlan: false,
  },

  // 内部缓存 all 视图数据（避免二次拉取）
  privateAllCache: null as PlanAllViewData | null,
  // 内部缓存今日视图阶段等元数据
  privateTodayCache: null as TodayPlan | null,

  onLoad() {
    void this.loadToday();
  },

  onShow() {
    // 切回时刷新当天（打卡后回首页反映最新状态）
    if (this.privateAllCache) return;
    void this.loadToday();
  },

  async loadToday(): Promise<void> {
    try {
      const today = await get<TodayPlan | { plan_id?: string; day_index: number }>(
        '/plans/today',
      );
      const dayIndex = (today as { day_index?: number }).day_index ?? 1;
      this.privateTodayCache = today as TodayPlan;
      this.setData({
        selectedDay: dayIndex,
        stageTitle: this.resolveStageTitle(dayIndex),
        weekProgressText: PLAN_TABS_COPY.weekProgress(dayIndex),
        loading: false,
        noPlan: false,
      });
      await this.refreshTodayTasks(dayIndex);
    } catch (err) {
      console.warn('[plan-tabs] today fetch fail', err);
      // 没有方案 → 切到骨架态
      this.setData({
        loading: false,
        noPlan: true,
        todayTasks: [],
        stageTitle: PLAN_TABS_COPY.week1,
        weekProgressText: PLAN_TABS_COPY.weekProgress(1),
      });
    }
  },

  async refreshTodayTasks(dayIndex: number): Promise<void> {
    try {
      const resp = await get<TodayPlan>(`/plans/today?day=${dayIndex}`);
      const tasks = (resp?.tasks ?? []).map((t, i) => ({
        id: t.task_id ?? `${resp.plan_id ?? 'task'}-${dayIndex}-${i}`,
        title: t.title,
        subtitle: t.subtitle,
        done: t.done,
      }));
      this.setData({ todayTasks: tasks });
    } catch (err) {
      console.warn('[plan-tabs] today tasks fetch fail', err);
      this.setData({ todayTasks: [] });
    }
  },

  /** 切到「全部 21 天」tab */
  async onTapAllTab(): Promise<void> {
    if (this.data.activeTab === 'all') return;
    this.setData({ activeTab: 'all' });
    if (this.privateAllCache) {
      this.setData({ weeks: this.privateAllCache.weeks });
      return;
    }
    try {
      const all = await get<PlanAllViewData>('/plans/current?view=all');
      this.privateAllCache = all;
      const stageTitle = this.resolveStageTitle(all.current_day_index);
      const weekProgressText = PLAN_TABS_COPY.weekProgress(all.current_day_index);
      this.setData({
        weeks: all.weeks ?? [],
        stageTitle,
        weekProgressText,
      });
    } catch (err) {
      console.warn('[plan-tabs] all fetch fail, fallback', err);
      this.setData({ weeks: this.fallbackWeeks() });
    }
  },

  /** 切回「今日」tab */
  onTapTodayTab(): void {
    if (this.data.activeTab === 'today') return;
    this.setData({ activeTab: 'today' });
  },

  /** 点击 day-cell（仅 all 视图生效） */
  onTapDay(e: WechatMiniprogram.CustomEvent<{ day: number; state: PlanDayState }>): void {
    const day = e.detail?.day;
    const state = e.detail?.state;
    if (!day || state === 'locked') return;
    this.setData({
      activeTab: 'today',
      selectedDay: day,
      stageTitle: this.resolveStageTitle(day),
      weekProgressText: PLAN_TABS_COPY.weekProgress(day),
    });
    void this.refreshTodayTasks(day);
  },

  resolveStageTitle(currentDay: number): string {
    if (currentDay <= 7) return PLAN_TABS_COPY.week1;
    if (currentDay <= 14) return PLAN_TABS_COPY.week2;
    return PLAN_TABS_COPY.week3;
  },

  /** 空态 21 天 fallback（dev / mock 友好） */
  fallbackWeeks(): PlanWeek[] {
    const mk = (day: number, state: PlanDayState, phase: 1 | 2 | 3): PlanDayCell => ({
      day,
      state,
      tasks_count: state === 'locked' ? 0 : 1,
      phase,
    });
    const weeks: PlanWeek[] = [];
    for (let w = 1 as 1 | 2 | 3; w <= 3; w = (w + 1) as 1 | 2 | 3) {
      const phase: 1 | 2 | 3 = w;
      const startDay = (w - 1) * 7 + 1;
      const days: PlanDayCell[] = [];
      for (let d = 0 as 0 | 1 | 2 | 3 | 4 | 5 | 6; d < 7; d = ((d + 1) as 0 | 1 | 2 | 3 | 4 | 5 | 6)) {
        const day = startDay + (d as number);
        const state: PlanDayState =
          day < this.data.selectedDay ? 'done' : day === this.data.selectedDay ? 'today' : 'locked';
        days.push(mk(day, state, phase));
      }
      weeks.push({
        week_no: w,
        title: this.resolveStageTitle(w * 7),
        days,
      });
    }
    return weeks;
  },

  onPlanLoaded(_data: PlanAllViewData | { current_day_index: number; plan_id: string; view: 'today' }): void {
    /* 由具体 fetch 路径内部 setData；这里留接口供后续 PR 接入 */
  },

  onDayLoaded(dayData: TodayPlan): void {
    const tasks = (dayData.tasks ?? []).map((t, i) => ({
      id: `${dayData.plan_id}-${dayData.day_index}-${i}`,
      title: t.title,
      subtitle: t.subtitle,
      done: t.done,
    }));
    this.setData({ todayTasks: tasks });
  },

  onTapGenerate(): void {
    wx.switchTab({ url: '/pages/home/index' });
  },
});
