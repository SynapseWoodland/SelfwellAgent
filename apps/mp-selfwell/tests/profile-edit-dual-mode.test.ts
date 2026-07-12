/**
 * PR-5 · profile-edit 双模扩展契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-unified-parent.md §2.5 + plans/v2-IA-pr-internal.md §PR-5
 *
 * 锁值 7 用例：
 *  1. mode 数据字段存在（'edit' | 'read'）
 *  2. onLoad 解析 query.mode → 默认 edit（向前兼容）
 *  3. read 模式调 GET /me/archive/summary
 *  4. read 模式调 wx.setNavigationBarTitle 切标题
 *  5. read 模式渲染 WXML 含 6 字段只读 + tag chip + 21 天小档案
 *  6. read 模式底部 [编辑] CTA → onTapEditMode → redirectTo ?mode=edit
 *  7. edit 模式不退：原 6 字段表单 + onSubmitProfile 保留
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readPage(file: string): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'profile-edit', file),
    'utf-8',
  );
}

describe('PR-5 · profile-edit 双模 (mode=edit | mode=read)', () => {
  it('用例 1: TS 声明 mode 数据字段 + ProfileEditMode 类型', () => {
    const ts = readPage('index.ts');
    expect(ts).toMatch(/type\s+ProfileEditMode\s*=\s*['"]edit['"]\s*\|\s*['"]read['"]/);
    expect(ts).toMatch(/mode\s*:\s*['"]edit['"]\s+as\s+ProfileEditMode/);
    // data 含 mode 字段
    expect(ts).toMatch(/mode\s*:\s*['"]edit['"]\s+as\s+ProfileEditMode/);
  });

  it('用例 2: onLoad 解析 query.mode → 默认 edit（向前兼容）', () => {
    const ts = readPage('index.ts');
    expect(ts).toMatch(/onLoad\s*\(\s*options\s*:\s*\{[^}]*mode\??\s*:\s*string/);
    // 三元表达式：options.mode === 'read' ? 'read' : 'edit'
    expect(ts).toMatch(/options\?\.mode\s*===\s*['"]read['"]\s*\?\s*['"]read['"]\s*:\s*['"]edit['"]/);
  });

  it('用例 3: read 模式调 GET /me/archive/summary（PR-2 契约兑现）', () => {
    const ts = readPage('index.ts');
    expect(ts).toContain("'/me/archive/summary'");
    expect(ts).toMatch(/get<ArchiveSummary>/);
    // 21 天小档案字段锁（与 backend archive_service 对齐）
    expect(ts).toContain('archiveSummary');
    expect(ts).toContain('archiveLoading');
    expect(ts).toContain('archiveError');
    // archive 字段
    expect(ts).toContain('current_day');
    expect(ts).toContain('total_days');
    expect(ts).toContain('stage');
    expect(ts).toContain('streak_days');
  });

  it('用例 4: read 模式 wx.setNavigationBarTitle 切标题为「档案概览」', () => {
    const ts = readPage('index.ts');
    expect(ts).toContain('wx.setNavigationBarTitle');
    expect(ts).toContain('档案概览');
  });

  it('用例 5: WXML read 模式块含 6 字段只读 + tag chip + 21 天小档案', () => {
    const wxml = readPage('index.wxml');
    // mode 条件分支
    expect(wxml).toMatch(/wx:if="\{\{mode === ['"]read['"]\}\}"/);
    expect(wxml).toMatch(/wx:elif|wx:else/);
    // 6 字段只读行
    expect(wxml).toContain('pe-read-row');
    expect(wxml).toContain('pe-read-label');
    expect(wxml).toContain('pe-read-value');
    // tag chip
    expect(wxml).toContain('pe-chip-selected');
    expect(wxml).toContain('archiveSummary.tags');
    // 21 天小档案
    expect(wxml).toContain('pe-read-archive-block');
    expect(wxml).toContain('pe-read-stat');
    // 编辑 CTA
    expect(wxml).toContain('pe-read-edit-cta');
  });

  it('用例 6: read 模式底部 [编辑] CTA 走 onTapEditMode → redirectTo ?mode=edit', () => {
    const ts = readPage('index.ts');
    expect(ts).toMatch(/onTapEditMode\s*\(\s*\)/);
    expect(ts).toContain('wx.redirectTo');
    expect(ts).toContain("'/pages/profile-edit/index?mode=edit'");
  });

  it('用例 7: edit 模式不退（原 PR5 行为保留：6 字段 + onSubmitProfile + submitting 锁）', () => {
    const ts = readPage('index.ts');
    // 原 6 字段表单保留
    expect(ts).toContain('onSelectAgeRange');
    expect(ts).toContain('onSelectIntensity');
    expect(ts).toContain('onSelectSkinType');
    // onSubmitProfile + submitting 锁保留
    expect(ts).toMatch(/async\s+onSubmitProfile\s*\(/);
    expect(ts).toContain('submitting');
    expect(ts).toContain("'/users/profile'");
    // 必填校验
    expect(ts).toContain('validateProfileRequiredFields');
    // WXML 含 6 字段 chip + 保存按钮
    const wxml = readPage('index.wxml');
    expect(wxml).toContain('保存档案');
    expect(wxml).toContain('onSubmitProfile');
    expect(wxml).toContain('profile-chip-selected');
  });
});