/**
 * FE-FIX-07 · PlanData.days 字段映射层
 * ──────────────────────────────────────────────────────────────
 * 真源：docs/architecture/api.yaml §PlanDay
 * 真源：docs/plan/frontend-fix-plan.md §FE-FIX-07
 *
 * 设计要点：
 *  - 后端 PlanDay schema 实际字段（openapi.yaml PlanDay）：
 *    day_index / duration_minutes / task / title / source / status
 *  - 历史后端字段（python snake_case 或 snake_case ↔ camelCase 误传）：
 *    day / phase / tasks / duration / meta
 *  - 前端 PreviewDay 内部契约字段（保留兼容）：
 *    day / title / meta / status
 *
 *  设计：mapPlanDay() 纯函数，输入容错（接受多种后端字段名），
 *  输出统一为 PreviewDay 类型，供 plan-delivery/index.ts 直接渲染。
 *
 * 调用方契约：
 *  - 所有 plan preview 解析走 mapPlanDay()，禁止在 page 文件内做字段猜测。
 *  - fallback param 提供离线 / 兜底数据。
 */

export interface PreviewDay {
  day: number;
  title: string;
  meta: string;
  status: 'completed' | 'active' | 'pending' | 'feedback';
  /** 阶段标识（p1/p2/p3），15h 原型专用 */
  phase?: 'p1' | 'p2' | 'p3';
}

/** 后端 PlanDay 可能字段集合（容错：覆盖 openapi.yaml 真值 + 历史 snake_case 残留）。 */
export interface RawPlanDay {
  day?: number;
  day_index?: number;
  phase?: number;
  duration?: number;
  duration_minutes?: number;
  task?: string | null;
  tasks?: Array<{ title?: string; video_id?: string; id?: string } | string> | null;
  title?: string;
  meta?: string;
  source?: string;
  status?: string | null;
  [key: string]: unknown;
}

const STATUS_MAP: Record<string, PreviewDay['status']> = {
  completed: 'completed',
  done: 'completed',
  active: 'active',
  in_progress: 'active',
  pending: 'pending',
  todo: 'pending',
  feedback: 'feedback',
  feedback_day: 'feedback',
  locked: 'pending',
};

/** 把后端 status 字符串归一化到 4 态。 */
export function normalizePlanStatus(rawStatus: string | null | undefined): PreviewDay['status'] {
  if (!rawStatus) return 'pending';
  return STATUS_MAP[rawStatus] ?? 'pending';
}

/** 从 RawPlanDay 抽 title：优先 task（含 video_id / title 解构），其次 title 字段。 */
function pickTitle(raw: RawPlanDay): string | null {
  if (typeof raw.title === 'string' && raw.title.length > 0) return raw.title;
  if (typeof raw.task === 'string' && raw.task.length > 0) return raw.task;
  // tasks: 数组可能是 [{title, video_id}] 或 [string]
  const tasks = Array.isArray(raw.tasks) ? raw.tasks : [];
  for (const item of tasks) {
    if (typeof item === 'string' && item.length > 0) return item;
    if (item && typeof item === 'object') {
      const obj = item as { title?: string; video_id?: string; id?: string };
      if (obj.title) return obj.title;
      if (obj.video_id) return obj.video_id;
      if (obj.id) return obj.id;
    }
  }
  return null;
}

/** 从 RawPlanDay 抽 duration_minutes。 */
function pickDurationMinutes(raw: RawPlanDay): number | null {
  if (typeof raw.duration_minutes === 'number') return raw.duration_minutes;
  if (typeof raw.duration === 'number') return raw.duration;
  // phase 在历史 schema 中可能充当"分钟数"（存疑 — 不可靠；只在 duration 缺失时使用）
  if (typeof raw.phase === 'number' && raw.phase > 0 && raw.phase < 240) return raw.phase;
  return null;
}

/**
 * 字段映射主函数。
 *
 * 优先级（day）：
 *  1. day_index（openapi.yaml PlanDay 真值）
 *  2. day（旧 snake_case 残留）
 *  3. fallbackDay
 *
 * 优先级（title）：
 *  1. title
 *  2. task / tasks[0].title
 *  3. fallbackDay.title
 *
 * 优先级（meta）：
 *  1. "{duration_minutes} 分钟 · {source}"
 *  2. fallbackDay.meta
 *
 * 优先级（status）：
 *  1. status（normalizePlanStatus）
 *  2. fallbackDay.status
 */
export function mapPlanDay(
  raw: RawPlanDay,
  fallbackDay: PreviewDay,
  fallbackDayIndex: number,
): PreviewDay {
  const day = raw.day_index ?? raw.day ?? fallbackDayIndex;
  const duration = pickDurationMinutes(raw);
  const title = pickTitle(raw) ?? fallbackDay.title;
  const baseMeta = duration != null ? `${duration} 分钟` : fallbackDay.meta;
  const source = typeof raw.source === 'string' && raw.source.length > 0 ? raw.source : null;
  const meta = source ? `${baseMeta} · ${source}` : baseMeta;
  const status = normalizePlanStatus(raw.status ?? null) ?? fallbackDay.status;
  return { day, title, meta, status, phase: fallbackDay.phase };
}

/** 批量映射：21 天占位 + 后端真实数据合并；缺位走 fallback。 */
export function mapPlanDays(
  raws: RawPlanDay[] | null | undefined,
  fallbacks: PreviewDay[],
): PreviewDay[] {
  const list = Array.isArray(raws) ? raws : [];
  return Array.from({ length: fallbacks.length }, (_, index) => {
    const raw = list[index];
    if (!raw) return fallbacks[index];
    return mapPlanDay(raw, fallbacks[index], index + 1);
  });
}