/**
 * FE-FIX-09 · RecallResponse.referenced_feedbacks 内联对象结构变更适配
 * ──────────────────────────────────────────────────────────────
 * 真源：docs/plan/frontend-fix-plan.md §FE-FIX-09
 * 真源：docs/architecture/api.yaml §RecallResponse（V1.1.1 BE-FIX-09 落地）
 *
 * 验收标准：
 *  - recall-flow/index.ts RecallResult 接口与 openapi.yaml RecallResponse 1:1 锁值
 *  - recall_id（替代旧 id）字段名锁定
 *  - referenced_feedbacks 是内联对象数组（id/body_part/snippet/feedback_type/photo_url）
 *  - referenced_photos 是内联对象数组（url/body_part/uploaded_at）
 *  - context_photos 是内联对象数组（url/caption）—— V1.1.1 起 array<{url, caption}>
 *  - 旧 AIMessageContextPhotos 对象结构（带 summary/directions/tags/injected_at）已删除
 *  - wxml 不再渲染 recall.context_photos.summary（旧假设）
 *
 * 设计要点：
 *  - 通过文本匹配 + interface 字段锁 双重验证
 *  - 不直接 import TS（与项目约定一致）；用 file read + regex
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const PAGE_DIR = join(__dirname, '..', 'miniprogram', 'pages', 'recall-flow');
const TS = readFileSync(join(PAGE_DIR, 'index.ts'), 'utf-8');
const WXML = readFileSync(join(PAGE_DIR, 'index.wxml'), 'utf-8');

describe('FE-FIX-09 · recall-flow RecallResponse 字段结构契约', () => {
  it('用例 1: RecallResult 含 recall_id 字段（替代旧 id）', () => {
    expect(TS).toMatch(/interface\s+RecallResult[\s\S]*recall_id:\s*string/);
    // 顶层 id 字段不应再作为 recall 标识符
    // （AIMessageContextPhotos 内的 id 是 feedback id，与 recall_id 不同，不在此断言范围）
  });

  it('用例 2: RecallResult 含 safety_passed 字段（Recall Safety 三层审查）', () => {
    expect(TS).toMatch(/interface\s+RecallResult[\s\S]*safety_passed\?:/);
  });

  it('用例 3: referenced_feedbacks 是 ReferencedFeedback[]（内联对象数组）', () => {
    expect(TS).toMatch(/interface\s+ReferencedFeedback[\s\S]*id:\s*string/);
    expect(TS).toMatch(/interface\s+ReferencedFeedback[\s\S]*body_part\?:\s*string\s*\|\s*null/);
    expect(TS).toMatch(/interface\s+ReferencedFeedback[\s\S]*snippet\?:\s*string/);
    expect(TS).toMatch(/interface\s+ReferencedFeedback[\s\S]*feedback_type\?:\s*string\s*\|\s*null/);
    expect(TS).toMatch(/interface\s+ReferencedFeedback[\s\S]*photo_url\?:\s*string\s*\|\s*null/);
    expect(TS).toMatch(/interface\s+ReferencedFeedback[\s\S]*created_at\?:\s*string\s*\|\s*null/);
    expect(TS).toMatch(/interface\s+RecallResult[\s\S]*referenced_feedbacks\?:\s*ReferencedFeedback\[\]/);
  });

  it('用例 4: referenced_photos 是 ReferencedPhoto[]（url / body_part / uploaded_at）', () => {
    expect(TS).toMatch(/interface\s+ReferencedPhoto[\s\S]*url:\s*string/);
    expect(TS).toMatch(/interface\s+ReferencedPhoto[\s\S]*body_part\?:\s*string\s*\|\s*null/);
    expect(TS).toMatch(/interface\s+ReferencedPhoto[\s\S]*uploaded_at\?:\s*string\s*\|\s*null/);
    expect(TS).toMatch(/interface\s+RecallResult[\s\S]*referenced_photos\?:\s*ReferencedPhoto\[\]/);
  });

  it('用例 5: context_photos 是 ContextPhoto[]（url / caption）—— V1.1.1 改为 array', () => {
    expect(TS).toMatch(/interface\s+ContextPhoto[\s\S]*url:\s*string/);
    expect(TS).toMatch(/interface\s+ContextPhoto[\s\S]*caption\?:\s*string\s*\|\s*null/);
    expect(TS).toMatch(/interface\s+RecallResult[\s\S]*context_photos\?:\s*ContextPhoto\[\]/);
  });

  it('用例 6: 旧 AIMessageContextPhotos 对象结构已删除（不再混用 recall 与 ai_message 上下文）', () => {
    expect(TS).not.toMatch(/interface\s+AIMessageContextPhotos/);
    expect(TS).not.toMatch(/interface\s+ContextDirection/);
    expect(TS).not.toMatch(/directions:\s*ContextDirection\[\]/);
    expect(TS).not.toMatch(/tags:\s*string\[\][\s\S]*injected_at/);
  });

  it('用例 7: wxml 不再渲染 recall.context_photos.summary（顶层 summary 替代）', () => {
    expect(WXML).not.toContain('recall.context_photos.summary');
    // summary 仍渲染，但走顶层 recall.summary
    expect(WXML).toContain('recall.summary');
  });

  it('用例 8: RecallResult 含 trigger / summary / encourage / created_at / days_offset', () => {
    expect(TS).toMatch(/interface\s+RecallResult[\s\S]*trigger:\s*string/);
    expect(TS).toMatch(/interface\s+RecallResult[\s\S]*summary\?:\s*string\s*\|\s*null/);
    expect(TS).toMatch(/interface\s+RecallResult[\s\S]*encourage\?:\s*string\s*\|\s*null/);
    expect(TS).toMatch(/interface\s+RecallResult[\s\S]*created_at\?:\s*string\s*\|\s*null/);
    expect(TS).toMatch(/interface\s+RecallResult[\s\S]*days_offset\?:/);
  });

  it('用例 9: POST /butler/recall 仍是入口端点 + body 字段对齐', () => {
    expect(TS).toContain("'/butler/recall'");
    expect(TS).toContain('{ trigger, days_offset: daysOffset }');
  });
});