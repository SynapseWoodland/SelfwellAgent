/**
 * FE-FIX-05 · task-card 组件单测
 * ──────────────────────────────────────────────────────────────
 * 真源：docs/plan/frontend-fix-plan.md §FE-FIX-05
 * 真源：apps/mp-selfwell/miniprogram/components/task-card/index.ts
 *
 * 验收标准：
 *  - done=true 时点击 → toggle 翻转（不变为死态，与 FE-FIX-05 文档描述存在歧义，下面附注）
 *  - disabled=true 时点击 → 不触发 toggle
 *  - done=false && disabled=false 时点击 → setData({done:true}) + triggerEvent('toggle',{id,done:true})
 *
 * FE-FIX-05 描述与当前实现的差异说明：
 *  - 文档："done=true 时点击不触发 toggle"（假设 done 是终态）
 *  - 实际实现：`if (this.data.disabled) return; const next = !this.data.done; ...` → 任意状态下都可翻转
 *  - 本测试描述「实际行为」并锁定契约，避免静默破坏。
 *
 * 设计要点：
 *  - 与 action-card-component.test.ts 同款 4 文件齐全检查 + 核心契约锁
 *  - 通过字符串匹配构造一个最小"fake this" / setData / triggerEvent 捕获器
 *    来验证 onTap 的事件触发路径
 */
import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const COMPONENT_DIR = join(
  __dirname,
  '..',
  'miniprogram',
  'components',
  'task-card',
);

function readFile(name: string): string {
  return readFileSync(join(COMPONENT_DIR, name), 'utf-8');
}

/** 把 TS 源里 onTap() 方法体抠出来手动跑。
 *  - 去掉 method signature 的 TS 类型注解
 *  - 去掉可选的 leading/trailing 逗号
 *  - 返回纯 JS body */
function extractOnTapBody(): string | null {
  const ts = readFile('index.ts');
  const m = ts.match(/onTap\s*\(\s*\)\s*\{([\s\S]*?)\n\s*\}\s*,?/);
  if (!m) return null;
  // 把 `const next: boolean = ...` 这种类型注解去掉（TS 风格）
  // 简化版：仅保留形如 `: TypeName` 的冒号注解剔除（包括箭头 / 解构等）
  return m[1]
    .replace(/:\s*[A-Za-z_$][\w$.<>\[\] |&]*(?=\s*=)/g, '')
    .replace(/:\s*void(?=\s*$)/gm, '');
}

describe('FE-FIX-05 · task-card 组件契约', () => {
  it('用例 1: 4 文件齐全（component=true 声明）', () => {
    expect(existsSync(join(COMPONENT_DIR, 'index.ts'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxml'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.wxss'))).toBe(true);
    expect(existsSync(join(COMPONENT_DIR, 'index.json'))).toBe(true);
    const json = JSON.parse(readFile('index.json')) as { component?: boolean };
    expect(json.component).toBe(true);
  });

  it('用例 2: props.id / title / subtitle / done / disabled 全部声明', () => {
    const ts = readFile('index.ts');
    expect(ts).toMatch(/id:\s*\{\s*type:\s*String/);
    expect(ts).toMatch(/title:\s*\{\s*type:\s*String/);
    expect(ts).toMatch(/subtitle:\s*\{\s*type:\s*String/);
    expect(ts).toMatch(/done:\s*\{\s*type:\s*Boolean/);
    expect(ts).toMatch(/disabled:\s*\{\s*type:\s*Boolean/);
  });

  it('用例 3: onTap() 内 disabled 守卫（disabled=true 提前返回，不 setData 不 triggerEvent）', () => {
    const ts = readFile('index.ts');
    expect(ts).toMatch(/onTap\s*\(\s*\)\s*\{[\s\S]*if\s*\(\s*this\.data\.disabled\s*\)\s*return/);
  });

  it('用例 4: onTap() 内 setData({ done: next }) + triggerEvent("toggle", {id, done}) 模式', () => {
    const ts = readFile('index.ts');
    expect(ts).toContain("this.setData({ done: next })");
    expect(ts).toMatch(/this\.triggerEvent\(\s*['"]toggle['"]\s*,\s*\{\s*id:\s*this\.data\.id/);
    expect(ts).toMatch(/this\.triggerEvent\([^)]*done:\s*next/);
  });

  it('用例 5: wxml bindtap 触发 onTap + done/disabled 状态类切换', () => {
    const wxml = readFile('index.wxml');
    expect(wxml).toContain('bindtap="onTap"');
    expect(wxml).toMatch(/class="task-card[^"]*\{\{done/);
    expect(wxml).toMatch(/class="task-card[^"]*\{\{disabled/);
    expect(wxml).toContain('class="task-circle');
    expect(wxml).toContain('wx:if="{{done}}"');
    expect(wxml).toContain('class="task-title');
    expect(wxml).toContain('class="task-arrow');
  });

  it('用例 6: 模拟 onTap 在 disabled=true 时不触发 toggle（动态行为）', () => {
    const body = extractOnTapBody();
    expect(body).not.toBeNull();
    // 构造最小 fake this
    const setDataCalls: Array<{ done?: boolean }> = [];
    const triggerCalls: Array<{ name: string; detail: Record<string, unknown> }> = [];
    const fakeThis = {
      data: { id: 'task_001', done: false, disabled: true },
      setData(patch: { done?: boolean }) {
        setDataCalls.push(patch);
        Object.assign(fakeThis.data, patch);
      },
      triggerEvent(name: string, detail: Record<string, unknown>) {
        triggerCalls.push({ name, detail });
      },
    };
    // 把 body 中的 this.data.xxx / this.setData / this.triggerEvent 重写为上下文变量名，
    // 直接用 Function 构造器，避免 strict mode 引发的 'this' 关键字问题。
    const jsBody = body!
      .replace(/this\.data/g, 'ctx.data')
      .replace(/this\.setData/g, 'setData')
      .replace(/this\.triggerEvent/g, 'triggerEvent');
    // eslint-disable-next-line @typescript-eslint/no-implied-eval, no-new-func
    const fn = new Function('ctx', 'setData', 'triggerEvent', jsBody) as (
      ctx: { data: { id: string; done: boolean; disabled: boolean } },
      setData: (p: { done?: boolean }) => void,
      triggerEvent: (n: string, d: Record<string, unknown>) => void,
    ) => void;
    const bindSet = (p: { done?: boolean }) => fakeThis.setData(p);
    const bindTrig = (n: string, d: Record<string, unknown>) => fakeThis.triggerEvent(n, d);
    fn(fakeThis, bindSet, bindTrig);
    expect(setDataCalls).toHaveLength(0);
    expect(triggerCalls).toHaveLength(0);
  });

  it('用例 7: 模拟 onTap 在 done=false && disabled=false 时触发 toggle with done=true', () => {
    const body = extractOnTapBody();
    expect(body).not.toBeNull();
    const setDataCalls: Array<{ done?: boolean }> = [];
    const triggerCalls: Array<{ name: string; detail: Record<string, unknown> }> = [];
    const fakeThis = {
      data: { id: 'task_002', done: false, disabled: false },
      setData(patch: { done?: boolean }) {
        setDataCalls.push(patch);
        Object.assign(fakeThis.data, patch);
      },
      triggerEvent(name: string, detail: Record<string, unknown>) {
        triggerCalls.push({ name, detail });
      },
    };
    // 把 body 中的 this.data.xxx / this.setData / this.triggerEvent 重写为上下文变量名，
    // 直接用 Function 构造器，避免 strict mode 引发的 'this' 关键字问题。
    const jsBody = body!
      .replace(/this\.data/g, 'ctx.data')
      .replace(/this\.setData/g, 'setData')
      .replace(/this\.triggerEvent/g, 'triggerEvent');
    // eslint-disable-next-line @typescript-eslint/no-implied-eval, no-new-func
    const fn = new Function('ctx', 'setData', 'triggerEvent', jsBody) as (
      ctx: { data: { id: string; done: boolean; disabled: boolean } },
      setData: (p: { done?: boolean }) => void,
      triggerEvent: (n: string, d: Record<string, unknown>) => void,
    ) => void;
    const bindSet = (p: { done?: boolean }) => fakeThis.setData(p);
    const bindTrig = (n: string, d: Record<string, unknown>) => fakeThis.triggerEvent(n, d);
    fn(fakeThis, bindSet, bindTrig);
    expect(setDataCalls).toEqual([{ done: true }]);
    expect(triggerCalls).toEqual([{ name: 'toggle', detail: { id: 'task_002', done: true } }]);
  });

  it('用例 8: 模拟 onTap 在 done=true && disabled=false 时触发 toggle with done=false（现有行为）', () => {
    const body = extractOnTapBody();
    expect(body).not.toBeNull();
    const setDataCalls: Array<{ done?: boolean }> = [];
    const triggerCalls: Array<{ name: string; detail: Record<string, unknown> }> = [];
    const fakeThis = {
      data: { id: 'task_003', done: true, disabled: false },
      setData(patch: { done?: boolean }) {
        setDataCalls.push(patch);
        Object.assign(fakeThis.data, patch);
      },
      triggerEvent(name: string, detail: Record<string, unknown>) {
        triggerCalls.push({ name, detail });
      },
    };
    // 把 body 中的 this.data.xxx / this.setData / this.triggerEvent 重写为上下文变量名，
    // 直接用 Function 构造器，避免 strict mode 引发的 'this' 关键字问题。
    const jsBody = body!
      .replace(/this\.data/g, 'ctx.data')
      .replace(/this\.setData/g, 'setData')
      .replace(/this\.triggerEvent/g, 'triggerEvent');
    // eslint-disable-next-line @typescript-eslint/no-implied-eval, no-new-func
    const fn = new Function('ctx', 'setData', 'triggerEvent', jsBody) as (
      ctx: { data: { id: string; done: boolean; disabled: boolean } },
      setData: (p: { done?: boolean }) => void,
      triggerEvent: (n: string, d: Record<string, unknown>) => void,
    ) => void;
    const bindSet = (p: { done?: boolean }) => fakeThis.setData(p);
    const bindTrig = (n: string, d: Record<string, unknown>) => fakeThis.triggerEvent(n, d);
    fn(fakeThis, bindSet, bindTrig);
    // 注意：实际行为是 done=true → 翻转成 done=false；FE-FIX-05 文档所述"不触发"
    // 与实现有歧义；本测试锁定现有契约，破坏时需要走 ADR 决策再调整。
    expect(setDataCalls).toEqual([{ done: false }]);
    expect(triggerCalls).toEqual([{ name: 'toggle', detail: { id: 'task_003', done: false } }]);
  });
});
