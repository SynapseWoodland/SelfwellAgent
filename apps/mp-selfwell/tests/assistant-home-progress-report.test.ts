/**
 * PR-3 commit-2 · assistant-home 5 阶段 SSE 消费不退（回归锁）
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-IA-pr-internal.md §PR-3 commit-2 §契约
 * 真源：plans/v2-unified-parent.md §3.3「_stream_smart_analyze 5 阶段事件序列」
 *
 * 锁值 5 用例（与 PR-3 §"assistant-home-progress-report 5 阶段不退"对齐）：
 *  1. consumeAssistantStream 5 事件分支保留：progress / report / end / start / error
 *  2. applyAssistantProgress 纯函数：progress event → 更新 progress_card.percent + steps
 *  3. applyAssistantReport：report event → 把 directions 缓存到 _pendingReportDirections
 *  4. applyAssistantEnd：end event → 触发 renderAssistantReport（一次性渲染 report 气泡）
 *  5. presignAndUploadOneForAssistant 调用保留 + image_keys / body_parts schema 不变
 *
 * 与现有 jest `assistant-home-smart-body.test.ts` 区别：
 *  - jest 测：index.smart-body.ts 纯函数（prerequisite / body 构造）
 *  - vitest 测（本文件）：index.ts SSE 消费者静态契约（PR-3 commit-2 回归锁）
 *  - 不同测试层，互补不重叠
 *
 * 设计：本测试只做静态契约锁（grep index.ts 的关键字符串），不实际运行 SSE 流；
 * 真正端到端 SSE 测试需要 wx runtime + DOM，超出 vitest 单元可达范围。
 *
 * 为什么不做 function-body 提取：Page({ ... }) 内 method 的参数类型常含嵌套 `{}`
 * （如 `payload: { step?: number; percent?: number; label?: string }`），brace-match 复杂；
 * 文件级 grep 锁已足够保证契约不退。
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readAssistantTs(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'assistant-home', 'index.ts'),
    'utf-8',
  );
}

describe('PR-3 commit-2 · assistant-home 5 阶段 SSE 消费不退', () => {
  it('用例 1: consumeAssistantStream 5 事件分支保留（progress/report/end/start/error）', () => {
    const src = readAssistantTs();
    // 函数声明存在
    expect(src).toMatch(/async\s+consumeAssistantStream\s*\(/);
    // 5 阶段事件名分支（按 SSE event.name 字符串比对）必须全在
    expect(src).toMatch(/name\s*===\s*['"]progress['"]/);
    expect(src).toMatch(/name\s*===\s*['"]report['"]/);
    expect(src).toMatch(/name\s*===\s*['"]end['"]/);
    expect(src).toMatch(/name\s*===\s*['"]start['"]/);
    expect(src).toMatch(/name\s*===\s*['"]error['"]/);
    // start 事件注释保留（PR-A4 已落地的语义：连接已建，不动 UI）
    expect(src).toContain('start 事件只是');
  });

  it('用例 2: applyAssistantProgress 纯函数契约（progress event → 更新 percent + steps）', () => {
    const src = readAssistantTs();
    // 函数声明存在 + 接收 payload 参数
    expect(src).toMatch(/applyAssistantProgress\s*\(\s*payload\s*:/);
    // payload.step / payload.percent / payload.label 三个字段
    expect(src).toMatch(/payload\??\.\s*step/);
    expect(src).toMatch(/payload\??\.\s*percent/);
    // clamp percent 到 [0, 100]
    expect(src).toMatch(/Math\.max\(0,\s*Math\.min\(100/);
    // 设置 attachment.percent + steps
    expect(src).toMatch(/percent\s*:/);
    expect(src).toMatch(/steps\s*:/);
  });

  it('用例 3: applyAssistantReport 把 directions 缓存到 _pendingReportDirections（end 一次性渲染）', () => {
    const src = readAssistantTs();
    // 函数声明存在
    expect(src).toMatch(/applyAssistantReport\s*\(\s*payload\s*:/);
    // directions 缓存（end 触发渲染）
    expect(src).toContain('_pendingReportDirections');
    expect(src).toMatch(/payload\??\.\s*directions/);
  });

  it('用例 4: applyAssistantEnd 触发 renderAssistantReport（一次性渲染 report 气泡）', () => {
    const src = readAssistantTs();
    // 函数声明存在
    expect(src).toMatch(/applyAssistantEnd\s*\(\s*payload\s*:/);
    // 调用 renderAssistantReport（end 事件统一渲染入口）
    expect(src).toContain('renderAssistantReport');
    // medical_guarded 分支保留（兜底）
    expect(src).toContain('medical_guarded');
  });

  it('用例 5: presignAndUploadOneForAssistant 调用保留 + image_keys / body_parts schema 不变', () => {
    const src = readAssistantTs();
    // upload 链路调用点
    expect(src).toContain('presignAndUploadOneForAssistant');
    // 字段命名契约（snake_case 与后端 _validate_image_keys 白名单对齐）
    expect(src).toContain('imageKeys');
    expect(src).toContain('bodyParts');
    // body 中字段名为 snake_case（image_keys / body_parts）→ 后端 schema
    expect(src).toContain('image_keys');
    expect(src).toContain('body_parts');
    // SSE URL 走 POST + AssistantMessage endpoint
    expect(src).toContain('/assistant/sessions/');
  });
});