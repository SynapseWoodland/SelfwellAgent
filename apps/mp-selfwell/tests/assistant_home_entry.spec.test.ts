/**
 * Selfwell 自愈 · 前端 RED 测试 — M5 入口卡 4 状态机 + 顶部回忆气泡
 * ───────────────────────────────────────────
 * 真源：
 * - docs/spec/SPEC-M5-persona-chat.md §3.5.1 入口卡 4 状态
 * - ADR-0017 Recall Safety
 * - apps/mp-selfwell/miniprogram/pages/assistant-home/index.{ts,wxml}
 *
 * 约束（不可绕过）：
 * - mock 4 张卡 × 4 状态副文案 + ⭐ 描边 class
 * - Day 7/14/21 触发时 wxml 顶部有回忆气泡
 * - 4 项 Chips 渲染：[智能分析] [今日·第 N 天] [聊聊今天] [查看对比]
 * - 顶部 [历史] [设置] 24x24 按钮
 * - 输入框 + 🎤 + 📷
 */

import { afterEach, describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// ─────────────────────────────────────────────────────────────────────────────
// 静态扫描：wxml 文本必须含 SPEC-M5 的关键文案（4 状态副文案）
// ─────────────────────────────────────────────────────────────────────────────
function readWxml(): string {
  return readFileSync(join(__dirname, '../miniprogram/pages/assistant-home/index.wxml'), 'utf-8');
}

describe('assistant-home wxml 契约 — 4 状态副文案 + ⭐', () => {
  it('wxml 包含 card1 smart_analyze 的 4 状态副文案', () => {
    const wxml = readWxml();
    expect(wxml).toContain('上传照片生成你的画像');   // not_started
    expect(wxml).toContain('正在为你生成画像');      // in_progress
    expect(wxml).toContain('已生成你的画像');         // completed
    expect(wxml).toContain('离上次互动有点久了');    // inactive_7d
  });

  it('wxml 包含 ⭐ 描边 class 或组件 highlight 占位', () => {
    const wxml = readWxml();
    // 至少包含 highlight 概念（class 或 wx:if），不强制具体名字
    const hasHighlightClass = /class="[^"]*highlight[^"]*"/.test(wxml)
      || /is-highlight|is_star|starred/.test(wxml)
      || /\{\{\s*item\.highlight\s*\}\}/.test(wxml);
    expect(hasHighlightClass).toBe(true);
  });
});

describe('assistant-home wxml 契约 — Chips 4 项 + 顶部按钮', () => {
  it('wxml 包含 4 项 Chips（智能分析 / 今日·第N天 / 聊聊今天 / 查看对比）', () => {
    const wxml = readWxml();
    expect(wxml).toContain('智能分析');
    expect(wxml).toContain('今日');
    expect(wxml).toContain('聊聊今天');
    expect(wxml).toContain('查看对比');
  });

  it('wxml 包含顶部 [历史] [设置] 按钮', () => {
    const wxml = readWxml();
    expect(wxml).toContain('历史');
    expect(wxml).toContain('设置');
  });

  it('wxml 包含输入框 + 🎤 麦克风 + 📷 相机', () => {
    const wxml = readWxml();
    // 至少包含图标占位（cemoji / iconfont / 文本）
    expect(wxml).toMatch(/🎤|麦克风|录音|voice|microphone/);
    expect(wxml).toMatch(/📷|拍照|照片|相机|photo|camera/);
  });
});

describe('assistant-home wxml 契约 — Day N 顶部回忆气泡', () => {
  it('wxml 包含回忆气泡 hook（Day 7/14/21 触发器）', () => {
    const wxml = readWxml();
    // 至少包含回忆气泡的占位元素
    expect(wxml).toMatch(/回忆气泡|recall_bubble|recallBubble|recall-tip/i);
  });

  it('wxml 不渲染 mock habitStreak 字段（ADR-0017 §3.5）', () => {
    const wxml = readWxml();
    expect(wxml).not.toContain('habitStreak');
    expect(wxml).not.toContain('habit_streak');
  });
});

describe('assistant-home wxml 契约 — 不评判基线问候文案', () => {
  it('基线问候文案不含违规短语', () => {
    const wxml = readWxml();
    const forbidden = ['坚持', '真棒', '你比之前', '打败', '排名', '效果显现'];
    for (const phrase of forbidden) {
      expect(wxml).not.toContain(phrase);
    }
  });
});

afterEach(() => {
  /* cleanup */
});
