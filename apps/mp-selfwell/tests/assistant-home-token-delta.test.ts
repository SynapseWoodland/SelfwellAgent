/**
 * PR-3 commit-3 · token_delta SSE consumer（chat 打字机）
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-IA-pr-internal.md §PR-3 commit-3 §契约
 * 真源：plans/v2-unified-parent.md §2.3 §Sprint 2 chat token_delta（vision-pipeline Sprint 2）
 *
 * 锁值 3 用例（与 PR-3 §"assistant-home-token-delta 3 用例"对齐）：
 *  1. consumeAssistantStream 新增 token_delta 事件分支
 *  2. applyTokenDelta(data) 方法存在 + 拼接逻辑（last.answer.text += token）
 *  3. runChatStream 走 SSE chat 模式（无 image_keys），不调原 post<{reply}> 同步路径
 *
 * 与现有 jest `assistant-home-smart-body.test.ts` 区别：
 *  - jest 测：index.smart-body.ts 纯函数（prerequisite / body 构造）
 *  - vitest 测（本文件）：index.ts token_delta 消费者静态契约（PR-3 commit-3 锁）
 *  - 不同测试层，互补不重叠
 *
 * 设计：本测试只做静态契约锁（grep index.ts 的关键字符串），不实际运行 SSE 流。
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

describe('PR-3 commit-3 · token_delta SSE consumer (chat 打字机)', () => {
  it('用例 1: consumeAssistantStream 新增 token_delta 事件分支', () => {
    const src = readAssistantTs();
    // 新增的 token_delta 分支（紧跟 start 分支后）
    expect(src).toMatch(/name\s*===\s*['"]token_delta['"]/);
    // 分支体调用 applyTokenDelta
    expect(src).toMatch(/this\.applyTokenDelta\(evt\.data\)/);
    // 注释说明：smart_analyze 模式不发 token_delta
    expect(src).toMatch(/token_delta|smart_analyze/);
  });

  it('用例 2: applyTokenDelta(data) 方法存在 + 拼接逻辑', () => {
    const src = readAssistantTs();
    // 方法存在 + 接收 payload 参数
    expect(src).toMatch(/applyTokenDelta\s*\(\s*payload\s*:/);
    // 拼接逻辑：把 token 增量拼接到 last.text
    expect(src).toMatch(/last\.text\s*\|\|\s*['"]['"]/);
    // nextText = lastText + token
    expect(src).toMatch(/const\s+nextText\s*=/);
    // 防御：token 必须是 string 且非空
    expect(src).toMatch(/typeof\s+payload\??\.\s*token\s*===\s*['"]string['"]/);
    // 仅在 state === 'answer' 时生效
    expect(src).toMatch(/state\s*!==\s*['"]answer['"]/);
  });

  it('用例 3: chat 模式改 SSE（无 image_keys），不再 post<{reply}> 同步等', () => {
    const src = readAssistantTs();
    // 新增 runChatStream 方法
    expect(src).toMatch(/async\s+runChatStream\s*\(\s*opts\s*:/);
    // runChatStream 调 consumeSse（与 runSmartAnalyze 同 SSE 框架）
    expect(src).toMatch(/runChatStream[\s\S]{0,2000}consumeSse/);
    // body 不含 image_keys（chat 模式无图）
    const chatMatch = src.match(/runChatStream\s*\([^)]*\)\s*:?\s*[^{}]*\{/);
    expect(chatMatch).toBeTruthy();
    const chatBodyStart = chatMatch!.index! + chatMatch![0].length - 1;
    // brace-match
    let depth = 0;
    let bodyEnd = chatBodyStart;
    for (let i = chatBodyStart; i < src.length; i++) {
      if (src[i] === '{') depth++;
      else if (src[i] === '}') {
        depth--;
        if (depth === 0) {
          bodyEnd = i + 1;
          break;
        }
      }
    }
    const chatBody = src.slice(chatBodyStart, bodyEnd);
    expect(chatBody).toContain('consumeSse');
    expect(chatBody).not.toContain('imageKeys');
    expect(chatBody).not.toContain('image_keys');
    // onSend chat 模式调用 runChatStream
    expect(src).toMatch(/this\.runChatStream\s*\(/);
    // 原 post<{reply}> 同步路径从 onSend 默认分支移除（保留 medical_guarded / A 类路由分支不受影响）
    // 检查 onSend 默认 chat 分支已不再含 post<{reply: string; ...}>
    const onSendMatch = src.match(/async\s+onSend\s*\(\s*\)\s*:?\s*[^{}]*\{/);
    expect(onSendMatch).toBeTruthy();
    const onSendStart = onSendMatch!.index! + onSendMatch![0].length - 1;
    let d2 = 0;
    let onSendEnd = onSendStart;
    for (let i = onSendStart; i < src.length; i++) {
      if (src[i] === '{') d2++;
      else if (src[i] === '}') {
        d2--;
        if (d2 === 0) {
          onSendEnd = i + 1;
          break;
        }
      }
    }
    const onSendBody = src.slice(onSendStart, onSendEnd);
    // onSend 调 runChatStream 替代原同步 post
    expect(onSendBody).toContain('runChatStream');
    // 同步 post<{reply; route; medicalGuarded}> 不在 onSend 默认 chat 分支了
    // （允许它在 medical_guarded / A 路由分支的兜底路径上）
    // 我们检查最直接的字面：onSend 内不含 "post<{reply" 子串模式
    expect(onSendBody).not.toMatch(/post<\{\s*reply\s*:/);
  });
});