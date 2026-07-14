/**
 * FE-FIX-07 · services/plan.ts 字段映射层单测
 * ──────────────────────────────────────────────────────────────
 * 真源：docs/plan/frontend-fix-plan.md §FE-FIX-07
 * 真源：docs/api/openapi.yaml §PlanDay
 *
 * 验收标准：
 *  - mapPlanDay 把后端 PlanDay（day_index/duration_minutes/task/title/source/status）
 *    正确转换为前端 PreviewDay（day/title/meta/status）
 *  - 容错：兼容旧字段 day/phase/tasks/duration/meta
 *  - 缺位 fallback：title/meta/status 缺时降级到 fallback
 *  - mapPlanDays 批量：长度对齐 fallbacks
 *  - plan-delivery/index.ts loadPreview 走 mapPlanDays
 */
import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

import {
  mapPlanDay,
  mapPlanDays,
  normalizePlanStatus,
  type PreviewDay,
  type RawPlanDay,
} from '../miniprogram/services/plan';

const SAMPLE_FALLBACK: PreviewDay = {
  day: 1,
  title: 'fallback-title',
  meta: '10 分钟 · 阶段 1',
  status: 'pending',
};

describe('FE-FIX-07 · services/plan.ts 字段映射层', () => {
  describe('normalizePlanStatus', () => {
    it('已知 status 映射正确', () => {
      expect(normalizePlanStatus('completed')).toBe('completed');
      expect(normalizePlanStatus('done')).toBe('completed');
      expect(normalizePlanStatus('active')).toBe('active');
      expect(normalizePlanStatus('in_progress')).toBe('active');
      expect(normalizePlanStatus('pending')).toBe('pending');
      expect(normalizePlanStatus('feedback')).toBe('feedback');
      expect(normalizePlanStatus('locked')).toBe('pending');
    });
    it('未知 / null / undefined 兜底 pending', () => {
      expect(normalizePlanStatus(null)).toBe('pending');
      expect(normalizePlanStatus(undefined)).toBe('pending');
      expect(normalizePlanStatus('')).toBe('pending');
      expect(normalizePlanStatus('mystery_state')).toBe('pending');
    });
  });

  describe('mapPlanDay · openapi.yaml PlanDay 真值', () => {
    it('day_index / duration_minutes / task / source / status 全部生效', () => {
      const raw: RawPlanDay = {
        day_index: 5,
        duration_minutes: 8,
        task: '收下巴训练',
        source: 'video_pool',
        status: 'completed',
      };
      const out = mapPlanDay(raw, SAMPLE_FALLBACK, 1);
      expect(out.day).toBe(5);
      expect(out.title).toBe('收下巴训练');
      expect(out.meta).toBe('8 分钟 · video_pool');
      expect(out.status).toBe('completed');
    });

    it('title 字段优先级高于 task', () => {
      const raw: RawPlanDay = {
        day_index: 7,
        title: '肩颈放松（高优）',
        task: 'video_007',
        source: 'video_pool',
      };
      const out = mapPlanDay(raw, SAMPLE_FALLBACK, 1);
      expect(out.title).toBe('肩颈放松（高优）');
    });
  });

  describe('mapPlanDay · 历史 snake_case 字段容错', () => {
    it('day（旧 snake_case）兼容', () => {
      const raw: RawPlanDay = { day: 12, title: '肩胛稳定' };
      expect(mapPlanDay(raw, SAMPLE_FALLBACK, 99).day).toBe(12);
    });
    it('phase 当 duration_minutes 缺失时充当分钟数（1..240 区间）', () => {
      const raw: RawPlanDay = { day_index: 3, phase: 15, title: '面部按摩' };
      const out = mapPlanDay(raw, SAMPLE_FALLBACK, 1);
      expect(out.meta).toBe('15 分钟');
    });
    it('duration（旧字段）兼容', () => {
      const raw: RawPlanDay = { day_index: 4, duration: 12, title: '面部循环' };
      expect(mapPlanDay(raw, SAMPLE_FALLBACK, 1).meta).toBe('12 分钟');
    });
    it('tasks: 数组中是 {title, video_id} 对象时抽 title', () => {
      const raw: RawPlanDay = {
        day_index: 6,
        tasks: [{ title: '睡前舒缓', video_id: 'v006' }],
      };
      expect(mapPlanDay(raw, SAMPLE_FALLBACK, 1).title).toBe('睡前舒缓');
    });
    it('tasks: 数组中是 string 时抽 string', () => {
      const raw: RawPlanDay = {
        day_index: 6,
        tasks: ['string-title-fallback'],
      };
      expect(mapPlanDay(raw, SAMPLE_FALLBACK, 1).title).toBe('string-title-fallback');
    });
  });

  describe('mapPlanDay · 缺位 fallback', () => {
    it('day / day_index 全缺 → 走 fallbackDayIndex（1-based）', () => {
      const out = mapPlanDay({}, SAMPLE_FALLBACK, 13);
      expect(out.day).toBe(13);
    });
    it('title / task 全缺 → fallback.title', () => {
      const out = mapPlanDay({}, SAMPLE_FALLBACK, 1);
      expect(out.title).toBe(SAMPLE_FALLBACK.title);
    });
    it('duration / phase 全缺 → fallback.meta', () => {
      const out = mapPlanDay({ day_index: 1 }, SAMPLE_FALLBACK, 1);
      expect(out.meta).toBe(SAMPLE_FALLBACK.meta);
    });
    it('status 缺 / 未知 → fallback.status', () => {
      const out = mapPlanDay({}, SAMPLE_FALLBACK, 1);
      expect(out.status).toBe(SAMPLE_FALLBACK.status);
    });
  });

  describe('mapPlanDays · 批量', () => {
    it('长度对齐 fallbacks.length（21 天）', () => {
      const fallbacks = Array.from({ length: 21 }, (_, i) => ({
        day: i + 1,
        title: `fallback-${i + 1}`,
        meta: '10 分钟',
        status: 'pending' as const,
      }));
      const raws: RawPlanDay[] = [
        { day_index: 1, duration_minutes: 8, title: 'day1', source: 'video_pool' },
      ];
      const out = mapPlanDays(raws, fallbacks);
      expect(out).toHaveLength(21);
      expect(out[0].day).toBe(1);
      expect(out[0].title).toBe('day1');
      expect(out[0].meta).toBe('8 分钟 · video_pool');
      // 未填位走 fallback
      expect(out[1].title).toBe('fallback-2');
    });
    it('raws = null / undefined 全部走 fallback', () => {
      const fallbacks = Array.from({ length: 3 }, (_, i) => ({
        day: i + 1,
        title: `fb-${i + 1}`,
        meta: 'm',
        status: 'pending' as const,
      }));
      expect(mapPlanDays(null, fallbacks)).toEqual(fallbacks);
      expect(mapPlanDays(undefined, fallbacks)).toEqual(fallbacks);
    });
  });

  describe('FE-FIX-07 集成契约锁', () => {
    it('plan-delivery/index.ts 必须调用 mapPlanDays', () => {
      const ts = readFileSync(
        join(__dirname, '..', 'miniprogram', 'pages', 'plan-delivery', 'index.ts'),
        'utf-8',
      );
      expect(ts).toMatch(/import\s*\{[^}]*mapPlanDays[^}]*\}\s*from\s*['"]\.\.\/\.\.\/services\/plan['"]/);
      expect(ts).toContain('mapPlanDays(preview.days, fallbacks)');
    });
    it('services/plan.ts 必须存在', () => {
      expect(existsSync(
        join(__dirname, '..', 'miniprogram', 'services', 'plan.ts'),
      )).toBe(true);
    });
    it('plan-delivery/index.ts onGoToday 走 getHomeTabUrl()（FE-FIX-06 联动）', () => {
      const ts = readFileSync(
        join(__dirname, '..', 'miniprogram', 'pages', 'plan-delivery', 'index.ts'),
        'utf-8',
      );
      expect(ts).toContain('getHomeTabUrl()');
      // onGoToday 内不允许硬编码 /pages/home/index
      const m = ts.match(/onGoToday\s*\(\s*\)\s*\{([\s\S]*?)\n\s*\}\s*,?/);
      const body = m?.[1] ?? '';
      expect(body).not.toContain("'/pages/home/index'");
    });
  });
});