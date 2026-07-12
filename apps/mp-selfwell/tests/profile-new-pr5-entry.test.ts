/**
 * PR-5 · profile-new 5 跳转入口契约锁
 * ─────────────────────────────────────────────────────────────────
 * 真源：plans/v2-IA-pr-internal.md §PR-5 §入口
 *
 * 锁值 7 用例：
 *  1. settings 列表 6 项（profile / time / notification / privacy / support / about）
 *  2. 用户档案 → /pages/profile-edit/index?mode=read（向前兼容 PR-3 mode=read 默认）
 *  3. 我的时光 → /pages/album/index（PR-5 新建）
 *  4. 通知设置 → /pages/notification-settings/index
 *  5. 隐私政策 → /pages/privacy-policy/index
 *  6. 联系客服 → /pages/contact/index
 *  7. 关于自愈 → /pages/about/index
 *  8. (bonus) 5 个具名方法存在（onTapNotifications/Privacy/Contact/About/ArchiveAlbum）
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readProfileNewTs(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'profile-new', 'index.ts'),
    'utf-8',
  );
}

describe('PR-5 · profile-new 5 跳转入口（4 子页 + album）', () => {
  it('用例 1: settings 列表含 6 项（profile/time/notification/privacy/support/about）', () => {
    const ts = readProfileNewTs();
    for (const id of ['profile', 'time', 'notification', 'privacy', 'support', 'about']) {
      expect(ts, `settings[].id 缺少 ${id}`).toContain(`id: '${id}'`);
    }
  });

  it('用例 2: 用户档案 pagePath = /pages/profile-edit/index?mode=read（read 默认）', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/profile-edit/index?mode=read'");
  });

  it('用例 3: 我的时光 pagePath = /pages/album/index（PR-5 新建）', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/album/index'");
    // 旧 record-album 不能再用
    expect(ts).not.toContain("/pages/record-album/index'");
  });

  it('用例 4: 通知设置 pagePath = /pages/notification-settings/index', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/notification-settings/index'");
  });

  it('用例 5: 隐私政策 pagePath = /pages/privacy-policy/index', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/privacy-policy/index'");
  });

  it('用例 6: 联系客服 pagePath = /pages/contact/index', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/contact/index'");
  });

  it('用例 7: 关于自愈 pagePath = /pages/about/index', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/about/index'");
  });

  it('用例 8: 5 个具名跳转方法存在（PR-5 显式入口）', () => {
    const ts = readProfileNewTs();
    expect(ts).toMatch(/onTapNotifications\s*\(\s*\)/);
    expect(ts).toMatch(/onTapPrivacy\s*\(\s*\)/);
    expect(ts).toMatch(/onTapContact\s*\(\s*\)/);
    expect(ts).toMatch(/onTapAbout\s*\(\s*\)/);
    expect(ts).toMatch(/onTapArchiveAlbum\s*\(\s*\)/);
    // 所有方法走 wx.navigateTo（profile-new 是 tabBar）
    for (const name of ['onTapNotifications', 'onTapPrivacy', 'onTapContact', 'onTapAbout', 'onTapArchiveAlbum']) {
      const idx = ts.indexOf(name);
      const next = ts.indexOf('}', idx);
      const slice = ts.slice(idx, next);
      expect(slice, `${name} 必须调 wx.navigateTo`).toContain('wx.navigateTo');
    }
  });
});